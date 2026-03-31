import os
import sys
import json
from datetime import datetime

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.final_pipeline import supabase

def init_categories():
    print("🚀 开始从 接口.txt 初始化品类数据...")
    
    txt_path = "d:/item/ProSourcing/接口.txt"
    if not os.path.exists(txt_path):
        print(f"❌ 找不到文件: {txt_path}")
        return

    try:
        with open(txt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # 接口.txt 第三行是 JSON 数据
            if len(lines) < 3:
                print("❌ 接口.txt 格式不正确，缺少数据行。")
                return
            
            data_json = lines[2].strip()
            data = json.loads(data_json)
            
            if not data.get("success") or "data" not in data:
                print("❌ JSON 数据不符合预期格式。")
                return
            
            categories = data["data"]
            print(f"📦 解析到 {len(categories)} 个品类。")
            
            for cat in categories:
                db_data = {
                    "category_id": cat["category_id"],
                    "category_name": cat["category_name"],
                    "monthly_sales": cat["sale_qty"],
                    "sale_amount": cat["sale_amount"],
                    "sale_product_qty": 0, # 接口 1 没有，初始化为 0
                    "is_has_subcategory": cat["is_has_subcategory"],
                    "amount_change_prc": cat["amount_change_prc"],
                    "restrict_type": cat["restrict_type"],
                    "parent_category_id": cat.get("parent_category_id"),
                    "is_top_level": True if not cat.get("parent_category_id") else False,
                    "last_sync_at": datetime.now().isoformat()
                }
                
                # 尝试 upsert
                try:
                    res = supabase.table("categories").upsert(db_data).execute()
                    print(f"  ✅ 已同步: {cat['category_name']} ({cat['category_id']})")
                except Exception as e:
                    print(f"  ❌ 同步失败: {cat['category_name']}, Error: {e}")

        print("\n✨ 初始化完成！")
        
    except Exception as e:
        print(f"❌ 运行报错: {e}")

if __name__ == "__main__":
    init_categories()
