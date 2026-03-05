import pandas as pd
import os

# 根据截图补充完整的表 1：实时感知与基础数据采集映射表
table1_data = [
    ["产品名称", "Kaspi.kz", "前端 item-card__name", "商品标准名称，用于多语言校对", "缺失则显示‘未知商品’"],
    ["SKU", "Kaspi.kz", "URL路径解析 / p/ 后缀", "全局唯一标识符，数据同步主键", "缺失则丢弃该条记录"],
    ["上架时间", "Algatop.kz", "详情页 listing_date", "YYYY-MM-DD，计算产品市场存续周期", "缺失按行业均值 90 天对冲"],
    ["品牌", "Kaspi/Algatop", "品牌字段引用", "品牌维度统计，用于 CR3 集中度分析", "显示‘无品牌’"],
    ["分级", "系统计算", "类目映射", "对应平台产品类目层级", "默认归类为‘其他’"],
    ["评论", "Kaspi.kz", "item-card__rating 提取", "累计真实评价数，反映用户信任基础", "缺失按 0 计"],
    ["卖家", "Kaspi.kz", "item-card__merchant-name", "当前提供最低价的活跃卖家名称", "显示‘未知卖家’"],
    ["价格", "Kaspi.kz", "item-card__prices-price", "实时有效销售价（坚戈）", "按 0 计，不参与评分"],
    ["Bec (重量)", "Algatop.kz", "weight 字段", "产品物流毛重（kg），用于跨境运费预估", "缺失按类目前 10 均值填充"],
    ["佣金", "Algatop.kz", "commission 比例", "平台类目扣点比例", "按类目通用比例填充"],
    ["产品链接", "Kaspi.kz", "href 属性", "商品详情页原始直链", "不显示"],
    ["近3个月销量数", "Algatop.kz", "sales_3m", "近 90 天累计成交单数", "按 0 计"],
    ["近3个月销售收入", "Algatop.kz", "revenue_3m", "近 90 天累计成交总额（坚戈）", "按 0 计"]
]
df1 = pd.DataFrame(table1_data, columns=["核心项", "数据来源", "获取方式 (字段级)", "计算口径 / 约束条件", "缺失与降级策略"])

# 根据截图补充完整的表 2：深度商业情报及量化评分矩阵
table2_data = [
    ["文件生成时间", "系统环境", "datetime.now()", "报告产出的精确时间戳", "自动生成"],
    ["产品类目树", "系统逻辑", "类目分级合并", "商品从一级到末级的完整路径", "按实际抓取深度显示"],
    ["产品首图", "Kaspi.kz", "img src 提取", "多媒体预览支持，提升人工评审效率", "显示占位图"],
    ["月销数量得分", "量化算法", "sales_3m / 3", "标准打分：≥500(4分), ≥200(3分), ≥100(2分), ≥60(1分)", "0分"],
    ["评论数量得分", "量化算法", "评论总数映射", "标准打分：≥300(3分), ≥100(2分), ≥50(1分), <50(0.5分)", "0.5分"],
    ["产品售价得分", "量化算法", "价格档位映射", "标准打分：≥8000(2分), ≥3000(1分), ≥1500(0.5分)", "0分"],
    ["供需平衡比得分", "统计推演", "月销 / 类目产品总数", "口径：产品在细分类目下的竞争烈度比值", "0分"],
    ["上架时间", "数据同步", "原始日期", "展示产品在平台的首发日期", "显示‘未知’"],
    ["上架时间/评论比 (DPR)", "核心算法", "天数 / 评论数", "独家爆款潜力：<1(3分), 1-2(3分), 2-2.5(1分), >2.5(0分)", "0分"],
    ["CR3 (集中度)", "品牌分析", "Top 3 品牌占比", "数值越高代表垄断越强，风险越大", "不参与评分"],
    ["产品链接", "原始链接", "直达详情", "支持一键跳转平台进行二次确认", "不显示"],
    ["近6个月销量曲线图", "Algatop.kz", "历史月度流量包", "通过时序数据拟合出的市场趋势图", "显示‘趋势平稳’"],
    ["得分总和", "综合加权", "各分项累加", "通过 AI 模型计算出的最终‘爆款潜力分’", "0分"]
]
df2 = pd.DataFrame(table2_data, columns=["评价指标", "数据来源", "获取方式 / 算法描述", "计算口径 / 规则描述", "缺失与降级策略"])

# 保存到 Excel
output_path = "d:/item/ProSourcing/ProSourcing_指标与评分规范_全字段版.xlsx"
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df1.to_excel(writer, sheet_name="表1-全量采集映射", index=False)
    df2.to_excel(writer, sheet_name="表2-全量评分矩阵", index=False)
    
    # 调整列宽
    for sheetname in writer.sheets:
        ws = writer.sheets[sheetname]
        for column in ws.columns:
            max_length = 0
            column_name = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except: pass
            adjusted_width = (max_length + 6)
            ws.column_dimensions[column_name].width = min(adjusted_width, 50) # 限制最大宽度

print(f"全字段版 Excel 文件已生成: {output_path}")
