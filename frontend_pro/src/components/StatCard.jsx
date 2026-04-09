import { ArrowUpRight } from 'lucide-react';
import { PDL } from '../lib/pdl';

export default function StatCard({ label, value, icon }) {
    return (
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
}
