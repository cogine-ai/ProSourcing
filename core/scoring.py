import pandas as pd
import numpy as np

class ScoringEngine:
    """
    根据 PRD 定义的规则进行商品评分
    """
    
    @staticmethod
    def score_monthly_sales(monthly_sales):
        """直接使用 1M 销量数据进行评分"""
        if monthly_sales >= 500: return 4
        if monthly_sales >= 200: return 3
        if monthly_sales >= 100: return 2
        if monthly_sales >= 60: return 1
        return 0

    @staticmethod
    def score_reviews(reviews):
        if reviews >= 300: return 3
        if reviews >= 100: return 2
        if reviews >= 50: return 1
        return 0.5

    @staticmethod
    def score_price(price):
        if price >= 8000: return 2
        if price >= 3000: return 1
        if price >= 1500: return 0.5
        return 0

    @staticmethod
    def score_days_per_review(days, reviews):
        if reviews == 0: return 0
        ratio = days / reviews
        if ratio < 1: return 3
        if 1 <= ratio <= 2: return 3 # PRD says 1-2 is 3
        if 2 < ratio <= 2.5: return 1
        return 0

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
        return top3_sales / total_sales

    @staticmethod
    def calculate_avg_sales_per_listing(total_category_sales, listing_count):
        """计算销品比：用于判断品类潜力"""
        if listing_count == 0:
            return 0
        return total_category_sales / listing_count
