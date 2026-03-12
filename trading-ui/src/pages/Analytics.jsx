import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import MonthlyReturnsHeatmap from "../components/charts/MonthlyReturnsHeatmap";
import PnLHistogram from "../components/charts/PnLHistogram";
import WinLossPie from "../components/charts/WinLossPie";
import DurationHistogram from "../components/charts/DurationHistogram";
import EquityChart from "../components/charts/EquityChart";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function Analytics() {
    const [sessions, setSessions] = useState([]);
    const [allTrades, setAllTrades] = useState([]);
    const [loadingTrades, setLoadingTrades] = useState(false);
    const navigate = useNavigate();

    // Load session list
    useEffect(() => {
        axios.get(`${API}/backtests?limit=200`).then(r => setSessions(r.data)).catch(() => { });
    }, []);

    // When sessions load, fetch trades for the most recent 10
    useEffect(() => {
        if (!sessions.length) return;
        setLoadingTrades(true);
        const recent = sessions.slice(0, 10);
        Promise.allSettled(recent.map(s => axios.get(`${API}/backtests/${s.id}`)))
            .then(results => {
                const trades = results
                    .filter(r => r.status === "fulfilled")
                    .flatMap(r => r.value.data.trades || []);
                setAllTrades(trades);
            })
            .finally(() => setLoadingTrades(false));
    }, [sessions]);

    return (
        <div className="min-h-screen flex flex-col gap-6 px-8 py-8" style={{ background: "#050505", color: "#E5E5E5" }}>
            <div>
                <h1 className="text-xl font-bold tracking-tight">Analytics</h1>
                <p className="text-xs text-textSecondary mt-1">
                    Aggregate analysis across {sessions.length} backtest sessions · {allTrades.length} trades
                </p>
            </div>

            {sessions.length === 0 ? (
                <div className="flex flex-col items-center gap-3 py-24 text-center">
                    <span className="text-textSecondary text-sm">No backtest data available yet.</span>
                    <button
                        onClick={() => navigate("/setup")}
                        className="px-5 py-2.5 rounded-lg text-xs font-semibold cursor-pointer"
                        style={{ background: "#E5E5E5", color: "#050505" }}
                    >
                        Run Your First Backtest
                    </button>
                </div>
            ) : (
                <div className="flex flex-col gap-5">
                    {/* Monthly heatmap */}
                    {loadingTrades ? (
                        <div className="rounded-xl py-12 text-center text-xs text-textSecondary border" style={{ background: "#111111", borderColor: "rgba(255,255,255,0.08)" }}>
                            Loading trade data…
                        </div>
                    ) : (
                        <MonthlyReturnsHeatmap trades={allTrades} />
                    )}

                    {/* Equity curve across all trades */}
                    {allTrades.length > 0 && (
                        <div className="rounded-xl border overflow-hidden" style={{ background: "#111111", borderColor: "rgba(255,255,255,0.08)", height: "220px" }}>
                            <div className="px-5 py-3 border-b flex items-center justify-between" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                                <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">Aggregate Equity Curve</span>
                                <span className="text-[10px] text-textSecondary opacity-50">red = drawdown</span>
                            </div>
                            <div style={{ height: "170px" }}>
                                <EquityChart trades={allTrades} />
                            </div>
                        </div>
                    )}

                    {/* 3-col distribution row */}
                    {allTrades.length > 0 && (
                        <div className="grid grid-cols-3 gap-4">
                            <PnLHistogram trades={allTrades} />
                            <WinLossPie trades={allTrades} />
                            <DurationHistogram trades={allTrades} />
                        </div>
                    )}

                    {/* Session performance table */}
                    <div className="rounded-xl border overflow-hidden" style={{ background: "#111111", borderColor: "rgba(255,255,255,0.08)" }}>
                        <div className="px-5 py-3 border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                            <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">Session Performance Comparison</span>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-xs">
                                <thead className="text-[10px] uppercase tracking-wider text-textSecondary border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                                    <tr>
                                        {["Symbol", "Return", "Sharpe", "Win Rate", "Trades", "Drawdown", "Date"].map(h => (
                                            <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {sessions.map(s => {
                                        const ret = s.total_return != null ? ((s.total_return * 100).toFixed(2)) : null;
                                        const isPos = ret != null && parseFloat(ret) >= 0;
                                        const date = s.created_at ? new Date(s.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : "—";
                                        return (
                                            <tr key={s.id} onClick={() => navigate(`/results?session_id=${s.id}`)} className="cursor-pointer hover:bg-white/[0.02] transition-colors">
                                                <td className="px-4 py-2.5 font-semibold text-textPrimary">{s.symbol}</td>
                                                <td className={`px-4 py-2.5 font-semibold tabular-nums ${isPos ? "text-emerald-400" : "text-red-400"}`}>
                                                    {ret != null ? `${isPos ? "+" : ""}${ret}%` : "—"}
                                                </td>
                                                <td className={`px-4 py-2.5 tabular-nums ${(s.sharpe_ratio ?? 0) > 1 ? "text-emerald-400" : "text-textSecondary"}`}>
                                                    {s.sharpe_ratio?.toFixed(2) ?? "—"}
                                                </td>
                                                <td className="px-4 py-2.5 tabular-nums text-textSecondary">
                                                    {s.win_rate != null ? `${(s.win_rate * 100).toFixed(0)}%` : "—"}
                                                </td>
                                                <td className="px-4 py-2.5 tabular-nums text-textSecondary">{s.total_trades ?? "—"}</td>
                                                <td className="px-4 py-2.5 tabular-nums text-red-400">
                                                    {s.max_drawdown != null ? `${(Math.abs(s.max_drawdown) * 100).toFixed(2)}%` : "—"}
                                                </td>
                                                <td className="px-4 py-2.5 text-textSecondary">{date}</td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
