import React, { useState, useEffect } from 'react';
import {
    BarChart3,
    Package,
    TrendingUp,
    Target,
    History,
    Play,
    Download,
    CheckCircle,
    Loader2,
    ChevronRight,
    LayoutDashboard
} from 'lucide-react';

const Dashboard = () => {
    const [activeTab, setActiveTab] = useState('dashboard'); // dashboard, pool, history
    const [topCategories, setTopCategories] = useState([]);
    const [categoryTree, setCategoryTree] = useState([]);
    const [taskHistory, setTaskHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedMainCat, setSelectedMainCat] = useState(null);

    useEffect(() => {
        fetchTopStats();
        fetchCategoryTree();
        fetchHistory();
    }, []);

    const fetchTopStats = async () => {
        const res = await fetch('http://localhost:8000/api/categories/top_stats');
        const data = await res.json();
        setTopCategories(data);
    };

    const fetchCategoryTree = async () => {
        const res = await fetch('http://localhost:8000/api/categories/tree');
        const data = await res.json();
        setCategoryTree(data);
        if (data.length > 0) setSelectedMainCat(data[0].id);
    };

    const fetchHistory = async () => {
        const res = await fetch('http://localhost:8000/api/tasks/history');
        const data = await res.json();
        setTaskHistory(data);
    };

    const startTask = async (categoryName) => {
        setLoading(true);
        try {
            await fetch('http://localhost:8000/api/tasks/category', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ category: categoryName })
            });
            fetchHistory();
            setActiveTab('history');
        } catch (e) {
            alert("启动失败");
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen bg-[#0b0c10] text-gray-100 font-sans flex">
            {/* Sidebar */}
            <div className="w-64 bg-[#14161c] border-r border-gray-800 flex flex-col p-6 gap-8">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-xl">P</div>
                    <span className="text-xl font-bold tracking-tight">ProSourcing</span>
                </div>

                <nav className="flex flex-col gap-2">
                    <button
                        onClick={() => setActiveTab('dashboard')}
                        className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'dashboard' ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20' : 'text-gray-400 hover:bg-gray-800'}`}
                    >
                        <LayoutDashboard size={18} /> 首页大盘
                    </button>
                    <button
                        onClick={() => setActiveTab('pool')}
                        className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'pool' ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20' : 'text-gray-400 hover:bg-gray-800'}`}
                    >
                        <Target size={18} /> 任务池
                    </button>
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'history' ? 'bg-blue-600/10 text-blue-400 border border-blue-500/20' : 'text-gray-400 hover:bg-gray-800'}`}
                    >
                        <History size={18} /> 历史任务
                    </button>
                </nav>
            </div>

            {/* Main Content */}
            <div className="flex-1 p-10 overflow-y-auto">
                <header className="flex justify-between items-center mb-10">
                    <h2 className="text-2xl font-bold">
                        {activeTab === 'dashboard' && "大盘趋势看板"}
                        {activeTab === 'pool' && "类目任务池"}
                        {activeTab === 'history' && "任务执行历史"}
                    </h2>
                    <div className="flex gap-4">
                        <div className="bg-[#1a1d27] px-4 py-2 rounded-lg border border-gray-800 flex items-center gap-2">
                            <TrendingUp size={16} className="text-emerald-400" />
                            <span className="text-sm">销品比计算已更新</span>
                        </div>
                    </div>
                </header>

                {/* Dashboard Tab */}
                {activeTab === 'dashboard' && (
                    <div className="space-y-10">
                        {/* Top Stats */}
                        <div className="grid grid-cols-4 gap-6">
                            {[
                                { label: '扫描分类', value: '1,240+', icon: <Package />, color: 'text-blue-400' },
                                { label: '活跃卖家', value: '12K+', icon: <BarChart3 />, color: 'text-emerald-400' },
                                { label: '月均增速', value: '14.2%', icon: <TrendingUp />, color: 'text-indigo-400' },
                                { label: '蓝海系数', value: '0.82', icon: <Target />, color: 'text-rose-400' },
                            ].map((s, idx) => (
                                <div key={idx} className="bg-[#14161c] p-6 rounded-2xl border border-gray-800 shadow-sm">
                                    <div className={`${s.color} mb-4 opacity-80`}>{s.icon}</div>
                                    <div className="text-gray-400 text-sm mb-1">{s.label}</div>
                                    <div className="text-2xl font-bold">{s.value}</div>
                                </div>
                            ))}
                        </div>

                        {/* Top 20 Categories Grid */}
                        <div className="bg-[#14161c] rounded-2xl border border-gray-800 p-8 shadow-sm">
                            <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                                <BarChart3 size={18} className="text-blue-500" /> 20大热门一级类目「销品比」大盘
                            </h3>
                            <div className="grid grid-cols-2 gap-x-12 gap-y-6">
                                {topCategories.map((cat, idx) => (
                                    <div key={idx} className="flex flex-col gap-2">
                                        <div className="flex justify-between text-sm">
                                            <span className="font-medium">{cat.name}</span>
                                            <span className="text-gray-500">销品比: <span className="text-blue-400">{(cat.sales_to_product_ratio * 100).toFixed(2)}%</span></span>
                                        </div>
                                        <div className="w-full bg-gray-900 rounded-full h-2 overflow-hidden">
                                            <div
                                                className="bg-gradient-to-r from-blue-600 to-indigo-500 h-full rounded-full transition-all duration-1000"
                                                style={{ width: `${Math.min(cat.sales_to_product_ratio * 200, 100)}%` }}
                                            ></div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* Task Pool Tab */}
                {activeTab === 'pool' && (
                    <div className="bg-[#14161c] rounded-2xl border border-gray-800 p-8 shadow-sm h-[calc(100vh-200px)] flex flex-col">
                        <div className="flex gap-4 mb-8 overflow-x-auto pb-4 border-b border-gray-800">
                            {categoryTree.filter(c => c.is_top_level).map(c => (
                                <button
                                    key={c.id}
                                    onClick={() => setSelectedMainCat(c.id)}
                                    className={`px-4 py-2 rounded-lg text-sm whitespace-nowrap transition-all ${selectedMainCat === c.id ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                                >
                                    {c.name}
                                </button>
                            ))}
                        </div>
                        <div className="overflow-y-auto flex-1 pr-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {categoryTree.filter(c => !c.is_top_level).map(c => (
                                    <div key={c.id} className="bg-[#0b0c10] border border-gray-800 p-4 rounded-xl flex justify-between items-center group">
                                        <span className="text-sm font-medium">{c.name}</span>
                                        <button
                                            onClick={() => startTask(c.name)}
                                            className="bg-blue-600/10 text-blue-400 w-10 h-10 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all hover:bg-blue-600 hover:text-white"
                                        >
                                            <Play size={16} fill="currentColor" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* History Tab */}
                {activeTab === 'history' && (
                    <div className="bg-[#14161c] rounded-2xl border border-gray-800 overflow-hidden shadow-sm">
                        <table className="w-full text-left">
                            <thead>
                                <tr className="border-b border-gray-800 text-gray-400 text-sm">
                                    <th className="p-6 font-medium">执行时间</th>
                                    <th className="p-6 font-medium">分析类目</th>
                                    <th className="p-6 font-medium">状态</th>
                                    <th className="p-6 font-medium">进度</th>
                                    <th className="p-6 font-medium">报告</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-800">
                                {taskHistory.map(task => (
                                    <tr key={task.id} className="hover:bg-gray-800/20 transition-colors">
                                        <td className="p-6 text-sm text-gray-500">{task.created_at?.slice(0, 16).replace('T', ' ')}</td>
                                        <td className="p-6 font-medium">{task.category}</td>
                                        <td className="p-6">
                                            <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500' :
                                                    task.status === 'failed' ? 'bg-rose-500/10 text-rose-500' : 'bg-blue-500/10 text-blue-500'
                                                }`}>
                                                {task.status}
                                            </span>
                                        </td>
                                        <td className="p-6 w-48">
                                            <div className="w-full bg-gray-900 rounded-full h-1.5 overflow-hidden">
                                                <div
                                                    className="bg-blue-500 h-full transition-all duration-500"
                                                    style={{ width: `${task.progress}%` }}
                                                ></div>
                                            </div>
                                        </td>
                                        <td className="p-6">
                                            {task.status === 'completed' ? (
                                                <a
                                                    href={`http://localhost:8000/api/download?path=${task.excel_path}`}
                                                    className="flex items-center gap-2 text-blue-400 hover:underline text-sm"
                                                >
                                                    <Download size={14} /> 下载报告
                                                </a>
                                            ) : <span className="text-gray-600 text-sm">-</span>}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
