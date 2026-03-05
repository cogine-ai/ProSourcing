import React, { useState, useEffect } from 'react';
import './index.css';
import { PDL } from './lib/pdl';
import Breadcrumbs from './components/Breadcrumbs';
import {
    LayoutDashboard,
    Target,
    History,
    Settings2,
    RefreshCw,
    Package,
    TrendingUp,
    BarChart3,
    Play,
    Download,
    Search,
    ChevronRight,
    Loader2,
    CheckCircle2,
    XCircle,
    Bell,
    ArrowUpRight,
    ChevronDown,
    Users,
    LineChart,
    Sun,
    Moon
} from 'lucide-react';

const API_BASE = "http://localhost:8000";

// --- 原子组件：指标卡片 ---
const StatCard = ({ label, value, icon }) => (
    <div className={`bg-card border border-border ${PDL.radius.card} rounded-card-force p-7 hover:border-primary/40 transition-all shadow-sm group relative overflow-hidden h-full`}>
        <div className="flex items-center justify-between mb-5">
            <div className={`p-3 ${PDL.radius.inner} bg-muted/40 border border-border group-hover:scale-105 transition-transform`}>
                {icon}
            </div>
            <ArrowUpRight size={16} className="text-muted-foreground opacity-30" />
        </div>
        <p className={`${PDL.typography.label} text-muted-foreground mb-1`}>{label}</p>
        <p className={`${PDL.typography.stat} text-foreground line-clamp-1`}>{value}</p>
    </div>
);

// --- 原子组件：类目卡片 ---
const CategoryCard = ({ cat }) => {
    const ratio = cat.sale_product_qty > 0 ? (cat.monthly_sales / cat.sale_product_qty).toFixed(2) : 0;

    // 拆分中俄双语：假设格式为 "俄语 (中文)"
    const nameParts = cat.category_name.match(/^(.*)\s\((.*)\)$/);
    const ruName = nameParts ? nameParts[1] : cat.category_name;
    const zhName = nameParts ? nameParts[2] : "";

    return (
        <div className={`bg-card border border-border ${PDL.radius.card} rounded-card-force p-10 hover:border-primary/50 transition-all shadow-md group flex flex-col justify-between h-full min-h-[440px]`}>
            {/* 头部：标题区域 */}
            <div className="mb-8">
                <h3 className="text-[32px] font-black leading-tight text-foreground group-hover:text-primary transition-colors flex flex-col gap-1">
                    <span>{zhName || ruName}</span>
                    {zhName && <span className="text-xs font-bold text-muted-foreground/30 font-mono italic">/ {ruName}</span>}
                </h3>
                <div className="mt-4 flex items-center gap-2">
                    <span className="text-[10px] bg-muted/30 text-muted-foreground px-2 py-0.5 rounded-full font-bold uppercase border border-border/50">子类数: {cat.leaf_count || '--'}</span>
                </div>
            </div>

            {/* 中间：核心指标 (垂直排版，字号回归理性) */}
            <div className="flex flex-col gap-6">
                <div className="group/item">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mb-1 border-l-2 border-primary/20 pl-3">月销售数量</p>
                    <p className="text-2xl font-black text-foreground tracking-tight transition-transform group-hover/item:translate-x-1">{(cat.monthly_sales || 0).toLocaleString()}</p>
                </div>

                <div className="group/item">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mb-1 border-l-2 border-border pl-3">全量产品数</p>
                    <p className="text-xl font-bold text-muted-foreground tracking-tight transition-transform group-hover/item:translate-x-1">{(cat.sale_product_qty || 0).toLocaleString()}</p>
                </div>
            </div>

            {/* 底部：效率指标 */}
            <div className="mt-10 pt-6 border-t border-border/10">
                <div className="flex justify-between items-center">
                    <div className="flex flex-col">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-primary/50">销品比效率</p>
                        <p className="text-[10px] text-muted-foreground/20 font-mono">RATIO ANALYSIS</p>
                    </div>
                    <p className="text-3xl font-black text-primary font-mono tracking-tighter">{ratio}</p>
                </div>
            </div>
        </div>
    );
};

