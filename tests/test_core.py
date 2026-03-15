from core.scoring import ScoringEngine, MarketAnalyzer
import pytest

def test_scoring_engine():
    # 测试月销量评分
    assert ScoringEngine.score_monthly_sales(1500) == 10
    assert ScoringEngine.score_monthly_sales(800) == 8
    assert ScoringEngine.score_monthly_sales(500) == 6
    assert ScoringEngine.score_monthly_sales(300) == 4
    assert ScoringEngine.score_monthly_sales(150) == 2
    assert ScoringEngine.score_monthly_sales(80) == 1
    assert ScoringEngine.score_monthly_sales(10) == 0

    # 测试评论数评分
    assert ScoringEngine.score_reviews(400) == 3
    assert ScoringEngine.score_reviews(200) == 2
    assert ScoringEngine.score_reviews(70) == 1
    assert ScoringEngine.score_reviews(20) == 0.5

    # 测试价格区间评分
    assert ScoringEngine.score_price(9000) == 2
    assert ScoringEngine.score_price(5000) == 1
    assert ScoringEngine.score_price(2000) == 0.5
    assert ScoringEngine.score_price(500) == 0

    # 测试上架时间/评论比
    # 比例 < 1 -> 3
    assert ScoringEngine.score_days_per_review(50, 100) == 3
    # 比例 1-2 -> 3
    assert ScoringEngine.score_days_per_review(150, 100) == 3
    # 比例 2-2.5 -> 1
    assert ScoringEngine.score_days_per_review(220, 100) == 1
    # 比例 > 2.5 -> 0
    assert ScoringEngine.score_days_per_review(300, 100) == 0

def test_market_analyzer():
    # 测试 CR3
    sales = [100, 80, 70, 50, 40, 30]
    # top3 = 100+80+70 = 250, total = 370
    expected_cr3 = 250 / 370
    assert MarketAnalyzer.calculate_cr3(sales) == pytest.approx(expected_cr3)
    
    # 测试平均销量
    assert MarketAnalyzer.calculate_avg_sales_per_listing(1000, 50) == 20
