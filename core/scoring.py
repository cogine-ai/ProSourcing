import pandas as pd
import numpy as np

# 哥，这是默认配置，以后可以在后台动态改，不用重新部署代码
DEFAULT_CONFIG = {
    "monthly_sales": {
        "ranges": [1000, 601, 401, 201, 101, 60],
        "scores": [10, 8, 6, 4, 2, 1, 0]
    },
    "reviews": {
        "ranges": [400, 200, 100, 50, 15],
        "scores": [3, 2, 1.5, 1, 0.5, 0]
    },
    "price": {
        "ranges": [8000, 3000, 1500],
        "scores": [0, 1, 0.5, 0]
    },
    "avg_sales": {
        "ranges": [80, 50, 30, 15],
        "scores": [4, 3, 2, 1, 0]
    },
    "days_per_review": {
        "ranges": [0.5, 1, 2, 2.5],
        "scores": [10, 5, 3, 1, 0]
    }
}

# 内存中的活跃配置，初始使用硬编码默认值
ACTIVE_CONFIG = DEFAULT_CONFIG.copy()

class ScoringEngine:
    """
    根据算法配置进行动态评分。
    哥，现在的逻辑全是从 ACTIVE_CONFIG 读，如果你在后台改了，这里立刻生效。
    """
    
    @staticmethod
    def update_config(new_config):
        global ACTIVE_CONFIG
        ACTIVE_CONFIG = new_config
        print("ScoringEngine: Configuration updated in memory.")

    @staticmethod
    def get_config():
        return ACTIVE_CONFIG

    @staticmethod
    def score_monthly_sales(monthly_sales):
        conf = ACTIVE_CONFIG["monthly_sales"]
        for i, threshold in enumerate(conf["ranges"]):
            if monthly_sales >= threshold:
                return conf["scores"][i]
        return conf["scores"][-1]

    @staticmethod
    def score_reviews(reviews):
        conf = ACTIVE_CONFIG["reviews"]
        for i, threshold in enumerate(conf["ranges"]):
            if reviews >= threshold:
                return conf["scores"][i]
        return conf["scores"][-1]

    @staticmethod
    def score_price(price):
        conf = ACTIVE_CONFIG["price"]
        # 价格逻辑略有不同：大于最高阈值得0分
        if price > conf["ranges"][0]:
            return conf["scores"][0]
        for i, threshold in enumerate(conf["ranges"][1:], 1):
            if price >= threshold:
                return conf["scores"][i]
        return conf["scores"][-1]

    @staticmethod
    def score_avg_sales_per_listing(avg_sales):
        conf = ACTIVE_CONFIG["avg_sales"]
        for i, threshold in enumerate(conf["ranges"]):
            if avg_sales >= threshold:
                return conf["scores"][i]
        return conf["scores"][-1]

    @staticmethod
    def score_days_per_review(days, reviews):
        if reviews == 0: return 0
        ratio = days / reviews
        conf = ACTIVE_CONFIG["days_per_review"]
        # 天数/评论比：越小得分越高
        for i, threshold in enumerate(conf["ranges"]):
            if ratio <= threshold:
                return conf["scores"][i]
        return conf["scores"][-1]

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
