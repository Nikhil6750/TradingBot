/**
 * MetricsPanel — 5 KPI strip + Strategy Summary card
 */
export default function MetricsPanel({ metrics, trades = [] }) {
    const wr = metrics ? (metrics.win_rate * 100).toFixed(1) : null;
    const ret = metrics ? (metrics.total_return * 100).toFixed(2) : null;
    // max_drawdown is now a negative fraction from backend (e.g. -0.032)
    const dd = metrics?.max_drawdown != null ? (Math.abs(metrics.max_drawdown) * 100).toFixed(2) : null;
    const pf = metrics?.profit_factor != null ? (
        metrics.profit_factor === Infinity ? "∞" : metrics.profit_factor.toFixed(2)
    ) : (metrics ? "—" : null);
    // sharpe_ratio is null when < 5 trades
    const sr = metrics?.sharpe_ratio != null ? metrics.sharpe_ratio.toFixed(2) : (metrics ? "—" : null);

    const kpis = [
        { label: "Win Rate", value: wr != null ? `${wr}%` : "—", color: wr != null && parseFloat(wr) > 50 ? "text-emerald-400" : "text-textPrimary" },
        { label: "Profit Factor", value: pf != null ? pf : "—", color: pf != null && pf !== "—" && parseFloat(pf) > 1 ? "text-emerald-400" : "text-textPrimary" },
        {
            label: "Total Return", value: ret != null ? (parseFloat(ret) >= 0 ? `+${ret}%` : `${ret}%`) : "—",
            color: ret != null ? (parseFloat(ret) >= 0 ? "text-emerald-400" : "text-red-400") : "text-textPrimary"
        },
        {
            label: "Sharpe", value: sr != null ? sr : "—",
            color: sr != null && sr !== "—" && parseFloat(sr) > 1 ? "text-emerald-400" : "text-textPrimary",
            sub: sr === "—" ? "< 5 trades" : null
        },
        { label: "Max Drawdown", value: dd != null ? `-${dd}%` : "—", color: "text-red-400" },
    ];

    // ── Strategy Summary derived from trades ─────────────────────────────────
    const pnls = trades.map(t => t.pnl ?? 0);
    const bestPnl = pnls.length ? Math.max(...pnls) : null;
    const worstPnl = pnls.length ? Math.min(...pnls) : null;
    const avgPnl = pnls.length ? pnls.reduce((a, b) => a + b, 0) / pnls.length : null;
    const wins = pnls.filter(p => p > 0);
    const losses = pnls.filter(p => p <= 0);
    const avgWin = wins.length ? wins.reduce((a, b) => a + b, 0) / wins.length : 0;
    const avgLoss = losses.length ? Math.abs(losses.reduce((a, b) => a + b, 0) / losses.length) : 0;
    const winFrac = pnls.length ? wins.length / pnls.length : 0;
    const expectancy = pnls.length ? (winFrac * avgWin - (1 - winFrac) * avgLoss) * 100 : null;

    const fmt = (v) => v != null ? `${v >= 0 ? "+" : ""}${(v * 100).toFixed(2)}%` : "—";

    const summary = [
        { label: "Total Trades", value: trades.length || "—", color: "text-textPrimary" },
        { label: "Best Trade", value: bestPnl != null ? fmt(bestPnl) : "—", color: "text-emerald-400" },
        { label: "Worst Trade", value: worstPnl != null ? fmt(worstPnl) : "—", color: "text-red-400" },
        { label: "Avg Trade", value: avgPnl != null ? fmt(avgPnl) : "—", color: avgPnl != null && avgPnl >= 0 ? "text-emerald-400" : "text-red-400" },
        {
            label: "Expectancy", value: expectancy != null ? `${expectancy >= 0 ? "+" : ""}${expectancy.toFixed(3)}%` : "—",
            color: expectancy != null && expectancy >= 0 ? "text-emerald-400" : "text-red-400"
        },
    ];

    return (
        <div className="flex flex-col gap-3">
            {/* ── 5 KPI strip ──────────────────────────────────────────── */}
            <div className="grid grid-cols-5 rounded-xl overflow-hidden bg-card shadow-card border border-card-border">
                {kpis.map(({ label, value, color, sub }, i) => (
                    <div key={label} className={`flex flex-col gap-1 px-5 py-4 ${i > 0 ? "border-l border-card-border" : ""}`}>
                        <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">{label}</span>
                        <span className={`text-2xl font-bold tracking-tight ${color}`}>{value}</span>
                        {sub && <span className="text-[9px] text-textSecondary opacity-50">{sub}</span>}
                    </div>
                ))}
            </div>

            {/* ── Strategy Summary card ────────────────────────────────── */}
            <div className="grid grid-cols-5 rounded-xl overflow-hidden bg-card border border-card-border">
                {summary.map(({ label, value, color }, i) => (
                    <div key={label} className={`flex flex-col gap-1 px-5 py-3 ${i > 0 ? "border-l border-card-border" : ""}`}>
                        <span className="text-[10px] font-medium uppercase tracking-widest text-textSecondary">{label}</span>
                        <span className={`text-base font-bold tracking-tight tabular-nums ${color}`}>{value}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}
