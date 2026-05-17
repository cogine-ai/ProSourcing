import { PDL } from '../lib/pdl';

export default function CategoryCard({ cat, onClick }) {
    const ratio = ((cat.sale_product_qty > 0 ? cat.monthly_sales / cat.sale_product_qty : 0)).toFixed(2);
    const ruName = cat?.name_ru || (cat?.category_name?.match(/^(.*)\s\(.*\)$/) || [null, cat?.category_name])[1] || cat?.name || "";
    const zhName = cat?.name_cn || (cat?.category_name?.match(/\s\((.*)\)$/) || [null, ""])[1] || "";

    return (
        <div 
            onClick={onClick}
            className={`bg-card border border-border ${PDL.radius.card} rounded-card-force p-8 hover:border-primary/50 transition-all shadow-md flex flex-col justify-between group h-[320px] cursor-pointer active:scale-[0.98]`}
        >
            <div className="mb-8">
                <h3 className="text-2xl font-black leading-tight text-foreground group-hover:text-primary transition-colors flex flex-col gap-1">
                    <span>{zhName || ruName}</span>
                    {zhName && <span className="text-xs font-bold text-muted-foreground/30 font-mono italic">/ {ruName}</span>}
                </h3>
            </div>

            <div className="flex flex-col gap-6">
                <div className="group/item">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mb-1 border-l-2 border-primary/20 pl-3">月销量</p>
                    <p className="text-2xl font-black text-foreground tracking-tight transition-transform group-hover/item:translate-x-1">{(cat.monthly_sales || 0).toLocaleString()}</p>
                </div>

                <div className="group/item">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mb-1 border-l-2 border-border pl-3">商品数</p>
                    <p className="text-xl font-bold text-muted-foreground tracking-tight transition-transform group-hover/item:translate-x-1">{(cat.sale_product_qty || 0).toLocaleString()}</p>
                </div>
            </div>

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
}
