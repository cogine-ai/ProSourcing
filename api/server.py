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

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.final_pipeline import run_scoring_and_export
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

@app.post("/api/tasks", response_model=TaskStatus)
async def create_task(req: TaskRequest, background_tasks: BackgroundTasks):
    from core.final_pipeline import supabase as sb
    
    # 在 Supabase 创建持久化任务
    task_data = {
        "category": req.category,
        "status": "pending",
        "progress": 0
    }
    res = sb.table("analysis_tasks").insert(task_data).execute()
    db_task = res.data[0]
    task_id = db_task['id']
    
    task = TaskStatus(
        task_id=task_id,
        category=req.category,
        status="pending",
        progress=0
    )
    tasks_db[task_id] = task
    
    # 放入后台执行
    # 注意：首页的任务没有专门的 ID，我们传递其名称作为 category_id 和 category_name
    background_tasks.add_task(execute_rpa_pipeline, task_id, req.category, req.category)
    return task

@app.get("/api/tasks/history")
async def get_task_history():
    """获取历史任务记录，包含执行时间、状态、导出路径"""
    from core.final_pipeline import supabase as sb
    res = sb.table("analysis_tasks").select("*").order("created_at", desc=True).limit(50).execute()
    return res.data

@app.get("/api/tasks")
async def list_tasks():
    from core.final_pipeline import supabase as sb
    res = sb.table("analysis_tasks").select("*").order("created_at", desc=True).execute()
    return res.data

