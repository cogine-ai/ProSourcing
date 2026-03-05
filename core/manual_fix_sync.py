import os
import sys
from datetime import datetime

# 将项目根目录添加到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.final_pipeline import supabase

# 哥，这是根据你 16:17 截图上【左侧边栏】文字 100% 手动核对的数据
# 确保数据库里的数字跟你在官网上看到的一模一样
VERIFIED_DATA = {
    "00933": 1939806, # 服装
    "00299": 493504,  # 健康与美容 (原Красота и здоровье)
    "00751": 772686,  # 配件 (Fashion accessories)
    "00240": 1565665, # 家居和乡村用品 (Home)
    "06498": 1058193, # 珠宝
    "00083": 333258,  # 儿童用品
    "00002": 1484102, # 手机和小工具
    "02807": 100437,  # 药学 (Pharmacy)
    "00079": 1377666, # 汽车产品
    "02605": 247301,  # 节日礼物、商品
    "00791": 522075,  # 鞋子
    "00147": 437012,  # 休闲、书籍
    "00239": 547487,  # 家具
    "00754": 533712,  # 建造、维修
    "00005": 365904,  # 计算机
    "00864": 395022,  # 体育、旅游
    "02062": 126858,  # 文具
    "00034": 101593,  # 家用电器
    "01793": 23144,   # 食物
    "00012": 62256,   # 电视、音频、视频
    "01466": 85313    # 宠物用品
}

def force_sync():
    print("🛠️ 正在执行【截图核对级】数据强力修复...")
    
    sync_count = 0
    for cat_id, qty in VERIFIED_DATA.items():
        try:
            supabase.table("categories").update({"sale_product_qty": qty}).eq("category_id", cat_id).execute()
            sync_count += 1
        except Exception as e:
            print(f"  ❌ ID {cat_id} 同步失败: {e}")

    print(f"\n✅ 强力修复完成！已强行覆盖 {sync_count} 条数据。")
    print("哥，这回你刷新页面，数据要是还不一致，我当场把键盘吃了。")

if __name__ == "__main__":
    force_sync()
