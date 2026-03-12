import { useMemo, useRef, useEffect } from "react";

/**
 * DurationHistogram — canvas histogram of trade durations (in hours).
 * Same compact card style as PnLHistogram.
 */
function formatDurLabel(h) {
    if (h < 1) return `${Math.round(h * 60)}m`;
    if (h < 24) return `${h.toFixed(0)}h`;
    return `${(h / 24).toFixed(0)}d`;
}

export default function DurationHistogram({ trades = [] }) {
    const canvasRef = useRef(null);

    const { buckets, maxCount, minH, maxH, avgH } = useMemo(() => {
        const hours = trades
            .map(t => {
                const dur = (t.exit_time ?? 0) - (t.entry_time ?? 0);
                return dur > 0 ? dur / 3600 : null;
            })
            .filter(h => h !== null);

        if (!hours.length) return { buckets: [], maxCount: 0, minH: 0, maxH: 0, avgH: 0 };

        const lo = 0;
        const hi = Math.max(...hours);
        const NUM = 15;
        const step = (hi - lo || 1) / NUM;

        const buckets = Array.from({ length: NUM }, (_, i) => ({
            lo: lo + i * step,
            hi: lo + (i + 1) * step,
            count: 0,
        }));

        hours.forEach(h => {
            const idx = Math.min(Math.floor((h - lo) / step), NUM - 1);
            buckets[idx].count++;
        });

        const maxCount = Math.max(...buckets.map(b => b.count), 1);
        const avgH = hours.reduce((a, b) => a + b, 0) / hours.length;
        return { buckets, maxCount, minH: lo, maxH: hi, avgH };
    }, [trades]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !buckets.length) return;
        const ctx = canvas.getContext("2d");
        const dpr = window.devicePixelRatio || 1;
        const W = canvas.offsetWidth;
        const H = canvas.offsetHeight;
        canvas.width = W * dpr;
        canvas.height = H * dpr;
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, W, H);

        const PAD_L = 32, PAD_R = 8, PAD_T = 8, PAD_B = 24;
        const plotW = W - PAD_L - PAD_R;
        const plotH = H - PAD_T - PAD_B;
        const barW = plotW / buckets.length;
        const GAP = 1.5;

        buckets.forEach((b, i) => {
            const barH = (b.count / maxCount) * plotH;
            const x = PAD_L + i * barW + GAP / 2;
            const y = PAD_T + plotH - barH;
            ctx.fillStyle = "rgba(229,229,229,0.55)";
            ctx.fillRect(x, y, barW - GAP, barH);
        });

        // Labels
        ctx.fillStyle = "rgba(161,161,161,0.8)";
        ctx.font = "9px monospace";
        ctx.textAlign = "left";
        ctx.fillText(formatDurLabel(minH), PAD_L, H - 6);
        ctx.textAlign = "center";
        ctx.fillText(`avg ${formatDurLabel(avgH)}`, W / 2, H - 6);
        ctx.textAlign = "right";
        ctx.fillText(formatDurLabel(maxH), W - PAD_R, H - 6);
        ctx.textAlign = "right";
        ctx.fillText(String(maxCount), PAD_L - 3, PAD_T + 10);
    }, [buckets, maxCount, minH, maxH, avgH]);

    if (!trades.length) return null;
    const hasDuration = trades.some(t => t.entry_time && t.exit_time && t.exit_time > t.entry_time);
    if (!hasDuration) return null;

    return (
        <div className="rounded-xl bg-card border border-card-border overflow-hidden" style={{ height: "130px" }}>
            <div className="flex items-center gap-2 px-4 pt-2.5 pb-0">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">Trade Duration</span>
                <span className="text-[10px] text-textSecondary opacity-50">· hours</span>
            </div>
            <canvas ref={canvasRef} className="w-full" style={{ height: "95px", display: "block" }} />
        </div>
    );
}
