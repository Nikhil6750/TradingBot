import { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useStrategy } from "../context/StrategyContext";
import axios from "axios";
import { BASE_URL } from "../lib/api";
import { motion } from "framer-motion";

export default function UploadData() {
    const navigate = useNavigate();
    const { config, setResults, setUploadedFile } = useStrategy();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    // Provider state
    const [brokers, setBrokers] = useState([]);
    const [selectedBroker, setSelectedBroker] = useState("");
    const [symbols, setSymbols] = useState([]);
    const [selectedSymbol, setSelectedSymbol] = useState("");
    const [timeframes, setTimeframes] = useState([]);
    const [selectedTimeframe, setSelectedTimeframe] = useState("");

    useEffect(() => {
        axios.get(`${BASE_URL}/brokers`).then(r => {
            if (r.data.brokers) {
                setBrokers(r.data.brokers);
                setSelectedBroker(r.data.brokers[0]);
            }
        }).catch(e => console.error(e));
    }, []);

    useEffect(() => {
        if (!selectedBroker) return;
        axios.get(`${BASE_URL}/symbols/${selectedBroker}`).then(r => {
            if (r.data.symbols) {
                setSymbols(r.data.symbols);
                setSelectedSymbol(r.data.symbols[0]);
            }
        }).catch(e => console.error(e));
    }, [selectedBroker]);

    useEffect(() => {
        if (!selectedSymbol) return;
        axios.get(`${BASE_URL}/timeframes`).then(r => {
            if (r.data.timeframes) {
                setTimeframes(r.data.timeframes);
                setSelectedTimeframe(r.data.timeframes[0]);
            }
        }).catch(e => console.error(e));
    }, [selectedSymbol]);

    /* ── Backtest logic (unchanged) ─────────────────────────────────────── */
    const handleUpload = async () => {
        if (!selectedSymbol || !selectedTimeframe) return;
        setError("");
        setLoading(true);
        try {
            let configObj = {
                mode: config.mode,
                stop_loss: config.globalStops.stop_loss,
                take_profit: config.globalStops.take_profit,
            };

            if (config.mode === "template") {
                configObj.strategy = config.strategyTemplate;
                configObj.parameters = config.templateParams;
            } else if (config.mode === "parameter") {
                configObj.rules = config.customRules;
                configObj.indicators = { rsi: { period: 14 }, sma50: { period: 50 }, sma_50: { period: 50 } };
            } else if (config.mode === "rules") {
                try {
                    const parsed = JSON.parse(config.jsonRules);
                    configObj.buy_rules = parsed.buy_rules || [];
                    configObj.sell_rules = parsed.sell_rules || [];
                } catch {
                    throw new Error("Invalid JSON in Rule Builder.");
                }
            }

            const payload = {
                symbol: selectedSymbol,
                timeframe: selectedTimeframe,
                config: configObj
            };

            const res = await axios.post(`${BASE_URL}/run-backtest`, payload);
            const data = res?.data || {};

            setResults({
                candles: Array.isArray(data.candles) ? data.candles : [],
                buySignals: Array.isArray(data.buy_signals) ? data.buy_signals : [],
                sellSignals: Array.isArray(data.sell_signals) ? data.sell_signals : [],
                trades: Array.isArray(data.trades) ? data.trades : [],
                metrics: data.metrics || null,
            });

            // Mock an uploaded file name to bypass strict CSV file guards in Results.jsx context
            setUploadedFile(new File([], `${selectedSymbol}_${selectedTimeframe}.csv`));
            navigate("/results");
        } catch (err) {
            setError(axios.isAxiosError(err) ? (err.response?.data?.error || err.message) : err.message);
        } finally {
            setLoading(false);
        }
    };

    const canRun = selectedSymbol && selectedTimeframe && !loading;

    /* ── UI ─────────────────────────────────────────────────────────────── */
    return (
        <div
            className="min-h-screen w-full flex items-center justify-center p-6"
            style={{ background: "radial-gradient(circle at top, #111111, #070707)" }}
        >
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16, filter: "blur(8px)" }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                className="w-full max-w-lg"
                style={{
                    background: "rgba(20,20,20,0.65)",
                    backdropFilter: "blur(18px)",
                    borderRadius: "14px",
                    border: "1px solid rgba(255,255,255,0.05)",
                    boxShadow: "0 20px 60px rgba(0,0,0,0.55), 0 0 60px rgba(255,255,255,0.02)",
                }}
            >
                {/* ── Header ──────────────────────────────────────────── */}
                <div
                    className="flex items-center justify-between px-7 py-5"
                    style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
                >
                    <div>
                        <h2 className="text-base font-medium tracking-wide text-textPrimary"
                            style={{ letterSpacing: "0.5px" }}>
                            Select Market Data
                        </h2>
                        <p className="text-xs text-textSecondary mt-0.5">
                            Seamless 10-year automated historical data
                        </p>
                    </div>
                    <Link
                        to="/setup"
                        className="text-xs text-textSecondary hover:text-textPrimary transition-colors duration-200 cursor-pointer"
                    >
                        ← Strategy
                    </Link>
                </div>

                {/* ── Body ────────────────────────────────────────────── */}
                <div className="px-7 py-7 flex flex-col gap-5">

                    {/* Dropdowns */}
                    <div className="flex flex-col gap-4">
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[11px] font-semibold tracking-wider text-textSecondary uppercase">Broker / Data Provider</label>
                            <select
                                className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-4 py-3 text-sm outline-none uppercase font-semibold text-textPrimary cursor-pointer transition-colors focus:border-white/30"
                                value={selectedBroker} onChange={e => setSelectedBroker(e.target.value)}
                                disabled={brokers.length === 0}
                            >
                                {brokers.map(b => <option key={b} value={b}>{b}</option>)}
                            </select>
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[11px] font-semibold tracking-wider text-textSecondary uppercase">Market Symbol</label>
                            <select
                                className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-4 py-3 text-sm outline-none uppercase font-semibold text-emerald-400 cursor-pointer transition-colors focus:border-white/30"
                                value={selectedSymbol} onChange={e => setSelectedSymbol(e.target.value)}
                                disabled={symbols.length === 0}
                            >
                                {symbols.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                        </div>
                        <div className="flex flex-col gap-1.5">
                            <label className="text-[11px] font-semibold tracking-wider text-textSecondary uppercase">Timeframe</label>
                            <select
                                className="w-full bg-[#0a0a0a] border border-white/10 rounded-lg px-4 py-3 text-sm outline-none uppercase font-semibold text-textPrimary cursor-pointer transition-colors focus:border-white/30"
                                value={selectedTimeframe} onChange={e => setSelectedTimeframe(e.target.value)}
                                disabled={timeframes.length === 0}
                            >
                                {timeframes.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div
                            className="rounded-xl px-4 py-3 text-sm text-red-400 text-center"
                            style={{
                                background: "rgba(239,68,68,0.08)",
                                border: "1px solid rgba(239,68,68,0.2)",
                            }}
                        >
                            {error}
                        </div>
                    )}

                    {/* Run Backtest button */}
                    <button
                        onClick={handleUpload}
                        disabled={!canRun}
                        className="btn-primary w-full py-3 text-sm tracking-wide"
                        style={
                            !canRun
                                ? { background: "rgba(255,255,255,0.06)", color: "#666", cursor: "not-allowed", borderRadius: "10px" }
                                : {}
                        }
                    >
                        {loading ? (
                            <span className="flex items-center justify-center gap-2">
                                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10"
                                        stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                                Processing…
                            </span>
                        ) : "Run Backtest"}
                    </button>
                </div>
            </motion.div>
        </div>
    );
}
