from api.category_tree_utils import mark_tree_leaves, structural_leaf_codes_from_p_map


def test_structural_leaf_codes_from_p_map():
    p_map = {
        "": [
            {"category_code": "root", "parent_code": ""},
        ],
        "root": [
            {"category_code": "leaf-a", "parent_code": "root"},
            {"category_code": "mid", "parent_code": "root"},
        ],
        "mid": [
            {"category_code": "leaf-b", "parent_code": "mid"},
        ],
    }

    assert structural_leaf_codes_from_p_map(p_map) == {"leaf-a", "leaf-b"}


def test_mark_tree_leaves():
    tree = [
        {
            "category_code": "root",
            "is_leaf": False,
            "children": [
                {"category_code": "leaf-a", "is_leaf": False, "children": []},
                {
                    "category_code": "mid",
                    "is_leaf": False,
                    "children": [
                        {"category_code": "leaf-b", "is_leaf": False, "children": []},
                    ],
                },
            ],
        }
    ]

    mark_tree_leaves(tree)

    assert tree[0]["is_leaf"] is False
    assert tree[0]["children"][0]["is_leaf"] is True
    assert tree[0]["children"][1]["is_leaf"] is False
    assert tree[0]["children"][1]["children"][0]["is_leaf"] is True
