import asyncio
from playwright.async_api import async_playwright
import json
import os

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Step 1: Inspect Kaspi search results
        print("--- Inspecting Kaspi ---")
        try:
            await page.goto("https://kaspi.kz/shop/search/?text=коврик%20для%20йоги", timeout=60000)
            await page.wait_for_selector('.item-card', timeout=15000)
            
            cards = await page.locator('.item-card').all()
            if cards:
                card = cards[0]
                html = await card.evaluate("el => el.outerHTML")
                with open("d:/item/ProSourcing/output/kaspi_card_dom.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"Saved Kaspi card HTML ({len(html)} bytes).")
            else:
                print("No item-card found on Kaspi.")
        except Exception as e:
            print(f"Error inspecting Kaspi: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
