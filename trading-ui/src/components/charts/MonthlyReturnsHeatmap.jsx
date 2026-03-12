import { useRef, useEffect, useMemo } from "react";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * MonthlyReturnsHeatmap — canvas grid (year × month) coloured green/red by return.
 * trades: array of { exit_time (unix seconds), pnl (fraction) }
 */
export default function MonthlyReturnsHeatmap({ trades = [] }) {
    const canvasRef = useRef(null);

    const { grid, years, maxAbsPnl } = useMemo(() => {
        if (!trades.length) return { grid: {}, years: [], maxAbsPnl: 0 };

        const map = {};
        for (const t of trades) {
            const d = new Date((t.exit_time || t.entry_time) * 1000);
            if (isNaN(d)) continue;
            const y = d.getFullYear();
            const m = d.getMonth(); // 0-11
            const key = `${y}-${m}`;
            map[key] = (map[key] ?? 0) + (t.pnl ?? 0);
        }

        const years = [...new Set(Object.keys(map).map(k => parseInt(k.split("-")[0])))].sort();
        const vals = Object.values(map);
        const maxAbsPnl = Math.max(...vals.map(Math.abs), 0.001);
        return { grid: map, years, maxAbsPnl };
    }, [trades]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !years.length) return;
        const ctx = canvas.getContext("2d");
        const dpr = window.devicePixelRatio || 1;
        const W = canvas.offsetWidth;
        const H = canvas.offsetHeight;
        canvas.width = W * dpr;
        canvas.height = H * dpr;
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, W, H);

        const PAD_L = 38, PAD_T = 22, PAD_R = 8, PAD_B = 8;
        const cellW = (W - PAD_L - PAD_R) / 12;
        const cellH = (H - PAD_T - PAD_B) / years.length;
        const GAP = 2;

        // Column headers (months)
        ctx.fillStyle = "rgba(161,161,161,0.8)";
        ctx.font = "9px system-ui";
        ctx.textAlign = "center";
        MONTHS.forEach((m, mi) => {
            ctx.fillText(m, PAD_L + mi * cellW + cellW / 2, PAD_T - 6);
        });

        // Row headers (years)
        ctx.textAlign = "right";
        years.forEach((yr, yi) => {
            const cy = PAD_T + yi * cellH + cellH / 2 + 3;
            ctx.fillText(String(yr), PAD_L - 6, cy);
        });

        // Cells
        years.forEach((yr, yi) => {
            MONTHS.forEach((_, mi) => {
                const key = `${yr}-${mi}`;
                const val = grid[key];
                const x = PAD_L + mi * cellW + GAP / 2;
                const y = PAD_T + yi * cellH + GAP / 2;
                const w = cellW - GAP;
                const h = cellH - GAP;

                if (val == null) {
                    ctx.fillStyle = "rgba(255,255,255,0.03)";
                } else {
                    const intensity = Math.min(Math.abs(val) / maxAbsPnl, 1);
                    if (val >= 0) {
                        ctx.fillStyle = `rgba(52,211,153,${0.15 + intensity * 0.65})`;
                    } else {
                        ctx.fillStyle = `rgba(239,68,68,${0.15 + intensity * 0.65})`;
                    }
                }
                ctx.beginPath();
                ctx.roundRect(x, y, w, h, 3);
                ctx.fill();

                // Value label inside cell if big enough
                if (val != null && cellH > 16) {
                    const pct = (val * 100).toFixed(1);
                    ctx.fillStyle = "rgba(255,255,255,0.85)";
                    ctx.font = "8px monospace";
                    ctx.textAlign = "center";
                    ctx.fillText(`${val >= 0 ? "+" : ""}${pct}%`, x + w / 2, y + h / 2 + 3);
                }
            });
        });
    }, [grid, years, maxAbsPnl]);

    if (!trades.length) return null;
    const rowH = Math.max(30, Math.min(52, 260 / Math.max(years.length, 1)));
    const totalH = 32 + years.length * rowH;

    return (
        <div className="rounded-xl overflow-hidden border" style={{ background: "#111111", borderColor: "rgba(255,255,255,0.08)" }}>
            <div className="px-5 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">Monthly Returns Heatmap</span>
            </div>
            <div className="px-4 py-3">
                <canvas ref={canvasRef} className="w-full" style={{ height: `${totalH}px`, display: "block" }} />
            </div>
        </div>
    );
}
