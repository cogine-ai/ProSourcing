import os
import re

file_path = r'd:\item\ProSourcing\frontend_pro\src\App.jsx'
if not os.path.exists(file_path):
    print("File not found")
    exit(1)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 升级 getCategoryDisplayName 函数 (中文化加固)
# 我们直接匹配从 const getCategoryDisplayName = (cat) => { 到下一个 }; 结束的部分
new_disp_func = """const getCategoryDisplayName = (cat) => {
    if (!cat) return "未知分类";
    
    // 哥，这是“地毯式”搜索中文名，优先从对象属性里翻
    const cnName = cat?.name_cn || 
                   cat?.category_name_cn || 
                   cat?.category_cn || 
                   cat?.cn_name || 
                   cat?.name_zh;
                   
    if (cnName && !anyCyrillic(cnName)) return cnName;

    // 兼容对象或原始字符串
    const fullName = (typeof cat === 'string') ? cat : (cat?.category_name || cat?.category || cat?.name || "");
    
    // 尝试提取括号内的中文，例如 "俄文 (中文)"
    const match = fullName.match(/\\((.*?)\\)/);
    if (match) return match[1];

    // 针对 RPA 采集前缀的特殊逻辑
    if (fullName.startsWith('RPA采集_')) {
        const parts = fullName.split('_');
        if (parts.length > 1) {
            const subMatch = parts[1].match(/\\((.*?)\\)/);
            if (subMatch) return subMatch[1];
            return parts[1];
        }
    }

    return fullName.split(' - ')[0];
};"""

# 查找原函数并替换
if 'const getCategoryDisplayName' in content:
    content = re.sub(r'const getCategoryDisplayName = \(cat\) => \{.*?\}\n?\};\n?', new_disp_func + "\n", content, flags=re.DOTALL)

# 2. 注入/更新 forceNum 和过滤逻辑 (保留之前的功能)
force_num_code = """    const forceNum = (v) => {
        if (v === null || v === undefined) return 0;
        if (typeof v === 'number') return v;
        const s = String(v).replace(/\\\\s/g, '').replace(/,/g, '').replace(/\\\\./g, '');
        const nums = s.match(/\\\\d+/);
        return nums ? parseInt(nums[0], 10) : 0;
    };
"""

if 'const forceNum' not in content:
    content = content.replace("const [sortBy, setSortBy] = useState('amount');", 
                              "const [sortBy, setSortBy] = useState('amount');\n\n" + force_num_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Surgery successful - Full Frontend Fix Applied (Category Localization + Indicators)")
