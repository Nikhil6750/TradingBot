import { useState } from "react";
import { useStrategy } from "../../context/StrategyContext";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Play, RotateCcw, CheckCircle, ChevronDown, ChevronUp } from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// ── Design tokens ─────────────────────────────────────────────────────────────
const S = {
    card: { background: "#111111", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "12px" },
    input: {
        background: "#0a0a0a", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "6px",
        color: "#E5E5E5", outline: "none", padding: "5px 10px", fontSize: "12px", width: "72px"
    },
    label: { color: "#A1A1A1", fontSize: "11px", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.08em" },
};

// ── Default parameter ranges matching optimizer.py expectations ───────────────
const DEFAULT_PARAMS = [
    { key: "short_ma", label: "Short MA Period", min: 5, max: 50, step: 1, isInt: true },
    { key: "long_ma", label: "Long MA Period", min: 20, max: 200, step: 5, isInt: true },
    { key: "rsi_period", label: "RSI Period", min: 7, max: 21, step: 1, isInt: true },
    { key: "rsi_lower", label: "RSI Oversold", min: 20, max: 40, step: 1, isInt: true },
    { key: "rsi_upper", label: "RSI Overbought", min: 60, max: 80, step: 1, isInt: true },
    { key: "stop_loss", label: "Stop Loss %", min: 0.005, max: 0.05, step: 0.005, isInt: false },
    { key: "take_profit", label: "Take Profit %", min: 0.01, max: 0.10, step: 0.01, isInt: false },
];

const TRIAL_OPTIONS = [25, 50, 100, 200];

// ── Helpers ───────────────────────────────────────────────────────────────────
function pct(v) { return v != null ? `${(v * 100).toFixed(2)}%` : "—"; }
function fmt(v, decimals = 4) {
    if (v == null) return "—";
    return typeof v === "number" ? v.toFixed(decimals) : String(v);
}

// ── Param row ─────────────────────────────────────────────────────────────────
function ParamRow({ param, enabled, min, max, onToggle, onChange }) {
    return (
        <div className="flex items-center gap-4 py-2.5" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            {/* Toggle */}
            <button
                onClick={() => onToggle(param.key)}
                className="w-4 h-4 rounded flex items-center justify-center flex-shrink-0 cursor-pointer transition-colors"
                style={{
                    background: enabled ? "rgba(255,255,255,0.9)" : "transparent",
                    border: `1px solid ${enabled ? "rgba(255,255,255,0.9)" : "rgba(255,255,255,0.2)"}`,
                }}
                title={enabled ? "Disable" : "Enable"}
            >
                {enabled && <span style={{ color: "#050505", fontSize: "9px", fontWeight: 900, lineHeight: 1 }}>✓</span>}
            </button>

            {/* Label */}
            <span className="flex-1 text-xs" style={{ color: enabled ? "#E5E5E5" : "#505050" }}>{param.label}</span>

            {/* Min / Max */}
            <div className="flex items-center gap-2">
                <div className="flex flex-col items-end gap-0.5">
                    <span style={{ ...S.label, fontSize: "9px" }}>MIN</span>
                    <input
                        type="number" disabled={!enabled}
                        value={min} step={param.step}
                        onChange={e => onChange(param.key, "min", param.isInt ? parseInt(e.target.value) : parseFloat(e.target.value))}
                        style={{ ...S.input, opacity: enabled ? 1 : 0.35 }}
                    />
                </div>
                <span style={{ color: "#444", fontSize: "10px", marginTop: "14px" }}>–</span>
                <div className="flex flex-col items-end gap-0.5">
                    <span style={{ ...S.label, fontSize: "9px" }}>MAX</span>
                    <input
                        type="number" disabled={!enabled}
                        value={max} step={param.step}
                        onChange={e => onChange(param.key, "max", param.isInt ? parseInt(e.target.value) : parseFloat(e.target.value))}
                        style={{ ...S.input, opacity: enabled ? 1 : 0.35 }}
                    />
                </div>
            </div>
        </div>
    );
}

// ── Results table ─────────────────────────────────────────────────────────────
function ResultsTable({ history, bestParams }) {
    if (!history?.length) return null;

    // Get param keys from first row (exclude known metric keys)
    const METRIC_KEYS = new Set(["Return", "Win Rate", "Max Drawdown", "Sharpe Ratio"]);
    const paramKeys = Object.keys(history[0]).filter(k => !METRIC_KEYS.has(k));

    return (
        <div style={S.card} className="overflow-hidden">
            <div className="px-5 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                <span className="text-xs font-semibold text-textPrimary">Optimization Results</span>
                <span className="text-[10px] text-textSecondary">{history.length} configurations · sorted by Sharpe</span>
            </div>
            <div className="overflow-x-auto">
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-textSecondary text-[10px] uppercase tracking-wider">
                            <th className="px-4 py-3 text-left font-medium">#</th>
                            {paramKeys.map(k => <th key={k} className="px-3 py-3 text-right font-medium">{k}</th>)}
                            <th className="px-3 py-3 text-right font-medium">Sharpe</th>
                            <th className="px-3 py-3 text-right font-medium">Return</th>
                            <th className="px-3 py-3 text-right font-medium">Win Rate</th>
                            <th className="px-3 py-3 text-right font-medium">Drawdown</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-border/30">
                        {history.map((row, i) => {
                            const isBest = i === 0;
                            return (
                                <tr
                                    key={i}
                                    style={{
                                        background: isBest ? "rgba(255,255,255,0.04)" : "transparent",
                                        borderLeft: isBest ? "2px solid rgba(255,255,255,0.6)" : "2px solid transparent",
                                    }}
                                >
                                    <td className="px-4 py-2.5 text-textSecondary font-mono">{i + 1}</td>
                                    {paramKeys.map(k => (
                                        <td key={k} className="px-3 py-2.5 text-right text-textPrimary font-mono tabular-nums">
                                            {fmt(row[k], typeof row[k] === "number" && !Number.isInteger(row[k]) ? 4 : 0)}
                                        </td>
                                    ))}
                                    <td className={`px-3 py-2.5 text-right font-mono tabular-nums font-semibold ${(row["Sharpe Ratio"] ?? 0) > 1 ? "text-emerald-400" : "text-textPrimary"}`}>
                                        {fmt(row["Sharpe Ratio"])}
                                    </td>
                                    <td className={`px-3 py-2.5 text-right font-mono tabular-nums ${(row["Return"] ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                                        {pct(row["Return"])}
                                    </td>
                                    <td className={`px-3 py-2.5 text-right font-mono tabular-nums ${(row["Win Rate"] ?? 0) > 0.5 ? "text-emerald-400" : "text-textPrimary"}`}>
                                        {pct(row["Win Rate"])}
                                    </td>
                                    <td className="px-3 py-2.5 text-right font-mono tabular-nums text-red-400">
                                        {pct(row["Max Drawdown"])}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

// ── Best config card ──────────────────────────────────────────────────────────
function BestConfigCard({ bestParams, bestScore, onApply }) {
    if (!bestParams) return null;
    return (
        <div
            className="rounded-xl p-5 flex flex-col gap-4"
            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.10)" }}
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <CheckCircle size={14} className="text-emerald-400" />
                    <span className="text-xs font-semibold text-textPrimary">Best Configuration</span>
                </div>
                <span className="text-[10px] text-textSecondary">
                    Sharpe {fmt(bestScore)}
                </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-x-6 gap-y-3">
                {Object.entries(bestParams).map(([k, v]) => (
                    <div key={k} className="flex flex-col gap-0.5">
                        <span className="text-[10px] uppercase tracking-wider text-textSecondary">{k.replace(/_/g, " ")}</span>
                        <span className="text-sm font-bold text-textPrimary tabular-nums font-mono">
                            {typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(4)) : String(v)}
                        </span>
                    </div>
                ))}
            </div>
            <button
                onClick={onApply}
                className="self-start flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-semibold cursor-pointer transition-all duration-150"
                style={{ background: "#E5E5E5", color: "#050505" }}
                onMouseEnter={e => { e.currentTarget.style.background = "#FFFFFF"; e.currentTarget.style.transform = "translateY(-1px)"; }}
                onMouseLeave={e => { e.currentTarget.style.background = "#E5E5E5"; e.currentTarget.style.transform = "translateY(0)"; }}
            >
                <RotateCcw size={12} />
                Apply & Re-run Backtest
            </button>
        </div>
    );
}

// ── Main export ───────────────────────────────────────────────────────────────
export default function OptimizePanel({ uploadedFile }) {
    const { config, setConfig } = useStrategy();
    const navigate = useNavigate();

    // Enabled params state (all on by default for params present in existing config)
    const [enabled, setEnabled] = useState(() =>
        Object.fromEntries(DEFAULT_PARAMS.map(p => [p.key, true]))
    );
    const [ranges, setRanges] = useState(() =>
        Object.fromEntries(DEFAULT_PARAMS.map(p => [p.key, { min: p.min, max: p.max }]))
    );
    const [trials, setTrials] = useState(50);

    const [running, setRunning] = useState(false);
    const [progress, setProgress] = useState(null); // e.g. "Running 50 trials…"
    const [error, setError] = useState(null);
    const [results, setResults] = useState(null);  // { best_parameters, best_score, optimization_history }

    const toggleParam = (key) => setEnabled(prev => ({ ...prev, [key]: !prev[key] }));
    const changeRange = (key, field, val) => setRanges(prev => ({ ...prev, [key]: { ...prev[key], [field]: val } }));

    const runOptimization = async () => {
        if (!uploadedFile) { setError("No CSV file available — run a backtest first."); return; }
        const activeParams = DEFAULT_PARAMS.filter(p => enabled[p.key]);
        if (!activeParams.length) { setError("Enable at least one parameter to optimize."); return; }

        const paramRanges = Object.fromEntries(
            activeParams.map(p => [p.key, [ranges[p.key].min, ranges[p.key].max]])
        );

        setRunning(true);
        setError(null);
        setResults(null);
        setProgress(`Running ${trials} trials with Bayesian optimization…`);

        const parts = uploadedFile.name.replace(".csv", "").split("_");
        const payload = {
            symbol: parts[0] || "EURUSD",
            timeframe: parts[1] || "1H",
            config: config || {},
            param_ranges: paramRanges,
            trials: trials
        };

        try {
            const { data } = await axios.post(`${API_BASE}/optimize_strategy`, payload, {
                timeout: 300_000, // 5 min max
            });
            setResults(data);
        } catch (e) {
            setError(e?.response?.data?.detail ?? e?.message ?? "Optimization failed.");
        } finally {
            setRunning(false);
            setProgress(null);
        }
    };

    const applyBest = () => {
        if (!results?.best_parameters) return;
        setConfig(prev => ({
            ...prev,
            parameters: { ...(prev?.parameters ?? {}), ...results.best_parameters },
        }));
        navigate("/upload");
    };

    return (
        <div className="flex flex-col gap-5 pb-6 overflow-y-auto custom-scrollbar h-full">

            {/* ── Config panel ────────────────────────────────────── */}
            <div style={S.card} className="overflow-hidden">
                <div className="px-5 py-3 flex items-center justify-between" style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                    <span className="text-xs font-semibold text-textPrimary">Parameter Search Space</span>
                    <span className="text-[10px] text-textSecondary">Toggle params to include / exclude</span>
                </div>
                <div className="px-5">
                    {DEFAULT_PARAMS.map(p => (
                        <ParamRow
                            key={p.key}
                            param={p}
                            enabled={enabled[p.key]}
                            min={ranges[p.key].min}
                            max={ranges[p.key].max}
                            onToggle={toggleParam}
                            onChange={changeRange}
                        />
                    ))}
                </div>
            </div>

            {/* ── Run controls ────────────────────────────────────── */}
            <div className="flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-2">
                    <span style={S.label}>Trials</span>
                    <div className="flex gap-1">
                        {TRIAL_OPTIONS.map(n => (
                            <button
                                key={n}
                                onClick={() => setTrials(n)}
                                className="px-3 py-1.5 rounded text-xs font-semibold cursor-pointer transition-colors duration-100"
                                style={{
                                    background: trials === n ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.04)",
                                    border: `1px solid ${trials === n ? "rgba(255,255,255,0.20)" : "rgba(255,255,255,0.07)"}`,
                                    color: trials === n ? "#E5E5E5" : "#A1A1A1",
                                }}
                            >
                                {n}
                            </button>
                        ))}
                    </div>
                </div>

                <button
                    onClick={runOptimization}
                    disabled={running}
                    className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-semibold cursor-pointer transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed ml-auto"
                    style={{ background: "#E5E5E5", color: "#050505" }}
                    onMouseEnter={e => { if (!running) { e.currentTarget.style.background = "#FFFFFF"; e.currentTarget.style.transform = "translateY(-1px)"; } }}
                    onMouseLeave={e => { e.currentTarget.style.background = "#E5E5E5"; e.currentTarget.style.transform = "translateY(0)"; }}
                >
                    {running
                        ? <><span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />Running…</>
                        : <><Play size={12} />Run Optimization</>
                    }
                </button>
            </div>

            {/* ── Progress / error ─────────────────────────────────── */}
            {progress && !error && (
                <div className="flex items-center gap-2 px-4 py-3 rounded-xl text-xs text-textSecondary"
                    style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <span className="w-2 h-2 rounded-full bg-textSecondary animate-pulse flex-shrink-0" />
                    {progress}
                </div>
            )}
            {error && (
                <div className="px-4 py-3 rounded-xl text-xs" style={{ background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.18)", color: "#fca5a5" }}>
                    {error}
                </div>
            )}

            {/* ── Results ──────────────────────────────────────────── */}
            {results && (
                <>
                    <BestConfigCard
                        bestParams={results.best_parameters}
                        bestScore={results.best_score}
                        onApply={applyBest}
                    />
                    <ResultsTable
                        history={results.optimization_history}
                        bestParams={results.best_parameters}
                    />
                </>
            )}
        </div>
    );
}
