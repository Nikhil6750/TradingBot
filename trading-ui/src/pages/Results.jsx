import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useStrategy } from "../context/StrategyContext";
import { useTheme } from "../context/ThemeContext";
import ChartView from "../components/charts/ChartView";
import MetricsPanel from "../components/trading/MetricsPanel";
import TradeHistory from "../components/trading/TradeHistory";
import TradeDetailPanel from "../components/trading/TradeDetailPanel";
import MarketRegimePanel from "../components/trading/MarketRegimePanel";
import RegimePerformancePanel from "../components/trading/RegimePerformancePanel";
import EquityChart from "../components/charts/EquityChart";
import PageTransition from "../components/ui/PageTransition";
import OptimizePanel from "../components/strategy/OptimizePanel";
import PnLHistogram from "../components/charts/PnLHistogram";
import WinLossPie from "../components/charts/WinLossPie";
import DurationHistogram from "../components/charts/DurationHistogram";
import { Lightbulb, ChevronDown } from "lucide-react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const TABS = ["Overview", "Trades", "Regime Analysis", "Optimize"];

// ── Tab button ────────────────────────────────────────────────────────────────
function TabButton({ label, active, onClick }) {
    return (
        <button
            onClick={onClick}
            className={`relative px-5 py-3 text-xs font-semibold tracking-wide transition-colors duration-150 cursor-pointer
                ${active ? "text-textPrimary" : "text-textSecondary hover:text-textPrimary"}`}
        >
            {label}
            {active && <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-textPrimary rounded-full" />}
        </button>
    );
}

// ── Strategy Insights panel ───────────────────────────────────────────────────
function InsightsPanel({ insights, loading }) {
    const [open, setOpen] = useState(true);
    if (loading) {
        return (
            <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-card border border-card-border text-textSecondary text-xs">
                <div className="w-1.5 h-1.5 rounded-full bg-textSecondary animate-pulse" />
                Generating strategy intelligence…
            </div>
        );
    }
    if (!insights?.length) return null;

    return (
        <div className="rounded-xl bg-card border border-card-border overflow-hidden">
            <button
                onClick={() => setOpen(o => !o)}
                className="w-full flex items-center justify-between px-5 py-3 cursor-pointer hover:bg-hoverSurface transition-colors"
            >
                <div className="flex items-center gap-2">
                    <Lightbulb size={14} className="text-textSecondary" />
                    <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">Strategy Intelligence</span>
                    <span className="text-[10px] text-textSecondary bg-card border border-card-border rounded-full px-1.5 py-px">{insights.length}</span>
                </div>
                <ChevronDown size={14} className={`text-textSecondary transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
            </button>
            {open && (
                <ul className="px-5 pb-4 flex flex-col gap-2.5">
                    {insights.map((ins, i) => (
                        <li key={i} className="flex gap-2.5 text-xs text-textSecondary leading-relaxed">
                            <span className="text-textSecondary opacity-30 font-mono mt-px flex-shrink-0">{String(i + 1).padStart(2, "0")}</span>
                            <span>{ins}</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

// ── Overview tab ──────────────────────────────────────────────────────────────
function OverviewTab({ results, insights, insightsLoading }) {
    const hasCandles = results.candles?.length > 0;
    const [chartView, setChartView] = useState(hasCandles ? "price" : "equity"); // "price" | "equity"

    return (
        <div className="flex flex-col gap-4 h-full min-h-0 overflow-y-auto custom-scrollbar pb-4">
            {/* Metrics + Summary */}
            <MetricsPanel metrics={results.metrics} trades={results.trades} />

            {/* Chart toggle + main chart slot */}
            <div className="flex-shrink-0 rounded-xl bg-card shadow-card overflow-hidden" style={{ height: "380px" }}>
                {/* Toggle header */}
                <div className="flex items-center gap-3 px-3 py-2 flex-shrink-0" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                    {[
                        { id: "price", label: "Price Action" },
                        { id: "equity", label: "Equity Curve" },
                    ].map(opt => (
                        <button
                            key={opt.id}
                            onClick={() => setChartView(opt.id)}
                            className="flex items-center gap-1.5 px-3 py-1 rounded-md text-[10px] font-semibold uppercase tracking-wider cursor-pointer transition-colors duration-100"
                            style={{
                                background: chartView === opt.id ? "rgba(255,255,255,0.10)" : "transparent",
                                color: chartView === opt.id ? "#E5E5E5" : "#A1A1A1",
                            }}
                        >
                            <span className={`w-1 h-1 rounded-full ${opt.id === "price" ? "bg-emerald-400" : "bg-textSecondary opacity-60"}`} />
                            {opt.label}
                        </button>
                    ))}
                    {chartView === "equity" && (
                        <span className="ml-auto text-[10px] text-textSecondary opacity-40">red = drawdown</span>
                    )}
                </div>

                {/* Chart canvas */}
                <div className="flex-1 overflow-hidden" style={{ height: "340px", background: "#0f0f0f", borderRadius: "0 0 10px 10px" }}>
                    {chartView === "price" && results.candles?.length > 0
                        ? <ChartView candles={results.candles} trades={results.trades} indicators={results.indicators} />
                        : chartView === "price"
                            ? <div className="flex items-center justify-center h-full text-xs text-textSecondary px-10 text-center">Price Action unavailable for historical sessions.</div>
                            : <EquityChart trades={results.trades} />
                    }
                </div>
            </div>

            {/* 3-col visual row */}
            <div className="grid grid-cols-3 gap-3">
                <PnLHistogram trades={results.trades} />
                <WinLossPie trades={results.trades} />
                <DurationHistogram trades={results.trades} />
            </div>

            {/* Strategy insights */}
            <InsightsPanel insights={insights} loading={insightsLoading} />
        </div>
    );
}

// ── Trades tab ────────────────────────────────────────────────────────────────
function TradesTab({ trades, candles }) {
    const [selected, setSelected] = useState(null);

    return (
        <div className="flex flex-col gap-4 h-full min-h-0 overflow-y-auto custom-scrollbar pb-4">
            <div className="flex-1 min-h-0">
                <TradeHistory
                    trades={trades}
                    selectedTrade={selected}
                    onSelectTrade={setSelected}
                />
            </div>
            {selected && (
                <TradeDetailPanel
                    trade={selected}
                    candles={candles}
                    onClose={() => setSelected(null)}
                />
            )}
        </div>
    );
}

// ── Regime Analysis tab ───────────────────────────────────────────────────────
function RegimeTab({ regimeData, regimePerfData, regimeLoading }) {
    if (regimeLoading) {
        return (
            <div className="flex items-center justify-center gap-3 text-textSecondary text-sm h-40">
                <div className="w-2 h-2 rounded-full bg-textSecondary animate-pulse" />
                Detecting market regime…
            </div>
        );
    }
    if (!regimeData && !regimePerfData) {
        return (
            <div className="flex items-center justify-center text-textSecondary text-sm h-40">
                No regime data available. Run a backtest first.
            </div>
        );
    }
    return (
        <div className="flex flex-col gap-4 overflow-y-auto custom-scrollbar pb-4">
            {regimeData && <MarketRegimePanel regimeData={regimeData} />}
            {regimePerfData && <RegimePerformancePanel data={regimePerfData} />}
        </div>
    );
}

// ── Main ──────────────────────────────────────────────────────────────────────
export default function Results() {
    const { results, uploadedFile, setResults } = useStrategy();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const sessionId = searchParams.get("session_id");

    const [activeTab, setActiveTab] = useState("Overview");
    const [regimeData, setRegimeData] = useState(null);
    const [regimeLoading, setRegimeLoading] = useState(false);
    const [regimePerfData, setRegimePerfData] = useState(null);
    const [insights, setInsights] = useState([]);
    const [insightsLoading, setInsightsLoading] = useState(false);
    const [fetchingSession, setFetchingSession] = useState(!!sessionId);

    // Fetch session data dynamically
    useEffect(() => {
        if (!sessionId) return;
        setFetchingSession(true);
        axios.get(`${API_BASE}/backtests/${sessionId}`)
            .then(({ data }) => {
                setResults({
                    candles: data.candles || [],
                    buySignals: data.buy_signals || [],
                    sellSignals: data.sell_signals || [],
                    trades: data.trades || [],
                    metrics: data.metrics || null,
                });
            })
            .catch(() => { })
            .finally(() => setFetchingSession(false));
    }, [sessionId, setResults]);

    // Guard: redirect if no results
    useEffect(() => {
        if (!fetchingSession && !sessionId && (!results || !results.candles || results.candles.length === 0)) {
            navigate("/setup");
        }
    }, [results, navigate, fetchingSession, sessionId]);

    // Set chart view to equity if historical session (no candles)
    useEffect(() => {
        if (sessionId && (!results?.candles || results.candles.length === 0)) {
            setActiveTab("Overview");
        }
    }, [sessionId, results?.candles]);

    // Regime detect
    useEffect(() => {
        if (!uploadedFile || !results?.candles?.length) return;
        setRegimeLoading(true);
        const parts = uploadedFile.name.replace(".csv", "").split("_");
        const payload = { symbol: parts[0] || "EURUSD", timeframe: parts[1] || "1H" };
        axios.post(`${API_BASE}/detect_regime`, payload)
            .then(({ data }) => setRegimeData(data))
            .catch(() => { })
            .finally(() => setRegimeLoading(false));
    }, [results, uploadedFile]);

    // Score trades
    useEffect(() => {
        if (!results?.candles?.length || !results?.trades?.length) return;
        if (results.trades[0]?.trade_score != null) return;
        axios.post(`${API_BASE}/score_trades`, { candles: results.candles, trades: results.trades })
            .then(({ data }) => {
                if (data?.scored_trades?.length)
                    setResults(prev => ({ ...prev, trades: data.scored_trades }));
            }).catch(() => { });
    }, [results?.candles, results?.trades, setResults]);

    // Regime performance
    useEffect(() => {
        if (!results?.candles?.length || !results?.trades?.length) return;
        axios.post(`${API_BASE}/regime_performance`, { candles: results.candles, trades: results.trades })
            .then(({ data }) => setRegimePerfData(data))
            .catch(() => { });
    }, [results?.candles, results?.trades]);

    // Strategy insights
    useEffect(() => {
        if (!results?.candles?.length || !results?.trades?.length) return;
        setInsightsLoading(true);
        axios.post(`${API_BASE}/strategy_insights`, { candles: results.candles, trades: results.trades })
            .then(({ data }) => setInsights(data?.insights ?? []))
            .catch(() => { })
            .finally(() => setInsightsLoading(false));
    }, [results?.candles, results?.trades]);

    if (fetchingSession) {
        return (
            <div className="min-h-screen flex items-center justify-center" style={{ background: "#050505", color: "#E5E5E5" }}>
                <div className="flex flex-col items-center gap-3">
                    <div className="w-4 h-4 rounded-full border-2 border-t-emerald-400 border-r-emerald-400 border-b-transparent border-l-transparent animate-spin" />
                    <span className="text-xs text-textSecondary font-semibold tracking-wider uppercase">Loading Session Data…</span>
                </div>
            </div>
        );
    }

    if (!results || (results.trades.length === 0 && !results.candles?.length)) return null;

    return (
        <PageTransition className="text-textPrimary bg-background min-h-screen p-0">
            <div className="flex flex-col h-screen overflow-hidden">

                {/* Header */}
                <header className="flex items-center justify-between px-6 py-3 bg-card border-b border-card-border flex-shrink-0">
                    <div className="flex items-center gap-6">
                        <span className="text-sm font-semibold text-textPrimary">Backtest Results</span>
                        <nav className="flex items-center">
                            {TABS.map(tab => (
                                <TabButton key={tab} label={tab} active={activeTab === tab} onClick={() => setActiveTab(tab)} />
                            ))}
                        </nav>
                    </div>
                    <Link to="/setup" className="text-xs text-textSecondary hover:text-textPrimary transition-colors duration-150">
                        ← Refine Strategy
                    </Link>
                </header>

                {/* Content */}
                <div className="flex-1 min-h-0 overflow-hidden px-6 py-5">
                    {activeTab === "Overview" && (
                        <OverviewTab results={results} insights={insights} insightsLoading={insightsLoading} />
                    )}
                    {activeTab === "Trades" && (
                        <TradesTab trades={results.trades} candles={results.candles} />
                    )}
                    {activeTab === "Regime Analysis" && (
                        <RegimeTab regimeData={regimeData} regimePerfData={regimePerfData} regimeLoading={regimeLoading} />
                    )}
                    {activeTab === "Optimize" && (
                        <OptimizePanel uploadedFile={uploadedFile} />
                    )}
                </div>

            </div>
        </PageTransition>
    );
}
