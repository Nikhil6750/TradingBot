import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function StatCard({ label, value, sub, accent }) {
    return (
        <div className="rounded-xl px-5 py-4 flex flex-col gap-1 border" style={{ background: "#111111", borderColor: "rgba(255,255,255,0.08)" }}>
            <span className="text-[10px] uppercase tracking-widest text-textSecondary font-semibold">{label}</span>
            <span className={`text-2xl font-bold tracking-tight ${accent || "text-textPrimary"}`}>{value}</span>
            {sub && <span className="text-[10px] text-textSecondary">{sub}</span>}
        </div>
    );
}

function SessionRow({ s, onClick }) {
    const ret = s.total_return != null ? (s.total_return * 100).toFixed(2) : null;
    const wr = s.win_rate != null ? (s.win_rate * 100).toFixed(0) : null;
    const sr = s.sharpe_ratio != null ? s.sharpe_ratio.toFixed(2) : "—";
    const isPos = ret != null && parseFloat(ret) >= 0;
    const date = s.created_at ? new Date(s.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : "—";

    return (
        <tr
            onClick={onClick}
            className="cursor-pointer border-b transition-colors duration-100 hover:bg-white/[0.03]"
            style={{ borderColor: "rgba(255,255,255,0.05)" }}
        >
            <td className="px-4 py-3 text-xs text-textSecondary tabular-nums">{s.id}</td>
            <td className="px-4 py-3 text-xs font-semibold text-textPrimary">{s.symbol}</td>
            <td className={`px-4 py-3 text-xs font-semibold tabular-nums ${isPos ? "text-emerald-400" : "text-red-400"}`}>
                {ret != null ? `${isPos ? "+" : ""}${ret}%` : "—"}
            </td>
            <td className="px-4 py-3 text-xs text-textSecondary tabular-nums">{wr != null ? `${wr}%` : "—"}</td>
            <td className="px-4 py-3 text-xs text-textSecondary tabular-nums">{sr}</td>
            <td className="px-4 py-3 text-xs text-textSecondary tabular-nums">{s.total_trades ?? "—"}</td>
            <td className="px-4 py-3 text-xs text-textSecondary">{date}</td>
        </tr>
    );
}

export default function Dashboard() {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        axios.get(`${API}/backtests?limit=20`).then(r => setSessions(r.data)).catch(() => { }).finally(() => setLoading(false));
    }, []);

    // Aggregate stats
    const count = sessions.length;
    const bestSR = sessions.length ? Math.max(...sessions.map(s => s.sharpe_ratio ?? -Infinity)).toFixed(2) : "—";
    const avgRet = sessions.length
        ? ((sessions.reduce((a, s) => a + (s.total_return ?? 0), 0) / sessions.length) * 100).toFixed(2)
        : "—";
    const wins = sessions.filter(s => (s.total_return ?? 0) > 0).length;

    return (
        <div className="min-h-screen flex flex-col gap-6 px-8 py-8" style={{ background: "#050505", color: "#E5E5E5" }}>
            <div>
                <h1 className="text-xl font-bold tracking-tight">Dashboard</h1>
                <p className="text-xs text-textSecondary mt-1">Overview of your strategy research sessions</p>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-4 gap-4">
                <StatCard label="Backtests Run" value={count} sub="all time" />
                <StatCard label="Best Sharpe" value={bestSR} sub="highest Sharpe across sessions" accent={parseFloat(bestSR) > 1 ? "text-emerald-400" : "text-textPrimary"} />
                <StatCard label="Avg Return" value={avgRet !== "—" ? `${parseFloat(avgRet) >= 0 ? "+" : ""}${avgRet}%` : "—"}
                    accent={avgRet !== "—" && parseFloat(avgRet) >= 0 ? "text-emerald-400" : "text-red-400"} />
                <StatCard label="Profitable" value={sessions.length ? `${wins}/${count}` : "—"} sub="sessions with positive return" />
            </div>

            {/* Recent sessions table */}
            <div className="rounded-xl overflow-hidden border" style={{ background: "#111111", borderColor: "rgba(255,255,255,0.08)" }}>
                <div className="px-5 py-3 border-b flex items-center justify-between" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                    <span className="text-xs font-semibold uppercase tracking-widest text-textSecondary">Recent Backtests</span>
                    <button
                        onClick={() => navigate("/backtests")}
                        className="text-[10px] text-textSecondary hover:text-textPrimary transition-colors cursor-pointer"
                    >
                        View all →
                    </button>
                </div>

                {loading ? (
                    <div className="py-12 text-center text-xs text-textSecondary">Loading…</div>
                ) : sessions.length === 0 ? (
                    <div className="py-12 text-center text-xs text-textSecondary">
                        No backtests yet. Run a backtest to see results here.
                    </div>
                ) : (
                    <table className="w-full">
                        <thead className="text-[10px] uppercase tracking-wider text-textSecondary border-b" style={{ borderColor: "rgba(255,255,255,0.06)" }}>
                            <tr>
                                {["#", "Symbol", "Return", "Win Rate", "Sharpe", "Trades", "Date"].map(h => (
                                    <th key={h} className="px-4 py-3 text-left font-medium">{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {sessions.map(s => (
                                <SessionRow key={s.id} s={s} onClick={() => navigate(`/backtests/${s.id}`)} />
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
