import { useState } from "react";

function formatDateTime(sec) {
    const v = Number(sec);
    if (!Number.isFinite(v)) return "—";
    const d = new Date(v * 1000);
    return d.toISOString().replace("T", " ").slice(0, 16);
}

function formatDuration(entry, exit) {
    if (!entry || !exit) return "—";
    const sec = Number(exit) - Number(entry);
    if (sec <= 0) return "—";
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    if (h === 0) return `${m}m`;
    if (h < 24) return `${h}h ${m}m`;
    const days = Math.floor(h / 24);
    const remH = h % 24;
    return remH > 0 ? `${days}d ${remH}h` : `${days}d`;
}

function ScoreBadge({ score, riskLevel }) {
    if (score == null) return null;
    const pct = Math.round(score * 100);
    const colors =
        riskLevel === "Low" ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" :
            riskLevel === "Medium" ? "bg-amber-500/15   text-amber-400   border-amber-500/25" :
                "bg-red-500/15     text-red-400     border-red-500/25";
    return (
        <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-bold ${colors}`}>
            <span>{pct}%</span>
            <span className="opacity-50">·</span>
            <span>{riskLevel}</span>
        </div>
    );
}

export default function TradeHistory({ trades, selectedTrade, onSelectTrade }) {
    const hasScores = trades.some(t => t.trade_score != null);

    const cols = [
        { key: "entry_time", label: "Entry Time", align: "left" },
        { key: "exit_time", label: "Exit Time", align: "left" },
        { key: "type", label: "Dir", align: "center" },
        { key: "entry_price", label: "Entry $", align: "right" },
        { key: "exit_price", label: "Exit $", align: "right" },
        { key: "duration", label: "Duration", align: "right" },
        { key: "pnl", label: "PnL %", align: "right" },
        ...(hasScores ? [{ key: "ai_score", label: "AI Score", align: "center" }] : []),
    ];

    return (
        <div className="min-h-0 bg-panel border border-border rounded-xl shadow-soft flex flex-col transition-colors duration-300">
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-border flex-shrink-0">
                <span className="text-sm font-semibold text-textPrimary">Trade History</span>
                <div className="flex items-center gap-3">
                    <span className="text-[10px] text-textSecondary">{trades.length} trades</span>
                    {hasScores && (
                        <span className="text-[10px] text-textSecondary uppercase tracking-widest bg-panel border border-border rounded-full px-2 py-0.5">
                            AI Scored
                        </span>
                    )}
                </div>
            </div>

            {trades.length === 0 ? (
                <div className="flex flex-col items-center justify-center gap-2 py-16 text-sm text-textSecondary">
                    <svg className="w-8 h-8 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                    No trades executed.
                </div>
            ) : (
                <div className="flex-1 overflow-auto custom-scrollbar">
                    <table className="w-full text-sm">
                        <thead className="sticky top-0 z-10 bg-panel text-textSecondary text-[10px] uppercase tracking-wider shadow-sm">
                            <tr>
                                {cols.map(c => (
                                    <th key={c.key} className={`font-medium px-4 py-3 text-${c.align}`}>
                                        {c.label}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40">
                            {trades.map((t, idx) => {
                                const isWin = (t.pnl ?? 0) > 0;
                                const isSelected = selectedTrade === t;
                                return (
                                    <tr
                                        key={idx}
                                        onClick={() => onSelectTrade?.(isSelected ? null : t)}
                                        className={`cursor-pointer transition-colors duration-100
                                            ${isSelected
                                                ? "bg-textPrimary/5 border-l-2 border-textPrimary"
                                                : "hover:bg-hoverSurface"}`}
                                    >
                                        {/* Entry Time */}
                                        <td className="px-4 py-3 text-textSecondary font-mono text-xs whitespace-nowrap">
                                            {formatDateTime(t.entry_time || t.exit_time)}
                                        </td>
                                        {/* Exit Time */}
                                        <td className="px-4 py-3 text-textSecondary font-mono text-xs whitespace-nowrap">
                                            {formatDateTime(t.exit_time)}
                                        </td>
                                        {/* Direction */}
                                        <td className={`px-2 py-3 text-center font-bold text-[10px] tracking-widest uppercase
                                            ${t.type === "BUY" ? "text-emerald-400" : "text-red-400"}`}>
                                            {t.type}
                                        </td>
                                        {/* Entry $ */}
                                        <td className="px-4 py-3 text-right text-textPrimary font-mono text-xs">
                                            {t.entry_price != null ? t.entry_price.toFixed(5) : "—"}
                                        </td>
                                        {/* Exit $ */}
                                        <td className="px-4 py-3 text-right text-textPrimary font-mono text-xs">
                                            {t.exit_price != null ? t.exit_price.toFixed(5) : "—"}
                                        </td>
                                        {/* Duration */}
                                        <td className="px-4 py-3 text-right text-textSecondary font-mono text-xs">
                                            {formatDuration(t.entry_time, t.exit_time)}
                                        </td>
                                        {/* PnL */}
                                        <td className={`px-4 py-3 text-right font-mono text-xs font-semibold
                                            ${isWin ? "text-emerald-400" : "text-red-400"}`}>
                                            {isWin ? "+" : ""}{((t.pnl ?? 0) * 100).toFixed(2)}%
                                        </td>
                                        {/* AI Score */}
                                        {hasScores && (
                                            <td className="px-4 py-3 text-center">
                                                <ScoreBadge score={t.trade_score} riskLevel={t.risk_level} />
                                            </td>
                                        )}
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
