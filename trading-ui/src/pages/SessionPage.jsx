/**
 * SessionPage.jsx
 * ----------------
 * FXReplay-style session chart view.
 * Loaded at /session/:id
 *
 * Workflow:
 *   1. Fetch session details from GET /sessions/{id}
 *   2. Fetch candles from GET /sessions/{id}/candles?timeframe=1h
 *   3. Render full-screen chart using TradingChart
 *   4. Timeframe toolbar changes the timeframe and re-fetches
 */

import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { BASE_URL } from "../lib/api";
import toast from "react-hot-toast";
import TradingChart from "../components/charts/TradingChart";

const TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"];

export default function SessionPage() {
    const { id }     = useParams();
    const navigate   = useNavigate();

    const [session,   setSession]   = useState(null);
    const [candles,   setCandles]   = useState([]);
    const [timeframe, setTimeframe] = useState("1h");
    const [loading,   setLoading]   = useState(true);
    const [error,     setError]     = useState("");

    // ── Fetch session meta ─────────────────────────────────────────────────────
    useEffect(() => {
        axios.get(`${BASE_URL}/sessions/${id}`)
            .then(r => setSession(r.data))
            .catch(() => { setError("Session not found."); setLoading(false); });
    }, [id]);

    // ── Fetch candles ──────────────────────────────────────────────────────────
    const fetchCandles = useCallback(async (tf) => {
        if (!id) return;
        setLoading(true);
        setError("");
        try {
            const r = await axios.get(`${BASE_URL}/sessions/${id}/candles`, {
                params: { timeframe: tf },
            });
            setCandles(r.data.candles || []);
        } catch (err) {
            const msg = err?.response?.data?.detail || "Failed to load candles.";
            setError(msg);
            toast.error(msg);
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => {
        if (session) fetchCandles(timeframe);
    }, [session, timeframe, fetchCandles]);

    // ── Helpers ────────────────────────────────────────────────────────────────
    const formatDate = (iso) => iso ? new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) : "—";

    // ── Render ─────────────────────────────────────────────────────────────────
    return (
        <div className="flex flex-col h-screen bg-[#070707] text-white overflow-hidden">

            {/* ── TOP BAR ── */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-white/5 bg-[#0d0d0d] shrink-0">

                {/* Left: back + session info */}
                <div className="flex items-center gap-5">
                    <button onClick={() => navigate(-1)}
                        className="text-textSecondary hover:text-white transition-colors text-xs flex items-center gap-1.5">
                        ← Back
                    </button>
                    {session && (
                        <>
                            <div className="w-px h-4 bg-white/10" />
                            <div className="flex items-center gap-3">
                                <span className="text-sm font-bold text-white">{session.symbol}</span>
                                <span className="px-2 py-0.5 bg-white/5 border border-white/10 rounded-full text-[10px] text-textSecondary font-bold uppercase">
                                    {session.broker}
                                </span>
                                <span className="text-[11px] text-textSecondary">
                                    {formatDate(session.start_date)} → {formatDate(session.end_date)}
                                </span>
                                <span className="px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full text-[10px] text-emerald-400 font-bold">
                                    ${Number(session.balance).toLocaleString()}
                                </span>
                            </div>
                        </>
                    )}
                    {loading && (
                        <span className="text-[10px] text-emerald-400 animate-pulse">Loading data...</span>
                    )}
                </div>

                {/* Right: session name + timeframe buttons */}
                <div className="flex items-center gap-5">
                    {session && (
                        <span className="text-xs text-textSecondary font-medium">{session.session_name}</span>
                    )}
                    <div className="flex gap-1">
                        {TIMEFRAMES.map(tf => (
                            <button
                                key={tf}
                                onClick={() => setTimeframe(tf)}
                                className={`px-2.5 py-1.5 text-[10px] font-bold rounded transition-all duration-150 ${
                                    timeframe === tf
                                    ? "bg-emerald-500 text-black"
                                    : "text-textSecondary hover:text-textPrimary hover:bg-white/5"
                                }`}
                            >
                                {tf}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── CHART AREA ── */}
            <div className="flex-1 relative min-h-0">
                {error && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center z-20 gap-4">
                        <p className="text-sm text-red-400 bg-red-500/10 px-6 py-3 rounded-xl border border-red-500/20">{error}</p>
                        <button onClick={() => navigate(-1)}
                            className="text-xs text-textSecondary hover:text-white transition-colors">
                            ← Return to previous page
                        </button>
                    </div>
                )}

                {!error && !loading && candles.length === 0 && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center z-20 gap-3 text-textSecondary">
                        <svg className="w-12 h-12 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                        </svg>
                        <p className="text-sm">No candles found for the selected date range</p>
                    </div>
                )}

                {/* Chart — rendered with override candles from session candles endpoint */}
                <TradingChart
                    broker={session?.broker || ""}
                    symbol={session?.symbol || ""}
                    candles={candles.length > 0 ? candles : null}
                    showToolbar={false}  /* SessionPage owns the toolbar */
                />
            </div>
        </div>
    );
}
