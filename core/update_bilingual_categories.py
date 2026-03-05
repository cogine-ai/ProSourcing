import os
import sys
from datetime import datetime

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.final_pipeline import supabase

TRANSLATIONS = {
    "00002": "Телефоны и гаджеты (手机与设备)",
    "00005": "Компьютеры (电脑)",
    "00012": "ТВ, Аудио, Видео (电视/视听设备)",
    "00034": "Бытовая техника (家用电器)",
    "00079": "Автотовары (汽车用品)",
    "00083": "Детские товары (母婴用品)",
    "00147": "Досуг, книги (休闲娱乐与书籍)",
    "00239": "Мебель (家具)",
    "00240": "Товары для дома и дачи (家居与园艺)",
    "00299": "Красота и здоровье (美容健康)",
    "00751": "Аксессуары (配饰)",
    "00754": "Строительство, ремонт (建筑与装修)",
    "00791": "Обувь (鞋类)",
    "00864": "Спорт, туризм (运动与旅游)",
    "00933": "Одежда (服装)",
    "01466": "Товары для животных (宠物用品)",
    "01793": "Продукты питания (食品)",
    "02062": "Канцелярские товары (办公文具)",
    "02605": "Подарки, товары для праздников (礼品节庆)",
    "02807": "Аптека (医药)",
    "06498": "Украшения (首饰)"
}

def update_translations():
    print("🌍 正在更新一级分类的双语译名...")
    
    for cat_id, bi_name in TRANSLATIONS.items():
        try:
            res = supabase.table("categories").update({"category_name": bi_name}).eq("category_id", cat_id).execute()
            print(f"  ✅ 已更新: {bi_name}")
        except Exception as e:
            print(f"  ❌ 更新失败 {cat_id}: {e}")

    print("\n✨ 双语更新完成！")

if __name__ == "__main__":
    update_translations()
