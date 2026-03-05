import asyncio
import httpx
import json
import os

def get_cookies():
    try:
        with open("d:/item/ProSourcing/auth.json", "r", encoding="utf-8") as f:
            state = json.load(f)
            cookies = state.get("cookies", [])
            return "; ".join([f"{c['name']}={c['value']}" for c in cookies])
    except:
        return ""

async def silent_diagnose():
    sku = "112769474"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "top-l": "2s3dfnfRgn43PkgmPolqre#",
        "Cookie": get_cookies()
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Algatop Detail
        try:
            url = f"https://app.algatop.kz/api/v1/niche/product/{sku}"
            resp = await client.get(url, headers=headers)
            with open("d:/item/ProSourcing/debug_full_detail.json", "w", encoding="utf-8") as f:
                json.dump(resp.json(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            with open("d:/item/ProSourcing/debug_error.log", "a", encoding="utf-8") as f:
                f.write(f"Detail Error: {str(e)}\n")

        # Kaspi Offers
        try:
            kaspi_url = f"https://kaspi.kz/yml/offer-view/offers/{sku}"
            resp_k = await client.post(kaspi_url, json={"cityId": "750000000"}, headers=headers)
            with open("d:/item/ProSourcing/debug_kaspi_offers.json", "w", encoding="utf-8") as f:
                json.dump(resp_k.json(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            with open("d:/item/ProSourcing/debug_error.log", "a", encoding="utf-8") as f:
                f.write(f"Kaspi Error: {str(e)}\n")

if __name__ == "__main__":
    asyncio.run(silent_diagnose())
