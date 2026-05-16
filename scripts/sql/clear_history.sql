"-- 哥，执行这个脚本会清空所有选品报告历史记录\n-- 包含：任务列表、商品原始数据、商品评分数据\n\nBEGIN;\n\nTRUNCATE TABLE products_calculated_metrics CASCADE;\nTRUNCATE TABLE products_raw_data CASCADE;\nTRUNCATE TA
<truncated 159 bytes>