import React, { useState, useEffect } from 'react';
import {
    Users,
    HardDrive,
    Key,
    FileText,
    Plus,
    Trash2,
    Save,
    RefreshCw,
    Shield,
    Calendar,
    Search,
    AlertCircle,
    CheckCircle2
} from 'lucide-react';
import { PDL } from '../lib/pdl';

const API_BASE = "http://localhost:8000";

// --- 子页面：用户管理 ---
const UserManagement = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [showAdd, setShowAdd] = useState(false);
    const [newUser, setNewUser] = useState({ username: '', password: '', role: 'analyst' });

    const fetchUsers = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/system/users`);
            const data = await res.json();
            setUsers(data);
        } catch (err) { console.error(err); }
        setLoading(false);
    };

    const handleAdd = async () => {
        if (!newUser.username || !newUser.password) return;
        try {
            await fetch(`${API_BASE}/api/system/users`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newUser)
            });
            setShowAdd(false);
            setNewUser({ username: '', password: '', role: 'analyst' });
            fetchUsers();
        } catch (err) { alert("添加失败了，哥"); }
    };

    const handleDelete = async (id) => {
        if (!confirm("确定要删除这个账号吗？")) return;
        try {
            await fetch(`${API_BASE}/api/system/users/${id}`, { method: 'DELETE' });
            fetchUsers();
        } catch (err) { console.error(err); }
    };

    useEffect(() => { fetchUsers(); }, []);

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-center">
                <h3 className="text-xl font-black text-foreground">用户管理</h3>
                <button
                    onClick={() => setShowAdd(true)}
                    className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-xs font-bold hover:opacity-90 transition-all"
                >
                    <Plus size={16} /> 新增账号
                </button>
            </div>

            {showAdd && (
                <div className="bg-card border border-primary/20 rounded-xl p-6 shadow-lg animate-in zoom-in-95 duration-300">
                    <div className="grid grid-cols-3 gap-4 mb-4">
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-muted-foreground uppercase">用户名</label>
                            <input
                                value={newUser.username}
                                onChange={e => setNewUser({ ...newUser, username: e.target.value })}
                                className="w-full bg-muted border-none rounded-md px-3 py-2 text-sm focus:ring-1 ring-primary outline-none"
                                placeholder="输入账号"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-muted-foreground uppercase">初始密码</label>
                            <input
                                type="password"
                                value={newUser.password}
                                onChange={e => setNewUser({ ...newUser, password: e.target.value })}
                                className="w-full bg-muted border-none rounded-md px-3 py-2 text-sm focus:ring-1 ring-primary outline-none"
                                placeholder="输入密码"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-[10px] font-bold text-muted-foreground uppercase">角色权限</label>
                            <select
                                value={newUser.role}
                                onChange={e => setNewUser({ ...newUser, role: e.target.value })}
                                className="w-full bg-muted border-none rounded-md px-3 py-2 text-sm focus:ring-1 ring-primary outline-none cursor-pointer"
                            >
                                <option value="analyst">数据分析员 (仅查看)</option>
                                <option value="admin">管理员 (全权限)</option>
                            </select>
                        </div>
                    </div>
                    <div className="flex justify-end gap-3">
                        <button onClick={() => setShowAdd(false)} className="px-4 py-2 text-xs font-bold text-muted-foreground hover:text-foreground">取消</button>
                        <button onClick={handleAdd} className="px-6 py-2 bg-primary text-primary-foreground rounded-md text-xs font-bold">立即创建</button>
                    </div>
                </div>
            )}

            <div className="bg-card border border-border rounded-xl overflow-hidden">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-muted/50 border-b border-border">
                        <tr>
                            <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">用户名</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">角色</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">创建时间</th>
                            <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest text-right">操作</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border/40">
                        {users.map(user => (
                            <tr key={user.id} className="hover:bg-muted/20 transition-colors">
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-xs">
                                            {user.username[0].toUpperCase()}
                                        </div>
                                        <span className="font-bold text-sm tracking-tight">{user.username}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <span className={`px-2 py-1 rounded text-[10px] font-black uppercase tracking-tight ${user.role === 'admin' ? 'bg-amber-500/10 text-amber-500' : 'bg-blue-500/10 text-blue-500'
                                        }`}>
                                        {user.role === 'admin' ? '管理员' : '数据分析员'}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-xs text-muted-foreground font-mono">
                                    {new Date(user.created_at).toLocaleString()}
                                </td>
                                <td className="px-6 py-4 text-right">
                                    {user.username !== 'admin' && (
                                        <button
                                            onClick={() => handleDelete(user.id)}
                                            className="p-2 text-muted-foreground hover:text-rose-500 transition-colors"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
                {users.length === 0 && !loading && (
                    <div className="py-20 flex flex-col items-center justify-center text-muted-foreground/30 gap-4">
                        <Users size={48} />
                        <p className="text-xs font-bold uppercase tracking-widest">暂无用户数据 // NO USERS</p>
                    </div>
                )}
            </div>
        </div>
    );
};

// --- 子页面：存储设置 ---
const StorageSettings = () => {
    const [config, setConfig] = useState({ path: '', auto_cleanup_days: 15 });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch(`${API_BASE}/api/system/settings/storage_config`)
            .then(res => res.json())
            .then(data => { setConfig(data.value); setLoading(false); });
    }, []);

    const handleSave = async () => {
        try {
            await fetch(`${API_BASE}/api/system/settings/storage_config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value: config })
            });
            alert("存储配置已更新");
        } catch (err) { alert("保存失败"); }
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h3 className="text-xl font-black text-foreground">存储设置</h3>

            <div className="space-y-6">
                <div className="bg-card border border-border rounded-xl p-6 space-y-4">
                    <div className="flex items-start gap-4">
                        <div className="p-3 bg-blue-500/10 rounded-lg text-blue-500">
                            <HardDrive size={20} />
                        </div>
                        <div className="flex-1 space-y-1">
                            <p className="font-bold text-sm">文件存储根路径</p>
                            <p className="text-xs text-muted-foreground">采集产出的 Excel、图片及日志文件的存放位置</p>
                            <input
                                value={config.path}
                                onChange={e => setConfig({ ...config, path: e.target.value })}
                                className="w-full mt-2 bg-muted border-none rounded-md px-4 py-2 text-sm font-mono focus:ring-1 ring-primary outline-none"
                            />
                        </div>
                    </div>
                </div>

                <div className="bg-card border border-border rounded-xl p-6 space-y-4">
                    <div className="flex items-start gap-4">
                        <div className="p-3 bg-emerald-500/10 rounded-lg text-emerald-500">
                            <RefreshCw size={20} />
                        </div>
                        <div className="flex-1 space-y-1">
                            <p className="font-bold text-sm">自动清理周期 (天)</p>
                            <p className="text-xs text-muted-foreground">系统将自动移除超过此天数的历史报告与日志</p>
                            <input
                                type="number"
                                value={config.auto_cleanup_days}
                                onChange={e => setConfig({ ...config, auto_cleanup_days: parseInt(e.target.value) || 0 })}
                                className="w-32 mt-2 bg-muted border-none rounded-md px-4 py-2 text-sm font-mono focus:ring-1 ring-primary outline-none"
                            />
                        </div>
                    </div>
                </div>

                <div className="flex justify-end pt-4">
                    <button
                        onClick={handleSave}
                        className="flex items-center gap-2 px-8 py-3 bg-primary text-primary-foreground rounded-xl text-sm font-bold shadow-lg shadow-primary/20 hover:opacity-90 active:scale-95 transition-all"
                    >
                        <Save size={18} /> 保存配置
                    </button>
                </div>
            </div>
        </div>
    );
};

