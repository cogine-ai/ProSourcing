import os
import uuid
import asyncio
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import sys
import json

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.final_pipeline import run_scoring_and_export
from core.scoring import ScoringEngine, DEFAULT_CONFIG
from deep_translator import GoogleTranslator

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

class TaskRequest(BaseModel):
    category: str

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

@app.post("/api/tasks", response_model=TaskStatus)
def create_task(req: TaskRequest, background_tasks: BackgroundTasks):
    from core.final_pipeline import supabase as sb
    # 哥，先把中文名翻出来
    cat_name = req.category
    res_master = sb.table("algatop_categories_master").select("name_cn").eq("name_ru", req.category).limit(1).execute()
    if res_master.data:
        cat_name = res_master.data[0]['name_cn']
        
    task_data = {"category": cat_name, "status": "pending", "progress": 0}
    res = sb.table("analysis_tasks").insert(task_data).execute()
    db_task = res.data[0]
    task_id = db_task['id']
    task = TaskStatus(task_id=task_id, category=cat_name, status="pending", progress=0)
    tasks_db[task_id] = task
    background_tasks.add_task(execute_rpa_pipeline, task_id, req.category, cat_name)
    return task

@app.get("/api/tasks/history")
def get_task_history():
    """获取历史任务记录，包含执行时间、状态、导出路径 - 改为普通 def 以免阻塞事件循环"""
    from core.final_pipeline import supabase as sb
    res = sb.table("analysis_tasks").select("*").order("created_at", desc=True).limit(50).execute()
    return res.data

@app.get("/api/tasks")
def list_tasks():
    from core.final_pipeline import supabase as sb
    res = sb.table("analysis_tasks").select("*").order("created_at", desc=True).execute()
    data = res.data
    for t in data:
        if not t.get('duration') and t['status'] == 'completed':
            try:
                t['duration'] = calculate_duration_from_logs(t['id'])
            except: t['duration'] = "--"
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


@app.get("/api/categories/search")
async def search_categories(q: str):
    """支持模糊检索类目名称 (还原)"""
    from core.final_pipeline import supabase as sb
    res = sb.table("categories").select("*").ilike("category_name", f"%{q}%").limit(100).execute()
    return res.data

@app.get("/api/categories/children/{parent_id}")
async def get_child_categories(parent_id: str):
    """获取指定父类目的所有直接子类目 (还原)"""
    from core.final_pipeline import supabase as sb
    res = sb.table("categories").select("*").eq("parent_category_id", parent_id).order("sale_product_qty", desc=True).execute()
    return res.data

@app.get("/api/categories/tree")
def get_category_tree():
    """复用 top_stats 的逻辑以获取带计数的树根 - 线程模式"""
    return get_top_categories()

@app.get("/api/categories/{top_id}/leaves")
async def get_top_category_leaves(top_id: str):
    """获取指定一级分类下的所有最小子类 (叶子节点) - 恢复原始逻辑"""
    from core.final_pipeline import supabase as sb
    
    # 1. 获取传入的大类信息
    res = sb.table("categories").select("*").eq("category_id", top_id).execute()
    if not res.data:
        return []
    
    # 全量拉取类目，在内存中构建树
    all_cats = []
    page_size = 1000
    for i in range(10): # 最多拉取 10000 条
        res = sb.table("categories").select("*").range(i * page_size, (i + 1) * page_size - 1).execute()
        all_cats.extend(res.data)
        if len(res.data) < page_size:
            break
            
    # 构建 parent_category_id -> [children...] 的映射
    p_map = {}
    nodes_by_id = {}
    for cat in all_cats:
        cid = cat['category_id']
        pid = cat.get("parent_category_id")
        nodes_by_id[cid] = cat
        if pid not in p_map: p_map[pid] = []
        p_map[pid].append(cat)
        
    leaves = []
    def find_leaves(curr_id):
        children = p_map.get(curr_id, [])
        if not children:
            node = nodes_by_id.get(curr_id)
            if node: leaves.append(node)
        else:
            for c in children:
                find_leaves(c['category_id'])
    
    find_leaves(top_id)
    return leaves



