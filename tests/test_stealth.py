import asyncio
from playwright_stealth import stealth

async def test_stealth():
    print("Testing playwright-stealth...")
    try:
        print(f"stealth type: {type(stealth)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_stealth())
