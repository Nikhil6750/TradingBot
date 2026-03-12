import { useMemo, useRef, useEffect } from "react";

/**
 * PnLHistogram — canvas-based bar chart bucketing trade PnLs.
 * Win buckets (pnl > 0): white/light  ·  Loss buckets (pnl ≤ 0): dim red
 */
export default function PnLHistogram({ trades = [] }) {
    const canvasRef = useRef(null);

    const { buckets, maxCount, minPnl, maxPnl } = useMemo(() => {
        const pnls = trades.map(t => (t.pnl ?? 0) * 100); // convert to %
        if (!pnls.length) return { buckets: [], maxCount: 0, minPnl: 0, maxPnl: 0 };

        const lo = Math.min(...pnls);
        const hi = Math.max(...pnls);
        const NUM_BUCKETS = 20;
        const range = hi - lo || 1;
        const step = range / NUM_BUCKETS;

        const buckets = Array.from({ length: NUM_BUCKETS }, (_, i) => ({
            lo: lo + i * step,
            hi: lo + (i + 1) * step,
            count: 0,
            isWin: lo + (i + 0.5) * step > 0,
        }));

        pnls.forEach(p => {
            const idx = Math.min(Math.floor((p - lo) / step), NUM_BUCKETS - 1);
            buckets[idx].count++;
        });

        const maxCount = Math.max(...buckets.map(b => b.count), 1);
        return { buckets, maxCount, minPnl: lo, maxPnl: hi };
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
            ctx.fillStyle = b.isWin ? "rgba(229,229,229,0.70)" : "rgba(239,68,68,0.55)";
            ctx.fillRect(x, y, barW - GAP, barH);
        });

        // Zero line
        const zeroX = PAD_L + ((-minPnl) / (maxPnl - minPnl || 1)) * plotW;
        ctx.strokeStyle = "rgba(255,255,255,0.15)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(zeroX, PAD_T);
        ctx.lineTo(zeroX, PAD_T + plotH);
        ctx.stroke();

        // X-axis labels: min, 0, max
        ctx.fillStyle = "rgba(161,161,161,0.8)";
        ctx.font = "9px monospace";
        ctx.textAlign = "left";
        ctx.fillText(`${minPnl.toFixed(1)}%`, PAD_L, H - 6);
        ctx.textAlign = "center";
        ctx.fillText("0%", zeroX, H - 6);
        ctx.textAlign = "right";
        ctx.fillText(`${maxPnl.toFixed(1)}%`, W - PAD_R, H - 6);

        // Y-axis label (max count)
        ctx.textAlign = "right";
        ctx.fillText(String(maxCount), PAD_L - 3, PAD_T + 10);
    }, [buckets, maxCount, minPnl, maxPnl]);

    if (!trades.length) return null;

    return (
        <div className="rounded-xl bg-card border border-card-border overflow-hidden" style={{ height: "130px" }}>
            <div className="flex items-center gap-2 px-4 pt-2.5 pb-0 flex-shrink-0">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">PnL Distribution</span>
                <span className="text-[10px] text-textSecondary opacity-50">·</span>
                <span className="text-[10px] text-textSecondary opacity-50">{trades.length} trades</span>
            </div>
            <canvas ref={canvasRef} className="w-full" style={{ height: "95px", display: "block" }} />
        </div>
    );
}
