import asyncio
import sys
import os
import re
import json

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.algatop_scraper import BaseScraper

class KaspiScraper(BaseScraper):
    async def search_products(self, keyword, limit=50):
        """
        在 Kaspi.kz 搜索商品并分页获取前 limit 个商品
        """
        products = []
        page_num = 1

        import urllib.parse
        encoded_kw = urllib.parse.quote(keyword)
        while len(products) < limit and page_num <= 10:
            if page_num == 1:
                search_url = f"https://kaspi.kz/shop/search/?text={encoded_kw}"
            else:
                search_url = f"https://kaspi.kz/shop/search/?text={encoded_kw}&page={page_num}"

            print(f"[Kaspi] Page {page_num} -> {search_url} (have {len(products)} so far)")
            await self.page.goto(search_url)
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(4)

            # 少量滚屏触发懒加载
            for _ in range(5):
                await self.page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1)

            page_cards = await self.page.locator('.item-card').all()
            print(f"  Got {len(page_cards)} cards on page {page_num}.")

            if not page_cards:
                print("  No cards found. Stopping.")
                break

            new_count = 0
            for card in page_cards:
                if len(products) >= limit:
                    break
                try:
                    title_el = card.locator('.item-card__name-link')
                    if await title_el.count() == 0:
                        continue
                    title = await title_el.inner_text()
                    href = await title_el.get_attribute('href')

                    price_el = card.locator('.item-card__prices-price').first
                    price = await price_el.inner_text() if await price_el.count() > 0 else "N/A"

                    reviews_el = card.locator('.item-card__rating a').first
                    reviews_text = ""
                    if await reviews_el.count() > 0:
                        reviews_text = await reviews_el.inner_text()
                    reviews_match = re.search(r'\d+', reviews_text.replace(' ', ''))
                    reviews = reviews_match.group(0) if reviews_match else "0"

                    img_el = card.locator('.item-card__image').first
                    img_url = await img_el.get_attribute('src') if await img_el.count() > 0 else ""

                    if href and "/p/" in href:
                        product_id = href.split('/')[-2].split('-')[-1]
                    else:
                        product_id = ""

                    if not product_id:
                        continue

                    print(f"  [{len(products)+1}] ID:{product_id}  '{title[:30]}' Reviews:{reviews}")
                    products.append({
                        "title": title.strip(),
                        "url": href,
                        "sku": product_id,
                        "price": price.strip(),
                        "reviews": reviews,
                        "image_url": img_url
                    })
                    new_count += 1
                except Exception as e:
                    continue

            print(f"  Page {page_num} done: +{new_count} products. Total: {len(products)}")
            page_num += 1

        return products


if __name__ == "__main__":
    async def main():
        scraper = KaspiScraper(storage_state_path=None)
        await scraper.init_browser(headless=False)
        products = await scraper.search_products("коврик для йоги", limit=100)

        os.makedirs("d:/item/ProSourcing/output", exist_ok=True)
        output_path = "d:/item/ProSourcing/output/kaspi_results.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        print(f"\nDone! Saved {len(products)} products to {output_path}")
        await scraper.close()

    asyncio.run(main())