const App = () => {
    const [taskProducts, setTaskProducts] = useState([]);
    const [activeTab, setActiveTab] = useState('market');
    const [isDark, setIsDark] = useState(true);
    const [categories, setCategories] = useState([]);
    const [allCategories, setAllCategories] = useState([]);
    const [tasks, setTasks] = useState([]);
    const [selectedTask, setSelectedTask] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCats, setSelectedCats] = useState([]);
    const [currentTopCategory, setCurrentTopCategory] = useState(null);
    const [loading, setLoading] = useState(false);

    const [expandedNodes, setExpandedNodes] = useState(new Set());

    const [globalStats, setGlobalStats] = useState({
        top_cat_count: 0,
        min_cat_count: 1248,
        sku_count: "154.2K",
    });

    // 主题逻辑挂载
    useEffect(() => {
        const root = window.document.documentElement;
        if (isDark) root.classList.add('dark');
        else root.classList.remove('dark');
    }, [isDark]);

    // 数据获取
    useEffect(() => {
        fetchTopStats();
        fetchHistory();
        fetchAllCategories();
        const interval = setInterval(fetchHistory, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchTopStats = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/categories/top_stats`);
            const data = await res.json();
            setCategories(data);
            setGlobalStats(prev => ({ ...prev, top_cat_count: data.length }));
        } catch (err) { console.error("Fetch top stats failed", err); }
    };

    const fetchAllCategories = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/categories/tree`);
            const data = await res.json();
            setAllCategories(data);
        } catch (err) { console.error("Fetch all categories failed", err); }
    };

    const fetchHistory = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/tasks/history`);
            const data = await res.json();
            setTasks(data);
        } catch (err) { console.error("Fetch history failed", err); }
    };

    // 获取抽屉类目树 (一级分类)
    // 此功能已集成到任务页主列表，保留基础树获取逻辑用于其他可能的引用或初始化
    const fetchLeafCategories = async (topId) => {
        // 检查是否已加载
        const target = categories.find(c => c.category_id === topId);
        if (target && target.leaves) return;

        // 设置 loading
        setCategories(prev => prev.map(c => c.category_id === topId ? { ...c, loadingLeaves: true } : c));

        try {
            const res = await fetch(`${API_BASE}/api/categories/${topId}/leaves`);
            const leaves = await res.json();
            setCategories(prev => prev.map(c => c.category_id === topId ? { ...c, leaves, loadingLeaves: false } : c));
        } catch (err) {
            console.error("Fetch leaves failed", err);
            setCategories(prev => prev.map(c => c.category_id === topId ? { ...c, loadingLeaves: false } : c));
        }
    };


    const handleCreateTask = async (categoryName) => {
        try {
            const res = await fetch(`${API_BASE}/api/tasks/category`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category: categoryName })
            });
            if (res.ok) {
                alert("哥，任务发下去了，在后台跑着呢！");
                fetchHistory();
                setShowDrawer(false);
            }
        } catch (error) { console.error("Create task failed", error); }
    };

    const handleToggleLeaf = (leafId) => {
        setSelectedCats(prev =>
            prev.includes(leafId) ? prev.filter(id => id !== leafId) : [...prev, leafId]
        );
    };

    const handleToggleAllLeaves = (topCat) => {
        if (!topCat.leaves || topCat.leaves.length === 0) return;

        const leafIds = topCat.leaves.map(l => l.category_id);
        const allSelected = leafIds.every(id => selectedCats.includes(id));

        if (allSelected) {
            setSelectedCats(prev => prev.filter(id => !leafIds.includes(id)));
        } else {
            setSelectedCats(prev => Array.from(new Set([...prev, ...leafIds])));
        }
    };

    const startBatchTask = async () => {
        if (selectedCats.length === 0) return;
        setLoading(true);

        // 找出所有选中的叶子类目对象，以便获取其名称
        // 由于类目是按大类分加载的，我们需要从 categories 中寻找
        const allKnownLeaves = categories.flatMap(c => c.leaves || []);

        for (const catId of selectedCats) {
            const leaf = allKnownLeaves.find(l => l.category_id === catId);
            const targetName = leaf ? leaf.category_name : catId; // 降级使用 ID

            await fetch(`${API_BASE}/api/tasks/category`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category: targetName })
            });
        }
        setSelectedCats([]);
        setLoading(false);
        fetchHistory();
        setActiveTab('archives');
    };

    // 穿透获取任务详情数据
    useEffect(() => {
        if (selectedTask) {
            const fetchTaskData = async () => {
                try {
                    const res = await fetch(`${API_BASE}/api/tasks/${selectedTask.id}/data`);
                    const data = await res.json();
                    setTaskProducts(data);
                } catch (err) { console.error("Fetch task products failed", err); }
            };
            fetchTaskData();
        } else {
            setTaskProducts([]);
        }
    }, [selectedTask]);

    return (
        <div className="flex h-screen bg-background text-foreground overflow-hidden font-sans transition-colors duration-300">

            {/* 1. Sidebar (Fixed) */}
            <aside className={`${PDL.layout.sidebarWidth} border-r bg-card flex flex-col shrink-0 transition-colors duration-300 z-50`}>
                <div className={`${PDL.layout.headerHeight} flex items-center px-6 border-b`}>
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shadow-lg shadow-primary/20">
                            <Package className="text-primary-foreground w-5 h-5" />
                        </div>
                        <span className="font-bold text-lg tracking-tight text-foreground">ProSourcing</span>
                    </div>
                </div>

                <div className="p-4 flex-1 space-y-6 overflow-y-auto">
                    <nav className="space-y-1">
                        {[
                            { id: 'market', label: '首页', icon: <LayoutDashboard size={18} /> },
                            { id: 'tasks', label: '采集任务', icon: <Target size={18} /> },
                            { id: 'archives', label: '选品报告', icon: <History size={18} /> },
                            { id: 'algo', label: '算法配置', icon: <Settings2 size={18} /> },
                            { id: 'settings', label: '系统管理', icon: <Users size={18} /> },
                        ].map((item) => (
                            <button
                                key={item.id}
                                onClick={() => setActiveTab(item.id)}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm font-semibold group ${activeTab === item.id ? 'bg-accent text-accent-foreground shadow-sm' : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                                    }`}
                            >
                                <span className={`${activeTab === item.id ? 'text-primary' : 'text-muted-foreground group-hover:text-primary transition-colors'}`}>
                                    {item.icon}
                                </span>
                                {item.label}
                            </button>
                        ))}
                    </nav>
                </div>

                <div className="p-4 border-t bg-muted/20">
                    <div className="flex items-center gap-3 px-2">
                        <div className="w-9 h-9 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-primary font-bold">Y</div>
                        <div className="min-w-0">
                            <p className="text-[10px] text-muted-foreground font-bold uppercase truncate tracking-tight">System Admin</p>
                            <p className="text-sm font-bold truncate text-foreground">哥，你好</p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* 2. Main Container (Sticky Header + Scrollable Content) */}
            <div className="flex-1 flex flex-col min-w-0 relative">

                {/* Header (Fixed) */}
                <header className={`${PDL.layout.headerHeight} flex items-center justify-between px-8 border-b bg-background/60 backdrop-blur-xl shrink-0 sticky top-0 z-40 transition-colors duration-300`}>
                    <div className="flex items-center gap-4">
                        <h2 className="text-sm font-black text-foreground uppercase tracking-[0.2em]">{activeTab} //</h2>
                    </div>

                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => setIsDark(!isDark)}
                            className="p-2 rounded-xl bg-muted/50 border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-all active:scale-90"
                        >
                            {isDark ? <Sun size={18} /> : <Moon size={18} />}
                        </button>

                        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></div>
                            <span className="text-[10px] font-bold text-emerald-500 uppercase">Engine Online</span>
                        </div>

                        <button className="p-2 text-muted-foreground hover:text-foreground transition-colors relative">
                            <Bell size={20} />
                            <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-rose-500 rounded-full"></span>
                        </button>
                    </div>
                </header>

                {/* 3. Content Area (Scrollable) */}
                <main className={`flex-1 overflow-y-auto ${PDL.layout.contentPadding} bg-background/30 transition-colors duration-300`}>
                    <div className="max-w-[1600px] 2xl:max-w-[1800px] mx-auto">

                        {/* Breadcrumb - 放置在 Header 下方，Content 区域上方 */}
                        <Breadcrumbs activeTab={activeTab} />

                        {/* --- 视图：首页 --- */}
                        {activeTab === 'market' && (
                            <div className={PDL.spacing.section}>
                                <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 ${PDL.spacing.gap}`}>
                                    <StatCard label="入库的一级品类数量" value={globalStats.top_cat_count} icon={<Package className="text-blue-500" />} />
                                    <StatCard label="最小品类数据" value={globalStats.min_cat_count} icon={<BarChart3 className="text-emerald-500" />} />
                                    <StatCard label="商品sku数据" value={globalStats.sku_count} icon={<TrendingUp className="text-indigo-500" />} />
                                    <StatCard label="已生成选品报告数量" value={tasks.filter(t => t.status === 'completed').length} icon={<History className="text-rose-500" />} />
                                </div>

                                <div className={PDL.spacing.section}>
                                    <div className="flex items-center justify-between">
                                        <h3 className="text-xl font-black text-foreground tracking-tight flex items-center gap-3">
                                            <div className="w-1 h-6 bg-primary rounded-full"></div>
                                            全量一级分类运行详情
                                        </h3>
                                        <div className="text-[10px] font-bold text-muted-foreground uppercase bg-muted/20 px-3 py-1 rounded-full border border-border">Real-time Syncing</div>
                                    </div>
                                    <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 3xl:grid-cols-6 ${PDL.spacing.gap}`}>
                                        {categories.map((cat, i) => <CategoryCard key={i} cat={cat} />)}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* --- 视图：采集任务 --- */}
                        {activeTab === 'tasks' && (
                            <div className={PDL.spacing.section}>
                                <div className={`bg-card ${PDL.spacing.cardPadding} ${PDL.radius.card} border border-border flex justify-between items-center shadow-sm mb-6`}>
                                    <div className="space-y-1">
                                        <h1 className={`${PDL.typography.title} text-foreground`}>采集任务</h1>
                                        <p className="text-muted-foreground text-sm">哥，这里是目前系统收录的所有大类。点击展开后，勾选底部的“最小子类”即可发起作战。勾选大类立得全选。</p>
                                    </div>
                                    <div className="flex gap-4 items-center">
                                        {selectedCats.length > 0 && (
                                            <button
                                                onClick={startBatchTask}
                                                className={`inline-flex items-center gap-3 px-8 py-3.5 ${PDL.radius.button} bg-primary text-primary-foreground hover:opacity-90 font-black text-sm shadow-xl shadow-primary/20 active:scale-95 transition-all`}
                                            >
                                                {loading ? <Loader2 className="animate-spin" /> : <Play size={18} fill="currentColor" />}
                                                启动作战 ({selectedCats.length})
                                            </button>
                                        )}
                                    </div>
                                </div>

                                <div className="space-y-4">
                                    {categories.map((topCat) => {
                                        const isExpanded = expandedNodes.has(topCat.category_id);
                                        // 解析大类名称
                                        const nameParts = topCat.category_name.match(/^(.*)\s\((.*)\)$/);
                                        const ruName = nameParts ? nameParts[1] : topCat.category_name;
                                        const zhName = nameParts ? nameParts[2] : "";

                                        return (
                                            <div key={topCat.category_id} className={`bg-card ${PDL.radius.card} border border-border shadow-sm overflow-hidden transition-all`}>
                                                <div
                                                    className={`px-8 py-5 flex items-center justify-between cursor-pointer hover:bg-muted/30 transition-colors ${isExpanded ? 'bg-muted/20 border-b border-border/50' : ''}`}
                                                    onClick={() => {
                                                        const next = new Set(expandedNodes);
                                                        if (isExpanded) {
                                                            next.delete(topCat.category_id);
                                                        } else {
                                                            next.add(topCat.category_id);
                                                        }
                                                        setExpandedNodes(next);
                                                    }}
                                                >
                                                    <div className="flex items-center gap-4">
                                                        <div className={`w-6 h-6 flex items-center justify-center rounded transition-transform ${isExpanded ? 'rotate-90 bg-primary/20 text-primary' : 'text-muted-foreground'}`}>
                                                            <ChevronRight size={18} />
                                                        </div>
                                                        <div>
                                                            <h3 className="text-xl font-black text-foreground flex flex-col leading-tight">
                                                                <span>{zhName || ruName}</span>
                                                                {zhName && <span className="text-[10px] font-bold text-muted-foreground/40 font-mono italic">/ {ruName}</span>}
                                                            </h3>
                                                            <p className="text-[10px] text-muted-foreground font-mono uppercase tracking-tighter mt-1">ID: {topCat.category_id} // SALES: {(topCat.monthly_sales || 0).toLocaleString()}</p>
                                                        </div>
                                                    </div>

                                                    <div className="flex items-center gap-6">
                                                        <div className="text-right">
                                                            <p className="text-[10px] font-black text-muted-foreground/40 uppercase">Sub-Categories</p>
                                                            <p className="text-sm font-bold text-foreground">{topCat.leaf_count || (topCat.leaves || []).length || '--'}</p>
                                                        </div>
                                                        <div
                                                            className={`w-10 h-10 flex items-center justify-center ${PDL.radius.inner} border-2 transition-all ${(topCat.leaves || []).length > 0 && topCat.leaves.every(l => selectedCats.includes(l.category_id)) ? 'bg-primary border-primary text-primary-foreground' : 'border-border text-transparent'
                                                                }`}
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                handleToggleAllLeaves(topCat);
                                                            }}
                                                        >
                                                            <CheckCircle2 size={20} className={(topCat.leaves || []).length > 0 && topCat.leaves.every(l => selectedCats.includes(l.category_id)) ? 'opacity-100' : 'opacity-0'} />
                                                        </div>
                                                    </div>
                                                </div>

                                                {isExpanded && (
                                                    <div className="p-0 border-t border-border/10 bg-muted/5">
                                                        {(!topCat.leaves || topCat.leaves.length === 0) ? (
                                                            <div className="py-12 flex flex-col items-center justify-center text-muted-foreground/30 gap-1">
                                                                <XCircle size={20} className="opacity-20" />
                                                                <p className="text-[10px] font-black uppercase tracking-widest italic">暂无子类数据 // NO DATA</p>
                                                            </div>
                                                        ) : (
                                                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 p-6 max-h-[500px] overflow-y-auto">
                                                                {(topCat.leaves || []).map(leaf => {
                                                                    const leafNameParts = leaf.category_name.match(/^(.*)\s\((.*)\)$/);
                                                                    const lRuName = leafNameParts ? leafNameParts[1] : leaf.category_name;
                                                                    const lZhName = leafNameParts ? leafNameParts[2] : "";
                                                                    const isSelected = selectedCats.includes(leaf.category_id);

                                                                    return (
                                                                        <div
                                                                            key={leaf.category_id}
                                                                            className={`p-4 rounded-xl border transition-all cursor-pointer flex items-center justify-between group ${isSelected ? 'bg-primary/5 border-primary shadow-sm' : 'bg-card border-border hover:border-primary/40'
                                                                                }`}
                                                                            onClick={() => handleToggleLeaf(leaf.category_id)}
                                                                        >
                                                                            <div className="min-w-0 pr-4">
                                                                                <p className={`text-sm font-bold truncate ${isSelected ? 'text-primary' : 'text-foreground'}`}>{lZhName || lRuName}</p>
                                                                                <p className="text-[10px] text-muted-foreground/50 truncate font-mono italic">{lRuName}</p>
                                                                            </div>
                                                                            <div className={`w-5 h-5 rounded border-2 shrink-0 transition-all flex items-center justify-center ${isSelected ? 'bg-primary border-primary' : 'border-border'}`}>
                                                                                {isSelected && <CheckCircle2 size={12} className="text-primary-foreground" />}
                                                                            </div>
                                                                        </div>
                                                                    );
                                                                })}
                                                            </div>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        )}

                        {/* --- 视图：选品报告 --- */}
                        {activeTab === 'archives' && (
                            <div className={PDL.spacing.section}>
                                <div className={`bg-card ${PDL.spacing.cardPadding} ${PDL.radius.card} border border-border mb-8 shadow-sm`}>
                                    <h1 className={`${PDL.typography.title} text-foreground mb-1`}>选品报告</h1>
                                    <p className="text-muted-foreground text-sm">作战情报已就绪。支持导出 Excel 与 6 个月历史趋势对比分析。</p>
                                </div>

                                <div className="grid grid-cols-1 gap-6">
                                    {tasks.map((task, i) => (
                                        <div
                                            key={i}
                                            className={`bg-card border border-border ${PDL.radius.card} rounded-card-force ${PDL.spacing.cardPadding} hover:border-primary/40 shadow-sm group cursor-pointer transition-all`}
                                            onClick={() => setSelectedTask(task)}
                                        >
                                            <div className="flex items-start justify-between">
                                                <div className="flex gap-6">
                                                    <div className={`w-14 h-14 ${PDL.radius.inner} flex items-center justify-center border-2 ${task.status === 'completed' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500' :
                                                        'bg-blue-500/10 border-blue-500/30 text-blue-500 animate-pulse'
                                                        }`}>
                                                        {task.status === 'completed' ? <CheckCircle2 size={24} /> : <Loader2 size={24} className="animate-spin" />}
                                                    </div>
                                                    <div className="space-y-2">
                                                        <h4 className="text-xl font-bold text-foreground">{task.category} <span className="text-[10px] font-mono text-muted-foreground ml-3 tracking-normal opacity-40">TASKID_{task.id.slice(0, 8)}</span></h4>
                                                        <div className="flex flex-wrap gap-5 text-xs font-bold text-muted-foreground uppercase tracking-widest">
                                                            <div className="flex items-center gap-2"><History size={14} className="text-primary" /> {new Date(task.created_at).toLocaleDateString()}</div>
                                                            <div className="flex items-center gap-2"><Package size={14} className="text-blue-500" /> 产品: {task.category_stats?.sale_product_qty || '--'}</div>
                                                            <div className="flex items-center gap-2"><BarChart3 size={14} className="text-emerald-500" /> 销售: {task.category_stats?.sale_qty?.toLocaleString() || '--'}</div>
                                                            <div className="flex items-center gap-2"><LineChart size={14} className="text-indigo-500" /> ABC: {task.category_stats?.amount_abc || 'A/B/C'}</div>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex gap-3">
                                                    {task.excel_path && (
                                                        <a
                                                            href={`${API_BASE}/api/download?path=${encodeURIComponent(task.excel_path)}`}
                                                            className={`h-11 px-5 flex items-center gap-2 bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-all ${PDL.radius.button} text-[10px] font-black uppercase tracking-widest shadow-sm border border-border/50`}
                                                            onClick={(e) => e.stopPropagation()}
                                                        >
                                                            <Download size={16} /> 导出
                                                        </a>
                                                    )}
                                                    <button className={`h-11 w-11 flex items-center justify-center border border-border ${PDL.radius.button} group-hover:bg-primary group-hover:text-primary-foreground group-hover:border-primary transition-all text-muted-foreground`}>
                                                        <ChevronRight size={20} />
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* --- 视图：算法配置 --- */}
                        {activeTab === 'algo' && (
                            <div className={PDL.spacing.section}>
                                <div className={`bg-card ${PDL.spacing.cardPadding} ${PDL.radius.card} border border-border shadow-sm`}>
                                    <h1 className={`${PDL.typography.title} text-foreground mb-1`}>算法作战模型</h1>
                                    <p className="text-muted-foreground text-sm">哥，手动干预评分指标。保存即实时生效，直接影响后续选品评分权重。</p>
                                </div>

                                <div className={`bg-card ${PDL.radius.card} border border-border ${PDL.spacing.cardPadding} space-y-10 shadow-md`}>
                                    {[
                                        { label: "销量活跃度权重 (Sales Score)", value: 40, color: "bg-primary", desc: "月销量、转化率与增长率权重" },
                                        { label: "价格竞争力权重 (Price Score)", value: 25, color: "bg-emerald-600", desc: "价格带覆盖与利润边际权重" },
                                        { label: "评价质量权重 (Review Score)", value: 20, color: "bg-indigo-600", desc: "好评率与用户口碑感知权重" },
                                        { label: "蓝海独占权重 (Growth Score)", value: 15, color: "bg-rose-600", desc: "竞争对手数量与品类天花板权重" },
                                    ].map((factor, i) => (
                                        <div key={i} className="space-y-4 group">
                                            <div className="flex justify-between items-end">
                                                <div className="space-y-1">
                                                    <span className="text-sm font-black text-foreground block">{factor.label}</span>
                                                    <span className={`${PDL.typography.label} text-muted-foreground`}>{factor.desc}</span>
                                                </div>
                                                <span className="text-xl font-black font-mono text-primary group-hover:scale-105 transition-transform">{factor.value}%</span>
                                            </div>
                                            <div className="h-3 bg-muted rounded-full overflow-hidden p-0.5 border border-border/50">
                                                <div className={`h-full ${factor.color} rounded-full transition-all duration-1000`} style={{ width: `${factor.value}%` }}></div>
                                            </div>
                                        </div>
                                    ))}
                                    <div className="pt-8 border-t border-border/10 flex justify-end gap-5">
                                        <button className={`px-8 py-3.5 ${PDL.radius.button} bg-muted text-foreground hover:bg-muted/80 transition-all border border-border font-bold text-xs uppercase tracking-widest`}>重置模型</button>
                                        <button className={`px-10 py-3.5 ${PDL.radius.button} bg-primary text-primary-foreground shadow-lg shadow-primary/20 hover:opacity-90 transition-all font-black text-xs uppercase tracking-widest`}>保存指令</button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* --- 视图：系统管理 --- */}
                        {activeTab === 'settings' && (
                            <div className={PDL.spacing.section}>
                                <div className={`bg-card ${PDL.spacing.cardPadding} ${PDL.radius.card} border border-border flex justify-between items-center shadow-sm`}>
                                    <div className="space-y-1">
                                        <h1 className={`${PDL.typography.title} text-foreground`}>影子指挥部</h1>
                                        <p className="text-muted-foreground text-sm">哥，管理协作者权限与任务并发额度。</p>
                                    </div>
                                    <button className={`px-8 py-3.5 ${PDL.radius.button} bg-secondary text-secondary-foreground border border-border font-black text-xs uppercase tracking-widest hover:bg-secondary/80 transition-all`}>+ 增加成员</button>
                                </div>

                                <div className={`bg-card ${PDL.radius.card} border border-border shadow-md overflow-hidden divide-y divide-border/10`}>
                                    {[
                                        { name: "哥 (Master Admin)", role: "root_access", email: "yj@prosourcing.ai", initial: "Y" }
                                    ].map((user, i) => (
                                        <div key={i} className={`p-8 flex items-center gap-8 group hover:bg-muted/5 transition-colors`}>
                                            <div className={`w-16 h-16 ${PDL.radius.inner} bg-primary text-primary-foreground flex items-center justify-center text-2xl font-black shadow-lg shadow-primary/10 transition-transform group-hover:scale-105`}>{user.initial}</div>
                                            <div className="flex-1 space-y-2">
                                                <h4 className="text-lg font-black text-foreground">{user.name}</h4>
                                                <div className="flex gap-3">
                                                    <span className={`${PDL.typography.label} bg-muted/30 px-3 py-1 rounded-full border border-border text-muted-foreground capitalize`}>{user.role}</span>
                                                    <span className={`${PDL.typography.label} bg-muted/30 px-3 py-1 rounded-full border border-border text-muted-foreground lowercase`}>{user.email}</span>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-3 px-5 py-2 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-[10px] font-black uppercase tracking-widest">
                                                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                                                Active
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Footer */}
                        <footer className="mt-24 py-12 border-t border-border/5 text-center transition-all duration-300">
                            <p className="text-[10px] font-black uppercase tracking-[0.4em] text-muted-foreground opacity-20 hover:opacity-100 transition-opacity">
                                Powerby Cogine AI | 万物构想
                            </p>
                        </footer>
                    </div>
                </main>

                {/* 4. Report Modal (Overlay) */}
                {selectedTask && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-[100] flex items-center justify-center p-8 lg:p-16 animate-in fade-in duration-500">
                        <div className={`bg-card border border-border w-full max-w-7xl h-full ${PDL.radius.card} rounded-card-force shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-500`}>
                            <div className={`px-10 py-8 border-b flex justify-between items-center bg-muted/5 shrink-0`}>
                                <div>
                                    <h2 className={`${PDL.typography.title} text-foreground`}>{selectedTask.category} // 深度选品简报</h2>
                                    <div className="flex gap-4 mt-2">
                                        <span className="text-xs text-muted-foreground font-black uppercase bg-muted/20 px-3 py-1 rounded-full border border-border/50">TASKID: {selectedTask?.id?.slice(0, 12)}</span>
                                        <span className="text-xs text-primary font-black uppercase bg-primary/10 px-3 py-1 rounded-full border border-primary/20">样本样本 × {taskProducts.length}</span>
                                    </div>
                                </div>
                                <button onClick={() => setSelectedTask(null)} className="p-3 hover:bg-muted rounded-full text-muted-foreground hover:text-foreground transition-all">
                                    <XCircle size={32} />
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto p-10 space-y-12 custom-scrollbar">
                                {/* 顶部核心指标 */}
                                <div className="grid grid-cols-4 gap-8">
                                    {[
                                        { label: "类目月销", value: selectedTask.category_stats?.sale_qty?.toLocaleString() || '--', color: "text-primary" },
                                        { label: "产品总数", value: selectedTask.category_stats?.sale_product_qty || '--', color: "text-emerald-500" },
                                        { label: "销品比 (Ratio)", value: (selectedTask.category_stats?.sale_qty / selectedTask.category_stats?.sale_product_qty || 0).toFixed(2), color: "text-indigo-500" },
                                        { label: "活跃卖家", value: selectedTask.category_stats?.sale_seller_qty || '--', color: "text-rose-500" }
                                    ].map((item, i) => (
                                        <div key={i} className={`p-6 bg-muted/5 border border-border/50 ${PDL.radius.inner} shadow-sm`}>
                                            <p className={`${PDL.typography.label} text-muted-foreground mb-2`}>{item.label}</p>
                                            <p className={`text-2xl font-black ${item.color}`}>{item.value}</p>
                                        </div>
                                    ))}
                                </div>

                                {/* 趋势图与商品穿透 */}
                                <div className="grid grid-cols-3 gap-10">
                                    <div className={`col-span-1 bg-muted/5 border border-border/40 ${PDL.radius.inner} p-8 space-y-8 flex flex-col justify-center text-center`}>
                                        <TrendingUp size={40} className="mx-auto text-primary" />
                                        <div>
                                            <h4 className="text-sm font-black text-foreground uppercase tracking-widest mb-1 font-mono">6 Month Trend</h4>
                                            <p className="text-xs text-muted-foreground font-medium">类目历史轨迹分析模型</p>
                                        </div>
                                        {/* 趋势图可视化（修正贴边） */}
                                        <div className="flex items-end justify-center gap-2 h-24 px-2">
                                            {selectedTask.trend_data?.slice(-6).map((t, i) => (
                                                <div key={i} className="w-full bg-primary/20 rounded-t-lg transition-all hover:bg-primary" style={{ height: `${(t.sale_qty / (selectedTask.category_stats?.sale_qty || 1) * 300)}%` }}></div>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="col-span-2 space-y-6">
                                        <h3 className="text-lg font-black text-foreground flex items-center gap-3">
                                            <div className="w-1 h-5 bg-primary rounded-full"></div>
                                            样本商品多维透视 (TOP SAMPLES)
                                        </h3>
                                        <div className="space-y-4">
                                            {taskProducts.slice(0, 5).map((tp, idx) => {
                                                const raw = tp.products_raw_data;
                                                return (
                                                    <div key={idx} className={`flex items-center gap-5 p-5 bg-card border border-border ${PDL.radius.inner} hover:border-primary/30 transition-all group shadow-sm`}>
                                                        <div className={`w-14 h-14 ${PDL.radius.inner} bg-muted overflow-hidden shrink-0 border border-border flex items-center justify-center text-xs font-bold text-muted-foreground shadow-inner`}>
                                                            {raw.preview_image_list ? <img src={JSON.parse(raw.preview_image_list)[0].medium} alt="" className="w-full h-full object-cover" /> : 'IMG'}
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <p className="text-sm font-black truncate text-foreground group-hover:text-primary transition-colors">{raw.product_name}</p>
                                                            <div className="flex gap-4 mt-2">
                                                                <span className="text-xs font-bold text-muted-foreground">月销: <span className="text-foreground">{raw.sale_qty}</span></span>
                                                                <span className="text-xs font-bold text-muted-foreground">评分: <span className="text-foreground">{raw.product_rate}</span></span>
                                                                <span className={`text-[10px] font-black uppercase px-2 py-0.5 rounded border ${raw.amount_abc === 'A' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500' :
                                                                    raw.amount_abc === 'B' ? 'bg-amber-500/10 border-amber-500/20 text-amber-500' :
                                                                        'bg-rose-500/10 border-rose-500/20 text-rose-500'
                                                                    }`}>ABC: {raw.amount_abc}</span>
                                                            </div>
                                                        </div>
                                                        <div className="text-right">
                                                            <p className="text-lg font-black text-foreground leading-none mb-1">{raw.sale_price?.toLocaleString()} ₸</p>
                                                            <p className="text-[10px] font-bold text-primary uppercase tracking-tighter">Score: {tp.total_score}</p>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* 底部操作区固定吸附 */}
                            <div className="px-10 py-8 border-t bg-muted/10 flex justify-end gap-5 shrink-0">
                                <button onClick={() => setSelectedTask(null)} className={`px-10 py-3 ${PDL.radius.button} bg-muted text-foreground font-bold text-sm uppercase tracking-widest border border-border hover:bg-muted/80 transition-all`}>关闭</button>
                                <button className={`px-12 py-3 ${PDL.radius.button} bg-primary text-primary-foreground font-black text-sm uppercase tracking-widest shadow-xl shadow-primary/20 hover:opacity-90 transition-all`}>导出 PRO 完整报告</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default App