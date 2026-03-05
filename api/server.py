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
    background_tasks.add_task(execute_pipeline, task_id, req.category)
    return task

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
        error=t.get('error_msg')
    )

@app.get("/api/tasks/{task_id}/data")
async def get_task_data(task_id: str):
    from core.final_pipeline import supabase as sb
    # 获取该任务下的所有计算指标及其关联的原始数据
    res = sb.table("products_calculated_metrics").select("*, products_raw_data(*)").eq("task_id", task_id).execute()
    return res.data

@app.get("/api/products")
async def get_products():
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
    """获取首页一级分类的大盘统计数据 (内存实时计算叶子节点数)"""
    from core.final_pipeline import supabase as sb
    
    # 1. 获取一级分类
    res = sb.table("categories").select("*").eq("is_top_level", True).order("monthly_sales", desc=True).execute()
    tops = res.data
    
    # 2. 拉取全量类目，用于构建树
    all_cats = []
    page_size = 1000
    for i in range(10): 
        r = sb.table("categories").select("category_id, category_name, parent_category_id, is_has_subcategory").range(i * page_size, (i + 1) * page_size - 1).execute()
        all_cats.extend(r.data)
        if len(r.data) < page_size: break
        
    p_map = {}
    for cat in all_cats:
        pid = cat.get("parent_category_id")
        if pid not in p_map: p_map[pid] = []
        p_map[pid].append(cat)
        
    def count_leaves_cached(p_id, memo):
        if p_id in memo: return memo[p_id]
        count = 0
        children = p_map.get(p_id, [])
        for cat in children:
            if cat.get("is_has_subcategory") == 0:
                count += 1
            else:
                count += count_leaves_cached(cat["category_id"], memo)
        memo[p_id] = count
        return count

    # 3. 注入数据
    import re
    
    # 手动建立一些名称匹配不上的映射 (由于数据库中根节点 ID 是英文，业务大类是数字)
    ROOT_MAPPING = {
        "01793": "Food and drink", # 食品
        "00864": "Sports and outdoors", # 运动与旅游
        "00005": "Computers", # 电脑
        "00012": "TV_Audio", # 电视/音频
        "02807": "Pharmacy", # 医药
        "00299": "Beauty care", # 美容健康
        "00002": "Smartphones and gadgets", # 手机
        "00240": "Home", # 家居与园艺
        "00079": "Car goods", # 汽车用品
        "01466": "Pet goods", # 宠物用品
    }

    def clean_name(n):
        if not n: return ""
        # 移除 (中文) 部分
        n = re.sub(r'[\(\/].*$', '', n)
        # 移除所有非字母数字字符
        n = re.sub(r'[^\w]', '', n, flags=re.UNICODE)
        return n.lower().strip()

    for top in tops:
        tid = top['category_id']
        ru_name_pure = clean_name(top['category_name'])
        
        # 优先使用硬编码映射
        real_root_id = None
        mapped_name = ROOT_MAPPING.get(tid)
        if mapped_name:
            # 在 all_cats 中寻找名称匹配的实际根节点 ID
            for c in all_cats:
                if clean_name(c['category_name']) == clean_name(mapped_name):
                    real_root_id = c['category_id']
                    break
        # 如果没有通过映射找到，回退到原始逻辑
        if not real_root_id:
            real_root_id = tid
            # 尝试名称匹配（防止 ID 与名称不一致的情况）
            for c in all_cats:
                if clean_name(c['category_name']) == ru_name_pure and c['category_id'] != tid:
                    real_root_id = c['category_id']
                    break
            
        # 递归获取子类，使用根节点的名称（可能是英文/俄文）作为键
        def get_all_leaves_by_key(p_key):
            leaves = []
            for child in p_map.get(p_key, []):
                if child.get("is_has_subcategory") == 0:
                    leaves.append(child)
                else:
                    leaves.extend(get_all_leaves_by_key(child["category_id"]))
            return leaves

        # 通过映射得到实际的根节点名称（英文/俄文），如果没有映射则使用清理后的中文名
        root_key = mapped_name if mapped_name else ru_name_pure
        # 获取子类列表（根键可能是名称而非 ID）
        item_leaves = get_all_leaves_by_key(real_root_id) # Changed to real_root_id to match p_map keys
        top['leaf_count'] = len(item_leaves)
        top['leaves'] = sorted(item_leaves, key=lambda x: x.get('monthly_sales', 0), reverse=True)

        
    return tops

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


@app.get("/api/tasks/history")
async def get_task_history():
    """获取历史任务记录，包含执行时间、状态、导出路径"""
    from core.final_pipeline import supabase as sb
    res = sb.table("analysis_tasks").select("*").order("created_at", desc=True).limit(50).execute()
    return res.data

@app.post("/api/tasks/category", response_model=TaskStatus)
async def create_category_task(req: TaskRequest, background_tasks: BackgroundTasks):
    """根据品类 ID 发起选品分析任务"""
    from core.final_pipeline import supabase as sb
    
    # 持久化任务
    task_data = {
        "category": req.category, # 这里传的是品类名称或ID
        "status": "pending",
        "progress": 0,
        "created_at": datetime.now().isoformat()
    }
    res = sb.table("analysis_tasks").insert(task_data).execute()
    db_task = res.data[0]
    task_id = db_task['id']
    
    # 放入后台执行
    background_tasks.add_task(execute_rpa_pipeline, task_id, req.category)
    return TaskStatus(task_id=task_id, category=req.category, status="pending", progress=0)

async def execute_rpa_pipeline(task_id: str, category: str):
    """RPA 静默执行流程：翻页 -> 截获 -> 评分 -> 导出"""
    from core.final_pipeline import supabase as sb
    
    def update_db(p, s, url=None, err=None):
        payload = {"progress": p, "status": s}
        if url: payload["excel_path"] = url
        if err: payload["error_msg"] = err
        sb.table("analysis_tasks").update(payload).eq("id", task_id).execute()

    try:
        update_db(10, "crawling")
        # 1. 调用 RPA 采集脚本 (进程模式运行)
        import subprocess
        process = subprocess.Popen(
            [sys.executable, "core/algatop_rpa_scraper.py", category, task_id],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        process_pool[task_id] = process
        
        while process.poll() is None:
            await asyncio.sleep(5)
            # 模拟进度增加
            update_db(30, "crawling")
            
        # 2. 调用 评分与导出
        update_db(80, "reporting")
        import subprocess
        # 使用专用的 RPA 导出脚本
        subprocess.run([sys.executable, "core/rpa_final_pipeline.py", task_id])
        
        # 3. 完成
        update_db(100, "completed")
    except Exception as e:
        update_db(0, "failed", err=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
