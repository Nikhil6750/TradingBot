/**
 * RegimePerformancePanel — clean data table layout.
 * Regime | Trades | Win Rate | Avg Return | Spark Bar
 */

const REGIME_LABELS = {
    "Trending": { dot: "bg-textPrimary" },
    "Sideways": { dot: "bg-textSecondary" },
    "High Volatility": { dot: "bg-red-400" },
    "Low Volatility": { dot: "bg-textSecondary" },
};

export default function RegimePerformancePanel({ data }) {
    if (!data?.breakdown || Object.keys(data.breakdown).length === 0) return null;

    const { breakdown, insight } = data;

    const rows = Object.entries(breakdown)
        .map(([name, d]) => ({ name, ...d }))
        .sort((a, b) => b.avg_return - a.avg_return);

    const maxAbsRet = Math.max(...rows.map(r => Math.abs(r.avg_return * 100)), 0.01);

    return (
        <div className="rounded-xl bg-card border border-card-border overflow-hidden">
            {/* Header */}
            <div className="px-5 py-3 border-b border-card-border">
                <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">
                    Performance by Market Regime
                </span>
            </div>

            {/* Table */}
            <table className="w-full text-xs">
                <thead>
                    <tr className="text-[10px] uppercase tracking-wider text-textSecondary border-b border-card-border">
                        <th className="px-5 py-2.5 text-left font-medium">Regime</th>
                        <th className="px-4 py-2.5 text-right font-medium">Trades</th>
                        <th className="px-4 py-2.5 text-right font-medium">Win Rate</th>
                        <th className="px-4 py-2.5 text-right font-medium">Avg Return</th>
                        <th className="px-5 py-2.5 text-left font-medium w-32">Performance</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-card-border/40">
                    {rows.map((r, i) => {
                        const ret = r.avg_return * 100;
                        const wr = Math.round((r.win_rate ?? 0) * 100);
                        const isPos = ret >= 0;
                        const barPct = Math.min(Math.abs(ret) / maxAbsRet * 100, 100);
                        const cfg = REGIME_LABELS[r.name] ?? { dot: "bg-textSecondary" };

                        return (
                            <tr key={r.name} className={i === 0 ? "bg-white/[0.02]" : ""}>
                                {/* Regime name */}
                                <td className="px-5 py-3">
                                    <div className="flex items-center gap-2">
                                        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${cfg.dot}`} />
                                        <span className="text-textPrimary font-medium">{r.name}</span>
                                    </div>
                                </td>
                                {/* Trades */}
                                <td className="px-4 py-3 text-right text-textSecondary tabular-nums">
                                    {r.trades ?? 0}
                                </td>
                                {/* Win Rate */}
                                <td className={`px-4 py-3 text-right tabular-nums font-semibold ${wr >= 50 ? "text-emerald-400" : "text-red-400"}`}>
                                    {wr}%
                                </td>
                                {/* Avg Return */}
                                <td className={`px-4 py-3 text-right tabular-nums font-semibold ${isPos ? "text-emerald-400" : "text-red-400"}`}>
                                    {isPos ? "+" : ""}{ret.toFixed(2)}%
                                </td>
                                {/* Bar spark */}
                                <td className="px-5 py-3">
                                    <div className="h-1.5 w-full rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                                        <div
                                            className={`h-full rounded-full transition-all duration-700 ${isPos ? "bg-emerald-400" : "bg-red-400"}`}
                                            style={{ width: `${barPct}%`, opacity: 0.7 }}
                                        />
                                    </div>
                                </td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>

            {/* Insight */}
            {insight && (
                <div className="px-5 pb-4 pt-3 border-t border-card-border">
                    <p className="text-[11px] leading-relaxed text-textSecondary">
                        💡 {insight}
                    </p>
                </div>
            )}
        </div>
    );
}