@app.post("/api/tasks/category", response_model=TaskStatus)
def create_category_task(req: TaskRequest, background_tasks: BackgroundTasks):
    """强制根据品类数字 ID 发起选品分析任务 - 改为线程模式"""
    from core.final_pipeline import supabase as sb
    category_id = req.category
    display_title = category_id
    
    # 哥，如果是数字 ID，直接去主表查中文名存库
    if str(category_id).isdigit():
        res_master = sb.table("algatop_categories_master").select("name_cn").eq("algatop_id", int(category_id)).limit(1).execute()
        if res_master.data and res_master.data[0]['name_cn']:
            display_title = res_master.data[0]['name_cn']

    task_data = {
        "category": display_title, 
        "category_id": category_id,
        "status": "pending",
        "progress": 0,
        "created_at": datetime.now().isoformat()
    }
    res = sb.table("analysis_tasks").insert(task_data).execute()
    db_task = res.data[0]
    task_id = db_task['id']
    background_tasks.add_task(execute_rpa_pipeline, task_id, category_id, display_title)
    return TaskStatus(task_id=task_id, category=display_title, status="pending", progress=0)

def execute_rpa_pipeline(task_id: str, category_id: str, category_name: str):
    """RPA 静默执行流程：普通 def 后台运行，基于线程池，不阻塞主线程"""
    from core.final_pipeline import supabase as sb
    import socket
    import subprocess
    import sys
    import os
    import time
    from datetime import datetime
    
    start_time = datetime.now()
    
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def launch_browser():
        """
        启动 Chrome RPA 浏览器。
        哥，这里我加了自动探测逻辑，防止不同电脑路径不一致。
        """
        # 1. 优先从环境变量获取
        chrome_path = os.getenv("CHROME_PATH")
        
        # 2. 如果没配置，则自动探测常见路径
        if not chrome_path or not os.path.exists(chrome_path):
            possible_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.join(os.environ.get('LocalAppData', 'C:\\Users\\Default\\AppData\\Local'), r"Google\Chrome\Application\chrome.exe"),
                os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), r"Google\Chrome\Application\chrome.exe"),
                os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), r"Google\Chrome\Application\chrome.exe"),
            ]
            for p in possible_paths:
                if os.path.exists(p):
                    chrome_path = p
                    break
        
        def is_port_in_use(port):
            # 哥，如果是容器环境，咱得查宿主机的端口，不能查容器自己的
            target = os.getenv("CHROME_REMOTE_DEBUG_ADDR", "host.docker.internal:9222").split(":")[0] if is_docker else "127.0.0.1"
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                return s.connect_ex((target, port)) == 0

        if not chrome_path or not os.path.exists(chrome_path):
            msg = "❌ 找不到 Chrome 可执行文件！"
            if is_docker:
                msg += " (处于容器环境)"
                # 检查一下宿主机的调试端口开了没
                if is_port_in_use(9222):
                    print(f"[SUCCESS] 探测到宿主机 9222 端口已开启，逻辑继续。")
                    return None
                else:
                    msg += " 请在宿主机手动运行 launch_rpa_chrome.py 开启浏览器。"
                    print(f"[WARNING] {msg} (Path: {chrome_path})")
                    return None
            else:
                env_info = f"is_docker={is_docker}, ENV_MOD={os.getenv('ENV_MOD')}"
                msg += f" (环境: {env_info}) 请确认安装 Chrome 或配置 CHROME_PATH。"
                raise FileNotFoundError(msg)

        if is_docker:
            # 容器环境不建议直接调用 subprocess 启动宿主机程序（除非做了复杂的挂载或 RPC）
            # 直接引导用户手动启动，避免报奇怪的权限/路径错误
            print("[DOCKER] 检测到生产/容器环境，跳过自动启动逻辑。请确保宿主机已开启 9222 端口。")
            return None

        port = 9222
        # 用户数据目录也改为相对路径或可配置路径，避免 C 盘权限问题
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        user_data_dir = os.path.join(current_dir, "tmp", "chrome_rpa_profile")
        if not os.path.exists(user_data_dir): 
            os.makedirs(user_data_dir, exist_ok=True)
            
        cmd = [
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        return subprocess.Popen(cmd)

    def update_db(p, s, url=None, err=None, duration=None):
        payload = {"progress": p, "status": s}
        if url: payload["excel_path"] = url
        if err: payload["error_msg"] = err
        if duration: payload["duration"] = duration
        sb.table("analysis_tasks").update(payload).eq("id", task_id).execute()

    try:
        log_dir = "logs"
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        log_path = os.path.join(log_dir, f"{task_id}.log")
        log_file = open(log_path, "a", encoding="utf-8")

        update_db(10, "crawling")
        log_file.write(f"[{datetime.now().isoformat()}] --- Starting RPA Pipeline for category: {category_name} ---\n")
        
        # 定义内部检测函数（因为要用到 is_docker）
        def check_port():
            # 同样需要检测环境
            is_docker_env = (
                os.path.exists('/.dockerenv') or 
                os.path.exists('/proc/1/cgroup') or 
                os.getenv("ENV_MOD") == "production"
            )
            target = os.getenv("CHROME_REMOTE_DEBUG_ADDR", "host.docker.internal:9222").split(":")[0] if is_docker_env else "127.0.0.1"
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                return s.connect_ex((target, 9222)) == 0

        if not check_port():
            log_file.write(f"[{datetime.now().isoformat()}] Detecting Chrome Debug port 9222... Not Found.\n")
            if is_docker:
                log_file.write(f"[{datetime.now().isoformat()}] [DOCKER] 请确保宿主机已运行 launch_rpa_chrome.py\n")
            else:
                log_file.write(f"[{datetime.now().isoformat()}] 正在自动启动浏览器...\n")
                launch_browser()
                time.sleep(5)
            
            if check_port():
                log_file.write(f"[{datetime.now().isoformat()}] Browser/Port is now ready.\n")
            else:
                log_file.write(f"[{datetime.now().isoformat()}] WARNING: Chrome Debug port 9222 is still closed.\n")
        
        log_file.flush()

        rpa_output_path = os.path.abspath(f"output/rpa_output_{task_id}.json")
        os.makedirs(os.path.dirname(rpa_output_path), exist_ok=True)

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        process = subprocess.Popen(
            [sys.executable, "core/algatop_rpa_scraper.py", category_id, task_id],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env=env,
            stdout=log_file,
            stderr=log_file
        )
        process_pool[task_id] = process
        
        while process.poll() is None:
            time.sleep(5)
            update_db(30, "crawling")
            
        if process.returncode != 0:
            msg = "Scraper failed with exit code " + str(process.returncode)
            log_file.write(f"\n[{datetime.now().isoformat()}] [ERROR] {msg}\n")
            log_file.close()
            update_db(0, "failed", err="Scraper failed. Check logs for details.")
            return

        update_db(80, "reporting")
        log_file.write(f"\n[{datetime.now().isoformat()}] --- Scraper finished, starting reporting pipeline ---\n")
        log_file.flush()
        
        report_process = subprocess.run(
            [sys.executable, "core/rpa_final_pipeline.py", task_id, rpa_output_path],
            stdout=log_file,
            stderr=log_file
        )

        if report_process.returncode != 0:
            update_db(0, "failed", err="Reporting pipeline failed.")
            log_file.close()
            return
        
        duration_str = "--"
        try:
            duration_str = calculate_duration_from_logs(task_id)
        except: pass
        
        update_db(100, "completed", duration=duration_str)
        log_file.write(f"\n[{datetime.now().isoformat()}] --- Pipeline COMPLETED successfully (Duration: {duration_str}) ---\n")
        log_file.close()

    except Exception as e:
        import traceback
        if 'log_file' in locals():
            log_file.write(f"\n[FATAL ERROR] {str(e)}\n{traceback.format_exc()}\n")
            log_file.close()
        update_db(0, "failed", err=str(e))

@app.get("/api/market/global_stats")
def get_global_stats():
    """获取顶部四卡片统计数据 - 线程模式响应"""
    from core.final_pipeline import supabase as sb
    res1 = sb.table("algatop_categories_master").select("algatop_id", count="exact").eq("level", 1).limit(1).execute()
    top_cat = res1.count if res1.count is not None else 21
    res2 = sb.table("algatop_categories_master").select("algatop_id", count="exact").eq("is_leaf", True).limit(1).execute()
    min_cat = res2.count if res2.count is not None else 0
    res3 = sb.table("analysis_tasks").select("id", count="exact").eq("status", "completed").limit(1).execute()
    reports = res3.count if res3.count is not None else 0
    res4 = sb.table("products_raw_data").select("sku", count="exact").limit(1).execute()
    skus = res4.count if res4.count is not None else 0
    sku_display = f"{skus / 1000:.1f}K" if skus > 1000 else str(skus)
    return {
        "top_cat_count": top_cat, "min_cat_count": min_cat,
        "sku_count": sku_display, "report_count": reports
    }

@app.get('/api/kaspi/tree')
def get_kaspi_global_tree():
    """基于 algatop_categories_master 构建完整分类树结构 - 彻底解决阻塞问题"""
    from core.final_pipeline import supabase as sb
    try:
        all_cats = []
        page_size = 1000
        for i in range(10):
            res = sb.table('algatop_categories_master').select('*').range(i * page_size, (i + 1) * page_size - 1).execute()
            if not res.data: break
            all_cats.extend(res.data)
            if len(res.data) < page_size: break
        
        if not all_cats: return []
        p_map = {}
        for c in all_cats:
            raw_pid = c.get('parent_id')
            pid = str(raw_pid) if raw_pid and str(raw_pid).lower() != 'none' else ''
            node = {
                'category_code': str(c['algatop_id']),
                'title': c.get('name_cn') or c.get('name_ru') or str(c['algatop_id']),
                'parent_code': pid,
                'is_leaf': c.get('is_leaf', False)
            }
            p_map.setdefault(pid, []).append(node)

        def build_tree(pid=''):
            children = p_map.get(pid, [])
            for child in children:
                child['children'] = build_tree(child['category_code'])
            return children

        return build_tree('')
    except Exception as e:
        print(f"[TREE API ERROR] {str(e)}")
        return []

@app.post('/api/kaspi/tasks/batch')
def create_kaspi_tasks_batch(item_codes: list[str], background_tasks: BackgroundTasks):
    from core.final_pipeline import supabase as sb
    # 哥，先把这些 ID 的中文名全副武装好，优先去 master 主表拿最正宗的翻译
    res_master = sb.table('algatop_categories_master').select('algatop_id, name_cn, name_ru').in_('algatop_id', item_codes).execute()
    
    code_map = {}
    # 先用 master 表的数据填充
    for row in res_master.data:
        algatop_id = str(row['algatop_id'])
        # 只要有中文名就用中文名，没有才用俄文
        cn_name = row.get('name_cn')
        # 如果 name_cn 还是俄文，或者是空，就先拿 name_ru 兜底
        code_map[algatop_id] = cn_name if cn_name and not any(u'\u0400' <= c <= u'\u04FF' for c in cn_name) else (row.get('name_ru') or algatop_id)

    # 如果 master 里没找全，再去 global_category_dict 碰碰运气
    missing_codes = [c for c in item_codes if c not in code_map]
    if missing_codes:
        res_dict = sb.table('global_category_dict').select('*').in_('algatop_id', missing_codes).execute()
        for row in res_dict.data:
            aid = str(row['algatop_id'])
            kid = str(row['kaspi_id'])
            name = row.get('name_cn')
            if not name or any(u'\u0400' <= c <= u'\u04FF' for c in name):
                name = row.get('name_ru') or row.get('name_en') or aid
            code_map[aid] = name
            code_map[kid] = name

    payload = []
    for code in item_codes:
        display_name = code_map.get(str(code), str(code))
        payload.append({
            'category_id': str(code),
            'category': display_name,
            'status': 'pending',
            'progress': 0
        })
        
    try:
        inserted = sb.table('analysis_tasks').insert(payload).execute()
        for task in inserted.data:
            background_tasks.add_task(execute_rpa_pipeline, task['id'], task['category_id'], task['category'])
        return {'success': True, 'count': len(inserted.data)}
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

# 注册启动事件
@app.on_event("startup")
async def startup_event():
    load_config_on_startup()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

