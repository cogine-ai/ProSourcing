def structural_leaf_codes_from_p_map(p_map):
    """Category codes that have no children in the parent map."""
    all_nodes = [node for children in p_map.values() for node in children]
    parents_with_kids = {node["parent_code"] for node in all_nodes if node.get("parent_code")}
    return {
        node["category_code"]
        for node in all_nodes
        if node["category_code"] not in parents_with_kids
    }


def mark_tree_leaves(nodes):
    """Infer leaf flags from tree shape so UI selection works without DB is_leaf."""
    for node in nodes:
        children = node.get("children") or []
        if children:
            mark_tree_leaves(children)
            node["is_leaf"] = False
        else:
            node["is_leaf"] = True
