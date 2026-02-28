import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scoring import ScoringEngine, MarketAnalyzer

def process_results(kaspi_file, algatop_stats=None):
    if not os.path.exists(kaspi_file):
        print(f"Error: {kaspi_file} not found.")
        return
    
    with open(kaspi_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    
    scored_products = []
    for p in products:
        # 清洗价格数据 2 449 ₸ -> 2449
        try:
            price_val = int(p['price'].replace("₸", "").replace(" ", "").strip())
        except:
            price_val = 0
            
        try:
            reviews_val = int(p['reviews'].replace(" ", "").strip())
        except:
            reviews_val = 0
            
        # 基础评分逻辑 (这里目前还没用到 Algatop 的月销量，先用评论数模拟)
        # 以后完善：如果有 Algatop 数据，则优先级更高
        monthly_sales_guess = reviews_val * 5 # 粗略估算：1个评论对应5个销量
        
        scores = {
            "sales_score": ScoringEngine.score_monthly_sales(monthly_sales_guess),
            "reviews_score": ScoringEngine.score_reviews(reviews_val),
            "price_score": ScoringEngine.score_price(price_val),
            # 假设商品上架了 90 天
            "days_per_review_score": ScoringEngine.score_days_per_review(90, reviews_val)
        }
        
        total_score = sum(scores.values())
        p['scores'] = scores
        p['total_score'] = total_score
        scored_products.append(p)
        
    # 按总分排序
    scored_products.sort(key=lambda x: x['total_score'], reverse=True)
    
    # 计算市场指标
    all_prices = [int(p['price'].replace("₸", "").replace(" ", "")) for p in products if "₸" in p['price']]
    market_stats = {
        "avg_price": sum(all_prices) / len(all_prices) if all_prices else 0,
        "product_count": len(products),
        "potential_level": "Medium" if len(products) > 5 else "Low"
    }
    
    final_output = {
        "market_stats": market_stats,
        "products": scored_products
    }
    
    output_path = "d:/item/ProSourcing/output/final_analysis.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)
        
    print(f"Analysis complete. Results saved to {output_path}")
    return final_output

if __name__ == "__main__":
    process_results("d:/item/ProSourcing/output/kaspi_results.json")
