import asyncio
import os
from sqlmodel import select
from core.db import AsyncSessionLocal, engine
from core.models import AnalysisTask, ProductRawData
from datetime import datetime
import uuid

async def test_crud():
    # 哥，咱们先开个异步会话测试一下
    async with AsyncSessionLocal() as session:
        print("[TEST] Testing Database Connection and CRUD...")
        
        # 1. 创建一个测试任务
        test_id = str(uuid.uuid4())
        new_task = AnalysisTask(
            id=test_id,
            category="ORM测试品类",
            status="pending",
            progress=0,
            created_at=datetime.utcnow()
        )
        session.add(new_task)
        await session.commit()
        print(f"✅ [CREATE] Task created with ID: {test_id}")

        # 2. 查询该任务
        statement = select(AnalysisTask).where(AnalysisTask.id == test_id)
        results = await session.execute(statement)
        task = results.scalar_one_or_none()
        if task:
            print(f"✅ [READ] Task found: {task.category}, Status: {task.status}")
        else:
            print(f"❌ [READ] Task NOT found!")
            return

        # 3. 更新任务状态
        task.status = "crawling"
        task.progress = 50
        session.add(task)
        await session.commit()
        await session.refresh(task)
        print(f"✅ [UPDATE] Task updated: Status={task.status}, Progress={task.progress}")

        # 4. 删除测试数据 (软清理)
        await session.delete(task)
        await session.commit()
        print(f"✅ [DELETE] Test task cleaned up.")

if __name__ == "__main__":
    # 确保 PYTHONPATH 包含项目根目录
    try:
        asyncio.run(test_crud())
    except Exception as e:
        import traceback
        print(f"❌ [FATAL] Test failed: {e}")
        traceback.print_exc()
