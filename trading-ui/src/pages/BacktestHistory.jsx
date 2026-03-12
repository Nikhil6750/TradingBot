import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function pct(v, digits = 2) {
    if (v == null) return "—";
    const p = (v * 100).toFixed(digits);
    return `${parseFloat(p) >= 0 ? "+" : ""}${p}%`;
}
function fmt2(v) { return v?.toFixed(2) ?? "—"; }

export default function BacktestHistory() {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [sortKey, setSortKey] = useState("id");
    const [sortDir, setSortDir] = useState(-1);  // -1 = desc
    const navigate = useNavigate();

    useEffect(() => {
        axios.get(`${API}/backtests?limit=200`).then(r => setSessions(r.data)).catch(() => { }).finally(() => setLoading(false));
    }, []);

    const COLS = [
        { key: "id", label: "#" },
        { key: "symbol", label: "Symbol" },
        { key: "total_return", label: "Return" },
        { key: "win_rate", label: "Win Rate" },
        { key: "sharpe_ratio", label: "Sharpe" },
        { key: "max_drawdown", label: "Drawdown" },
        { key: "total_trades", label: "Trades" },
        { key: "created_at", label: "Date" },
    ];

    const sorted = [...sessions].sort((a, b) => {
        const av = a[sortKey] ?? (typeof a[sortKey] === "number" ? -Infinity : "");
        const bv = b[sortKey] ?? (typeof b[sortKey] === "number" ? -Infinity : "");
        return av < bv ? sortDir : av > bv ? -sortDir : 0;
    });

    const toggle = (key) => {
        if (sortKey === key) setSortDir(d => -d);
        else { setSortKey(key); setSortDir(-1); }
    };

    return (
        <div className="min-h-screen flex flex-col gap-5 px-8 py-8" style={{ background: "#050505", color: "#E5E5E5" }}>
            <div>
                <h1 className="text-xl font-bold tracking-tight">Backtest History</h1>
                <p className="text-xs text-textSecondary mt-1">{sessions.length} sessions recorded</p>
            </div>

            <div className="rounded-xl overflow-hidden border" style={{ background: "#111111", borderColor: "rgba(255,255,255,0.08)" }}>
                {loading ? (
                    <div className="py-16 text-center text-xs text-textSecondary">Loading…</div>
                ) : sessions.length === 0 ? (
                    <div className="py-16 text-center text-xs text-textSecondary">No backtest sessions saved yet.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                            <thead className="text-[10px] uppercase tracking-wider text-textSecondary border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                                <tr>
                                    {COLS.map(c => (
                                        <th
                                            key={c.key}
                                            className="px-4 py-3 text-left font-medium cursor-pointer select-none hover:text-textPrimary transition-colors"
                                            onClick={() => toggle(c.key)}
                                        >
                                            {c.label}
                                            {sortKey === c.key && <span className="ml-1 opacity-60">{sortDir === -1 ? "↓" : "↑"}</span>}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {sorted.map(s => {
                                    const isPos = (s.total_return ?? 0) >= 0;
                                    const date = s.created_at ? new Date(s.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "2-digit" }) : "—";
                                    return (
                                        <tr
                                            key={s.id}
                                            onClick={() => navigate(`/results?session_id=${s.id}`)}
                                            className="cursor-pointer transition-colors duration-100 hover:bg-white/[0.03]"
                                        >
                                            <td className="px-4 py-3 text-textSecondary tabular-nums">{s.id}</td>
                                            <td className="px-4 py-3 font-semibold text-textPrimary">{s.symbol}</td>
                                            <td className={`px-4 py-3 font-semibold tabular-nums ${isPos ? "text-emerald-400" : "text-red-400"}`}>
                                                {pct(s.total_return)}
                                            </td>
                                            <td className={`px-4 py-3 tabular-nums ${(s.win_rate ?? 0) > 0.5 ? "text-emerald-400" : "text-textSecondary"}`}>
                                                {pct(s.win_rate, 1)}
                                            </td>
                                            <td className={`px-4 py-3 tabular-nums font-semibold ${(s.sharpe_ratio ?? 0) > 1 ? "text-emerald-400" : "text-textSecondary"}`}>
                                                {fmt2(s.sharpe_ratio)}
                                            </td>
                                            <td className="px-4 py-3 tabular-nums text-red-400">
                                                {s.max_drawdown != null ? `${(Math.abs(s.max_drawdown) * 100).toFixed(2)}%` : "—"}
                                            </td>
                                            <td className="px-4 py-3 tabular-nums text-textSecondary">{s.total_trades ?? "—"}</td>
                                            <td className="px-4 py-3 text-textSecondary">{date}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
