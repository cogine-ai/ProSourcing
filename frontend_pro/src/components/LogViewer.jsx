import React, { useEffect, useRef, useState } from 'react';
import { XCircle } from 'lucide-react';

export function LogViewer({ apiBase, taskId, onClose }) {
    const [logs, setLogs] = useState("Loading logs...");
    const [autoScroll, setAutoScroll] = useState(true);
    const logEndRef = useRef(null);

    useEffect(() => {
        const fetchLogs = async () => {
            try {
                const res = await fetch(`${apiBase}/api/tasks/${taskId}/logs`);
                if (!res.ok) {
                    throw new Error(`Failed to fetch logs: ${res.status}`);
                }
                const data = await res.json();
                setLogs(data.logs || "No logs found yet.");
            } catch (err) {
                setLogs("Error fetching logs.");
            }
        };

        fetchLogs();
        const timer = setInterval(fetchLogs, 3000);
        return () => clearInterval(timer);
    }, [apiBase, taskId]);

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
                            <input type="checkbox" checked={autoScroll} onChange={(e) => setAutoScroll(e.target.checked)} className="accent-primary" />
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
}
