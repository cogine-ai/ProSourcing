export default function PageHeader({ title, description, actions }) {
    return (
        <div className="mb-8 flex justify-between items-start animate-in fade-in slide-in-from-left-4 duration-500">
            <div>
                <h1 className="text-3xl font-black text-foreground tracking-tight mb-2">{title}</h1>
                <p className="text-muted-foreground text-sm font-medium">{description}</p>
            </div>
            {actions && <div className="flex gap-3">{actions}</div>}
        </div>
    );
}
