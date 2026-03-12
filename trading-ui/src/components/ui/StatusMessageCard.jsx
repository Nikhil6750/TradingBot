export default function StatusMessageCard({
    title,
    description,
    actionLabel = "",
    onAction,
    tone = "warning",
    className = "",
}) {
    let palette = "border-[#1f1f1f] bg-[rgba(20,20,20,0.7)] text-[#e5e5e5]";
    if (tone === "error") {
        palette = "border-[#1f1f1f] bg-[rgba(20,20,20,0.7)] text-[#e5e5e5]";
    } else if (tone === "neutral") {
        palette = "border-[#1f1f1f] bg-[rgba(20,20,20,0.7)] text-[#e5e5e5]";
    }

    return (
        <div className={`rounded-[12px] border px-5 py-4 backdrop-blur-[12px] ${palette} ${className}`.trim()}>
            <div className="space-y-1">
                <p className="text-sm font-semibold">{title}</p>
                <p className="text-xs leading-5 text-[#8a8a8a]">{description}</p>
            </div>
            {actionLabel && onAction && (
                <button
                    type="button"
                    onClick={onAction}
                    className="mt-4 rounded-xl border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-xs font-semibold text-[#e5e5e5] transition hover:border-[#e5e5e5]/20"
                >
                    {actionLabel}
                </button>
            )}
        </div>
    );
}
