import json

def get_depth(node, d=1):
    children = node.get('children', [])
    if not children:
        return d
    return max([get_depth(c, d + 1) for c in children])

def main():
    try:
        with open('d:/item/ProSourcing/output/algatop_full_tree.json', 'r', encoding='utf-8') as f:
            tree = json.load(f)
        
        if not tree:
            print("Tree is empty.")
            return

        depths = [get_depth(root) for root in tree]
        print(f"Total root nodes: {len(tree)}")
        print(f"Max tree depth: {max(depths)}")
        
        # 统计每一层的节点数
        level_counts = {}
        def count_levels(node, l=1):
            level_counts[l] = level_counts.get(l, 0) + 1
            for c in node.get('children', []):
                count_levels(c, l + 1)
        
        for root in tree:
            count_levels(root)
            
        print("Nodes per level:")
        for l in sorted(level_counts.keys()):
            print(f"  Level {l}: {level_counts[l]} nodes")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
