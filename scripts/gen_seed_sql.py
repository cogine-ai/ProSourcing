import json
import os

def generate_seed_sql():
    input_file = r"d:\item\ProSourcing\kaspi_full_tree_raw.json"
    output_file = r"d:\item\ProSourcing\deployment_package\scripts\seed_data.sql"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    sql_lines = [
        "-- ProSourcing 初始类目数据同步脚本",
        "TRUNCATE TABLE algatop_categories_master CASCADE;"
    ]

    def process_node(node, parent_id=None):
        cid = node.get('code', '')
        name_ru = node.get('title', '').replace("'", "''")
        level = node.get('level', 0)
        sub_nodes = node.get('subNodes')
        is_leaf = sub_nodes is None or len(sub_nodes) == 0
        
        # 过滤掉顶层的 desktop-menu 虚拟节点
        if cid == "desktop-menu":
            if sub_nodes:
                for sub in sub_nodes:
                    process_node(sub, None)
            return

        # 插入语句
        p_id_str = f"'{parent_id}'" if parent_id else "NULL"
        sql = f"INSERT INTO algatop_categories_master (algatop_id, name_ru, parent_id, level, is_leaf) VALUES ('{cid}', '{name_ru}', {p_id_str}, {level}, {str(is_leaf).upper()}) ON CONFLICT (algatop_id) DO NOTHING;"
        sql_lines.append(sql)

        if sub_nodes:
            for sub in sub_nodes:
                process_node(sub, cid)

    process_node(data)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(sql_lines))
    
    print(f"Success: {output_file} generated with {len(sql_lines)} lines.")

if __name__ == "__main__":
    generate_seed_sql()
