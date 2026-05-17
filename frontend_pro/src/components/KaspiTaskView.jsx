import React, { useEffect, useState } from 'react';
import { useTaskStore } from '../store/useTaskStore';
import { Loader2, PlusCircle, CheckCircle2, ChevronRight, Play, Trash2, X } from 'lucide-react';
import { PDL } from '../lib/pdl';

const API_BASE = window.location.origin;

function TreeNode({ node, level = 0 }) {
    const { selectedLeafIds, addLeaf, removeLeaf } = useTaskStore();
    const isLeaf = node.is_leaf;
    const checked = isLeaf && selectedLeafIds.has(node.category_code);
    const indeterminate = !isLeaf && node.children?.some(c => hasSelectedChild(c, selectedLeafIds));

    // recursive helper to check if any descendant is selected
    function hasSelectedChild(n, selectedSet) {
        if (n.is_leaf) return selectedSet.has(n.category_code);
        return n.children?.some(child => hasSelectedChild(child, selectedSet));
    }

    const toggle = () => {
        if (isLeaf) {
            checked ? removeLeaf(node.category_code) : addLeaf(node.category_code);
        } else {
            const ids = collectLeafIds(node);
            const allChecked = ids.every(id => selectedLeafIds.has(id));
            ids.forEach(id => (allChecked ? removeLeaf(id) : addLeaf(id)));
        }
    };

    const collectLeafIds = (n) => {
        if (n.is_leaf) return [n.category_code];
        return n.children?.flatMap(collectLeafIds) || [];
    };

    const [expanded, setExpanded] = useState(level < 1); // Expand top level by default

    // Format Kaspi names to avoid HTML entities if any
    const displayName = node.title || node.category_code;

    return (
        <div className="pl-4 border-l border-border/30 ml-2 mt-1 relative">
            <div className={`flex items-start gap-2 py-1 ${isLeaf ? 'text-sm' : 'font-medium'} hover:bg-muted/10 rounded cursor-pointer transition-colors`} >
                <div className="pt-0.5 flex items-center justify-center gap-1">
                    {!isLeaf && (
                        <div onClick={() => setExpanded(!expanded)} className="p-0.5 hover:bg-border/50 rounded inline-flex items-center justify-center">
                            <ChevronRight size={14} className={`transition-transform opacity-70 ${expanded ? 'rotate-90' : ''}`} />
                        </div>
                    )}
                    <input
                        type="checkbox"
                        className="accent-primary w-3.5 h-3.5 mt-0.5 cursor-pointer"
                        checked={isLeaf ? checked : collectLeafIds(node).every(id => selectedLeafIds.has(id)) && collectLeafIds(node).length > 0}
                        ref={(el) => {
                            if (el && !isLeaf) {
                                const ids = collectLeafIds(node);
                                const someChecked = ids.some(id => selectedLeafIds.has(id));
                                const allChecked = ids.every(id => selectedLeafIds.has(id)) && ids.length > 0;
                                el.indeterminate = someChecked && !allChecked;
                            }
                        }}
                        onChange={toggle}
                    />
                </div>
                <div className="flex-1 cursor-pointer select-none" onClick={() => !isLeaf && setExpanded(!expanded)}>
                    <span className={`${isLeaf ? 'text-muted-foreground font-medium' : 'text-foreground'}`}>{displayName}</span>
                    {isLeaf && node.last_crawl_date && (
                        <span className="ml-2 text-[10px] font-mono text-muted-foreground/80 dark:text-muted-foreground">
                            ({node.last_crawl_date})
                        </span>
                    )}
                    {isLeaf ? '' : <span className="text-[10px] ml-2 opacity-30">({collectLeafIds(node).length})</span>}
                </div>
            </div>
            {expanded && !isLeaf && node.children && node.children.length > 0 && (
                <div className="mt-1">
                    {node.children.map(child => (
                        <TreeNode key={child.category_code} node={child} level={level + 1} />
                    ))}
                </div>
            )}
        </div>
    );
}

