import asyncio
import os
import sys
import traceback
from datetime import datetime
from sqlmodel import select
from core.db import AsyncSessionLocal
from core.models import AnalysisTask

# Set encoding to avoid issues
sys.stdout.reconfigure(encoding='utf-8')

async def simple_test():
    async with AsyncSessionLocal() as session:
        print("Checking tables...")
        try:
            # Try to fetch one task to see if schema matches
            statement = select(AnalysisTask).limit(1)
            results = await session.execute(statement)
            item = results.scalars().first()
            print(f"Fetch success: {item.id if item else 'No tasks'}")
            
            # Try to insert a minimal task
            import uuid
            new_id = str(uuid.uuid4())
            new_task = AnalysisTask(
                id=new_id,
                category="Test",
                category_id="test_id",
                status="pending",
                progress=0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(new_task)
            await session.commit()
            print(f"Insert success: {new_id}")
            
            # Clean up
            await session.delete(new_task)
            await session.commit()
            print("Delete success")
            
        except Exception as e:
            print(f"Error caught: {type(e).__name__}: {str(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_test())
