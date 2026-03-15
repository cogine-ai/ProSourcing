import asyncio
import json
import os
import re
from deep_translator import GoogleTranslator

# 哥，咱们这次用“唯一字串映射”法，起飞！

def merge_data():
    print("🚀 Starting Optimized Force Translation Journey...")
    
    # 1. 加载基础树数据
    tree_path = 'd:/item/ProSourcing/output/algatop_full_tree.json'
    with open(tree_path, 'r', encoding='utf-8') as f:
        full_tree = json.load(f)

    # 2. 拍平并去重类目节点
    master_list_flat = []
    def flatten_tree(nodes_tree, level=1, parent_id=None):
        for node in nodes_tree:
            master_list_flat.append({
                "algatop_id": node['id'],
                "name_ru": node['name'],
                "parent_id": parent_id,
                "level": level,
                "is_leaf": len(node.get('children', [])) == 0
            })
            flatten_tree(node.get('children', []), level + 1, node['id'])

    flatten_tree(full_tree)
    unique_nodes = {n['algatop_id']: n for n in master_list_flat}
    dedup_list = list(unique_map.values()) if 'unique_map' in locals() else list(unique_nodes.values())
    
    # 哥，这里是提速关键：提取唯一俄文名
    unique_names = list(set([n['name_ru'] for n in dedup_list if n['name_ru']]))
    print(f"Total Nodes: {len(dedup_list)}, Unique Russian Names: {len(unique_names)}")

    translation_cache = {} # ru -> (cn, en)
    
    # 3. 极速翻译单元
    async def translate_name(ru_name):
        try:
            t_cn = GoogleTranslator(source='ru', target='zh-CN')
            t_en = GoogleTranslator(source='ru', target='en')
            cn = await asyncio.to_thread(t_cn.translate, ru_name)
            en = await asyncio.to_thread(t_en.translate, ru_name)
            return ru_name, (cn if cn else ru_name, en if en else "")
        except:
            return ru_name, (ru_name, "")

    async def safe_translate(name, t_cn, t_en):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 哥，咱们自己实现重试，不行就让它等一小会儿
                cn = t_cn.translate(name)
                en = t_en.translate(name)
                return name, (cn if cn else name, en if en else "")
            except Exception as e:
                # 等待一会儿再重试
                await asyncio.sleep(1 + attempt * 2)
        # 如果彻底失败，原汁原味返回
        return name, (name, "")

    # 4. 批量翻译唯一字串
    async def process_translations():
        batch_size = 10 # 哥，调低一点并发，稳拿
        
        for i in range(0, len(unique_names), batch_size):
            chunk = unique_names[i : i + batch_size]
            
            # 每批新建翻译器，规避状态污染并尝试刷新限制
            t_cn = GoogleTranslator(source='ru', target='zh-CN')
            t_en = GoogleTranslator(source='ru', target='en')
            
            tasks = [safe_translate(n, t_cn, t_en) for n in chunk]
            results = await asyncio.gather(*tasks)
            for ru, mapped in results:
                translation_cache[ru] = mapped
            
            print(f"  Translation Progress: {min(i + batch_size, len(unique_names))}/{len(unique_names)} cached...")
            # 必须加上延迟，不能一味拉满
            await asyncio.sleep(0.5)

    print("Step 1: Building Translation Cache...")
    asyncio.run(process_translations())

    # 5. 回填数据
    print("Step 2: Mapping Cache back to Nodes...")
    final_master = []
    for node in dedup_list:
        cn, en = translation_cache.get(node['name_ru'], (node['name_ru'], ""))
        node['name_cn'] = cn
        node['name_en'] = en
        final_master.append(node)

    # 排序并保存
    final_master.sort(key=lambda x: (x['level'], x['algatop_id']))
    output_path = "d:/item/ProSourcing/output/algatop_master_final.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_master, f, ensure_ascii=False, indent=2)
    
    print(f"🎉 Optimized Master Table ready with {len(final_master)} records!")

if __name__ == "__main__":
    merge_data()