export function KaspiTaskView() {
    const [tree, setTree] = useState([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const { selectedLeafIds, clearAll, removeLeaf } = useTaskStore();

    useEffect(() => {
        fetch(`${API_BASE}/api/kaspi/tree`)
            .then(res => res.json())
            .then(data => {
                setTree(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching Kaspi tree", err);
                setLoading(false);
            });
    }, []);

    // Create a flat map for quick access
    const [leafMap, setLeafMap] = useState({});

    useEffect(() => {
        if (!tree.length) return;
        const map = {};
        const walk = (n, path = [], nodePath = []) => {
            const currentPath = [...path, n.title || n.category_code];
            const currentNodePath = [...nodePath, n];
            if (n.is_leaf) {
                const topNode = currentNodePath[0];
                map[n.category_code] = {
                    ...n,
                    fullPath: currentPath,
                    topCategoryId: topNode?.category_code,
                    topCategoryNameCn: topNode?.title,
                };
            }
            n.children?.forEach(c => walk(c, currentPath, currentNodePath));
        };
        tree.forEach(n => walk(n));
        setLeafMap(map);
    }, [tree]);

    const selectedLeavesList = Array.from(selectedLeafIds).map(id => leafMap[id]).filter(Boolean);

    const handleCreateTasks = async () => {
        if (selectedLeavesList.length === 0) return;
        setSubmitting(true);
        try {
            const ids = selectedLeavesList.map((leaf) => ({
                category_code: leaf.category_code,
                top_category_id: leaf.topCategoryId,
                top_category_name_cn: leaf.topCategoryNameCn,
            }));
            const res = await fetch(`${API_BASE}/api/kaspi/tasks/batch`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(ids),
            });
            const data = await res.json();
            if (data.success) {
                alert(data.message || `已成功分发 ${data.count} 条任务！`);
                clearAll();
            } else {
                alert("创建失败: " + (data.message || "未知错误"));
            }
        } catch (err) {
            console.error(err);
            alert("网络请求失败，请检查后端服务是否正常运行");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center h-[500px] text-muted-foreground gap-4">
                <Loader2 size={32} className="animate-spin text-primary" />
                <p className="font-mono text-sm tracking-widest uppercase">Fetching Original Kaspi Catalog...</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full min-h-[500px]">
            <div className="flex flex-1 overflow-hidden gap-6 bg-transparent">
                {/* Left Drawer: Category Tree */}
                <aside className={`w-[45%] h-full flex flex-col bg-card/50 backdrop-blur-md rounded-2xl border border-border/30 overflow-hidden shadow-xl`}>
                    <div className="p-4 border-b border-border/20 bg-muted/10 font-black tracking-widest uppercase text-sm flex items-center justify-between">
                        <span>全量分类模型 ({tree.length} 类)</span>
                    </div>
                    <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                        {tree.map(rootNode => (
                            <TreeNode key={rootNode.category_code} node={rootNode} />
                        ))}
                    </div>
                </aside>

                {/* Right: Selected Pool */}
                <main className={`w-[55%] flex flex-col bg-card/50 backdrop-blur-md rounded-2xl border border-border/30 overflow-hidden shadow-xl relative`}>
                    <div className="p-4 border-b border-border/20 bg-muted/10 flex items-center justify-between">
                        <span className="font-black tracking-widest uppercase text-sm">任务池 </span>
                        <div className="flex items-center gap-3">
                            <span className="font-mono text-xs text-primary font-bold bg-primary/10 px-3 py-1 rounded-full">已选择 {selectedLeavesList.length} </span>
                            {selectedLeavesList.length > 0 && (
                                <button
                                    onClick={clearAll}
                                    className="p-1.5 text-muted-foreground hover:text-rose-500 hover:bg-rose-500/10 rounded transition-colors"
                                    title="清空所有选择"
                                >
                                    <Trash2 size={16} />
                                </button>
                            )}
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto p-6 custom-scrollbar space-y-3 pb-[80px]">
                        {selectedLeavesList.length === 0 ? (
                            <div className="h-full flex flex-col items-center justify-center opacity-30 mix-blend-luminosity grayscale gap-2">
                                <PlusCircle size={48} />
                                <span className="uppercase tracking-widest text-[10px] font-black">NO LEAF SELECTED YET</span>
                            </div>
                        ) : (
                            selectedLeavesList.map(leaf => (
                                <div key={leaf.category_code} className={`p-4 rounded-xl border border-border/40 bg-card hover:bg-muted/10 shadow-sm transition-all animate-in fade-in slide-in-from-bottom-2 flex items-start justify-between group/item`}>
                                    <div className="flex-1 min-w-0 pr-4">
                                        <h4 className="font-bold text-foreground">{leaf.title}</h4>
                                        <p className="text-xs text-muted-foreground font-mono mt-1 opacity-60 truncate">
                                            {leaf.fullPath.join(" / ")}
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => removeLeaf(leaf.category_code)}
                                        className="p-1.5 text-muted-foreground/40 hover:text-rose-500 hover:bg-rose-500/10 rounded transition-colors opacity-0 group-hover/item:opacity-100"
                                        title="取消勾选"
                                    >
                                        <X size={16} />
                                    </button>
                                </div>
                            ))
                        )}
                    </div>

                    {/* Footer Action */}
                    <div className="absolute bottom-0 left-0 w-full p-4 bg-gradient-to-t from-background via-background/90 to-transparent border-t border-transparent pointer-events-none">
                        <button
                            disabled={selectedLeavesList.length === 0 || submitting}
                            onClick={handleCreateTasks}
                            className={`pointer-events-auto w-full flex items-center justify-center gap-2 py-3.5 rounded-xl font-black uppercase tracking-widest text-sm transition-all shadow-xl shadow-primary/20 ${selectedLeavesList.length > 0 ? 'bg-primary text-primary-foreground hover:opacity-90 active:scale-95 cursor-pointer' : 'bg-muted text-muted-foreground opacity-50 cursor-not-allowed'}`}
                        >
                            {submitting ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} fill="currentColor" />}
                            {submitting ? 'DISPATCHING...' : `DISPATCH ${selectedLeavesList.length} TASKS`}
                        </button>
                    </div>
                </main>
            </div>
        </div>
    );
}