@app.get("/api/tasks/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str):
    from core.final_pipeline import supabase as sb
    res = sb.table("analysis_tasks").select("*").eq("id", task_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Task not found")
    t = res.data[0]
    return TaskStatus(
        task_id=t['id'],
        category=t['category'],
        status=t['status'],
        progress=t['progress'] or 0,
        result_url=t.get('excel_path'),
        category_stats=t.get('category_stats'),
        trend_data=t.get('trend_data'),
        up_categories=t.get('up_categories'),
        error=t.get('error_msg'),
        duration=t.get('duration') or await calculate_duration_from_logs(task_id)
    )

async def calculate_duration_from_logs(task_id: str):
    import re
    from datetime import datetime
    log_path = f"logs/{task_id}.log"
    if not os.path.exists(log_path): return None
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            if not lines: return None
            # 提取第一行和最后一行的 [2026-03-11T01:08:20...] 格式时间
            def extract_time(line):
                m = re.search(r"\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
                if m: return datetime.fromisoformat(m.group(1))
                return None
            start = extract_time(lines[0])
            # 从后往前找最后一个有效时间
            end = None
            for l in reversed(lines):
                end = extract_time(l)
                if end: break
            if start and end:
                diff = end - start
                seconds = diff.total_seconds()
                return f"{int(seconds//60)}m {int(seconds%60)}s"
    except: pass
    return None

@app.get("/api/tasks/{task_id}/data")
async def get_task_data(task_id: str):
    from core.final_pipeline import supabase as sb
    # 首先尝试获取计算后的指标 (全量流程)
    res = sb.table("products_calculated_metrics").select("*, products_raw_data(*)").eq("task_id", task_id).execute()
    if res.data:
        return res.data
    
    # [Fallback] 如果计算表没数据，说明是手动同步或中途停止，直接取原始数据表
    print(f"[API INFO] Task {task_id} 无计算指标，尝试回显原始数据...")
    raw_res = sb.table("products_raw_data").select("*").eq("task_id", task_id).execute()
    # 构造兼容格式，让前端不报错
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
async def get_top_categories():
    """获取首页一级分类的大盘统计数据 (使用新版全局字典表)"""
    from core.final_pipeline import supabase as sb
    
    # 1. 直接获取标记为 top_level 的分类 (共 21 个)
    res = sb.table("global_category_dict").select("*").eq("is_top_level", True).order("monthly_sales", desc=True).execute()
    tops = res.data
    
    # 为了兼容前端，我们将字段映射回旧名称
    mapped_tops = []
    for t in tops:
        mapped_tops.append({
            "category_id": t["kaspi_id"],
            "category_name": f"{t['name_ru']} ({t['name_cn']})" if t['name_cn'] else t['name_ru'],
            "monthly_sales": t["monthly_sales"],
            "sale_amount": t["sale_amount"],
            "sale_product_qty": t["sale_product_qty"],
            "amount_change_prc": t["amount_change_prc"],
            "is_has_subcategory": True,
            "is_top_level": True
        })
    return mapped_tops


@app.get("/api/categories/search")
async def search_categories(q: str):
    """支持模糊检索类目名称"""
    from core.final_pipeline import supabase as sb
    res = sb.table("categories").select("*").ilike("category_name", f"%{q}%").limit(100).execute()
    return res.data

@app.get("/api/categories/children/{parent_id}")
async def get_child_categories(parent_id: str):
    """获取指定父类目的所有直接子类目"""
    from core.final_pipeline import supabase as sb
    res = sb.table("categories").select("*").eq("parent_category_id", parent_id).order("sale_product_qty", desc=True).execute()
    return res.data

@app.get("/api/categories/tree")
async def get_category_tree():
    """复用 top_stats 的逻辑以获取带计数的树根"""
    return await get_top_categories()

@app.get("/api/categories/{top_id}/leaves")
async def get_top_category_leaves(top_id: str):
    """获取指定一级分类下的所有最小子类 (叶子节点)"""
    from core.final_pipeline import supabase as sb
    
    # 1. 获取传入的大类信息
    res = sb.table("categories").select("*").eq("category_id", top_id).execute()
    if not res.data:
        return []
    
    top_cat = res.data[0]
    category_name = top_cat['category_name']
    
    # 2. 从名称中提取俄文部分 (去除中文括号)
    import re
    m = re.search(r'^(.*?)(?:\s*\(.*\))?$', category_name)
    ru_name = m.group(1).strip() if m else category_name
    # 全量拉取类目，在内存中构建树以避免 N+1 查询导致的超时
    # 对于一个小型的类目树 (<1万 条记录) 放入内存计算是最快的。
    # 由于 Supabase (PostgREST) 默认有 1000 条最大限制，必须分页拉取全量
    all_cats = []
    page_size = 1000
    for i in range(10): # 最多拉取 10000 条
        res = sb.table("categories").select("*").range(i * page_size, (i + 1) * page_size - 1).execute()
        all_cats.extend(res.data)
        if len(res.data) < page_size:
            break
    
    # 构建 parent_category_id -> [children...] 的映射
    p_map = {}
    for cat in all_cats:
        pid = cat.get("parent_category_id")
        if pid not in p_map:
            p_map[pid] = []
        p_map[pid].append(cat)
    
    # 3. 寻找实际的层级根节点
    # 如果名称是 "俄文 (中文)" 格式，提取俄文去做匹配
    m = re.search(r'^(.*?)(?:\s*[\(\/].*)?$', category_name)
    ru_name_pure = m.group(1).strip() if m else category_name

    root_id = top_id
    for cat in all_cats:
        if cat['category_name'].strip() == ru_name_pure and cat['category_id'] != top_id:
            root_id = cat['category_id']
            break

    # 4. 内存递归查找所有叶子节点
    all_leaves = []
    
    def find_leaves_in_memory(p_id):
        children = p_map.get(p_id, [])
        for cat in children:
            if cat["is_has_subcategory"] == 0:
                all_leaves.append(cat)
            else:
                find_leaves_in_memory(cat["category_id"])

    # 从真正的根节点开始查
    find_leaves_in_memory(root_id)
    
    # 5. 按销量排序
    all_leaves.sort(key=lambda x: x.get("monthly_sales", 0) or 0, reverse=True)
    return all_leaves



@app.post("/api/tasks/category", response_model=TaskStatus)
async def create_category_task(req: TaskRequest, background_tasks: BackgroundTasks):
    """强制根据品类数字 ID 发起选品分析任务"""
    from core.final_pipeline import supabase as sb
    
    # 强制校验：必须为纯数字 ID
    if not req.category.isdigit():
        raise HTTPException(status_code=400, detail="Category ID must be numeric (e.g. '01793')")
    
    category_id = req.category
    display_title = category_id # 统一以 ID 作为展示标题
    
    # 尝试从字典表找一下名称，仅用于展示 (选做，不强制成功)
    res = sb.table("global_category_dict").select("name_cn").eq("kaspi_id", category_id).limit(1).execute()
    if res.data:
        display_title = f"{res.data[0]['name_cn']} ({category_id})"
    
    # 持久化任务
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
    
    # 放入后台执行
    background_tasks.add_task(execute_rpa_pipeline, task_id, category_id, display_title)
    return TaskStatus(task_id=task_id, category=display_title, status="pending", progress=0)

async def execute_rpa_pipeline(task_id: str, category_id: str, category_name: str):
    """RPA 静默执行流程：翻页 -> 截获 -> 评分 -> 导出"""
    from core.final_pipeline import supabase as sb
    import socket
    import subprocess
    import sys
    import os
    from datetime import datetime
    
    start_time = datetime.now()
    
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def launch_browser():
        # 默认 Chrome 路径（Windows）
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome_path):
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
        port = 9222
        user_data_dir = r"C:\AlgatopRPA_ChromeData"
        if not os.path.exists(user_data_dir): os.makedirs(user_data_dir)
            
        cmd = [
            chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        return subprocess.Popen(cmd)

    def update_db(p, s, url=None, err=None):
        payload = {"progress": p, "status": s}
        if url: payload["excel_path"] = url
        if err: payload["error_msg"] = err
        sb.table("analysis_tasks").update(payload).eq("id", task_id).execute()

    try:
        # 建立独立的任务日志目录
        log_dir = "logs"
        if not os.path.exists(log_dir): os.makedirs(log_dir)
        log_path = os.path.join(log_dir, f"{task_id}.log")
        log_file = open(log_path, "a", encoding="utf-8") # 使用追加模式

        update_db(10, "crawling")
        log_file.write(f"[{datetime.now().isoformat()}] --- Starting RPA Pipeline for category: {category_name} ---\n")
        
        # 0. 自动检查并启动浏览器
        if not is_port_in_use(9222):
            log_file.write(f"[{datetime.now().isoformat()}] Detecting Chrome Debug port 9222 is closed. 正在自动启动浏览器...\n")
            log_file.flush()
            launch_browser()
            # 给浏览器一点启动时间
            await asyncio.sleep(5)
            if is_port_in_use(9222):
                log_file.write(f"[{datetime.now().isoformat()}] Browser started successfully.\n")
            else:
                log_file.write(f"[{datetime.now().isoformat()}] WARNING: Browser start timeout or failed. RPA might fail.\n")
        
        log_file.flush()

        # 定义唯一的采集数据输出路径
        rpa_output_path = os.path.abspath(f"output/rpa_output_{task_id}.json")
        os.makedirs(os.path.dirname(rpa_output_path), exist_ok=True)

        # 1. 调用 RPA 采集脚本 (进程模式运行)
        # 增加环境变量强制 UTF-8 编码，防止 Windows 编码崩溃
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
            await asyncio.sleep(5)
            # 模拟进度增加
            update_db(30, "crawling")
            
        # 检查采集脚本是否成功
        if process.returncode != 0:
            msg = "Scraper failed with exit code " + str(process.returncode)
            log_file.write(f"\n[{datetime.now().isoformat()}] [ERROR] {msg}\n")
            log_file.close()
            update_db(0, "failed", err="Scraper failed. Check logs for details.")
            return

        # 2. 调用 评分与导出
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
        
        # 3. 完成
        update_db(100, "completed")
        log_file.write(f"\n[{datetime.now().isoformat()}] --- Pipeline COMPLETED successfully ---\n")
        log_file.close()

    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            if 'log_file' in locals():
                log_file.write(f"\n[FATAL ERROR] {str(e)}\n{traceback.format_exc()}\n")
                log_file.close()
            update_db(0, "failed", err=str(e))
        except: pass

# --- KASPI GLOBAL CATEGORIES ENDPOINTS ---

@app.get('/api/kaspi/tree')
async def get_kaspi_global_tree():
    from core.final_pipeline import supabase as sb
    
    # 1. Fetch all records from dictionary
    all_cats = []
    page_size = 1000
    for i in range(10):
        res = sb.table('global_category_dict').select('*').range(i * page_size, (i + 1) * page_size - 1).execute()
        all_cats.extend(res.data)
        if len(res.data) < page_size: break
            
    # 2. 构建 ID 映射关系表 (Kaspi ID -> 优先使用的数字 ID)
    # 因为数据库建立在 Kaspi 树上，但用户要求全链路数字 ID，我们必须在返回给前端时进行“实时脱壳”
    id_map = {c['kaspi_id']: c['algatop_id'] if c.get('algatop_id') and c['algatop_id'].isdigit() else c['kaspi_id'] for c in all_cats}
            
    p_map = {}
    for c in all_cats:
        # 映射 DB 模型到前端模型，ID 字段强制映射为数字标识 (如有)
        node = {
            'category_code': id_map.get(c['kaspi_id']),
            'title': c['name_cn'] if c.get('name_cn') else c.get('name_ru') or c['name_en'],
            'parent_code': id_map.get(c['parent_kaspi_id']) if c.get('parent_kaspi_id') else None,
            'is_leaf': c['is_leaf']
        }
        pid = node['parent_code'] or ''
        p_map.setdefault(pid, []).append(node)

    def build_tree(pid='', visited=None):
        if visited is None: visited = set()
        if pid in visited: return [] # 哥，出现循环引用了，直接打断点
        visited.add(pid)
        
        children = p_map.get(pid, [])
        for child in children:
            # Recursive build
            child['children'] = build_tree(child['category_code'], set(visited))
        return children

    # 2. Get roots
    # - Standard Kaspi roots (children of desktop-menu)
    roots = build_tree('desktop-menu')
    
    # - Extra roots (nodes with no parent but marked as top level, like 01793)
    root_codes = set(n['category_code'] for n in roots)
    for c in all_cats:
        if c.get('is_top_level') and not c.get('parent_kaspi_id') and c['kaspi_id'] != 'desktop-menu':
            if c['kaspi_id'] not in root_codes:
                node = {
                    'category_code': c['kaspi_id'],
                    'title': c['name_cn'] if c.get('name_cn') else c.get('name_ru') or c['name_en'],
                    'parent_code': None,
                    'is_leaf': c['is_leaf'],
                    'children': build_tree(c['kaspi_id'])
                }
                roots.append(node)
                root_codes.add(node['category_code'])
        
    return roots

@app.post('/api/kaspi/tasks/batch')
async def create_kaspi_tasks_batch(item_codes: list[str], background_tasks: BackgroundTasks):
    from core.final_pipeline import supabase as sb
    
    # 优先匹配数字 ID (algatop_id)
    res = sb.table('global_category_dict').select('*').in_('algatop_id', item_codes).execute()
    # 兜底匹配：如果数字 ID 没搜全，尝试匹配 kaspi_id (兼容历史数据)
    if len(res.data) < len(item_codes):
        missing = set(item_codes) - set(r['algatop_id'] for r in res.data)
        res_ext = sb.table('global_category_dict').select('*').in_('kaspi_id', list(missing)).execute()
        res.data.extend(res_ext.data)

    # 建立显示的名称映射，键必须对应传入的 ID
    code_map = {}
    for row in res.data:
        name = row['name_cn'] if row.get('name_cn') else (row.get('name_ru') or row['name_en'])
        # 记录映射：无论是传入数字 ID 还是字符串 ID 都能找回名称
        if row.get('algatop_id'): code_map[row['algatop_id']] = name
        code_map[row['kaspi_id']] = name
    
    payload = []
    for code in item_codes:
        payload.append({
            'category_id': code,
            'category': code_map.get(code, code),
            'status': 'pending',
            'progress': 0
        })
        
    try:
        inserted = sb.table('analysis_tasks').insert(payload).execute()
        
        # 核心修复：将批量生成的任务依次放入后台队列执行
        for task in inserted.data:
            background_tasks.add_task(execute_rpa_pipeline, task['id'], task['category_id'], task['category'])
            
        return {'success': True, 'count': len(inserted.data)}
    except Exception as e:
        return {'success': False, 'message': str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

