import uuid
import asyncio
import os
import subprocess
from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import sys
import json

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 环境检测
is_docker = (
    os.path.exists('/.dockerenv') or 
    os.path.exists('/proc/1/cgroup') or 
    os.getenv("ENV_MOD") == "production"
)

from core.final_pipeline import run_scoring_and_export
from core.scoring import ScoringEngine, DEFAULT_CONFIG
# from deep_translator import GoogleTranslator

app = FastAPI(title="ProSourcing API")

# 解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 临时内存任务追踪 (包含进程对象以便取消)
tasks_db = {}
process_pool = {}
browser_launch_lock = asyncio.Lock()
top_category_stats_process = None


def _get_top_category_stats_script_path():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, "core", "fetch_top_category_stats.py"), project_root


def _start_top_category_stats_refresh():
    global top_category_stats_process

    if top_category_stats_process and top_category_stats_process.poll() is None:
        return False

    script_path, project_root = _get_top_category_stats_script_path()
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"Missing refresh script: {script_path}")

    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_path = os.path.join(logs_dir, "top_category_stats_refresh.log")
    log_file = open(log_path, "a", encoding="utf-8")

    top_category_stats_process = subprocess.Popen(
        [sys.executable, script_path],
        cwd=project_root,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    return True


def _get_task_valid_product_count(task):
    stats = task.get("category_stats") or {}
    if isinstance(stats, str):
        try:
            stats = json.loads(stats)
        except json.JSONDecodeError:
            stats = {}

    for key in ("valid_product_count", "valid_product_qty"):
        value = stats.get(key)
        if value is None:
            continue
        try:
            return int(float(str(value).replace(",", "").strip() or 0))
        except (TypeError, ValueError):
            continue

    return 0


def _normalize_category_code(category_id):
    raw = str(category_id or "").strip()
    if not raw:
        return ""
    return raw.zfill(5) if raw.isdigit() else raw


def _category_code_variants(category_id):
    raw = str(category_id or "").strip()
    if not raw:
        return []

    variants = []
    for candidate in (raw, raw.zfill(5) if raw.isdigit() else raw, raw.lstrip("0") or "0"):
        candidate = str(candidate).strip()
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants


def _sync_last_crawl_date(category_id, crawl_date=None):
    normalized_code = _normalize_category_code(category_id)
    if not normalized_code:
        return False

    from core.final_pipeline import supabase as sb

    crawl_date = str(crawl_date or datetime.now().date().isoformat())[:10]
    updated_at = datetime.now().isoformat()

    sb.table("category_last_crawl_dates").upsert(
        {
            "category_code": normalized_code,
            "last_crawl_date": crawl_date,
            "updated_at": updated_at,
        }
    ).execute()

    updated = False
    for candidate in _category_code_variants(category_id):
        try:
            res = (
                sb.table("algatop_categories_master")
                .update({"last_crawl_date": crawl_date})
                .eq("algatop_id", candidate)
                .execute()
            )
            if res.data:
                updated = True
                break
        except Exception:
            continue
    return updated


def _extract_category_aliases(category_value):
    aliases = set()
    if category_value is None:
        return aliases

    if isinstance(category_value, str):
        value = category_value.strip()
        if not value:
            return aliases
        aliases.add(value)
        if " (" in value and value.endswith(")"):
            main_part, _, tail = value.partition(" (")
            aliases.add(main_part.strip())
            aliases.add(tail[:-1].strip())
        return {alias for alias in aliases if alias}

    if isinstance(category_value, dict):
        for key in ("category_name", "name_ru", "name_cn", "category_cn", "name"):
            value = category_value.get(key)
            if isinstance(value, str) and value.strip():
                aliases.update(_extract_category_aliases(value))
        return aliases

    return aliases


def _contains_chinese(text):
    return any("\u4e00" <= ch <= "\u9fff" for ch in str(text or ""))


def _normalize_up_categories(up_categories):
    if not up_categories:
        return []

    if isinstance(up_categories, str):
        raw = up_categories.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            if parsed:
                return [parsed]
        except json.JSONDecodeError:
            return [raw]

    if isinstance(up_categories, list):
        return up_categories

    return [up_categories]


def _task_matches_top_category(task, top_category):
    target_aliases = _extract_category_aliases(top_category)
    if not target_aliases:
        return True

    task_path = _normalize_up_categories(task.get("up_categories")) or _resolve_task_up_categories(task)
    for item in task_path:
        if _extract_category_aliases(item) & target_aliases:
            return True

    return False


RUNNING_TASK_STATUSES = {"pending", "scraping", "crawling", "reporting", "processing", "retrying"}


def _expand_status_filters(status_filters):
    if not status_filters:
        return []

    if isinstance(status_filters, str):
        raw_filters = [status_filters]
    else:
        raw_filters = list(status_filters)

    expanded = []
    for item in raw_filters:
        normalized = (item or "").strip().lower()
        if not normalized or normalized == "all":
            continue
        if normalized == "pending":
            for running_status in RUNNING_TASK_STATUSES:
                if running_status not in expanded:
                    expanded.append(running_status)
            continue
        if normalized not in expanded:
            expanded.append(normalized)
    return expanded


@lru_cache(maxsize=1024)
def _get_category_master_row(category_id: str):
    if not category_id or not str(category_id).isdigit():
        return None

    from core.final_pipeline import supabase as sb

    res = (
        sb.table("algatop_categories_master")
        .select("algatop_id,parent_id,level,name_ru,name_cn")
        .eq("algatop_id", str(category_id))
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


@lru_cache(maxsize=1)
def _analysis_tasks_has_updated_at():
    from core.final_pipeline import supabase as sb

    try:
        res = (
            sb.table("information_schema.columns")
            .select("column_name")
            .eq("table_name", "analysis_tasks")
            .eq("column_name", "updated_at")
            .limit(1)
            .execute()
        )
        return bool(res.data)
    except Exception:
        return False


def _resolve_task_up_categories(task):
    normalized_existing = _normalize_up_categories(task.get("up_categories"))
    has_cn_label = any(
        (
            isinstance(item, dict)
            and any("\u4e00" <= ch <= "\u9fff" for ch in str(item.get("name_cn") or item.get("category_name") or ""))
        )
        or (isinstance(item, str) and any("\u4e00" <= ch <= "\u9fff" for ch in item))
        for item in normalized_existing
    )
    if normalized_existing and has_cn_label:
        return normalized_existing

    category_id = str(
        task.get("category_id")
        or (task.get("category_stats") or {}).get("category_id")
        or (task.get("category_stats") or {}).get("category_ext_id")
        or ""
    ).strip()
    if not category_id.isdigit():
        return normalized_existing if normalized_existing else []

    lineage = []
    current_id = category_id
    visited = set()

    while current_id and current_id not in visited:
        visited.add(current_id)
        row = _get_category_master_row(current_id)
        if not row:
            break

        lineage.append(
            {
                "category_id": str(row.get("algatop_id")),
                "category_name": row.get("name_cn") or row.get("name_ru") or "",
                "name_ru": row.get("name_ru") or "",
                "name_cn": row.get("name_cn") or "",
            }
        )

        parent_id = row.get("parent_id")
        if parent_id in (None, "", 0, "0"):
            break
        current_id = str(parent_id)

    lineage.reverse()
    return lineage


def _enrich_task_metadata(task):
    task_path = _resolve_task_up_categories(task)
    if task_path:
        task["up_categories"] = task_path
        top_category = task_path[0]
        task["top_category_label"] = top_category.get("name_cn") or top_category.get("category_name") or top_category.get("name_ru") or "一级分类"
    else:
        task["top_category_label"] = None
    raw_category = str(task.get("category") or "").strip()
    leaf_category = task_path[-1] if task_path else None
    leaf_name_cn = str((leaf_category or {}).get("name_cn") or (leaf_category or {}).get("category_name") or "").strip()
    if leaf_name_cn and (not raw_category or not _contains_chinese(raw_category)):
        task["category"] = leaf_name_cn

    return task


def _parse_task_timestamp(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _task_matches_days(task, days):
    if not days or days <= 0:
        return True
    created_at = _parse_task_timestamp(task.get("created_at"))
    if not created_at:
        return False
    return created_at >= (datetime.now(created_at.tzinfo) - timedelta(days=days))


def _task_matches_status_filters(task, expanded_statuses):
    if not expanded_statuses:
        return True
    return (task.get("status") or "").strip().lower() in expanded_statuses


def _build_initial_up_categories(category_id: str):
    seed_task = {"category_id": str(category_id or "").strip(), "up_categories": None}
    return _resolve_task_up_categories(seed_task)


def _build_task_insert_payload(category_id: str, display_title: str):
    now_iso = datetime.now().isoformat()
    initial_up_categories = _build_initial_up_categories(category_id)
    top_category = initial_up_categories[0] if initial_up_categories else None
    payload = {
        "category": display_title,
        "category_id": str(category_id),
        "status": "pending",
        "progress": 0,
        "created_at": now_iso,
        "top_category_id": str(top_category.get("category_id")) if top_category else None,
        "top_category_name_cn": top_category.get("name_cn") if top_category else None,
        "top_category_name_ru": top_category.get("name_ru") if top_category else None,
    }
    if _analysis_tasks_has_updated_at():
        payload["updated_at"] = now_iso
    if initial_up_categories:
        payload["up_categories"] = json.dumps(initial_up_categories, ensure_ascii=False)
    return payload


def _apply_top_category_overrides(payload, top_category_id=None, top_category_name_cn=None, top_category_name_ru=None):
    if top_category_id:
        payload["top_category_id"] = str(top_category_id)
    if top_category_name_cn:
        payload["top_category_name_cn"] = str(top_category_name_cn)
    if top_category_name_ru:
        payload["top_category_name_ru"] = str(top_category_name_ru)
    return payload

class TaskRequest(BaseModel):
    category: str
    top_category_id: Optional[str] = None
    top_category_name_cn: Optional[str] = None
    top_category_name_ru: Optional[str] = None

class TaskStatus(BaseModel):
    task_id: str
    category: str
    status: str  # pending, crawling, scoring, reporting, completed, failed
    progress: int
    result_url: Optional[str] = None
    error: Optional[str] = None
    duration: Optional[str] = None
    category_stats: Optional[dict] = None
    trend_data: Optional[list] = None
    up_categories: Optional[list] = None


class RecoverInterruptedTasksRequest(BaseModel):
    stale_minutes: int = 20
    limit: Optional[int] = None
    statuses: Optional[List[str]] = None
    dry_run: bool = False

# --- 系统管理模型 ---
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "analyst"

class SystemSettingsUpdate(BaseModel):
    value: dict

class LogCleanupRequest(BaseModel):
    days: Optional[int] = None
    date: Optional[str] = None # YYYY-MM-DD

@app.post("/api/tasks", response_model=TaskStatus)
def create_task(req: TaskRequest, background_tasks: BackgroundTasks):
    from core.final_pipeline import supabase as sb
    # 哥，先把中文名翻出来
    cat_name = req.category
    category_id = req.category
    res_master = sb.table("algatop_categories_master").select("algatop_id,name_cn").eq("name_ru", req.category).limit(1).execute()
    if res_master.data:
        category_id = str(res_master.data[0].get("algatop_id") or req.category)
        cat_name = res_master.data[0]['name_cn']
        
    task_data = _build_task_insert_payload(category_id, cat_name)
    task_data = _apply_top_category_overrides(
        task_data,
        req.top_category_id,
        req.top_category_name_cn,
        req.top_category_name_ru,
    )
    res = sb.table("analysis_tasks").insert(task_data).execute()
    db_task = res.data[0]
    task_id = db_task['id']
    task = TaskStatus(task_id=task_id, category=cat_name, status="pending", progress=0)
    tasks_db[task_id] = task
    background_tasks.add_task(execute_rpa_pipeline, task_id, req.category, cat_name)
    return task

@app.get("/api/tasks/history")
def get_task_history(page: int = 1, page_size: int = 20, q: Optional[str] = None, days: Optional[int] = None, status: Optional[List[str]] = Query(None), top_category: Optional[str] = None, hide_zero: bool = False):
    """获取历史任务记录，支持物理分页和搜索/时间筛选"""
    from core.final_pipeline import supabase as sb
    offset = (page - 1) * page_size
    
    # 哥，先构建基础查询
    query = sb.table("analysis_tasks")
    if q:
        query = query.ilike("category", f"%{q}%")
    
    if days and days > 0:
        after = datetime.now() - timedelta(days=days)
        # 兼容 ISO 格式
        query = query.gte("created_at", after.isoformat())
        
    expanded_statuses = _expand_status_filters(status)
    if len(expanded_statuses) == 1:
        query = query.eq("status", expanded_statuses[0])
    elif len(expanded_statuses) > 1:
        query = query.in_("status", expanded_statuses)

    if top_category and top_category != 'all':
        query = query.eq("top_category_name_cn", top_category)
        
    if False and top_category and top_category != 'all':
        # 通过 supabase jsonb 的包含查询过滤含有该大类名的节点
        query = query.contains("up_categories", [{"category_name": top_category}])
    
    # 1. 获取满足条件的精确总数
    if hide_zero:
        filtered = []
        fetch_offset = 0
        batch_size = 1000
        while True:
            all_res = query.select("*").order("created_at", desc=True).range(fetch_offset, fetch_offset + batch_size - 1).execute()
            batch = all_res.data or []
            for t in batch:
                if _get_task_valid_product_count(t) <= 0:
                    continue
                if not t.get('duration') and t['status'] == 'completed':
                    try:
                        t['duration'] = calculate_duration_from_logs(t['id'])
                    except: t['duration'] = "--"
                _enrich_task_metadata(t)
                filtered.append(t)
            if len(batch) < batch_size:
                break
            fetch_offset += batch_size

        total = len(filtered)
        return {"data": filtered[offset:offset + page_size], "total": total, "page": page, "page_size": page_size}

    count_res = query.select("*", count="exact").execute()
    total = count_res.count
    
    # 2. 获取当前分页的数据
    # 注意：select(count=None) 恢复正常查询模式
    res = query.select("*").order("created_at", desc=True).range(offset, offset + page_size - 1).execute()
    
    # 3. 补全兼容逻辑 (时长解析)
    data = res.data or []
    for t in data:
        if not t.get('duration') and t['status'] == 'completed':
            try:
                t['duration'] = calculate_duration_from_logs(t['id'])
            except: t['duration'] = "--"
        _enrich_task_metadata(t)
            
    return {"data": data, "total": total, "page": page, "page_size": page_size}

@app.get("/api/tasks")
def list_tasks(category: Optional[str] = None, status: Optional[str] = None):
    """获取任务列表，支持品类搜索和状态过滤"""
    from core.final_pipeline import supabase as sb
    query = sb.table("analysis_tasks").select("*")
    
    if category:
        query = query.ilike("category", f"%{category}%")
    if status:
        query = query.eq("status", status)
        
    res = query.order("created_at", desc=True).execute()
    data = res.data
    for t in data:
        if not t.get('duration') and t['status'] == 'completed':
            try:
                t['duration'] = calculate_duration_from_logs(t['id'])
            except: t['duration'] = "--"
        _enrich_task_metadata(t)
    return data

@app.get("/api/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str):
    from core.final_pipeline import supabase as sb
    res = sb.table("analysis_tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    t = res.data[0]
    
    duration = t.get('duration')
    if not duration and t['status'] == 'completed':
        try:
            duration = calculate_duration_from_logs(task_id)
        except: duration = "--"
    _enrich_task_metadata(t)

    return TaskStatus(
        task_id=t['id'],
        category=t['category'],
        status=t['status'],
        progress=t['progress'] or 0,
        result_url=t.get('excel_path'),
        error=t.get('error_msg'),
        duration=duration,
        category_stats=t.get('category_stats'),
        trend_data=t.get('trend_data'),
        up_categories=t.get('up_categories')
    )

def calculate_duration_from_logs(task_id: str):
    import re
    from datetime import datetime
    log_path = f"logs/{task_id}.log"
    if not os.path.exists(log_path): return None
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = [l for l in f.readlines() if l.strip()]
            if not lines: return None
            
            def extract_time(line):
                # 哥，针对类似 [2026-03-11T22:59:39.122943] 的格式做兼容
                m = re.search(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?)", line)
                if m:
                    try:
                        ts_str = m.group(1)
                        # 支持带微秒的解析
                        return datetime.fromisoformat(ts_str)
                    except: return None
                return None

            start = None
            for l in lines:
                start = extract_time(l)
                if start: break
                
            end = None
            for l in reversed(lines):
                end = extract_time(l)
                if end: break
                
            if start and end:
                diff = end - start
                seconds = max(0, int(diff.total_seconds()))
                if seconds < 60: return f"{seconds}s"
                m = seconds // 60
                s = seconds % 60
                return f"{m}m {s}s"
    except Exception as e:
        print(f"[DURATION ERROR] {e}")
    return None

@app.get("/api/tasks/{task_id}/data")
def get_task_data(task_id: str):
    from core.final_pipeline import supabase as sb
    from core.final_pipeline import ENV_MOD
    
    # 哥，如果是生产环境（本地 PG），兼容层做不了 Join，咱得手动拼装
    if ENV_MOD == "production":
        metrics_res = sb.table("products_calculated_metrics").select("*").eq("task_id", task_id).execute()
        raw_res = sb.table("products_raw_data").select("*").eq("task_id", task_id).execute()
        
        # 建立 SKU 索引，保证拼装速度起飞
        raw_map = {p['sku']: p for p in raw_res.data}
        
        joined_data = []
        for m in metrics_res.data:
            sku = m['sku']
            # 手动塞进嵌套对象，前端就认这个
            m['products_raw_data'] = raw_map.get(sku, {})
            joined_data.append(m)
            
        if not joined_data and raw_res.data:
            return [{"products_raw_data": p, "total_score": 0} for p in raw_res.data]
        return joined_data

    # 开发环境 (云端 Supabase) 保持原样
    res = sb.table("products_calculated_metrics").select("*, products_raw_data(*)").eq("task_id", task_id).execute()
    if res.data:
        return res.data
    raw_res = sb.table("products_raw_data").select("*").eq("task_id", task_id).execute()
    return [{"products_raw_data": p, "total_score": 0} for p in raw_res.data]

@app.get("/api/tasks/{task_id}/logs")
async def get_task_logs(task_id: str):
    log_path = f"logs/{task_id}.log"
    if not os.path.exists(log_path):
        return {"logs": "Logging initialized, waiting for output..."}
    try:
        # 使用 powershell 读取最后一部分，或者直接全量读取（如果日志不大）
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            return {"logs": f.read()}
    except Exception as e:
        return {"logs": f"Error reading logs: {str(e)}"}

def get_products():
    from core.final_pipeline import supabase as sb
    res = sb.table("products_calculated_metrics").select("*, products_raw_data(*)").order("total_score", desc=True).limit(50).execute()
    return res.data

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open(os.path.join(os.path.dirname(__file__), "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/system/logs/cleanup")
def cleanup_logs(days: int = 7):
    """清理 N 天前的任务日志 (保留兼容性)"""
    return clear_logs(LogCleanupRequest(days=days))

# --- 系统管理 API ---

@app.get("/api/system/users")
def list_system_users():
    from core.final_pipeline import supabase as sb
    res = sb.table("system_users").select("id, username, role, created_at").execute()
    return res.data

@app.post("/api/system/users")
def create_system_user(user: UserCreate):
    from core.final_pipeline import supabase as sb
    # 哥，这里简单处理，实际应加盐哈希
    payload = {
        "username": user.username,
        "password_hash": user.password,
        "role": user.role
    }
    res = sb.table("system_users").insert(payload).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to create user")
    return res.data[0]

@app.delete("/api/system/users/{user_id}")
def delete_system_user(user_id: str):
    from core.final_pipeline import supabase as sb
    sb.table("system_users").delete().eq("id", user_id).execute()
    return {"status": "success"}

@app.get("/api/system/settings/{key}")
def get_system_setting(key: str):
    from core.final_pipeline import supabase as sb
    try:
        res = sb.table("system_settings").select("*").eq("key", key).execute()
        if not res.data:
            # 如果不存在，返回默认值
            if key == "storage_config":
                return {"key": key, "value": {"path": "./output", "auto_cleanup_days": 15}}
            if key == "collection_config":
                return {"key": key, "value": {"algatop": {"username": "", "password": ""}}}
            raise HTTPException(status_code=404, detail="Setting not found")
        return res.data[0]
    except:
        # 兼容表不存在的情况
        if key == "storage_config":
            return {"key": key, "value": {"path": "./output", "auto_cleanup_days": 15}}
        if key == "collection_config":
            return {"key": key, "value": {"algatop": {"username": "", "password": ""}}}
        raise HTTPException(status_code=404, detail="Setting not found")

@app.post("/api/system/settings/{key}")
def update_system_setting(key: str, req: SystemSettingsUpdate):
    from core.final_pipeline import supabase as sb
    payload = {
        "key": key,
        "value": req.value,
        "updated_at": datetime.now().isoformat()
    }
    res = sb.table("system_settings").upsert(payload).execute()
    return res.data[0]

@app.get("/api/system/logs")
def list_logs():
    """获取所有日志文件及其日期属性"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        return []
    
    logs = []
    for filename in os.listdir(log_dir):
        if filename.endswith(".log"):
            path = os.path.join(log_dir, filename)
            stat = os.stat(path)
            logs.append({
                "filename": filename,
                "size": stat.st_size,
                "date": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d"),
                "mtime": stat.st_mtime
            })
    logs.sort(key=lambda x: x['mtime'], reverse=True)
    return logs

@app.post("/api/system/logs/clear")
def clear_logs(req: LogCleanupRequest):
    """灵活清理日志：按天数、按日期、或全部"""
    import time
    log_dir = "logs"
    if not os.path.exists(log_dir):
        return {"count": 0}
        
    count = 0
    now = time.time()
    
    for filename in os.listdir(log_dir):
        if not filename.endswith(".log"): continue
        file_path = os.path.join(log_dir, filename)
        mtime = os.path.getmtime(file_path)
        
        should_delete = False
        
        # 情况 1: 按天数 (如 15 天前)
        if req.days is not None:
            cutoff = now - (req.days * 86400)
            if mtime < cutoff:
                should_delete = True
        
        # 情况 2: 按特定日期 (YYYY-MM-DD)
        elif req.date is not None:
            file_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
            if file_date == req.date:
                should_delete = True
                
        # 情况 3: 全部清除 (days=0)
        elif req.days == 0:
            should_delete = True

        if should_delete:
            try:
                os.remove(file_path)
                count += 1
            except: pass
                
    return {"count": count, "message": f"Successfully cleared {count} logs"}

@app.get("/api/download")
async def download_file(path: str):
    if os.path.exists(path):
        return FileResponse(path, filename=os.path.basename(path))
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    if task_id in process_pool:
        import subprocess
        p = process_pool[task_id]
        try:
            # 暴力清理该进程及其所有子进程 (包括 chromium)
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            # 同步更新内存和数据库
            if task_id in tasks_db:
                tasks_db[task_id].status = "cancelled"
                tasks_db[task_id].progress = 0
            
            from core.final_pipeline import supabase as sb
            sb.table("analysis_tasks").update({"status": "cancelled", "progress": 0}).eq("id", task_id).execute()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    raise HTTPException(status_code=404, detail="Task not active")

@app.get("/api/categories/top_stats")
def get_top_categories():
    """获取大类大盘数据 - 改为普通 def 线程模式"""
    from core.final_pipeline import supabase as sb
    master_res = sb.table("algatop_categories_master").select("*").eq("level", 1).execute()
    cids = [str(m['algatop_id']) for m in master_res.data]
    stats_map = {}
    if cids:
        stats_res = sb.table("algatop_top_category_stats").select("*").in_("algatop_id", cids).execute()
        stats_map = {str(s['algatop_id']): s for s in stats_res.data}
    mapped = []
    for m in master_res.data:
        cid = str(m['algatop_id'])
        s = stats_map.get(cid, {})
        ru_name = m.get("name_ru") or ""
        cn_name = m.get("name_cn") or ""
        display_name = f"{ru_name} ({cn_name})" if cn_name else ru_name
        sales = s.get("sales_qty") or 0
        products = s.get("product_count") or 0
        ratio = (sales / products) if products > 0 else 0
        mapped.append({
            "id": cid, "category_id": cid, "name": display_name, "category_name": display_name,
            "name_ru": ru_name, "name_cn": cn_name,
            "is_top_level": True, "sales_to_product_ratio": ratio, "monthly_sales": sales,
            "sale_product_qty": products, "revenue": s.get("revenue") or 0,
            "seller_count": s.get("seller_count") or 0, "brand_count": s.get("brand_count") or 0
        })
    mapped.sort(key=lambda x: x['monthly_sales'], reverse=True)
    return mapped


@app.post("/api/categories/top_stats/refresh")
def refresh_top_category_stats():
    global top_category_stats_process

    if top_category_stats_process and top_category_stats_process.poll() is None:
        return {"success": False, "message": "21个大类数据更新任务正在执行中"}

    try:
        started = _start_top_category_stats_refresh()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"启动21个大类数据更新失败: {exc}")

    if not started:
        return {"success": False, "message": "21个大类数据更新任务正在执行中"}

    return {"success": True, "message": "已开始后台获取更新21大类数据"}

@app.get("/api/system/health")
def system_health():
    """系统健康检查：Chrome, Database, Disk"""
    import socket
    import os
    from core.final_pipeline import supabase as sb
    
    # 1. 检查数据库连接
    db_status = "healthy"
    db_error = None
    try:
        sb.table("analysis_tasks").select("id").limit(1).execute()
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)
        
    # 2. 检查 Chrome RPA 端口
    chrome_status = "closed"
    # 哥，针对容器环境探测宿主机端口，非容器探测本地
    target = os.getenv("CHROME_REMOTE_DEBUG_ADDR", "host.docker.internal:9222").split(":")[0] if is_docker else "127.0.0.1"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            if s.connect_ex((target, 9222)) == 0:
                chrome_status = "open"
    except: pass
    
    # 3. 检查存储目录
    storage = {
        "output": os.path.exists("output"),
        "logs": os.path.exists("logs"),
        "templates": os.path.exists("templates")
    }
    
    return {
        "status": "ok" if db_status == "healthy" else "error",
        "database": {"status": db_status, "error": db_error},
        "chrome": {"status": chrome_status, "port": 9222, "target": target},
        "storage": storage,
        "environment": "docker" if is_docker else "local",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/categories/tree")
def get_category_tree():
    """复用 top_stats 的逻辑以获取带计数的树根 - 线程模式"""
    return get_top_categories()

@app.post("/api/tasks/{task_id}/retry", response_model=TaskStatus)
def retry_task(task_id: str, background_tasks: BackgroundTasks):
    """重试失败的任务，接通前端点击"""
    from core.final_pipeline import supabase as sb
    res = sb.table("analysis_tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    t = res.data[0]
    
    # 哥，针对防重试连点（幂等性）的增强：如果已经在队列或执行中，直接拦截
    if t.get("status") in ["pending", "scraping", "crawling", "reporting", "processing"]:
        return TaskStatus(task_id=task_id, category=t['category'], status=t['status'], progress=t['progress'] or 0)

    # 哥，针对防重试连点（幂等性）的增强：如果已经在队列或执行中，直接拦截
    if t.get("status") in ["pending", "scraping", "crawling", "reporting", "processing"]:
        return TaskStatus(task_id=task_id, category=t['category'], status=t['status'], progress=t['progress'] or 0)

    # 强制重置状态和进度
    payload = {
        "status": "pending", 
        "progress": 0, 
        "error_msg": None, 
        "excel_path": None
    }
    if _analysis_tasks_has_updated_at():
        payload["updated_at"] = datetime.now().isoformat()
    sb.table("analysis_tasks").update(payload).eq("id", task_id).execute()
    
    # 获取原始类别ID，如果是空则用名称兜底
    cat_id = t.get("category_id") or t.get("category")
    
    background_tasks.add_task(execute_rpa_pipeline, task_id, cat_id, t.get("category"))
    return TaskStatus(task_id=task_id, category=t['category'], status="pending", progress=0)


@app.post("/api/tasks/recover-interrupted")
def recover_interrupted_tasks(req: RecoverInterruptedTasksRequest, background_tasks: BackgroundTasks):
    """Recover stale in-flight tasks after a restart by re-enqueueing them."""
    from core.final_pipeline import supabase as sb

    candidate_statuses = req.statuses or ["pending", "scraping", "crawling", "reporting", "processing", "retrying"]
    normalized_statuses = []
    for status in candidate_statuses:
        normalized = (status or "").strip().lower()
        if normalized and normalized not in normalized_statuses:
            normalized_statuses.append(normalized)

    if not normalized_statuses:
        return {"success": False, "message": "No valid statuses provided", "count": 0, "tasks": []}

    stale_minutes = max(int(req.stale_minutes or 0), 1)
    stale_before = datetime.now() - timedelta(minutes=stale_minutes)
    res = (
        sb.table("analysis_tasks")
        .select("*")
        .in_("status", normalized_statuses)
        .order("created_at", desc=False)
        .execute()
    )

    matched = []
    for task in res.data or []:
        activity_time = _parse_task_timestamp(task.get("updated_at")) or _parse_task_timestamp(task.get("created_at"))
        if activity_time and activity_time > stale_before:
            continue
        matched.append(task)

    matched.sort(
        key=lambda task: (
            _parse_task_timestamp(task.get("updated_at")) or _parse_task_timestamp(task.get("created_at")) or datetime.min
        )
    )

    if req.limit and req.limit > 0:
        matched = matched[: req.limit]

    preview = [
        {
            "id": task.get("id"),
            "category": task.get("category"),
            "category_id": task.get("category_id"),
            "status": task.get("status"),
            "updated_at": task.get("updated_at"),
            "created_at": task.get("created_at"),
        }
        for task in matched
    ]

    if req.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "count": len(preview),
            "stale_before": stale_before.isoformat(),
            "tasks": preview,
        }

    requeued = []
    for task in matched:
        payload = {
            "status": "pending",
            "progress": 0,
            "error_msg": None,
            "excel_path": None,
        }
        if _analysis_tasks_has_updated_at():
            payload["updated_at"] = datetime.now().isoformat()

        sb.table("analysis_tasks").update(payload).eq("id", task["id"]).execute()
        background_tasks.add_task(
            execute_rpa_pipeline,
            task["id"],
            task.get("category_id") or task.get("category"),
            task.get("category") or str(task.get("category_id") or task["id"]),
        )
        requeued.append(task["id"])

    return {
        "success": True,
        "dry_run": False,
        "count": len(requeued),
        "stale_before": stale_before.isoformat(),
        "task_ids": requeued,
        "tasks": preview,
    }


@app.post("/api/tasks/category", response_model=TaskStatus)
def create_category_task(req: TaskRequest, background_tasks: BackgroundTasks):
    """强制根据品类数字 ID 发起选品分析任务 - 改为线程模式"""
    from core.final_pipeline import supabase as sb
    category_id = req.category
    display_title = category_id
    
    # 哥，针对防重复抓取的检测：15天同类目拦截
    recent_limit = (datetime.now() - timedelta(days=15)).isoformat()
    recent = sb.table("analysis_tasks").select("id").eq("category_id", str(category_id)).eq("status", "completed").gte("created_at", recent_limit).limit(1).execute()
    if recent.data:
        # 如果已经有了，不创建任务，直接返回一个已完成的 Task 占位
        if str(category_id).isdigit():
            res_master = sb.table("algatop_categories_master").select("name_cn").eq("algatop_id", str(category_id)).limit(1).execute()
            if res_master.data and res_master.data[0]['name_cn']:
                display_title = res_master.data[0]['name_cn']
        return TaskStatus(
            task_id=recent.data[0]['id'],
            category=display_title,
            status="completed",
            progress=100
        )
    
    # 如果是数字 ID，直接去主表查中文名存库
    if str(category_id).isdigit():
        res_master = sb.table("algatop_categories_master").select("name_cn").eq("algatop_id", str(category_id)).limit(1).execute()
        if res_master.data and res_master.data[0]['name_cn']:
            display_title = res_master.data[0]['name_cn']

    task_data = _build_task_insert_payload(category_id, display_title)
    task_data = _apply_top_category_overrides(
        task_data,
        req.top_category_id,
        req.top_category_name_cn,
        req.top_category_name_ru,
    )
    res = sb.table("analysis_tasks").insert(task_data).execute()
    db_task = res.data[0]
    task_id = db_task['id']
    background_tasks.add_task(execute_rpa_pipeline, task_id, category_id, display_title)
    return TaskStatus(task_id=task_id, category=display_title, status="pending", progress=0)

async def execute_rpa_pipeline(task_id: str, category_id: str, category_name: str):
    """RPA 静默执行流程：改为 async def，支持多任务并发不阻塞"""
    from core.final_pipeline import supabase as sb
    import asyncio
    import sys
    import os
    from datetime import datetime
    
    async def is_port_in_use_async(port):
        target = os.getenv("CHROME_REMOTE_DEBUG_ADDR", "host.docker.internal:9222").split(":")[0] if is_docker else "127.0.0.1"
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(target, port), timeout=2.0)
            writer.close()
            await writer.wait_closed()
            return True
        except:
            return False

    async def launch_browser_async():
        chrome_path = os.getenv("CHROME_PATH")
        if not chrome_path or not os.path.exists(chrome_path):
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.join(os.environ.get('LocalAppData', 'C:\\Users\\Default\\AppData\\Local'), r"Google\Chrome\Application\chrome.exe"),
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    chrome_path = p
                    break
        
        if is_docker or not chrome_path or not os.path.exists(chrome_path):
            return None

        port = 9222
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_data_dir = os.path.join(current_dir, "tmp", "chrome_rpa_profile")
        os.makedirs(user_data_dir, exist_ok=True)
            
        cmd = [
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        import subprocess
        return subprocess.Popen(cmd)

    async def update_db_async(p, s, url=None, err=None, duration=None):
        payload = {"progress": p, "status": s}
        if url: payload["excel_path"] = url
        if err: payload["error_msg"] = err
        if duration: payload["duration"] = duration
        if _analysis_tasks_has_updated_at():
            payload["updated_at"] = datetime.now().isoformat()
        await asyncio.to_thread(sb.table("analysis_tasks").update(payload).eq("id", task_id).execute)

    async def write_log(f, msg):
        timestamp = datetime.now().isoformat()
        await asyncio.to_thread(f.write, f"[{timestamp}] {msg}\n")
        await asyncio.to_thread(f.flush)

    log_file = None
    try:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{task_id}.log")
        log_file = await asyncio.to_thread(open, log_path, "a", encoding="utf-8")

        await update_db_async(10, "crawling")
        await write_log(log_file, f"--- Starting RPA Pipeline for category: {category_name} ---")
        
        # 哥，针对 Chrome 启动加个异步锁，防止任务 1 和任务 2 同时去 Popen 导致 Profile 锁死
        async with browser_launch_lock:
            if not await is_port_in_use_async(9222):
                await write_log(log_file, "Detecting Chrome Debug port 9222... Not Found. Attempting to launch...")
                await launch_browser_async()
                # 给 Chrome 一点点呼吸时间
                await asyncio.sleep(5)
            else:
                await write_log(log_file, "Chrome Debug port 9222 is ALREADY active. Joining existing session.")
        
        rpa_output_path = os.path.abspath(f"output/rpa_output_{task_id}.json")
        os.makedirs(os.path.dirname(rpa_output_path), exist_ok=True)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        # 哥，优先从系统设置里拿账号，这样 UI 上改完就能直接生效
        try:
            settings_res = await asyncio.to_thread(sb.table("system_settings").select("*").eq("key", "collection_config").execute)
            if settings_res.data:
                config = settings_res.data[0].get("value", {})
                algatop_config = config.get("algatop", {})
                if algatop_config.get("username"):
                    env["ALGATOP_USER"] = algatop_config.get("username")
                if algatop_config.get("password"):
                    env["ALGATOP_PASS"] = algatop_config.get("password")
        except: pass
        
        # 核心：使用 asyncio.create_subprocess_exec 启动爬虫，不阻塞事件循环
        process = await asyncio.create_subprocess_exec(
            sys.executable, "core/algatop_rpa_scraper.py", category_id, task_id,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env=env,
            stdout=log_file,
            stderr=log_file
        )
        process_pool[task_id] = process
        await write_log(log_file, f"[PROCESS] Crawler process started (PID: {process.pid})")
        
        # 轮询直至完成
        while process.returncode is None:
            await asyncio.sleep(10)
            res = await asyncio.to_thread(sb.table("analysis_tasks").select("status").eq("id", task_id).execute)
            if res.data and res.data[0]['status'] == 'crawling':
                await update_db_async(30, "crawling")
            if process.returncode is not None: break

        if process.returncode != 0:
            await write_log(log_file, f"Scraper failed with exit code {process.returncode}")
            await update_db_async(0, "failed", err="Scraper failed. Check logs for details.")
            return

        await update_db_async(80, "reporting")
        await write_log(log_file, "--- Scraper finished, starting reporting pipeline ---")
        
        report_process = await asyncio.create_subprocess_exec(
            sys.executable, "core/rpa_final_pipeline.py", task_id, rpa_output_path,
            stdout=log_file,
            stderr=log_file
        )
        await report_process.wait()

        if report_process.returncode != 0:
            await update_db_async(0, "failed", err="Reporting pipeline failed.")
            return
        
        duration_str = "--"
        try:
            duration_str = await asyncio.to_thread(calculate_duration_from_logs, task_id)
        except: pass
        
        await update_db_async(100, "completed", duration=duration_str)
        try:
            await asyncio.to_thread(_sync_last_crawl_date, category_id)
        except Exception as sync_err:
            await write_log(log_file, f"[LAST_CRAWL_DATE WARN] {sync_err}")
        await write_log(log_file, f"--- Pipeline COMPLETED successfully (Duration: {duration_str}) ---")

    except Exception as e:
        import traceback
        if log_file:
            await write_log(log_file, f"[FATAL ERROR] {str(e)}\n{traceback.format_exc()}")
        await update_db_async(0, "failed", err=str(e))
    finally:
        if log_file:
            await asyncio.to_thread(log_file.close)


@app.get("/api/market/global_stats")
def get_global_stats():
    """获取顶部四卡片统计数据 - 线程模式响应"""
    from core.final_pipeline import supabase as sb
    res1 = sb.table("categories").select("category_id", count="exact").eq("is_top_level", True).limit(1).execute()
    top_cat = res1.count if res1.count is not None else 21
    res2 = sb.table("categories").select("category_id", count="exact").eq("is_leaf", True).limit(1).execute()
    min_cat = res2.count if res2.count is not None else 0
    res3 = sb.table("analysis_tasks").select("id", count="exact").eq("status", "completed").limit(1).execute()
    reports = res3.count if res3.count is not None else 0
    res4 = sb.table("products_raw_data").select("sku", count="exact").limit(1).execute()
    skus = res4.count if res4.count is not None else 0
    sku_display = f"{skus / 1000:.1f}K" if skus > 1000 else str(skus)
    # 哥，获取大盘最后同步时间 (取各品类统计中最晚的更新日期)
    res_last = sb.table("algatop_top_category_stats").select("updated_at").order("updated_at", desc=True).limit(1).execute()
    last_val = res_last.data[0]['updated_at'] if res_last.data else datetime.now().isoformat()

    return {
        "top_cat_count": top_cat, "min_cat_count": min_cat,
        "sku_count": sku_display, "report_count": reports,
        "last_updated": last_val
    }

@app.get('/api/kaspi/tree')
def get_kaspi_global_tree():
    """Build full kaspi tree from categories table and attach last_crawl_date."""
    from core.final_pipeline import supabase as sb
    try:
        all_cats = []
        page_size = 1000
        for i in range(20):
            res = (
                sb.table("categories")
                .select("*")
                .range(i * page_size, (i + 1) * page_size - 1)
                .execute()
            )
            rows = res.data or []
            if not rows:
                break
            all_cats.extend(rows)
            if len(rows) < page_size:
                break
        if not all_cats:
            return []

        leaf_ids = {
            _normalize_category_code(c.get("category_id"))
            for c in all_cats
            if c.get("is_leaf")
        }
        leaf_ids = {code for code in leaf_ids if code}

        date_map = {}
        try:
            res_cache = (
                sb.table("category_last_crawl_dates")
                .select("category_code,last_crawl_date")
                .execute()
            )
            for row in (res_cache.data or []):
                code_raw = str(row.get("category_code") or "").strip()
                dt = str(row.get("last_crawl_date") or "").strip()
                if not code_raw or not dt:
                    continue
                code = code_raw.zfill(5) if code_raw.isdigit() else code_raw
                if code in leaf_ids:
                    date_map[code] = dt[:10]
        except Exception as e_cache:
            print(f"[TREE DATE CACHE ERROR] {e_cache}")

        # Fallback: recent completed tasks should still surface a date even if the cache table
        # was not refreshed during a restart or partial deploy.
        missing_leaf_ids = [code for code in leaf_ids if code not in date_map]
        if missing_leaf_ids:
            try:
                lookup_codes = sorted(
                    {
                        candidate
                        for code in missing_leaf_ids
                        for candidate in _category_code_variants(code)
                    }
                )
                res_tasks = (
                    sb.table("analysis_tasks")
                    .select("category_id,updated_at,created_at")
                    .eq("status", "completed")
                    .in_("category_id", lookup_codes)
                    .order("updated_at", desc=True)
                    .execute()
                )
                for row in (res_tasks.data or []):
                    code_raw = _normalize_category_code(row.get("category_id"))
                    dt = str(row.get("updated_at") or row.get("created_at") or "").strip()
                    if not code_raw or not dt:
                        continue
                    if code_raw in leaf_ids and code_raw not in date_map:
                        date_map[code_raw] = dt[:10]
            except Exception as e_tasks:
                print(f"[TREE DATE TASK FALLBACK ERROR] {e_tasks}")

        # 哥，建立一个 category_id -> algatop_id 的映射，确保树结构的 ID 全是数字
        id_to_aid = {str(c.get("category_id") or "").strip(): str(c.get("algatop_id") or "").strip() for c in all_cats}

        p_map = {}
        for c in all_cats:
            raw_pid = c.get("parent_category_id")
            pid_code = str(raw_pid) if raw_pid and str(raw_pid).lower() != "none" else ""
            
            orig_code = str(c.get("category_id") or "").strip()
            
            # 优先使用 algatop_id (数字 ID)，如果没用再用 category_id 兜底
            aid = id_to_aid.get(orig_code) or orig_code
            paid = id_to_aid.get(pid_code) or pid_code
            
            normalized_code = _normalize_category_code(aid)
            node = {
                "category_code": aid,
                "title": c.get("name_cn") or c.get("name_ru") or aid,
                "parent_code": paid,
                "is_leaf": bool(c.get("is_leaf", False)),
                "last_crawl_date": date_map.get(normalized_code),
            }
            p_map.setdefault(paid, []).append(node)

        def build_tree(pid=""):
            # 哥，这里 pid 也要映射一下
            children = p_map.get(pid, [])
            for child in children:
                child["children"] = build_tree(child["category_code"])
            return children

        return build_tree("")
    except Exception as e:
        print(f"[TREE API ERROR] {str(e)}")
        return []

@app.post('/api/kaspi/tasks/batch')
def create_kaspi_tasks_batch(items = Body(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    from core.final_pipeline import supabase as sb

    normalized_items = []
    for item in items or []:
        if isinstance(item, dict):
            code = str(item.get("category_code") or item.get("category_id") or "").strip()
            if not code:
                continue
            normalized_items.append(
                {
                    "category_code": code,
                    "top_category_id": str(item.get("top_category_id") or "").strip() or None,
                    "top_category_name_cn": str(item.get("top_category_name_cn") or "").strip() or None,
                    "top_category_name_ru": str(item.get("top_category_name_ru") or "").strip() or None,
                }
            )
        else:
            code = str(item).strip()
            if not code:
                continue
            normalized_items.append(
                {
                    "category_code": code,
                    "top_category_id": None,
                    "top_category_name_cn": None,
                    "top_category_name_ru": None,
                }
            )

    requested_codes = [item["category_code"] for item in normalized_items]
    total_requested = len(requested_codes)
    if total_requested == 0:
        return {
            'success': False,
            'message': 'No valid category codes provided',
            'count': 0,
            'total_requested': 0,
            'filtered_duplicate': 0,
            'actual_executed': 0
        }

    def norm_code(v: str) -> str:
        s = str(v).strip().lstrip('0')
        return s if s else '0'

    dedup_map = {}
    for item in normalized_items:
        dedup_map.setdefault(norm_code(item["category_code"]), item)
    dedup_requested_items = list(dedup_map.values())
    dedup_requested_codes = [item["category_code"] for item in dedup_requested_items]
    
    # 哥，先把这些 ID 的中文名全副武装好，优先去 master 主表拿最正宗的翻译
    res_master = sb.table('algatop_categories_master').select('algatop_id, name_cn, name_ru').in_('algatop_id', dedup_requested_codes).execute()
    
    code_map = {}
    # 先用 master 表的数据填充
    for row in res_master.data:
        algatop_id = str(row['algatop_id'])
        # 只要有中文名就用中文名，没有才用俄文
        cn_name = row.get('name_cn')
        # 如果 name_cn 还是俄文，或者是空，就先拿 name_ru 兜底
        code_map[algatop_id] = cn_name if cn_name and not any(u'\u0400' <= c <= u'\u04FF' for c in cn_name) else (row.get('name_ru') or algatop_id)

    # 如果 master 里没找全，再去 global_category_dict 碰碰运气
    missing_codes = [c for c in dedup_requested_codes if c not in code_map]
    if missing_codes:
        try:
            res_dict = sb.table('global_category_dict').select('*').in_('algatop_id', missing_codes).execute()
            for row in res_dict.data:
                aid = str(row['algatop_id'])
                kid = str(row['kaspi_id'])
                name = row.get('name_cn')
                if not name or any(u'\u0400' <= c <= u'\u04FF' for c in name):
                    name = row.get('name_ru') or row.get('name_en') or aid
                code_map[aid] = name
                code_map[kid] = name
        except Exception as e:
            print(f"[BATCH FALLBACK WARN] global_category_dict unavailable: {e}")

    try:
        # 哥，15天同类目拦截过滤！防止重复发起资源浪费
        recent_limit = (datetime.now() - timedelta(days=15)).isoformat()
        lookup_codes = sorted({
            v
            for c in dedup_requested_codes
            for v in (str(c), str(c).zfill(5), norm_code(c))
        })
        
        blocked_norm_ids = set()
        if lookup_codes:
            # 哥，分批查重，防止 SQL 过长报 500
            chunk_size = 200
            for i in range(0, len(lookup_codes), chunk_size):
                chunk = lookup_codes[i : i + chunk_size]
                try:
                    recent = (
                        sb.table("analysis_tasks")
                        .select("category_id,status,created_at")
                        .in_("category_id", chunk)
                        .execute()
                    )
                    for r in (recent.data or []):
                        cid = r.get("category_id")
                        if not cid: continue
                        cid_norm = norm_code(cid)
                        st = (r.get("status") or "").lower()
                        created_at = r.get("created_at") or ""
                        if st in {"pending", "running", "crawling", "reporting", "processing", "retrying"}:
                            blocked_norm_ids.add(cid_norm)
                            continue
                        if st == "completed" and created_at >= recent_limit:
                            blocked_norm_ids.add(cid_norm)
                except Exception as e_chunk:
                    print(f"[BATCH CHECK WARN] Chunk failed: {e_chunk}")

        filtered_items = [item for item in dedup_requested_items if norm_code(item["category_code"]) not in blocked_norm_ids]
        filtered_count = total_requested - len(filtered_items)

        payload = []
        for item in filtered_items:
            code = item["category_code"]
            display_name = code_map.get(str(code), str(code))
            payload_item = _build_task_insert_payload(str(code), display_name)
            payload.append(
                _apply_top_category_overrides(
                    payload_item,
                    item.get("top_category_id"),
                    item.get("top_category_name_cn"),
                    item.get("top_category_name_ru"),
                )
            )
        
        if payload:
            inserted = sb.table('analysis_tasks').insert(payload).execute()
            for task in inserted.data:
                background_tasks.add_task(execute_rpa_pipeline, task['id'], task['category_id'], task['category'])
            actual_count = len(inserted.data)
        else:
            actual_count = 0
            
        return {
            'success': True,
            'count': actual_count,
            'total_requested': total_requested,
            'filtered_duplicate': filtered_count,
            'actual_executed': actual_count
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}

# --- 算法配置相关接口 (哥，这是你要的轻量化方案) ---

@app.get("/api/algo/config")
def get_algo_config():
    """获取当前评分算法配置"""
    return ScoringEngine.get_config()

@app.post("/api/algo/config")
def save_algo_config(config: dict):
    """保存并实时同步算法配置"""
    from core.final_pipeline import supabase as sb
    # 1. 更新内存缓存 (立刻生效)
    ScoringEngine.update_config(config)
    # 2. 异步/简单存入数据库覆盖 (持久化)
    try:
        # 我们用一个固定 ID=1 的记录来存全量配置
        sb.table("algorithm_settings").upsert({
            "id": 1,
            "config_json": config,
            "updated_at": datetime.now().isoformat()
        }).execute()
        return {"status": "success", "message": "配置已保存并实时生效"}
    except Exception as e:
        print(f"[CONFIG SAVE ERROR] {e}")
        # 如果数据库还没建，这里可能会报错，但不影响内存生效
        return {"status": "success", "message": "内存配置已更新，但数据库同步暂不可用 (请检查表结构)"}

@app.post("/api/algo/reset")
def reset_algo_config():
    """重置为代码硬编码的默认配置"""
    from core.final_pipeline import supabase as sb
    ScoringEngine.update_config(DEFAULT_CONFIG)
    try:
        sb.table("algorithm_settings").delete().eq("id", 1).execute()
    except: pass
    return {"status": "success", "message": "已恢复默认配置"}

def seed_database_on_startup():
    """如果数据库为空，自动从 JSON 种子文件加载数据 (哥，增加了 30s 自动重试)"""
    from core.final_pipeline import supabase as sb
    import time
    import json
    
    max_retries = 10
    retry_delay = 3
    
    for attempt in range(max_retries):
        try:
            # 1. 检查 Master 表是否为空 (顺便测试连接)
            res = sb.table("algatop_categories_master").select("algatop_id").limit(1).execute()
            
            if not res.data:
                # 哥，路径适配容器环境，优先找 app/scripts
                seed_file = "scripts/full_category_data.json"
                if not os.path.exists(seed_file):
                    seed_file = "/app/scripts/full_category_data.json"
                
                if os.path.exists(seed_file):
                    print(f"[SEED] Database empty. Seeding from {seed_file}...")
                    with open(seed_file, "r", encoding="utf-8-sig") as f:
                        data = json.load(f)
                        
                    # 批量导入 Master (分批以防太大)
                    master_list = data.get('master', [])
                    for i in range(0, len(master_list), 500):
                        batch = master_list[i:i+500]
                        sb.table("algatop_categories_master").insert(batch).execute()
                    
                    # 批量导入 Stats
                    stats_list = data.get('stats', [])
                    for i in range(0, len(stats_list), 500):
                        batch = stats_list[i:i+500]
                        sb.table("algatop_top_category_stats").insert(batch).execute()
                    
                    print(f"✅ Successfully seeded {len(master_list)} categories and {len(stats_list)} stats.")

            # 2. 检查兼容表 categories 是否有数据
            res_compat = sb.table("categories").select("category_id").limit(1).execute()
            if not res_compat.data:
                print("[SEED] Categories table is empty. Syncing from Master...")
                all_master = []
                for i in range(10): # 最多 10000 条
                    res_m = sb.table("algatop_categories_master").select("*").range(i*1000, (i+1)*1000-1).execute()
                    if not res_m.data: break
                    all_master.extend(res_m.data)
                
                if all_master:
                    compat_payload = []
                    for m in all_master:
                        ru = m.get('name_ru') or ""
                        cn = m.get('name_cn') or ""
                        display = f"{ru} ({cn})" if cn else ru
                        compat_payload.append({
                            "category_id": m['algatop_id'],
                            "category_name": display,
                            "monthly_sales": m.get("monthly_sales") or 0,
                            "parent_category_id": m.get("parent_id"),
                            "is_top_level": m.get("level") == 1
                        })
                    
                    for i in range(0, len(compat_payload), 500):
                        sb.table("categories").insert(compat_payload[i:i+500]).execute()
                    print(f"✅ Successfully synced {len(compat_payload)} records to categories.")
            
            break 

        except Exception as e:
            err_msg = str(e).lower()
            if "starting up" in err_msg or "connection" in err_msg:
                print(f"[RETRY] Database is starting up... Waiting {retry_delay}s (Attempt {attempt+1}/{max_retries})")
                time.sleep(retry_delay)
            else:
                print(f"❌ Seeding error: {e}")
                break

def load_config_on_startup():
    """启动时尝试从数据库加载配置"""
    from core.final_pipeline import supabase as sb
    try:
        res = sb.table("algorithm_settings").select("config_json").eq("id", 1).execute()
        if res.data:
            ScoringEngine.update_config(res.data[0]['config_json'])
            print("Successfully loaded algorithm config from database.")
    except Exception as e:
        print(f"No custom config found or table missing, using hardcoded defaults. ({e})")

def init_system_tables():
    """初始化系统管理相关的表和默认数据 (哥，这是为了保证你直接运行就能看到数据)"""
    from core.final_pipeline import supabase as sb
    try:
        # 1. 尝试创建 system_users 表 (如果不存在则 SQL 报错，我们会捕获)
        print("[INIT] Checking system tables...")
        
        # 2. 检查并初始化默认配置 (system_settings)
        # 哥，这里直接用 upsert，保证基础配置存在
        default_settings = [
            {
                "key": "storage_config", 
                "value": {"path": "./output", "auto_cleanup_days": 15},
                "description": "文件存储相关配置"
            },
            {
                "key": "collection_config", 
                "value": {"algatop": {"username": "", "password": ""}}, # 哥，改成 AlgaTop 了
                "description": "数据平台采集凭据"
            }
        ]
        for s in default_settings:
            try:
                sb.table("system_settings").upsert(s).execute()
            except: pass # 表可能还没创建，下文会处理
            
        # 3. 检查并初始化默认管理员
        try:
            res = sb.table("system_users").select("*").eq("username", "admin").execute()
            if not res.data:
                sb.table("system_users").insert({
                    "username": "admin",
                    "password_hash": "admin123", # 建议生产环境修改
                    "role": "admin"
                }).execute()
                print("✅ Default admin created.")
        except: pass

    except Exception as e:
        print(f"[INIT] System tables auto-init skipped or failed (might need manual SQL): {e}")

# 注册启动事件
@app.on_event("startup")
async def startup_event():
    seed_database_on_startup()
    init_system_tables() # 哥，新增这一行
    load_config_on_startup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