// --- 子页面：采集配置 ---
const CollectionConfig = () => {
    const [config, setConfig] = useState({ algatop: { username: '', password: '' } });

    useEffect(() => {
        fetch(`${API_BASE}/api/system/settings/collection_config`)
            .then(res => res.json())
            .then(data => setConfig(data.value));
    }, []);

    const handleSave = async () => {
        try {
            await fetch(`${API_BASE}/api/system/settings/collection_config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ value: config })
            });
            alert("采集账户已更新");
        } catch (err) { alert("保存失败"); }
    };

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h3 className="text-xl font-black text-foreground">采集配置</h3>

            <div className="p-6 bg-amber-500/5 border border-amber-500/20 rounded-xl flex gap-4">
                <AlertCircle className="text-amber-500 shrink-0" />
                <div>
                    <p className="text-sm font-bold text-amber-700 dark:text-amber-400">注意权限风险</p>
                    <p className="text-xs text-amber-600/70 dark:text-amber-400/50 mt-1">此处保存的账户将用于 RPA 自动登录，请确保账户已开启必要的访问权限并保持活跃。</p>
                </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-8 space-y-6">
                <div className="flex items-center gap-3 mb-2">
                    <div className="w-1.5 h-6 bg-primary rounded-full"></div>
                    <h4 className="font-bold text-sm uppercase tracking-widest">AlgaTop Platform</h4>
                </div>

                <div className="grid grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-muted-foreground uppercase">登录账号</label>
                        <input
                            value={config.algatop?.username}
                            onChange={e => setConfig({ ...config, algatop: { ...config.algatop, username: e.target.value } })}
                            className="w-full bg-muted border-none rounded-md px-4 py-2.5 text-sm focus:ring-1 ring-primary outline-none"
                            placeholder="Email / Phone"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-[10px] font-bold text-muted-foreground uppercase">账户密码</label>
                        <input
                            type="password"
                            value={config.algatop?.password}
                            onChange={e => setConfig({ ...config, algatop: { ...config.algatop, password: e.target.value } })}
                            className="w-full bg-muted border-none rounded-md px-4 py-2.5 text-sm focus:ring-1 ring-primary outline-none"
                            placeholder="••••••••"
                        />
                    </div>
                </div>

                <div className="flex justify-end pt-4">
                    <button
                        onClick={handleSave}
                        className="flex items-center gap-2 px-8 py-3 bg-primary text-primary-foreground rounded-xl text-sm font-bold shadow-lg shadow-primary/20 hover:opacity-90 active:scale-95 transition-all"
                    >
                        <Save size={18} /> 更新凭据
                    </button>
                </div>
            </div>
        </div>
    );
};

// --- 子页面：日志管理 ---
const LogManagement = () => {
    const [logs, setLogs] = useState([]);
    const [filterDate, setFilterDate] = useState('');

    const fetchLogs = async () => {
        try {
            const res = await fetch(`${API_BASE}/api/system/logs`);
            const data = await res.json();
            setLogs(data);
        } catch (err) { console.error(err); }
    };

    const handleClear = async (params) => {
        if (!confirm("确定要进行清理操作吗？")) return;
        try {
            const res = await fetch(`${API_BASE}/api/system/logs/clear`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            const data = await res.json();
            alert(`清理完成，删除了 ${data.count} 个文件`);
            fetchLogs();
        } catch (err) { alert("清理失败"); }
    };

    useEffect(() => { fetchLogs(); }, []);

    const filteredLogs = filterDate ? logs.filter(l => l.date === filterDate) : logs;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 h-full flex flex-col">
            <div className="flex justify-between items-center shrink-0">
                <h3 className="text-xl font-black text-foreground">日志管理</h3>
                <div className="flex gap-3">
                    <button
                        onClick={() => handleClear({ days: 15 })}
                        className="px-4 py-2 border border-border rounded-lg text-xs font-bold hover:bg-muted transition-all"
                    >
                        清除15天前日志
                    </button>
                    <button
                        onClick={() => handleClear({ days: 0 })}
                        className="px-4 py-2 bg-rose-500/10 text-rose-500 border border-rose-500/20 rounded-lg text-xs font-bold hover:bg-rose-500/20 transition-all"
                    >
                        一键清空日志
                    </button>
                </div>
            </div>

            <div className="bg-card border border-border rounded-xl p-4 flex items-center gap-6 shrink-0">
                <div className="flex items-center gap-3 flex-1">
                    <Search size={16} className="text-muted-foreground" />
                    <input
                        type="date"
                        value={filterDate}
                        onChange={e => setFilterDate(e.target.value)}
                        className="bg-transparent border-none outline-none text-sm font-bold cursor-pointer"
                    />
                    {filterDate && (
                        <button onClick={() => setFilterDate('')} className="text-[10px] font-black uppercase text-primary hover:underline">清除筛选</button>
                    )}
                </div>
                {filterDate && (
                    <button
                        onClick={() => handleClear({ date: filterDate })}
                        className="px-4 py-1.5 bg-rose-500 text-white rounded-md text-[10px] font-black uppercase tracking-widest"
                    >
                        删除该日日志
                    </button>
                )}
            </div>

            <div className="flex-1 bg-card border border-border rounded-xl overflow-hidden flex flex-col min-h-0">
                <div className="overflow-y-auto custom-scrollbar flex-1">
                    <table className="w-full text-left border-collapse">
                        <thead className="sticky top-0 bg-muted/90 backdrop-blur-md border-b border-border z-10">
                            <tr>
                                <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">日志文件</th>
                                <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">日期</th>
                                <th className="px-6 py-4 text-[10px] font-bold text-muted-foreground uppercase tracking-widest text-right">大小</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40">
                            {filteredLogs.map((log, i) => (
                                <tr key={i} className="hover:bg-muted/20 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <FileText size={16} className="text-muted-foreground" />
                                            <span className="text-sm font-mono tracking-tight">{log.filename}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-xs font-bold text-muted-foreground">{log.date}</span>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <span className="text-xs font-mono text-muted-foreground">{(log.size / 1024).toFixed(1)} KB</span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {filteredLogs.length === 0 && (
                        <div className="py-20 flex flex-col items-center justify-center text-muted-foreground/30 gap-4">
                            <Calendar size={48} />
                            <p className="text-xs font-bold uppercase tracking-widest">没有对应日期的日志 // NO LOGS FOUND</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- 主组件：系统设置 (左右布局) ---
export const SystemSettings = () => {
    const [activeSubTab, setActiveSubTab] = useState('users');
    const [userRole, setUserRole] = useState('admin'); // 模拟从 Context/Auth 获取

    const menuItems = [
        { id: 'users', label: '用户管理', icon: <Users size={18} />, adminOnly: false },
        { id: 'storage', label: '存储设置', icon: <HardDrive size={18} />, adminOnly: true },
        { id: 'collection', label: '采集配置', icon: <Key size={18} />, adminOnly: true },
        { id: 'logs', label: '日志管理', icon: <FileText size={18} />, adminOnly: false },
    ].filter(item => !item.adminOnly || userRole === 'admin');

    const renderContent = () => {
        switch (activeSubTab) {
            case 'users': return <UserManagement />;
            case 'storage': return <StorageSettings />;
            case 'collection': return <CollectionConfig />;
            case 'logs': return <LogManagement />;
            default: return null;
        }
    };

    return (
        <div className="flex h-full gap-8 animate-in fade-in duration-500">
            {/* 左侧导航树 (Tree-like aside) */}
            <aside className="w-64 shrink-0 flex flex-col gap-2">
                <div className="px-2 mb-4">
                </div>
                <nav className="space-y-1">
                    {menuItems.map(item => (
                        <button
                            key={item.id}
                            onClick={() => setActiveSubTab(item.id)}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all group ${activeSubTab === item.id
                                ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20 scale-[1.02]'
                                : 'text-muted-foreground hover:bg-card hover:text-foreground'
                                }`}
                        >
                            <span className={`${activeSubTab === item.id ? 'text-primary-foreground' : 'group-hover:text-primary transition-colors'}`}>
                                {item.icon}
                            </span>
                            <span className="text-sm font-bold tracking-tight">{item.label}</span>
                        </button>
                    ))}
                </nav>

                <div className="mt-auto p-4 bg-muted/20 border border-border/50 rounded-2xl flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary">
                        <Shield size={20} />
                    </div>
                    <div>
                        <p className="text-[10px] font-bold text-muted-foreground uppercase">Current Identity</p>
                        <p className="text-sm font-black text-foreground tracking-tight">{userRole === 'admin' ? '系统管理员' : '数据分析员'}</p>
                    </div>
                </div>
            </aside>

            {/* 右侧内容主区 */}
            <div className="flex-1 bg-card/30 rounded-3xl border border-border/50 p-8 overflow-hidden flex flex-col shadow-inner">
                <div className="flex-1 overflow-y-auto custom-scrollbar pr-4">
                    {renderContent()}
                </div>
            </div>
        </div>
    );
};
