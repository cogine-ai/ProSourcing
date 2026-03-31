import React, { useState, useEffect, useRef } from 'react';
import './index.css';
import { PDL } from './lib/pdl';
import { TASK_STATUS } from './constants';
import Breadcrumbs from './components/Breadcrumbs';
import { KaspiTaskView } from './components/KaspiTaskView';
import { SystemSettings } from './components/SystemSettings';
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
    ChevronLeft,
    Sun,
    Moon
} from 'lucide-react';

const API_BASE = "http://localhost:8000";

const PageHeader = ({ title, description, actions }) => (
    <div className="mb-8 flex justify-between items-start animate-in fade-in slide-in-from-left-4 duration-500">
        <div>
            <h1 className="text-3xl font-black text-foreground tracking-tight mb-2">{title}</h1>
            <p className="text-muted-foreground text-sm font-medium">{description}</p>
        </div>
        {actions && <div className="flex gap-3">{actions}</div>}
    </div>
);

// --- 日志查看器组件 ---
const LogViewer = ({ taskId, onClose }) => {
    const [logs, setLogs] = useState("Loading logs...");
    const [autoScroll, setAutoScroll] = useState(true);
    const logEndRef = React.useRef(null);

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/tasks/${taskId}/logs`);
                const data = await res.json();
                setLogs(data.logs || "No logs found yet.");
            } catch (err) { setLogs("Error fetching logs."); }
        };

        fetchLogs();
        const timer = setInterval(fetchLogs, 3000);
        return () => clearInterval(timer);
    }, [taskId]);

    useEffect(() => {
        if (autoScroll && logEndRef.current) {
            logEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [logs, autoScroll]);

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-300">
            <div className="bg-card border border-border w-full max-w-4xl h-[70vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-300">
                <div className="p-4 border-b border-border flex justify-between items-center bg-muted/20">
                    <div className="flex items-center gap-3">
                        <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                        <h3 className="font-black text-xs uppercase tracking-widest">Task Runtime Logs // {taskId.slice(0, 8)}</h3>
                    </div>
                    <div className="flex items-center gap-4">
                        <label className="flex items-center gap-2 cursor-pointer group">
                            <span className="text-[10px] font-bold text-muted-foreground uppercase group-hover:text-foreground">Auto-scroll</span>
                            <input type="checkbox" checked={autoScroll} onChange={e => setAutoScroll(e.target.checked)} className="accent-primary" />
                        </label>
                        <button onClick={onClose} className="p-1 hover:bg-muted rounded-md transition-colors text-muted-foreground hover:text-foreground">
                            <XCircle size={20} />
                        </button>
                    </div>
                </div>
                <div className="flex-1 overflow-y-auto p-6 bg-[#09090b] font-mono text-[11px] leading-relaxed custom-scrollbar selection:bg-primary/30">
                    <pre className="whitespace-pre-wrap text-emerald-500/90">
                        {logs}
                        <div ref={logEndRef} />
                    </pre>
                </div>
            </div>
        </div>
    );
};

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
const getCategoryDisplayName = (cat) => {
    if (!cat) return "未知品类";
    
    // 哥，优先拿字段里存好的中文
    const cnName = cat?.name_cn || cat?.category_name_cn || cat?.category_cn;
    if (cnName && !anyCyrillic(cnName)) return cnName;

    // 针对对象结构 (cat_stats)，或者带括号的格式 "俄文 (中文)"
    const fullName = cat?.category_name || cat?.category || cat?.name || "";
    
    // 尝试匹配括号内的中文
    const match = fullName.match(/\((.*?)\)/);
    if (match) return match[1];

    // 如果包含 "RPA采集_" 前缀的，通常格式是 RPA采集_俄文(中文)_日期
    if (fullName.startsWith('RPA采集_')) {
        const parts = fullName.split('_');
        if (parts.length > 1) {
            const subMatch = parts[1].match(/\((.*?)\)/);
            if (subMatch) return subMatch[1];
            return parts[1];
        }
    }

    // 兜底：如果还是俄文，且有横杠，尝试拆分
    return fullName.split(' - ')[0];
};

// 哥，辅助函数检测俄文字符
const anyCyrillic = (str) => {
    return /[а-яА-ЯЁё]/.test(str);
};

const CategoryCard = ({ cat }) => {
    const ratio = cat.sale_product_qty > 0 ? (cat.monthly_sales / cat.sale_product_qty).toFixed(2) : 0;

    // 拆分中俄双语：假设格式为 "俄语 (中文)"
    // 哥，咱们现在优先用独立的列，干净利落
    const ruName = cat?.name_ru || (cat?.category_name?.match(/^(.*)\s\(.*\)$/) || [null, cat?.category_name])[1] || cat?.name || "";
    const zhName = cat?.name_cn || (cat?.category_name?.match(/\s\((.*)\)$/) || [null, ""])[1] || "";

    return (
        <div className={`bg-card border border-border ${PDL.radius.card} rounded-card-force p-8 hover:border-primary/50 transition-all shadow-md flex flex-col justify-between group h-[320px]`}>
            {/* 头部：标题区域 */}
            <div className="mb-8">
                <h3 className="text-2xl font-black leading-tight text-foreground group-hover:text-primary transition-colors flex flex-col gap-1">
                    <span>{zhName || ruName}</span>
                    {zhName && <span className="text-xs font-bold text-muted-foreground/30 font-mono italic">/ {ruName}</span>}
                </h3>

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
            <div className="mt-4 pt-4 border-t border-border/10">
                <div className="flex justify-between items-center">
                    <div className="flex flex-col">
                        <p className="text-[10px] font-bold uppercase tracking-widest text-primary/50">销品比效率</p>

                    </div>
                    <p className="text-3xl font-black text-primary font-mono tracking-tighter">{ratio}</p>
                </div>
            </div>
        </div>
    );
};

const App = () => {
    const [taskProducts, setTaskProducts] = useState([]);
    const [activeTab, setActiveTab] = useState('archives'); // Default to archives for now
    const [reportSearch, setReportSearch] = useState('');
    const [reportStatus, setReportStatus] = useState('all');
    const [reportTime, setReportTime] = useState('all');
    const [reportTopCat, setReportTopCat] = useState('all');
    const [reportPage, setReportPage] = useState(1);
    const [totalTasks, setTotalTasks] = useState(0);
    const reportListRef = useRef(null); // 哥，专门用来管列表滚动的
    const [viewLogId, setViewLogId] = useState(null);
    const [onlyHighQuality, setOnlyHighQuality] = useState(true);
    const [filterDays, setFilterDays] = useState(300);
    const [filterSales, setFilterSales] = useState(60);
    const [filterReviews, setFilterReviews] = useState(15);
    const [filterMinPrice, setFilterMinPrice] = useState(800);
    const [sortBy, setSortBy] = useState('amount');

    // Helper to format ISO date to YYYY.MM.DD HH:mm:ss
    const formatDateTime = (iso) => {
        if (!iso) return '--';
        try {
            const d = new Date(iso);
            const pad = (n) => n.toString().padStart(2, '0');
            return `${d.getFullYear()}.${pad(d.getMonth() + 1)}.${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
        } catch (e) {
            return iso;
        }
    };
    // Original activeTab initialization logic, now commented out or replaced by the above line
    // const [activeTab, setActiveTab] = useState(() => {
    //     const hash = window.location.hash.replace('#', '');
    //     return ['market', 'tasks', 'archives', 'algo', 'settings'].includes(hash) ? hash : 'market';
    // });
    const [isDark, setIsDark] = useState(true);
    const [categories, setCategories] = useState([]);
    const [allCategories, setAllCategories] = useState([]);
    const [tasks, setTasks] = useState([]);
    const [selectedTask, setSelectedTask] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCats, setSelectedCats] = useState([]);
    const [currentTopCategory, setCurrentTopCategory] = useState(null);
    const [loading, setLoading] = useState(false);
    const [reportTab, setReportTab] = useState('metrics');
    const [viewMode, setViewMode] = useState('list'); // 'list' or 'detail'
    const [algoConfig, setAlgoConfig] = useState(null); // 哥，这是存放算法配置的状态

    // 哥，这是统一的评分逻辑，直接根据 algoConfig 来算，保证前后端和配置页全对齐
    const getMetricScore = (metricKey, value, secondaryValue = null) => {
        if (!algoConfig || !algoConfig[metricKey]) return 0;
        const conf = algoConfig[metricKey];
        const ranges = conf.ranges;
        const scores = conf.scores;

        if (metricKey === 'days_per_review') {
            if (secondaryValue === 0 || secondaryValue === '--') return 0;
            const ratio = value / secondaryValue;
            for (let i = 0; i < ranges.length; i++) {
                if (ratio <= ranges[i]) return scores[i];
            }
            return scores[scores.length - 1];
        }

        if (metricKey === 'price') {
            if (value > ranges[0]) return scores[0];
            for (let i = 1; i < ranges.length; i++) {
                if (value >= ranges[i]) return scores[i];
            }
            return scores[scores.length - 1];
        }

        // 默认逻辑：从大到小比对阈值
        for (let i = 0; i < ranges.length; i++) {
            if (value >= ranges[i]) return scores[i];
        }
        return scores[scores.length - 1];
    };

    const [expandedNodes, setExpandedNodes] = useState(new Set());

    const [globalStats, setGlobalStats] = useState({
        top_cat_count: 0,
        min_cat_count: 1248,
        sku_count: "154.2K",
    });

    const tabs = [
        { id: 'market', label: '首页', description: '全量大盘数据概览', icon: <LayoutDashboard size={18} /> },
        { id: 'tasks', label: '采集任务', description: '管理和执行商品数据采集', icon: <Target size={18} /> },
        { id: 'archives', label: '选品报告', description: '查看AI生成的选品分析结果', icon: <History size={18} /> },
        { id: 'algo', label: '算法配置', description: '配置选品算法参数和模型策略', icon: <Settings2 size={18} /> },
        { id: 'settings', label: '系统管理', description: '管理账号、权限和系统配置', icon: <Users size={18} /> },
    ];

    const currentTabInfo = tabs.find(t => t.id === activeTab);

    // Helper for status colors
    const getStatusColor = (status) => {
        switch (status) {
            case TASK_STATUS.COMPLETED: return 'border-emerald-600/50 text-emerald-600 dark:border-emerald-400/50 dark:text-emerald-400';
            case TASK_STATUS.PENDING:
            case 'running':
            case 'crawling':
            case 'reporting':
            case 'processing':
            case TASK_STATUS.SCRAPING: return 'border-amber-600/50 text-amber-600 dark:border-amber-400/50 dark:text-amber-400';
            case TASK_STATUS.FAILED:
            case 'error': return 'border-rose-600/50 text-rose-600 dark:border-rose-400/50 dark:text-rose-400';
            case TASK_STATUS.RETRYING: return 'border-blue-600/50 text-blue-600 dark:border-blue-400/50 dark:text-blue-400';
            default: return 'border-muted-foreground/50 text-muted-foreground';
        }
    };

    // 主题逻辑挂载
    useEffect(() => {
        const root = window.document.documentElement;
        if (isDark) root.classList.add('dark');
        else root.classList.remove('dark');
    }, [isDark]);

    // Hash 路由同步
    useEffect(() => {
        window.location.hash = activeTab;
    }, [activeTab]);

    useEffect(() => {
        const onHashChange = () => {
            const hash = window.location.hash.replace('#', '');
            if (['market', 'tasks', 'archives', 'algo', 'settings'].includes(hash)) {
                setActiveTab(hash);
            }
        };
        window.addEventListener('hashchange', onHashChange);
        return () => window.removeEventListener('hashchange', onHashChange);
    }, []);

    // --- 趋势数据获取逻辑 ---
    useEffect(() => {
        const fetchTrendData = async () => {
            if (selectedTask.trend_data && selectedTask.trend_data.length > 0) {
                console.log("Trend data already exists in task", selectedTask.trend_data.length);
                return;
            }

            // 兜底：如果任务里没带数据（可能是老任务），尝试去后端补充获取
            try {
                const res = await fetch(`${API_BASE}/api/tasks/${selectedTask.id}`);
                const data = await res.json();
                if (data.trend_data && data.trend_data.length > 0) {
                    setSelectedTask(prev => ({ ...prev, trend_data: data.trend_data }));
                    return;
                }
            } catch (err) {
                console.error("Fetch full task data failed:", err);
            }
        };

        fetchTrendData();
    }, [selectedTask?.id]);

    // 数据获取
    useEffect(() => {
        fetchTopStats();
        fetchGlobalStats();
        fetchHistory(reportPage, reportSearch, reportTime, reportStatus, reportTopCat);
        fetchAllCategories();
        const interval = setInterval(() => fetchHistory(reportPage, reportSearch, reportTime, reportStatus, reportTopCat), 5000);
        fetchAlgoConfig();
        return () => clearInterval(interval);
    }, [reportPage, reportSearch, reportTime, reportStatus, reportTopCat]);

    const fetchAlgoConfig = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/algo/config`);
            const data = await res.json();
            setAlgoConfig(data);
        } catch (err) { console.error("Fetch algo config failed", err); }
    };

    const handleSaveAlgoConfig = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/algo/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(algoConfig)
            });
            if (res.ok) {
                alert("配置已保存，下次采集任务生效");
            }
        } catch (err) { alert("保存失败了，哥你看看网络？"); }
    };

    const handleResetAlgoConfig = async () => {
        if (!confirm("确定要恢复默认设置吗？")) return;
        try {
            const res = await fetch(`${API_BASE}/api/algo/reset`, { method: 'POST' });
            if (res.ok) {
                alert("已恢复默认配置！");
                fetchAlgoConfig();
            }
        } catch (err) { console.error("Reset failed", err); }
    };

    const updateAlgoConfigValue = (metric, index, value, type = 'scores') => {
        const newConf = { ...algoConfig };
        const val = parseFloat(value) || 0;
        newConf[metric][type][index] = val;
        setAlgoConfig(newConf);
    };

    const fetchGlobalStats = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/market/global_stats`);
            const data = await res.json();
            setGlobalStats(data);
        } catch (err) { console.error("Fetch global stats failed", err); }
    };

    const fetchTopStats = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/categories/top_stats`);
            const data = await res.json();
            setCategories(data);
        } catch (err) { console.error("Fetch top stats failed", err); }
    };

    const fetchAllCategories = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/categories/tree`);
            const data = await res.json();
            setAllCategories(data);
        } catch (err) { console.error("Fetch all categories failed", err); }
    };

    const fetchHistory = async (page = reportPage, q = reportSearch, time = reportTime, status = reportStatus, topCat = reportTopCat) => {
        try {
            const url = new URL(`${API_BASE}/api/tasks/history`);
            url.searchParams.append('page', page);
            url.searchParams.append('page_size', 20);
            if (q) url.searchParams.append('q', q);
            
            // 哥，转换时间过滤为天数
            if (time !== 'all') {
                let days = 0;
                if (time === '7d') days = 7;
                else if (time === '30d') days = 30;
                else if (time === 'this_month') {
                    const today = new Date();
                    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
                    days = Math.floor((today - firstDay) / (1000 * 60 * 60 * 24)) + 1;
                }
                if (days > 0) url.searchParams.append('days', days);
            }
            if (status !== 'all') url.searchParams.append('status', status);
            if (topCat !== 'all') url.searchParams.append('top_category', topCat);
            
            const res = await fetch(url);
            const data = await res.json();

            setTasks(data.data || []);
            setTotalTasks(data.total || 0);
        } catch (err) { console.error("Fetch history failed", err); }
    };

    // 获取抽屉类目树 (一级分类)
    const fetchLeafCategories = async (topId) => {
        const target = categories.find(c => c.category_id === topId);
        if (target && target.leaves) return;

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
            }
        } catch (error) { console.error("Create task failed", error); }
    };
    
    const handleRetryTask = async (taskId) => {
        try {
            const res = await fetch(`${API_BASE}/api/tasks/${taskId}/retry`, { method: 'POST' });
            if (res.ok) {
                alert('任务已重新加入采集队列！');
                fetchHistory();
            }
        } catch (e) { console.error("Retry task failed", e); }
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

        try {
            const res = await fetch(`${API_BASE}/api/kaspi/tasks/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(selectedCats)
            });
            const data = await res.json();
            if (data.success || data.status === 'success') {
                const total = data.total_requested || selectedCats.length;
                const filtered = data.filtered_duplicate || 0;
                const actual = data.actual_executed || (data.tasks ? data.tasks.length : 0);
                alert(`本次发起 ${total} 个任务，已存在/过滤 ${filtered} 个，实际新执行 ${actual} 个并发采集任务。`);
            }
        } catch(e) { console.error('Batch error', e); }

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
            setViewMode('list');
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
                        {tabs.map((item) => (
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
                            <p className="text-sm font-bold truncate text-foreground">欢迎使用 ProSourcing 系统</p>
                        </div>
                    </div>
                </div>
            </aside>

            {/* 2. Main Container (Sticky Header + Scrollable Content) */}
            <div className="flex-1 flex flex-col min-w-0 relative h-full">

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

                {/* 3. Content Area (Fixed height, internal scrolling only) */}
                <main className={`flex-1 overflow-hidden ${PDL.layout.contentPadding} bg-background/30 transition-colors duration-300 flex flex-col`}>
                    <div className="max-w-[1600px] 2xl:max-w-[1800px] mx-auto w-full flex-1 flex flex-col min-h-0">

                        {/* 页面标题区 */}
                        {!(activeTab === 'archives' && viewMode === 'detail') && (
                            <PageHeader
                                title={activeTab === 'algo' ? "算法配置" : currentTabInfo?.label}
                                description={activeTab === 'algo' ? "设置商品评分维度权重与逻辑规则" : currentTabInfo?.description}
                                actions={activeTab === 'algo' ? (
                                    <>
                                        <button
                                            onClick={handleResetAlgoConfig}
                                            className="px-5 py-2 text-[10px] font-black uppercase tracking-widest bg-muted border border-border hover:bg-muted/80 rounded-md transition-all shadow-sm"
                                        >
                                            重置默认
                                        </button>
                                        <button
                                            onClick={handleSaveAlgoConfig}
                                            className="px-6 py-2 text-[10px] font-black uppercase tracking-widest bg-primary text-primary-foreground shadow-lg shadow-primary/20 hover:opacity-90 rounded-md transition-all"
                                        >
                                            保存配置
                                        </button>
                                    </>
                                ) : activeTab === 'archives' && viewMode === 'list' ? (
                                    <div className="flex gap-4 items-center animate-in fade-in slide-in-from-right-4 duration-500">
                                        <div className="relative group">
                                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-primary transition-colors" size={16} />
                                            <input 
                                                type="text" 
                                                placeholder="搜索品类报告..." 
                                                value={reportSearch}
                                                onChange={e => { setReportSearch(e.target.value); setReportPage(1); }}
                                                className="pl-10 pr-4 py-2.5 bg-card/50 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/10 w-64 transition-all hover:border-primary/30"
                                            />
                                        </div>
                                        <select 
                                            value={reportTime}
                                            onChange={e => { setReportTime(e.target.value); setReportPage(1); }}
                                            className="bg-card/50 border border-border rounded-xl px-4 py-2.5 text-xs font-bold uppercase tracking-widest focus:outline-none appearance-none cursor-pointer hover:border-primary/30 transition-all min-w-[140px]"
                                        >
                                            <option value="all">全部时间历史</option>
                                            <option value="7d">最近 7 天内</option>
                                            <option value="30d">最近 30 天内</option>
                                            <option value="this_month">本月报告</option>
                                        </select>
                                        <select 
                                            value={reportStatus}
                                            onChange={e => { setReportStatus(e.target.value); setReportPage(1); }}
                                            className="bg-card/50 border border-border rounded-xl px-4 py-2.5 text-xs font-bold uppercase tracking-widest focus:outline-none appearance-none cursor-pointer hover:border-primary/30 transition-all min-w-[120px]"
                                        >
                                            <option value="all">全部状态</option>
                                            <option value="completed">已完成</option>
                                            <option value="pending">执行中</option>
                                            <option value="failed">错误失败</option>
                                        </select>
                                        <select 
                                            value={reportTopCat}
                                            onChange={e => { setReportTopCat(e.target.value); setReportPage(1); }}
                                            className="bg-card/50 border border-border rounded-xl px-4 py-2.5 text-xs font-bold uppercase tracking-widest focus:outline-none appearance-none cursor-pointer hover:border-primary/30 transition-all min-w-[120px]"
                                        >
                                            <option value="all">全部分类</option>
                                            {categories.map(c => <option key={c.category_id} value={c.name_cn || c.name_ru}>{c.name_cn || c.name_ru}</option>)}
                                        </select>
                                    </div>
                                ) : null}
                            />
                        )}

                        {/* --- 视图：首页 --- */}
                        {activeTab === 'market' && (
                            <div className={`${PDL.spacing.section} flex-1 overflow-y-auto custom-scrollbar pr-2`}>
                                <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 ${PDL.spacing.gap}`}>
                                    <StatCard label="入库的一级品类数量" value={globalStats.top_cat_count} icon={<Package className="text-blue-500" />} />
                                    <StatCard label="最小品类数据" value={globalStats.min_cat_count} icon={<BarChart3 className="text-emerald-500" />} />
                                    <StatCard label="商品sku数据" value={globalStats.sku_count} icon={<TrendingUp className="text-indigo-500" />} />
                                    <StatCard label="已生成选品报告数量" value={globalStats.report_count || tasks.filter(t => t.status === 'completed').length} icon={<History className="text-rose-500" />} />
                                </div>

                                <div className={PDL.spacing.section}>
                                    <div className="flex items-center justify-between">
                                        <h3 className="text-xl font-black text-foreground tracking-tight flex items-center gap-3">
                                            <div className="w-1 h-6 bg-primary rounded-full"></div>
                                            全量一级分类运行详情
                                        </h3>
                                        <div className="text-[10px] font-bold text-muted-foreground uppercase bg-muted/20 px-3 py-1 rounded-full border border-border">
                                            最后更新: {formatDateTime(globalStats.last_updated)}
                                        </div>
                                    </div>
                                    <div className={`grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 ${PDL.spacing.gap}`}>
                                        {categories.map((cat, i) => <CategoryCard key={i} cat={cat} />)}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* --- 视图：采集任务 --- */}
                        {activeTab === "tasks" && (
                            <div className="flex-1 flex flex-col min-h-0">
                                <KaspiTaskView />
                            </div>
                        )}

                        {/* --- 视图：选品报告 --- */}
                        {activeTab === 'archives' && (
                            <div className="flex-1 flex flex-col min-h-0">
                                {viewMode === 'list' ? (
                                    <>
                                        <div 
                                            ref={reportListRef}
                                            className="flex-1 overflow-y-auto custom-scrollbar pr-2 space-y-8 pb-10"
                                        >
                                        {tasks.length === 0 ? (
                                            <div className="flex flex-col items-center justify-center py-20 opacity-30 grayscale gap-4">
                                                <History size={48} />
                                                <p className="font-black uppercase tracking-widest text-sm">暂无选品报告 // NO DATA</p>
                                            </div>
                                        ) : (
                                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                                                {tasks.map((task) => {
                                                        const isCompleted = task.status === TASK_STATUS.COMPLETED;
                                                        const isFailed = task.status === TASK_STATUS.FAILED;
                                                        const isRunning = !isCompleted && !isFailed && task.status !== TASK_STATUS.RETRYING;

                                                        return (
                                                            <div
                                                                key={task.id}
                                                                className={`bg-card border border-border ${PDL.radius.card} rounded-xl p-5 flex flex-col shadow-sm hover:shadow-md hover:border-primary/40 transition-all ${isCompleted ? 'cursor-pointer hover:-translate-y-1' : ''}`}
                                                                onClick={() => {
                                                                    if (isCompleted) {
                                                                        setSelectedTask(task);
                                                                        setViewMode('detail');
                                                                    }
                                                                }}
                                                            >
                                                                {/* Header */}
                                                                <div className="flex justify-between items-start mb-4 border-b border-border/40 pb-3">
                                                                    <div className="pr-3 flex-1 min-w-0">
                                                                        <h4 className="font-black text-foreground text-xl truncate flex items-center gap-2" title={task.category}>
                                                                            {getCategoryDisplayName(task)}
                                                                            {task.up_categories && typeof task.up_categories !== 'string' && task.up_categories.length > 0 && (
                                                                                <span className="px-2 py-0.5 bg-primary/10 border border-primary/20 text-primary text-[10px] uppercase font-bold tracking-widest rounded-md shrink-0">
                                                                                    {getCategoryDisplayName(task.up_categories[0]) || '一级类目'}
                                                                                </span>
                                                                            )}
                                                                        </h4>
                                                                        <p className="text-xs text-muted-foreground mt-2 tracking-tight truncate flex items-center gap-2">
                                                                            <span className="w-1.5 h-1.5 bg-muted-foreground/30 rounded-full"></span>
                                                                            {formatDateTime(task.updated_at || task.created_at)}
                                                                            {task.updated_at && <span className="ml-1 text-[9px] font-bold tracking-widest uppercase border px-1 rounded-sm border-muted/50 text-muted-foreground/50">Updated</span>}
                                                                        </p>
                                                                    </div>
                                                                    <div className="shrink-0 ml-2 flex flex-col items-end gap-1">
                                                                        {isCompleted && <div className={`px-3 py-1 font-black text-xs opacity-80 uppercase rounded-md tracking-widest border-2 ${getStatusColor(task.status)}`}>已完成</div>}
                                                                        {isRunning && (
                                                                            <>
                                                                                <div className={`px-3 py-1 font-black text-xs opacity-80 uppercase rounded-md tracking-widest border-2 mb-0.5 ${getStatusColor(task.status)}`}>
                                                                                    {task.status === 'pending' ? '等待中' : '生成中'}
                                                                                </div>
                                                                                <div className="flex gap-2">
                                                                                    <button className="text-[10px] font-bold text-muted-foreground hover:text-rose-500 transition-colors tracking-widest uppercase" onClick={(e) => e.stopPropagation()}>取消</button>
                                                                                    <button
                                                                                        className="text-[10px] font-bold text-muted-foreground hover:text-primary transition-colors tracking-widest uppercase"
                                                                                        onClick={(e) => { e.stopPropagation(); setViewLogId(task.id); }}
                                                                                    >
                                                                                        日志
                                                                                    </button>
                                                                                </div>
                                                                            </>
                                                                        )}
                                                                        {isFailed && (
                                                                            <>
                                                                                <div className={`px-3 py-1 font-black text-xs opacity-80 uppercase rounded-md tracking-widest border-2 mb-0.5 ${getStatusColor(task.status)}`}>失败</div>
                                                                                <div className="flex gap-2">
                                                                                    <button className="text-[10px] font-bold text-muted-foreground hover:text-rose-500 transition-colors tracking-widest uppercase" onClick={(e) => { e.stopPropagation(); handleRetryTask(task.id); }}>重试</button>
                                                                                    <button
                                                                                        className="text-[10px] font-bold text-muted-foreground hover:text-primary transition-colors tracking-widest uppercase"
                                                                                        onClick={(e) => { e.stopPropagation(); setViewLogId(task.id); }}
                                                                                    >
                                                                                        日志
                                                                                    </button>
                                                                                </div>
                                                                            </>
                                                                        )}
                                                                    </div>
                                                                </div>

                                                                {/* Content: Completed */}
                                                                {isCompleted && (
                                                                    <div className="flex-1 flex flex-col justify-center">
                                                                        <div className="grid grid-cols-3 gap-2 mt-4 text-center divide-x divide-border/40">
                                                                            <div className="flex flex-col px-1">
                                                                                <span className="text-[10px] text-muted-foreground mb-1 font-bold">产品总数/有效数</span>
                                                                                <span className="text-xl font-black text-foreground">{task.category_stats?.sale_product_qty || '--'} / <span className="text-primary">{task.category_stats?.valid_product_count || '--'}</span></span>
                                                                            </div>
                                                                            <div className="flex flex-col px-1">
                                                                                <span className="text-[10px] text-muted-foreground mb-1 font-bold">类目销量</span>
                                                                                <span className="text-xl font-black text-emerald-600 dark:text-emerald-600 dark:text-emerald-400 flex items-center justify-center gap-0.5">
                                                                                    {task.category_stats?.sale_qty?.toLocaleString() || '--'} <ArrowUpRight size={14} />
                                                                                </span>
                                                                            </div>
                                                                            <div className="flex flex-col px-1">
                                                                                <span className="text-[10px] text-muted-foreground mb-1 font-bold">销品比</span>
                                                                                <span className="text-xl font-black text-foreground tracking-tight">
                                                                                    {task.category_stats?.sale_product_qty ? (task.category_stats.sale_qty / task.category_stats.sale_product_qty).toFixed(1) : '--'}
                                                                                </span>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                )}

                                                                {/* Content: Running */}
                                                                {isRunning && (
                                                                    <div className="flex-1 flex flex-col justify-end mt-4 mb-2">
                                                                        <div className="w-full px-2">
                                                                            <div className="flex justify-between text-xs mb-2 font-medium">
                                                                                <span className="text-muted-foreground uppercase text-[10px] tracking-widest">
                                                                                    {task.status === 'pending' ? '等待资源分配...' : '正在提取数据...'}
                                                                                </span>
                                                                                <span className="text-muted-foreground font-mono text-[10px]">
                                                                                    {task.progress || 0}%
                                                                                </span>
                                                                            </div>
                                                                            <div className="w-full bg-muted rounded-full h-2 overflow-hidden mb-1">
                                                                                <div
                                                                                    className="bg-primary h-2 rounded-full transition-all duration-1000 animate-[pulse_2s_ease-in-out_infinite]"
                                                                                    style={{
                                                                                        width: `${task.progress || 0}%`
                                                                                    }}
                                                                                ></div>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                )}

                                                                {/* Content: Failed */}
                                                                {isFailed && (
                                                                    <div className="flex-1 flex flex-col justify-end mt-4 mb-2">
                                                                        <div className="bg-rose-500/10 border border-rose-500/20 rounded-lg p-3 flex gap-3 items-center mb-1">
                                                                            <XCircle size={18} className="text-rose-500 shrink-0" />
                                                                            <span className="text-xs text-rose-700 dark:text-rose-300 font-bold truncate">错误：{task.error_msg || '数据源连接超时'}</span>
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        );
                                                    })}
                                            </div>
                                        )}

                                        </div>

                                        {/* 分页导航 (Pinned at the bottom) */}
                                        <div className="shrink-0 sticky bottom-0 bg-background/90 backdrop-blur-md border-t border-border/20 py-4 mt-2 z-[50] flex items-center justify-between px-2 pointer-events-auto">
                                            <div className="flex flex-col">
                                                <p className="text-xs font-black text-foreground">
                                                    共 <span className="text-primary">{totalTasks}</span> 项报告 
                                                    <span className="mx-3 text-muted-foreground/20">|</span> 
                                                    第 {reportPage} / {Math.ceil(totalTasks / 20) || 1} 页
                                                </p>
                                            </div>
                                            <div className="flex gap-3">
                                                <button 
                                                    disabled={reportPage === 1}
                                                    onClick={() => { 
                                                        setReportPage(p => Math.max(1, p - 1)); 
                                                        reportListRef.current?.scrollTo({top: 0, behavior: 'smooth'}); 
                                                    }}
                                                    className="flex items-center justify-center w-32 py-3 bg-card border border-border rounded-xl hover:bg-accent hover:border-primary/50 disabled:opacity-20 disabled:grayscale transition-all font-black text-[10px] uppercase tracking-widest shadow-sm active:scale-95"
                                                >
                                                    <ChevronLeft size={16} className="mr-1" /> 上一页
                                                </button>
                                                <button 
                                                    disabled={reportPage >= Math.ceil(totalTasks / 20)}
                                                    onClick={() => { 
                                                        setReportPage(p => p + 1); 
                                                        reportListRef.current?.scrollTo({top: 0, behavior: 'smooth'}); 
                                                    }}
                                                    className="flex items-center justify-center w-32 py-3 bg-primary text-primary-foreground border border-primary rounded-xl hover:opacity-90 disabled:opacity-20 disabled:grayscale transition-all font-black text-[10px] uppercase tracking-widest shadow-lg shadow-primary/20 active:scale-95"
                                                >
                                                    下一页 <ChevronRight size={16} className="ml-1" />
                                                </button>
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    /* --- 内部详情页视图 (填满内容区) --- */
                                    <div className={`bg-card border border-border ${PDL.radius.card} rounded-card-force shadow-xl flex flex-col overflow-hidden animate-in slide-in-from-right-4 duration-500 flex-1`}>
                                        <div className={`px-6 pt-3 pb-0 border-b flex flex-col gap-2 bg-muted/5 shrink-0`}>
                                            <div className="flex justify-between items-center py-2 px-1">
                                                <button
                                                    onClick={() => setViewMode('list')}
                                                    className={`flex items-center justify-center px-4 py-1.5 text-xs font-black uppercase tracking-widest text-primary border border-border bg-background hover:bg-muted transition-all rounded-md shadow-sm`}
                                                >
                                                    返回
                                                </button>
                                                <div className="flex-1 px-8 flex justify-end gap-8 items-center">
                                                    <div className="flex flex-col items-end">
                                                        <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">任务时间</span>
                                                        <span className="text-xs font-black text-foreground">{formatDateTime(selectedTask?.created_at)}</span>
                                                    </div>
                                                    <div className="flex flex-col items-end border-l border-border/40 pl-8">
                                                        <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">执行时长</span>
                                                        <span className="text-xs font-black text-foreground">
                                                            {selectedTask?.duration || (() => {
                                                                if (!selectedTask?.created_at || !selectedTask?.finished_at) return '--';
                                                                const start = new Date(selectedTask.created_at);
                                                                const end = new Date(selectedTask.finished_at);
                                                                const diff = Math.floor((end - start) / 1000);
                                                                const m = Math.floor(diff / 60);
                                                                const s = diff % 60;
                                                                return m > 0 ? `${m}m ${s}s` : `${s}s`;
                                                            })()}
                                                        </span>
                                                    </div>
                                                    <div className="flex flex-col items-end">
                                                        <div className="flex items-center gap-4">
                                                            <h2 className="text-[32px] font-black text-foreground leading-tight tracking-tighter">
                                                                {getCategoryDisplayName(selectedTask)}
                                                            </h2>
                                                            {selectedTask?.excel_path && (
                                                                <a
                                                                    href={`${API_BASE}/api/download?path=${encodeURIComponent(selectedTask.excel_path)}`}
                                                                    className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-[10px] font-black text-emerald-500 uppercase tracking-widest hover:bg-emerald-500/20 transition-all self-center"
                                                                >
                                                                    EXCEL
                                                                </a>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => setReportTab('metrics')}
                                                    className={`px-6 py-2 text-xs font-black uppercase tracking-widest transition-all border-b-2 ${reportTab === 'metrics' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                                                >
                                                    指标详解概况
                                                </button>
                                                <button
                                                    onClick={() => setReportTab('raw')}
                                                    className={`px-6 py-2 text-xs font-black uppercase tracking-widest transition-all border-b-2 ${reportTab === 'raw' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
                                                >
                                                    采集原始数据
                                                </button>
                                            </div>
                                        </div>

                                        <div className="flex-1 overflow-hidden relative">
                                            <div className="absolute inset-0 overflow-y-auto p-6 custom-scrollbar">
                                                {reportTab === 'metrics' ? (
                                                    <div className="h-full animate-in fade-in slide-in-from-bottom-2 duration-500 mt-2">
                                                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start h-full">

                                                            {/* --- 左侧栏：商品详情列表 (占 2 份宽度) --- */}
                                                            <div className="lg:col-span-2 space-y-4 max-h-[calc(100vh-280px)] overflow-y-auto pr-2 custom-scrollbar pb-6">
                                                                {/* 哥，这是 100% 还原下午版本的筛选与排序工具条 */}
                                                                <div className="bg-muted/10 border border-border/40 rounded-xl p-3 mb-6 flex items-center justify-between animate-in fade-in slide-in-from-top-2 duration-500">
                                                                    <div className="flex items-center gap-6">
                                                                        <div className="flex items-center gap-3 pr-4 border-r border-border/40">
                                                                            <div 
                                                                                onClick={() => setOnlyHighQuality(!onlyHighQuality)}
                                                                                className={`w-10 h-5 rounded-full relative transition-all cursor-pointer ${onlyHighQuality ? 'bg-orange-500' : 'bg-muted-foreground/30'}`}
                                                                            >
                                                                                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${onlyHighQuality ? 'left-[22px]' : 'left-0.5'}`} />
                                                                            </div>
                                                                            <span className="text-xs font-black text-foreground/80 whitespace-nowrap">潜力优质商品挑选</span>
                                                                        </div>
                                                                        
                                                                        <div className="flex items-center gap-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">
                                                                            <div className="flex items-center gap-2">
                                                                                <span>天数 &lt;</span>
                                                                                <input type="number" value={filterDays} onChange={e => setFilterDays(Number(e.target.value))} className="bg-transparent border-b border-border/40 text-emerald-500 w-10 text-center focus:outline-none focus:border-primary" />
                                                                            </div>
                                                                            <div className="flex items-center gap-2">
                                                                                <span>销量 &gt;</span>
                                                                                <input type="number" value={filterSales} onChange={e => setFilterSales(Number(e.target.value))} className="bg-transparent border-b border-border/40 text-emerald-500 w-10 text-center focus:outline-none focus:border-primary" />
                                                                            </div>
                                                                            <div className="flex items-center gap-2">
                                                                                <span>评论 &gt;</span>
                                                                                <input type="number" value={filterReviews} onChange={e => setFilterReviews(Number(e.target.value))} className="bg-transparent border-b border-border/40 text-emerald-500 w-10 text-center focus:outline-none focus:border-primary" />
                                                                            </div>
                                                                            <div className="flex items-center gap-2">
                                                                                <span>价格 &gt;</span>
                                                                                <input type="number" value={filterMinPrice} onChange={e => setFilterMinPrice(Number(e.target.value))} className="bg-transparent border-b border-border/40 text-emerald-500 w-16 text-center focus:outline-none focus:border-primary" />
                                                                            </div>
                                                                        </div>
                                                                    </div>

                                                                    <div className="flex items-center gap-6">
                                                                        <div className="flex items-center gap-2">
                                                                            <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">排序:</span>
                                                                            <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="bg-transparent border-none text-[11px] font-black focus:outline-none cursor-pointer text-foreground uppercase tracking-wider">
                                                                                <option value="amount">月销金额降序</option>
                                                                                <option value="sales">月销量降序</option>
                                                                                <option value="days_desc">上架时间降序</option>
                                                                                <option value="score">系统得分降序</option>
                                                                            </select>
                                                                        </div>
                                                                        <div className="text-[10px] font-bold text-muted-foreground/40 whitespace-nowrap border-l border-border/40 pl-6 uppercase tracking-tighter">
                                                                            共计 <span className="text-primary">{taskProducts.filter(tp => {
                                                                                if (!onlyHighQuality) return true;
                                                                                const raw = tp.products_raw_data;
                                                                                const listedDays = raw.created_dt ? Math.max(1, Math.floor((new Date() - new Date(raw.created_dt.split('.')[0].replace(' ', 'T'))) / (1000 * 60 * 60 * 24))) : 999;
                                                                                return listedDays <= filterDays && (raw.sale_qty || 0) >= filterSales && (raw.review_qty || 0) >= filterReviews && (raw.sale_price || 0) >= filterMinPrice;
                                                                            }).length}</span> 个商品 / 总数 {taskProducts.length}
                                                                        </div>
                                                                    </div>
                                                                </div>

                                                                {taskProducts.length === 0 ? (
                                                                    <div className="p-10 text-center text-muted-foreground text-sm border border-dashed border-border/50 rounded-xl">无样本商品数据</div>
                                                                ) : (
                                                                    taskProducts
                                                                        .filter(tp => {
                                                                            if (!onlyHighQuality) return true;
                                                                            const raw = tp.products_raw_data;
                                                                            const listedDays = raw.created_dt ? Math.max(1, Math.floor((new Date() - new Date(raw.created_dt.split('.')[0].replace(' ', 'T'))) / (1000 * 60 * 60 * 24))) : 999;
                                                                            return listedDays <= filterDays && (raw.sale_qty || 0) >= filterSales && (raw.review_qty || 0) >= filterReviews && (raw.sale_price || 0) >= filterMinPrice;
                                                                        })
                                                                        .sort((a, b) => {
                                                                            const ra = a.products_raw_data;
                                                                            const rb = b.products_raw_data;
                                                                            if (sortBy === 'amount') return (rb.sale_amount || 0) - (ra.sale_amount || 0);
                                                                            if (sortBy === 'sales') return (rb.sale_qty || 0) - (ra.sale_qty || 0);
                                                                            if (sortBy === 'days_desc') {
                                                                                const da = ra.created_dt ? new Date(ra.created_dt.split('.')[0].replace(' ', 'T')).getTime() : 0;
                                                                                const db = rb.created_dt ? new Date(rb.created_dt.split('.')[0].replace(' ', 'T')).getTime() : 0;
                                                                                return da - db; // 时间值越小(越老)越靠前 = 降序？不对，上架时间降序应该是天数大的在前面，即时间小的在前面。
                                                                                // 天数 = Now - Created. 天数降序 = 时间小(老)的在前。
                                                                            }
                                                                            // Default: score
                                                                            const getScore = (tp) => {
                                                                                const raw = tp.products_raw_data;
                                                                                const ld = raw.created_dt ? Math.max(1, Math.floor((new Date() - new Date(raw.created_dt.split('.')[0].replace(' ', 'T'))) / (1000 * 60 * 60 * 24))) : 999;
                                                                                return getMetricScore('monthly_sales', raw.sale_qty || 0) +
                                                                                       getMetricScore('reviews', raw.review_qty || 0) +
                                                                                       getMetricScore('price', raw.sale_price || 0) +
                                                                                       getMetricScore('days_per_review', ld, raw.review_qty || 0) +
                                                                                       getMetricScore('avg_sales', selectedTask?.category_stats?.sale_qty / selectedTask?.category_stats?.sale_product_qty || 0);
                                                                            };
                                                                            return getScore(b) - getScore(a);
                                                                        })
                                                                        .map((tp, idx) => {
                                                                        const raw = tp.products_raw_data;

                                                                        // Extract create date safely
                                                                        const createDateOnly = raw.created_dt ? raw.created_dt.substring(0, 10) : '--';
                                                                        const listedDays = raw.created_dt ? Math.max(1, Math.floor((new Date() - new Date(raw.created_dt.split('.')[0].replace(' ', 'T'))) / (1000 * 60 * 60 * 24))) : '--';
                                                                        const ratingRatio = raw.review_qty > 0 && listedDays !== '--' ? (listedDays / raw.review_qty).toFixed(2) : '--';

                                                                        return (
                                                                            <div key={idx} className="flex gap-4 p-4 bg-card border border-border rounded-xl shadow-sm hover:border-primary/30 transition-all group items-center">
                                                                                {/* 1. 左侧图片区 (固定宽高) */}
                                                                                <a href={raw.product_url} target="_blank" rel="noopener noreferrer" className="w-16 h-16 rounded-md bg-muted overflow-hidden shrink-0 border border-border flex items-center justify-center text-[10px] font-bold text-muted-foreground group-hover:border-primary/50 transition-colors">
                                                                                    {raw.preview_image_list ? <img src={JSON.parse(raw.preview_image_list)[0].medium} alt="" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" /> : 'IMG'}
                                                                                </a>

                                                                                {/* 2. 中间商品名称及附加信息区 (固定宽度或比例) */}
                                                                                <div className="w-[25%] min-w-[180px] max-w-[240px] flex flex-col justify-between h-full pr-4 border-r border-border/30">
                                                                                    <a href={raw.product_url} target="_blank" rel="noopener noreferrer" className="text-[13px] font-bold text-foreground hover:text-primary transition-colors leading-snug line-clamp-2" title={raw.product_name}>
                                                                                        {raw.product_name || '未知商品名称'}
                                                                                    </a>
                                                                                    <div className="flex gap-2 mt-2 items-center">
                                                                                        <span className="text-[10px] font-mono text-muted-foreground/60 font-medium">{createDateOnly} | {listedDays}天</span>
                                                                                    </div>
                                                                                </div>

                                                                                {/* 3. 右侧横向排列的数据指标区 (自适应剩余宽度) - 得分优先 */}
                                                                                <div className="flex-1 flex justify-between items-start pl-2 h-full py-1">

                                                                                    <div className="flex flex-col px-1 w-20 min-h-[60px]">
                                                                                        <span className="text-[10px] text-muted-foreground font-bold mb-1 uppercase tracking-tighter shrink-0">销量</span>
                                                                                        <div className="flex-1 flex flex-col justify-center">
                                                                                            <span className="text-sm font-black text-emerald-500 font-mono leading-none">
                                                                                                +{getMetricScore('monthly_sales', raw.sale_qty || 0).toFixed(1)}
                                                                                            </span>
                                                                                            <span className="text-[10px] font-bold text-muted-foreground/40 font-mono mt-1">{raw.sale_qty || 0}</span>
                                                                                        </div>
                                                                                    </div>

                                                                                    <div className="flex flex-col px-1 w-20 min-h-[60px]">
                                                                                        <span className="text-[10px] text-muted-foreground font-bold mb-1 uppercase tracking-tighter shrink-0">评论</span>
                                                                                        <div className="flex-1 flex flex-col justify-center">
                                                                                            <span className="text-sm font-black text-amber-500 font-mono leading-none">
                                                                                                +{getMetricScore('reviews', raw.review_qty || 0).toFixed(1)}
                                                                                            </span>
                                                                                            <span className="text-[10px] font-bold text-muted-foreground/40 font-mono mt-1">{raw.review_qty || 0}</span>
                                                                                        </div>
                                                                                    </div>

                                                                                    <div className="flex flex-col px-1 w-24 min-h-[60px]">
                                                                                        <span className="text-[10px] text-muted-foreground font-bold mb-1 uppercase tracking-tighter shrink-0">售价</span>
                                                                                        <div className="flex-1 flex flex-col justify-center">
                                                                                            <span className="text-sm font-black text-blue-500 font-mono leading-none">
                                                                                                +{getMetricScore('price', raw.sale_price || 0).toFixed(1)}
                                                                                            </span>
                                                                                            <span className="text-[10px] font-bold text-muted-foreground/40 font-mono mt-1 truncate">{raw.sale_price?.toLocaleString() || 0} ₸</span>
                                                                                        </div>
                                                                                    </div>

                                                                                    <div className="flex flex-col px-1 w-24 min-h-[60px]">
                                                                                        <span className="text-[10px] text-muted-foreground font-bold mb-1 uppercase tracking-tighter shrink-0">天数/评论</span>
                                                                                        <div className="flex-1 flex flex-col justify-center">
                                                                                            <span className="text-sm font-black text-rose-500 font-mono leading-none">
                                                                                                +{getMetricScore('days_per_review', listedDays, raw.review_qty || 0).toFixed(1)}
                                                                                            </span>
                                                                                            <span className="text-[10px] font-bold text-muted-foreground/40 font-mono mt-1 leading-tight">
                                                                                                {listedDays} / {raw.review_qty || 0}
                                                                                                <br />
                                                                                                比值: {ratingRatio}
                                                                                            </span>
                                                                                        </div>
                                                                                    </div>

                                                                                    <div className="flex flex-col px-1 w-24 min-h-[60px]">
                                                                                        <span className="text-[10px] text-muted-foreground font-bold mb-1 uppercase tracking-tighter shrink-0">销品比</span>
                                                                                        <div className="flex-1 flex flex-col justify-center">
                                                                                            <span className="text-sm font-black text-violet-500 dark:text-violet-400 font-mono leading-none">
                                                                                                +{getMetricScore('avg_sales', selectedTask?.category_stats?.sale_qty / selectedTask?.category_stats?.sale_product_qty || 0).toFixed(1)}
                                                                                            </span>
                                                                                            <span className="text-[10px] font-bold text-muted-foreground/40 font-mono mt-1 leading-tight">
                                                                                                {selectedTask?.category_stats?.sale_qty || 0} / {selectedTask?.category_stats?.sale_product_qty || 0}
                                                                                                <br />
                                                                                                比值: {(selectedTask?.category_stats?.sale_qty / selectedTask?.category_stats?.sale_product_qty || 0).toFixed(2)}
                                                                                            </span>
                                                                                        </div>
                                                                                    </div>

                                                                                    {/* 4. 最右侧总得分 */}
                                                                                    <div className="flex flex-col items-center pl-4 ml-2 border-l border-border/30 h-full min-w-[70px] min-h-[60px]">
                                                                                        <span className="text-[9px] text-muted-foreground font-bold uppercase mb-1 shrink-0">总得分</span>
                                                                                        <div className="flex-1 flex flex-col justify-center">
                                                                                            <span className="text-2xl font-black text-primary font-mono leading-none">
                                                                                                {(
                                                                                                    getMetricScore('monthly_sales', raw.sale_qty || 0) +
                                                                                                    getMetricScore('reviews', raw.review_qty || 0) +
                                                                                                    getMetricScore('price', raw.sale_price || 0) +
                                                                                                    getMetricScore('days_per_review', listedDays, raw.review_qty || 0) +
                                                                                                    getMetricScore('avg_sales', selectedTask?.category_stats?.sale_qty / selectedTask?.category_stats?.sale_product_qty || 0)
                                                                                                ).toFixed(1)}
                                                                                            </span>
                                                                                        </div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        );
                                                                    })
                                                                )}
                                                            </div>

                                                            {/* --- 右侧栏：类目聚合数据 与 趋势图 (占 1 份宽度) --- */}
                                                            <div className="lg:col-span-1 space-y-6 sticky top-0">
                                                                {/* 1. 类目综合数据区 */}
                                                                <div className="bg-card border border-border rounded-2xl p-6 shadow-xl flex flex-col gap-6">
                                                                    <h3 className="text-xl font-black text-foreground px-1">该类目的指标数据</h3>

                                                                    {/* 1. 采集覆盖区间 */}
                                                                    <div className="bg-muted/40 rounded-xl px-4 py-3 flex justify-between items-center border border-border">
                                                                        <span className="text-[12px] font-bold text-muted-foreground uppercase tracking-tight">采集覆盖区间</span>
                                                                        <span className="text-sm font-mono font-bold text-primary">
                                                                            {(() => {
                                                                                const stats = selectedTask?.category_stats;
                                                                                if (stats?.startDate && stats?.endDate) {
                                                                                    const fmt = (s) => `${s.substring(0, 4)}.${s.substring(4, 6)}.${s.substring(6, 8)}`;
                                                                                    return `${fmt(stats.startDate)}-${fmt(stats.endDate)}`;
                                                                                }
                                                                                return '--';
                                                                            })()}
                                                                        </span>
                                                                    </div>

                                                                    {/* 2. 四大核心指标 Grid */}
                                                                    <div className="grid grid-cols-4 gap-3">
                                                                        {[
                                                                            { label: '销量数', val: selectedTask?.category_stats?.sale_qty?.toLocaleString() || '0', color: 'text-orange-500' },
                                                                            { label: '商品数', val: selectedTask?.category_stats?.sale_product_qty?.toLocaleString() || '0', color: 'text-orange-500' },
                                                                            { label: '卖家数', val: selectedTask?.category_stats?.sale_merchant_qty?.toLocaleString() || (selectedTask?.category_stats?.merchant_count || '0'), color: 'text-orange-500' },
                                                                            { label: '品牌数', val: selectedTask?.category_stats?.brand_qty?.toLocaleString() || '0', color: 'text-orange-500' }
                                                                        ].map((item, id) => (
                                                                            <div key={id} className="bg-muted/40 rounded-xl p-3 border border-border flex flex-col gap-2">
                                                                                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-tight">{item.label}</span>
                                                                                <span className={`text-xl font-black ${item.color} font-mono leading-none`}>{item.val}</span>
                                                                            </div>
                                                                        ))}
                                                                    </div>

                                                                    {/* 3. 销售收入与 CR3 */}
                                                                    <div className="grid grid-cols-3 gap-4">
                                                                        <div className="col-span-2 flex flex-col gap-3">
                                                                            <div className="bg-muted/40 rounded-xl px-4 py-3 border border-border flex justify-between items-center">
                                                                                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">前3名销售收入</span>
                                                                                <span className="text-lg font-black text-sky-500 font-mono">
                                                                                    {selectedTask?.category_stats?.top3_revenue?.toLocaleString() || '0'}
                                                                                </span>
                                                                            </div>
                                                                            <div className="bg-muted/40 rounded-xl px-4 py-3 border border-border flex justify-between items-center">
                                                                                <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">总销售收入金额</span>
                                                                                <span className="text-lg font-black text-sky-500 font-mono">
                                                                                    {(selectedTask?.category_stats?.sale_amount || 0).toLocaleString()}
                                                                                </span>
                                                                            </div>
                                                                        </div>
                                                                        <div className="col-span-1 bg-muted/40 rounded-xl p-4 border border-border flex flex-col justify-between">
                                                                            <span className="text-[10px] font-black text-foreground uppercase tracking-tighter">CR3 集中度</span>
                                                                            <span className="text-2xl font-black text-sky-500 font-mono leading-none mb-1">
                                                                                {selectedTask?.category_stats?.cr3 || '0.0%'}
                                                                            </span>
                                                                        </div>
                                                                    </div>
                                                                </div>

                                                                {/* 2. 6个月销量趋势图区 */}
                                                                <div className="bg-card border border-border rounded-xl shadow-sm p-6 flex flex-col group hover:border-primary/30 transition-all">
                                                                    <h3 className="text-lg font-black text-foreground mb-1">销量趋势 (近6个月)</h3>

                                                                    <div className="relative h-32 w-full flex items-end justify-between px-2 pt-4">
                                                                        {(!selectedTask?.trend_data || selectedTask.trend_data.length === 0) ? (
                                                                            <div className="absolute inset-0 flex items-center justify-center opacity-20 flex-col gap-2">
                                                                                <TrendingUp size={24} />
                                                                                <span className="text-[10px] uppercase font-black tracking-tighter">Loading Trend Data...</span>
                                                                            </div>
                                                                        ) : (
                                                                            <>
                                                                                {selectedTask.trend_data.slice(-6).map((t, i, arr) => {
                                                                                    const maxSale = Math.max(...arr.map(d => d.sale_qty || 0), 1);
                                                                                    const heightPercent = maxSale > 0 ? ((t.sale_qty || 0) / maxSale * 100) : 0;
                                                                                    const monthLabel = t.event_date ? new Date(t.event_date).getMonth() + 1 : (i + 1);

                                                                                    return (
                                                                                        <div key={i} className="relative flex-1 flex flex-col justify-end h-full gap-2 group/bar cursor-pointer">
                                                                                            <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] font-mono font-black opacity-0 group-hover/bar:opacity-100 transition-opacity bg-foreground text-background px-1.5 py-0.5 rounded z-10 whitespace-nowrap">
                                                                                                {t.sale_qty >= 1000 ? (t.sale_qty / 1000).toFixed(1) + 'k' : (t.sale_qty || 0)}
                                                                                            </div>
                                                                                            {/* 直方图柱子 */}
                                                                                            <div
                                                                                                className="w-6 mx-auto bg-primary/10 rounded-t-sm transition-all group-hover/bar:bg-primary/30"
                                                                                                style={{ height: `${heightPercent}%` }}
                                                                                            ></div>
                                                                                            {/* X轴标签 */}
                                                                                            <span className="text-[9px] text-muted-foreground font-mono text-center absolute -bottom-5 w-full">{monthLabel}月</span>
                                                                                        </div>
                                                                                    );
                                                                                })}

                                                                                {/* 折线图 Overlay SVG */}
                                                                                <svg className="absolute inset-0 h-full w-full pointer-events-none pt-4 px-2" viewBox="0 0 100 100" preserveAspectRatio="none">
                                                                                    <polyline
                                                                                        fill="none"
                                                                                        stroke="currentColor"
                                                                                        strokeWidth="2"
                                                                                        className="text-primary drop-shadow-[0_2px_4px_rgba(var(--primary),0.5)]"
                                                                                        points={selectedTask.trend_data.slice(-6).map((t, i, arr) => {
                                                                                            const maxSale = Math.max(...arr.map(d => d.sale_qty || 0), 1);
                                                                                            // 将高度映射到 0-100 (反转，SVG y 轴向下)
                                                                                            const h = 100 - (Math.min(100, (t.sale_qty || 0) / maxSale * 100));
                                                                                            const x = ((i + 0.5) / arr.length) * 100;
                                                                                            return `${x},${h}`;
                                                                                        }).join(' ')}
                                                                                        vectorEffect="non-scaling-stroke"
                                                                                    />
                                                                                </svg>
                                                                            </>
                                                                        )}
                                                                    </div>
                                                                    <div className="h-6"></div> {/* padding-bottom buffer */}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="animate-in fade-in slide-in-from-bottom-2 duration-500">
                                                        {/* 哥，这是同步到 Raw Tab 的筛选与排序工具条 */}
                                                        <div className="bg-muted/10 border border-border/40 rounded-xl p-3 mb-4 flex items-center justify-between">
                                                            <div className="flex items-center gap-6">
                                                                <div className="flex items-center gap-3 pr-4 border-r border-border/40">
                                                                    <div 
                                                                        onClick={() => setOnlyHighQuality(!onlyHighQuality)}
                                                                        className={`w-10 h-5 rounded-full relative transition-all cursor-pointer ${onlyHighQuality ? 'bg-orange-500' : 'bg-muted-foreground/30'}`}
                                                                    >
                                                                        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${onlyHighQuality ? 'left-[22px]' : 'left-0.5'}`} />
                                                                    </div>
                                                                    <span className="text-xs font-black text-foreground/80 whitespace-nowrap">潜力优质商品挑选</span>
                                                                </div>
                                                                
                                                                <div className="flex items-center gap-4 text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">
                                                                    <div className="flex items-center gap-2">
                                                                        <span>天数 &lt;</span>
                                                                        <input type="number" value={filterDays} onChange={e => setFilterDays(Number(e.target.value))} className="bg-transparent border-b border-border/40 text-emerald-500 w-10 text-center focus:outline-none focus:border-primary" />
                                                                    </div>
                                                                    <div className="flex items-center gap-2">
                                                                        <span>销量 &gt;</span>
                                                                        <input type="number" value={filterSales} onChange={e => setFilterSales(Number(e.target.value))} className="bg-transparent border-b border-border/40 text-emerald-500 w-10 text-center focus:outline-none focus:border-primary" />
                                                                    </div>
                                                                    <div className="flex items-center gap-2">
                                                                        <span>评论 &gt;</span>
                                                                        <input type="number" value={filterReviews} onChange={e => setFilterReviews(Number(e.target.value))} className="bg-transparent border-b border-border/40 text-emerald-500 w-10 text-center focus:outline-none focus:border-primary" />
                                                                    </div>
                                                                    <div className="flex items-center gap-2">
                                                                        <span>价格 &gt;</span>
                                                                        <input type="number" value={filterMinPrice} onChange={e => setFilterMinPrice(Number(e.target.value))} className="bg-transparent border-b border-border/40 text-emerald-500 w-16 text-center focus:outline-none focus:border-primary" />
                                                                    </div>
                                                                </div>
                                                            </div>

                                                            <div className="flex items-center gap-6">
                                                                <div className="flex items-center gap-2">
                                                                    <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/40">排序:</span>
                                                                    <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="bg-transparent border-none text-[11px] font-black focus:outline-none cursor-pointer text-foreground uppercase tracking-wider">
                                                                        <option value="amount">月销售额降序</option>
                                                                        <option value="score">系统总得分降序</option>
                                                                        <option value="sales">销量优先降序</option>
                                                                        <option value="price_asc">价格最低升序</option>
                                                                        <option value="reviews">评论数量降序</option>
                                                                        <option value="days_asc">新品优先</option>
                                                                    </select>
                                                                </div>
                                                                <div className="text-[10px] font-bold text-muted-foreground/40 whitespace-nowrap border-l border-border/40 pl-6 uppercase tracking-tighter">
                                                                    共计 <span className="text-primary">{taskProducts.filter(tp => {
                                                                        if (!onlyHighQuality) return true;
                                                                        const raw = tp.products_raw_data;
                                                                        const listedDays = raw.created_dt ? Math.max(1, Math.floor((new Date() - new Date(raw.created_dt.split('.')[0].replace(' ', 'T'))) / (1000 * 60 * 60 * 24))) : 999;
                                                                        return listedDays <= filterDays && (raw.sale_qty || 0) >= filterSales && (raw.review_qty || 0) >= filterReviews && (raw.sale_price || 0) >= filterMinPrice;
                                                                    }).length}</span> 个商品 / 总数 {taskProducts.length}
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="bg-card border border-border rounded-xl shadow-sm overflow-x-auto custom-scrollbar">
                                                            <table className="w-full text-left text-sm min-w-[1200px]">
                                                                <thead className="bg-muted/30 border-b border-border text-[10px] uppercase text-muted-foreground font-black tracking-widest">
                                                                    <tr>
                                                                        <th className="px-6 py-4 sticky left-0 bg-card z-10">商品 ID / 名称</th>
                                                                        <th className="px-6 py-4">品牌</th>
                                                                        <th className="px-6 py-4 text-right">参考价格 (₸)</th>
                                                                        <th className="px-6 py-4 text-right">月销量</th>
                                                                        <th className="px-6 py-4 text-center">评价/星级</th>
                                                                        <th className="px-6 py-4 text-center">卖家</th>
                                                                        <th className="px-6 py-4 text-center">ABC 分类</th>
                                                                        <th className="px-6 py-4 text-right">月销金额</th>
                                                                        <th className="px-6 py-4">上架时间</th>
                                                                        <th className="px-6 py-4">限制类型</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody className="divide-y divide-border/20">
                                                                    {taskProducts
                                                                        .filter(tp => {
                                                                            if (!onlyHighQuality) return true;
                                                                            const raw = tp.products_raw_data;
                                                                            const listedDays = raw.created_dt ? Math.max(1, Math.floor((new Date() - new Date(raw.created_dt.split('.')[0].replace(' ', 'T'))) / (1000 * 60 * 60 * 24))) : 999;
                                                                            return listedDays <= filterDays && (raw.sale_qty || 0) >= filterSales && (raw.review_qty || 0) >= filterReviews && (raw.sale_price || 0) >= filterMinPrice;
                                                                        })
                                                                        .sort((a, b) => {
                                                                            const ra = a.products_raw_data;
                                                                            const rb = b.products_raw_data;
                                                                            if (sortBy === 'amount') return (rb.sale_amount || 0) - (ra.sale_amount || 0);
                                                                            if (sortBy === 'sales') return (rb.sale_qty || 0) - (ra.sale_qty || 0);
                                                                            if (sortBy === 'days_desc') {
                                                                                const da = ra.created_dt ? new Date(ra.created_dt.split('.')[0].replace(' ', 'T')).getTime() : 0;
                                                                                const db = rb.created_dt ? new Date(rb.created_dt.split('.')[0].replace(' ', 'T')).getTime() : 0;
                                                                                return da - db; // 时间值越小(越老)越靠前 = 降序？不对，上架时间降序应该是天数大的在前面，即时间小的在前面。
                                                                                // 天数 = Now - Created. 天数降序 = 时间小(老)的在前。
                                                                            }
                                                                            // Default: score (哥，这里也用同样的评分函数)
                                                                            const getScore = (tp) => {
                                                                                const raw = tp.products_raw_data;
                                                                                const ld = raw.created_dt ? Math.max(1, Math.floor((new Date() - new Date(raw.created_dt.split('.')[0].replace(' ', 'T'))) / (1000 * 60 * 60 * 24))) : 999;
                                                                                return getMetricScore('monthly_sales', raw.sale_qty || 0) +
                                                                                       getMetricScore('reviews', raw.review_qty || 0) +
                                                                                       getMetricScore('price', raw.sale_price || 0) +
                                                                                       getMetricScore('days_per_review', ld, raw.review_qty || 0) +
                                                                                       getMetricScore('avg_sales', selectedTask?.category_stats?.sale_qty / selectedTask?.category_stats?.sale_product_qty || 0);
                                                                            };
                                                                            return getScore(b) - getScore(a);
                                                                        })
                                                                        .map((tp, idx) => {
                                                                        const raw = tp.products_raw_data;
                                                                        const mainImg = raw.preview_image_list ? JSON.parse(raw.preview_image_list)[0]?.medium : "https://via.placeholder.com/150";

                                                                        return (
                                                                            <tr key={idx} className="hover:bg-muted/5 transition-colors group">
                                                                                <td className="px-6 py-4 sticky left-0 bg-card group-hover:bg-muted/5 z-10">
                                                                                    <div className="flex gap-4 items-center min-w-[300px]">
                                                                                        <a href={raw.product_url} target="_blank" rel="noopener noreferrer" className="w-12 h-12 rounded-lg bg-muted border border-border/50 shrink-0 overflow-hidden block">
                                                                                            <img src={mainImg} alt="" className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                                                                                        </a>
                                                                                        <div className="min-w-0">
                                                                                            <a href={raw.product_url} target="_blank" rel="noopener noreferrer" className="font-bold text-foreground line-clamp-1 text-xs hover:underline group-hover:text-primary transition-colors block" title={raw.product_name}>{raw.product_name}</a>
                                                                                            <div className="text-[9px] text-muted-foreground mt-1 font-mono">{raw.sku}</div>
                                                                                        </div>
                                                                                    </div>
                                                                                </td>
                                                                                <td className="px-6 py-4 text-xs font-normal text-muted-foreground">{raw.brand_name || '--'}</td>
                                                                                <td className="px-6 py-4 font-mono font-normal text-xs text-foreground text-right">{raw.sale_price?.toLocaleString() || '--'}</td>
                                                                                <td className="px-6 py-4 font-mono font-normal text-xs text-foreground text-right">{raw.sale_qty?.toLocaleString() || '--'}</td>
                                                                                <td className="px-6 py-4 text-center">
                                                                                    <div className="flex flex-col gap-1 items-center">
                                                                                        <span className="text-amber-500 text-xs font-normal">{raw.product_rate || '0.0'} ★</span>
                                                                                        <span className="text-xs text-muted-foreground">{raw.review_qty || 0} 评</span>
                                                                                    </div>
                                                                                </td>
                                                                                <td className="px-6 py-4 text-center font-mono font-normal text-xs">{raw.merchant_count || 1}</td>
                                                                                <td className="px-6 py-4 text-center">
                                                                                    <span className={`px-2 py-0.5 rounded text-xs font-normal ${raw.amount_abc === 'A' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>{raw.amount_abc || 'C'}</span>
                                                                                </td>
                                                                                <td className="px-6 py-4 text-right font-mono font-normal text-muted-foreground text-xs">{raw.sale_amount?.toLocaleString()}</td>
                                                                                <td className="px-6 py-4 text-xs font-normal text-muted-foreground whitespace-nowrap">
                                                                                    {raw.created_dt ? `${Math.max(0, Math.floor((new Date() - new Date(raw.created_dt.split('.')[0].replace(' ', 'T'))) / (1000 * 60 * 60 * 24)))} 天` : '--'}
                                                                                </td>
                                                                                <td className="px-6 py-4 text-xs font-normal text-muted-foreground uppercase">{raw.restrict_type || '无'}</td>
                                                                            </tr>
                                                                        );
                                                                    })}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* --- 视图：算法配置 --- */}
                        {activeTab === 'algo' && (
                            <div className={`${PDL.spacing.section} flex-1 overflow-y-auto custom-scrollbar pr-2 pb-10`}>
                                <div className="space-y-6">
                                    <div className={`bg-card ${PDL.radius.card} border border-border overflow-hidden shadow-xl`}>
                                        <table className="w-full text-left border-collapse">
                                            <thead className="bg-muted/30 text-[10px] font-black uppercase tracking-widest text-muted-foreground border-b border-border/50">
                                                <tr>
                                                    <th className="px-8 py-5">序号</th>
                                                    <th className="px-6 py-5">指标类别</th>
                                                    <th className="px-6 py-5">指标名称</th>
                                                    <th className="px-6 py-5">获取方式 / 处理逻辑</th>
                                                    <th className="px-6 py-5">评分区间 (阈值)</th>
                                                    <th className="px-6 py-5 text-center">对应得分</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-border/10">
                                                {algoConfig && [
                                                    { id: 1, key: "monthly_sales", type: "市场需求", name: "月销量", logic: "读取商品近30天销量", ranges: [">1000", "601-1000", "401-600", "201-400", "101-200", "60-100", "<60"] },
                                                    { id: 2, key: "reviews", type: "用户反馈", name: "评论数量", logic: "读取评论总数", ranges: [">400", "200-400", "100-200", "50-100", "15-50", "<15"] },
                                                    { id: 3, key: "price", type: "价格结构", name: "商品价格", logic: "读取当前SKU价格(₸)", ranges: [">8000", "3000-8000", "1500-3000", "<1500"] },
                                                    { id: 4, key: "avg_sales", type: "类目容量", name: "单品均销", logic: "类目总销量 ÷ 商品数", ranges: [">80", "50-80", "30-50", "15-30", "≤15"] },
                                                    { id: 5, key: "days_per_review", type: "成长潜力", name: "天数/评论比", logic: "上架天数 ÷ 评论数", ranges: ["≤0.5", "0.5-1", "1-2", "2-2.5", ">2.5"] },
                                                ].map((row) => (
                                                    <tr key={row.id} className="hover:bg-muted/5 transition-colors group">
                                                        <td className="px-8 py-6 font-mono text-xs text-muted-foreground">{row.id}</td>
                                                        <td className="px-6 py-6"><span className="px-3 py-1 bg-primary/10 text-primary border border-primary/20 rounded-full text-[10px] font-black uppercase">{row.type}</span></td>
                                                        <td className="px-6 py-6 font-bold text-sm">{row.name}</td>
                                                        <td className="px-6 py-6 text-xs text-muted-foreground font-medium">{row.logic}</td>
                                                        <td className="px-6 py-6">
                                                            <div className="flex flex-col gap-1.5">
                                                                {row.ranges.map((r, idx) => (
                                                                    <div key={idx} className="text-xs font-mono text-foreground/80 h-6 flex items-center">{r}</div>
                                                                ))}
                                                            </div>
                                                        </td>
                                                        <td className="px-6 py-6">
                                                            <div className="flex flex-col gap-1.5 items-center">
                                                                {algoConfig[row.key].scores.map((s, idx) => (
                                                                    <input
                                                                        key={idx}
                                                                        type="text"
                                                                        value={s}
                                                                        onChange={(e) => updateAlgoConfigValue(row.key, idx, e.target.value)}
                                                                        className="w-14 h-6 bg-muted/40 border border-border/50 rounded text-center text-xs font-black text-primary hover:border-primary/50 focus:border-primary focus:outline-none transition-all"
                                                                    />
                                                                ))}
                                                            </div>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="bg-card border border-border p-6 rounded-2xl shadow-lg border-l-4 border-l-rose-500">
                                        <h4 className="text-sm font-black mb-2 flex items-center gap-2">
                                            <XCircle size={16} className="text-rose-500" />
                                            市场结构过滤 (Market Filtering)
                                        </h4>
                                        <p className="text-xs text-muted-foreground leading-relaxed">
                                            配置 CR3 集中度判定逻辑。当前系统设定：如果 CR3 ＞ 60% 标记为高度集中（红海），30%-60% 为中度，小于 30% 为蓝海。
                                        </p>
                                    </div>
                                    <div className="bg-card border border-border p-6 rounded-2xl shadow-lg border-l-4 border-l-emerald-500">
                                        <h4 className="text-sm font-black mb-2 flex items-center gap-2">
                                            <CheckCircle2 size={16} className="text-emerald-500" />
                                            权重应用规则
                                        </h4>
                                        <p className="text-xs text-muted-foreground leading-relaxed">
                                            修改上述数值后，点击“保存”将自动更新全局评分策略。所有新采集的商品将立即按照新矩阵进行评分计算。
                                        </p>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* --- 视图：系统管理 --- */}
                        {activeTab === 'settings' && (
                            <div className={`${PDL.spacing.section} flex-1 overflow-y-auto custom-scrollbar pr-2`}>
                                <SystemSettings />
                            </div>
                        )}
                    </div>
                </main>
                {viewLogId && <LogViewer taskId={viewLogId} onClose={() => setViewLogId(null)} />}
            </div>
        </div>
    );
};

export default App;