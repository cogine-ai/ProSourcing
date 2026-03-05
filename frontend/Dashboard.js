import React, { useState, useEffect } from 'react';
import { Search, Play, Download, CheckCircle, Loader2, BarChart3, Package, TrendingUp } from 'lucide-react';

const Dashboard = () => {
  const [query, setQuery] = useState('');
  const [tasks, setTasks] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);

  // 模拟获取数据
  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/products');
      const data = await res.json();
      setProducts(data);
    } catch (e) {
      console.error("Failed to fetch products", e);
    }
  };

  const startTask = async () => {
    if (!query) return;
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: query })
      });
      const task = await res.json();
      setTasks([task, ...tasks]);
      // 开始轮询进度
      pollTask(task.task_id);
    } catch (e) {
      alert("启动失败，请检查后端服务");
    }
    setLoading(false);
  };

  const pollTask = (id) => {
    const timer = setInterval(async () => {
      const res = await fetch(`http://localhost:8000/api/tasks/${id}`);
      const data = await res.json();
      setTasks(prev => prev.map(t => t.task_id === id ? data : t));
      if (data.status === 'completed' || data.status === 'failed') {
        clearInterval(timer);
        fetchProducts(); 
      }
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-[#0f1117] text-white p-8 font-sans">
      {/* Header */}
      <header className="flex justify-between items-center mb-12">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            ProSourcing AI 选品工作台
          </h1>
          <p className="text-gray-400 mt-2">哥，今天想分析点什么？</p>
        </div>
        <div className="flex gap-4">
          <div className="bg-[#1a1d27] border border-gray-700 rounded-xl px-4 py-2 flex items-center gap-3">
            <TrendingUp size={18} className="text-emerald-400" />
            <span className="text-sm font-medium">昨日新增: 124 件</span>
          </div>
        </div>
      </header>

      {/* Main Action */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
        <div className="lg:col-span-2 bg-[#1a1d27] rounded-2xl p-6 border border-gray-800 shadow-xl">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
            <Search size={20} className="text-blue-400"/> 发起分析任务
          </h2>
          <div className="flex gap-4">
            <input 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入类目名称 (如: 无人机, 电动牙刷)" 
              className="flex-1 bg-[#0f1117] border border-gray-700 rounded-xl px-6 py-4 focus:ring-2 focus:ring-blue-500 outline-none transition-all"
            />
            <button 
              onClick={startTask}
              disabled={loading}
              className="bg-gradient-to-br from-blue-500 to-blue-700 hover:from-blue-600 hover:to-blue-800 px-8 py-4 rounded-xl font-bold flex items-center gap-2 transition-all active:scale-95 disabled:opacity-50"
            >
              {loading ? <Loader2 className="animate-spin" /> : <Play size={18} />}
              立刻执行
            </button>
          </div>
          
          {/* Active Tasks */}
          <div className="mt-8 space-y-4">
            {tasks.map(task => (
              <div key={task.task_id} className="bg-[#0f1117] rounded-xl p-4 border border-gray-800">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium">{task.category} 分析中...</span>
                  <span className="text-xs text-gray-450 uppercase tracking-widest">{task.status}</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div 
                    className="bg-blue-500 h-full rounded-full transition-all duration-500" 
                    style={{width: `${task.progress}%`}}
                  ></div>
                </div>
                {task.status === 'completed' && (
                  <div className="mt-3 flex gap-4">
                     <a href={`http://localhost:8000/download?path=${task.result_url}`} className="text-emerald-400 text-sm flex items-center gap-1 hover:underline">
                       <Download size={14} /> 下载 Excel 报告
                     </a>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Info Card */}
        <div className="bg-gradient-to-br from-indigo-900/40 to-blue-900/40 rounded-2xl p-6 border border-blue-800/50">
          <h2 className="text-xl font-semibold mb-6 flex items-center gap-2 text-blue-200">
            <BarChart3 size={20}/> 选品模型逻辑
          </h2>
          <ul className="space-y-4 text-blue-100/80 text-sm">
            <li className="flex gap-3"><CheckCircle size={16} className="text-emerald-400 shrink-0"/> Algatop API 实时采集</li>
            <li className="flex gap-3"><CheckCircle size={16} className="text-emerald-400 shrink-0"/> 销量、评论、价格三维评分</li>
            <li className="flex gap-3"><CheckCircle size={16} className="text-emerald-400 shrink-0"/> 动态 CR3 集中度计算</li>
            <li className="flex gap-3"><CheckCircle size={16} className="text-emerald-400 shrink-0"/> 自动生成标准 Excel</li>
          </ul>
        </div>
      </div>

      {/* Results Table */}
      <div className="bg-[#1a1d27] rounded-2xl p-6 border border-gray-800 shadow-xl">
        <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
          <Package size={20} className="text-emerald-400"/> 高分选选品预览
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-800">
                <th className="pb-4 font-medium">产品信息</th>
                <th className="pb-4 font-medium">总评分</th>
                <th className="pb-4 font-medium">月销</th>
                <th className="pb-4 font-medium">评论</th>
                <th className="pb-4 font-medium">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {products.map((p, idx) => (
                <tr key={idx} className="hover:bg-[#0f1117] transition-colors">
                  <td className="py-4">
                     <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
                          <img src={p.products_raw_data.image_url} alt="product" className="w-full h-full object-cover" />
                        </div>
                        <div className="max-w-xs">
                          <p className="font-medium truncate">{p.products_raw_data.product_name}</p>
                          <p className="text-xs text-gray-500">{p.products_raw_data.sku}</p>
                        </div>
                     </div>
                  </td>
                  <td className="py-4 font-bold text-blue-400">{p.total_score}</td>
                  <td className="py-4">{Math.floor(p.products_raw_data.sales_3m/3)}</td>
                  <td className="py-4">{p.products_raw_data.reviews_count}</td>
                  <td className="py-4">
                    <button className="text-gray-400 hover:text-white transition-colors">预览</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
