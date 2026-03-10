import pandas as pd
import numpy as np

class ScoringEngine:
    """
    根据用户提供的评分规范（图1）进行商品评分
    """
    
    @staticmethod
    def score_monthly_sales(monthly_sales):
        """月销量评分"""
        if monthly_sales > 500: return 4
        if 200 <= monthly_sales <= 500: return 3
        if 100 <= monthly_sales < 200: return 2
        if 60 <= monthly_sales < 100: return 1
        return 0

    @staticmethod
    def score_reviews(reviews):
        """评论数量评分"""
        if reviews > 400: return 3
        if 200 <= reviews <= 400: return 2
        if 100 <= reviews < 200: return 1.5
        if 50 <= reviews < 100: return 1
        if 15 <= reviews <= 50: return 0.5
        return 0  # <15 不计入/0分

    @staticmethod
    def score_price(price):
        """商品价格评分"""
        if price > 8000: return 0
        if 3000 <= price <= 8000: return 1
        if 1500 <= price < 3000: return 0.5
        return 0  # <1500 为 0分

    @staticmethod
    def score_avg_sales_per_listing(avg_sales):
        """类目平均销量（单品均销/销品比）评分"""
        if avg_sales > 80: return 4
        if 50 <= avg_sales <= 80: return 3
        if 30 <= avg_sales < 50: return 2
        if 15 <= avg_sales < 30: return 1
        return 0  # <=15 为 0分

    @staticmethod
    def score_days_per_review(days, reviews):
        """上架天数 / 评论数 评分 (成长潜力)"""
        if reviews == 0: return 0
        ratio = days / reviews
        if ratio <= 0.5: return 10
        if 0.5 < ratio <= 1: return 5
        if 1 < ratio <= 2: return 3
        if 2 < ratio <= 2.5: return 1
        return 0 # >2.5 为 0分

class MarketAnalyzer:
    """
    计算市场竞争度指标
    """
    @staticmethod
    def calculate_cr3(sales_list):
        if not sales_list or len(sales_list) == 0:
            return 0
        total_sales = sum(sales_list)
        if total_sales == 0:
            return 0
        top3_sales = sum(sorted(sales_list, reverse=True)[:3])
        cr3 = top3_sales / total_sales
        return cr3

    @staticmethod
    def get_cr3_status(cr3_value):
        """根据 CR3 值返回竞争集中度描述"""
        if cr3_value < 0.3: return "分散"
        if 0.3 <= cr3_value <= 0.6: return "中度集中"
        return "高度集中"
