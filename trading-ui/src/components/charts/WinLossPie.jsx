import { useMemo, useRef, useEffect } from "react";

/**
 * WinLossPie — canvas donut chart showing win vs loss split.
 * White arc = wins · Red arc = losses · Centre shows win% + counts.
 */
export default function WinLossPie({ trades = [] }) {
    const canvasRef = useRef(null);

    const { wins, losses, winPct } = useMemo(() => {
        const w = trades.filter(t => (t.pnl ?? 0) > 0).length;
        const l = trades.length - w;
        return { wins: w, losses: l, winPct: trades.length ? (w / trades.length) * 100 : 0 };
    }, [trades]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || !trades.length) return;
        const ctx = canvas.getContext("2d");
        const dpr = window.devicePixelRatio || 1;
        const SIZE = canvas.offsetWidth;
        canvas.width = SIZE * dpr;
        canvas.height = SIZE * dpr;
        ctx.scale(dpr, dpr);
        ctx.clearRect(0, 0, SIZE, SIZE);

        const cx = SIZE / 2;
        const cy = SIZE / 2;
        const R = SIZE * 0.38;
        const r = SIZE * 0.22;
        const gapRad = 0.025;
        const startRad = -Math.PI / 2;

        const total = wins + losses;
        const winAng = total ? (wins / total) * (2 * Math.PI - 2 * gapRad) : 0;
        const lossAng = 2 * Math.PI - 2 * gapRad - winAng;

        // Win arc (white)
        const winEnd = startRad + winAng;
        ctx.beginPath();
        ctx.arc(cx, cy, R, startRad + gapRad, winEnd, false);
        ctx.arc(cx, cy, r, winEnd, startRad + gapRad, true);
        ctx.closePath();
        ctx.fillStyle = "rgba(229,229,229,0.85)";
        ctx.fill();

        // Loss arc (red)
        const lossStart = winEnd + gapRad;
        ctx.beginPath();
        ctx.arc(cx, cy, R, lossStart, lossStart + lossAng, false);
        ctx.arc(cx, cy, r, lossStart + lossAng, lossStart, true);
        ctx.closePath();
        ctx.fillStyle = "rgba(239,68,68,0.70)";
        ctx.fill();

        // Centre text — win%
        ctx.fillStyle = "#E5E5E5";
        ctx.font = `bold ${Math.round(SIZE * 0.18)}px system-ui`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(`${Math.round(winPct)}%`, cx, cy - SIZE * 0.04);

        ctx.fillStyle = "rgba(161,161,161,0.8)";
        ctx.font = `${Math.round(SIZE * 0.08)}px system-ui`;
        ctx.fillText("win rate", cx, cy + SIZE * 0.12);
    }, [trades, wins, losses, winPct]);

    if (!trades.length) return null;

    return (
        <div className="rounded-xl bg-card border border-card-border p-3 flex flex-col gap-2" style={{ height: "130px" }}>
            <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">Win / Loss</span>
            <div className="flex items-center gap-3 flex-1 min-h-0">
                <canvas ref={canvasRef} style={{ width: "80px", height: "80px", flexShrink: 0 }} />
                <div className="flex flex-col gap-1.5">
                    <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-sm" style={{ background: "rgba(229,229,229,0.85)" }} />
                        <span className="text-[11px] text-textPrimary font-semibold">{wins}</span>
                        <span className="text-[10px] text-textSecondary">wins</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-sm" style={{ background: "rgba(239,68,68,0.70)" }} />
                        <span className="text-[11px] text-textPrimary font-semibold">{losses}</span>
                        <span className="text-[10px] text-textSecondary">losses</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
