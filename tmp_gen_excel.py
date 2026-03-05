import pandas as pd
import os

# 定义表 1 数据
table1_data = [
    ["实时单价", "Kaspi.kz", "前端 item-card__prices-price", "实时有效售价，支持多卖家最低价采集", "默认取 0，该项得分权重清零"],
    ["累计评论数", "Kaspi.kz", "item-card__rating 链接文本解析", "使用正则 \\d+ 提取纯数字，剔除非数文字", "缺失设为 0，触发出厂保底分 (0.5)"],
    ["产品图片 / SKU", "Kaspi.kz", "图片 src 属性 / URL p/ 路径拆解", "提取 SKU 作为全局唯一主键，自动下载首图", "图片缺失显示占位图，SKU 缺失则抛弃该数据"],
    ["上架日期", "Algatop.kz", "商品详情 listing_date 字段", "YYYY-MM-DD 格式，用于计算“上架天数”", "缺失按 90 天（行业平均值）作为对冲基准"]
]
df1 = pd.DataFrame(table1_data, columns=["核心项", "数据来源", "获取方式 (字段级)", "计算口径 / 约束条件", "缺失与降级策略"])

# 定义表 2 数据
table2_data = [
    ["动销热度得分", "Algatop.kz", "sales_3m 销售流水包", "口径：3M销量 / 3.0 按月月销计算。\n规则：≥500 (4分), ≥200 (3分), ≥100 (2分), ≥60 (1分)", "缺失按月销 0 计，该维度得分 0"],
    ["信任深度得分", "Kaspi & AI 计算", "基于评论数加权", "规则：≥300 (3分), ≥100 (2分), ≥50 (1分), <50 (0.5分)", "缺失时使用系统保底分 (0.5)"],
    ["爆款潜力 (DPR)", "组合推演", "上架天数 / 评论总数", "规则：比值 < 1 (3分), 1-2 (3分), 2-2.5 (1分), >2.5 (0分)", "评论为 0 时，DPR 得分为 0"],
    ["盈利权重分", "实时价格", "价格分档映射", "规则：≥8000₸ (2分), ≥3000₸ (1分), ≥1500₸ (0.5分)", "默认按 0 计"],
    ["市场集中度 (CR3)", "Algatop 品牌层", "top3_sales / category_total", "约束：仅对类目前 3 品牌效额进行累积求和", "数据缺失显示 0%，不参与加权"],
    ["供需平衡比", "统计接口", "月销 / 类目产品总数", "口径：衡量单一 SKU 在类目池中的流量捕获效率", "默认为 0"]
]
df2 = pd.DataFrame(table2_data, columns=["评价指标", "数据来源", "获取方式", "计算口径 / 打分规则", "缺失与降级策略"])

# 保存到 Excel
output_path = "d:/item/ProSourcing/ProSourcing_指标与评分规范.xlsx"
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df1.to_excel(writer, sheet_name="表1-实时采集映射", index=False)
    df2.to_excel(writer, sheet_name="表2-评分量化矩阵", index=False)
    
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
            adjusted_width = (max_length + 5)
            ws.column_dimensions[column_name].width = adjusted_width

print(f"Excel 文件已生成: {output_path}")
