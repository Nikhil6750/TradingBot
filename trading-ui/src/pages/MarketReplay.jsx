import { useMemo, useState } from "react";
import toast from "react-hot-toast";
import { Activity, BarChart3, Bot, Clock3, Database, PlayCircle, Shield, TrendingUp } from "lucide-react";

import {
    apiPost,
    getApiErrorMessage,
    getConnectivityMessage,
    isServerUnavailableError,
} from "../lib/api";
import { useStrategy } from "../context/StrategyContext";
import PageTransition from "../components/ui/PageTransition";
import GlassPanel from "../components/ui/GlassPanel";
import DatasetUploader from "../components/trading/DatasetUploader";
import ReplayControls from "../components/trading/ReplayControls";
import ReplayChart from "../components/charts/ReplayChart";
import StrategyTemplates from "../components/strategy/StrategyTemplates";
import RuleBuilder from "../components/strategy/RuleBuilder";
import CodeEditorStrategy from "../components/strategy/CodeEditorStrategy";
import useReplayEngine from "../replay/useReplayEngine";
import {
    applyReplayEvents,
    buildReplayRuntime,
    buildReplayStrategyConfig,
    buildStrategyPlan,
    computeReplayMetrics,
    createEmptyReplayRuntime,
    formatPercent,
    formatPrice,
    formatReplayTime,
    inferReplayStart,
} from "../replay/replayUtils";

const TIMEFRAMES = [
    { label: "1m", value: "1m" },
    { label: "5m", value: "5m" },
    { label: "15m", value: "15m" },
    { label: "1h", value: "1h" },
    { label: "4h", value: "4h" },
    { label: "1d", value: "1d" },
];

const MODES = [
    { id: "template", label: "Templates" },
    { id: "rules", label: "Rules" },
    { id: "code", label: "Code" },
];

const INITIAL_BALANCE = 10000;

export default function MarketReplay() {
    const { config, setConfig } = useStrategy();

    const [selectedAsset, setSelectedAsset] = useState(null);
    const [timeframe, setTimeframe] = useState("1h");
    const [stopLossPct, setStopLossPct] = useState(2);
    const [takeProfitPct, setTakeProfitPct] = useState(4);
    const [loadingReplay, setLoadingReplay] = useState(false);
    const [replayResult, setReplayResult] = useState(null);
    const [preparedConfig, setPreparedConfig] = useState(null);
    const [preparedSignature, setPreparedSignature] = useState("");
    const [runtime, setRuntime] = useState(createEmptyReplayRuntime());

    const strategyRequest = useMemo(
        () => buildReplayStrategyConfig(config, { stopLossPct, takeProfitPct }),
        [config, stopLossPct, takeProfitPct],
    );

    const currentSignature = useMemo(
        () => JSON.stringify({
            datasetId: selectedAsset?.id || null,
            timeframe,
            strategyRequest,
        }),
        [selectedAsset?.id, strategyRequest, timeframe],
    );

    const replayCandles = replayResult?.candles || [];
    const strategyPlan = useMemo(() => buildStrategyPlan(replayResult), [replayResult]);
    const initialCursor = useMemo(
        () => inferReplayStart(replayCandles, preparedConfig || strategyRequest),
        [preparedConfig, replayCandles, strategyRequest],
    );

    const {
        cursor,
        isPlaying,
        speed,
        setSpeed,
        play,
        pause,
        step,
        reset,
    } = useReplayEngine({
        candles: replayCandles,
        initialCursor,
        onCandle: handleReplayCandle,
        onReset: handleReplayReset,
    });

    const currentCandle = replayCandles[cursor] || null;
    const openTrade = runtime.openTrades.length ? runtime.openTrades[runtime.openTrades.length - 1] : null;
    const completedTrades = runtime.completedTrades;
    const metrics = useMemo(() => computeReplayMetrics(completedTrades), [completedTrades]);

    const baseBalance = useMemo(() => {
        return completedTrades.reduce((balance, trade) => balance * (1 + Number(trade.pnl || 0)), INITIAL_BALANCE);
    }, [completedTrades]);

    const openTradePnl = useMemo(() => {
        if (!openTrade || !currentCandle) {
            return 0;
        }

        const delta = (Number(currentCandle.close) - Number(openTrade.entry_price)) / Number(openTrade.entry_price);
        return openTrade.type === "BUY" ? delta : -delta;
    }, [currentCandle, openTrade]);

    const liveBalance = openTrade ? baseBalance * (1 + openTradePnl) : baseBalance;
    const replayReady = replayCandles.length > 0;
    const canStep = replayReady && cursor < replayCandles.length - 1;
    const replayStale = Boolean(replayResult) && preparedSignature !== currentSignature;
    const chartKey = replayReady
        ? `${selectedAsset?.id || "dataset"}-${timeframe}-${replayCandles[0].time}-${replayCandles[replayCandles.length - 1].time}`
        : "replay-empty";
    const visibleSignals = runtime.buySignals.length + runtime.sellSignals.length;

    async function handlePrepareReplay() {
        if (!selectedAsset?.id) {
            toast.error("Upload a CSV dataset before preparing replay.");
            return;
        }

        setLoadingReplay(true);
        pause();
        const loadingToast = toast.loading("Preparing replay engine...");

        try {
            const payload = {
                symbol: selectedAsset.id,
                timeframe,
                config: strategyRequest,
            };

            const result = await apiPost("/replay/evaluate", payload);

            setRuntime(createEmptyReplayRuntime());
            setReplayResult(result);
            setPreparedConfig(JSON.parse(JSON.stringify(strategyRequest)));
            setPreparedSignature(currentSignature);

            toast.dismiss(loadingToast);
            toast.success(`Replay ready with ${result.candles?.length || 0} candles.`);
        } catch (error) {
            toast.dismiss(loadingToast);
            toast.error(
                isServerUnavailableError(error)
                    ? getConnectivityMessage()
                    : getApiErrorMessage(error, "Replay preparation failed."),
            );
        } finally {
            setLoadingReplay(false);
        }
    }

    function handleReplayCandle(candle) {
        if (!strategyPlan || !candle) {
            return;
        }

        setRuntime((previousRuntime) => applyReplayEvents(previousRuntime, candle, strategyPlan));
    }

    function handleReplayReset(_visibleCandles, nextCursor) {
        if (!strategyPlan || replayCandles.length === 0) {
            setRuntime(createEmptyReplayRuntime());
            return;
        }

        setRuntime(buildReplayRuntime(replayCandles, nextCursor, strategyPlan));
    }

    function handleDatasetChange(asset) {
        pause();
        setSelectedAsset(asset);
        // If uploader provided candles, seed the chart immediately
        if (asset?.candles) {
            setReplayResult({ candles: asset.candles });
        } else {
            setReplayResult(null);
        }
        setPreparedConfig(null);
        setPreparedSignature("");
        setRuntime(createEmptyReplayRuntime());
    }

    function setMode(mode) {
        setConfig((previousConfig) => ({ ...previousConfig, mode }));
    }

    return (
        <PageTransition className="min-h-screen bg-[#03080d] p-6 text-slate-100">
            <GlassPanel className="flex h-[calc(100vh-3rem)] min-h-[760px] overflow-hidden border border-white/5 bg-[#050b11]">
                <aside className="flex w-[360px] shrink-0 flex-col overflow-y-auto border-r border-white/5 bg-[#071018]">
                    <div className="space-y-8 p-6">
                        <div>
                            <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-[#7dd3fc]">AlgoTradeX Replay</p>
                            <h1 className="mt-3 text-3xl font-black tracking-tight text-white">Strategy Lab</h1>
                            <p className="mt-2 text-sm leading-6 text-slate-400">
                                Upload a dataset, prepare the strategy once, then replay the market one candle at a time.
                            </p>
                        </div>

                        <section className="space-y-4">
                            <SectionTitle icon={Database} label="Dataset" />
                            <DatasetUploader onUploadSuccess={handleDatasetChange} />
                            <Field label="Replay timeframe">
                                <select
                                    value={timeframe}
                                    onChange={(event) => setTimeframe(event.target.value)}
                                    className="w-full rounded-xl border border-white/10 bg-[#0b1823] px-3 py-2.5 text-sm text-white outline-none transition focus:border-lime-300/40"
                                >
                                    {TIMEFRAMES.map((option) => (
                                        <option key={option.value} value={option.value}>
                                            {option.label}
                                        </option>
                                    ))}
                                </select>
                            </Field>
                        </section>

                        <section className="space-y-4">
                            <SectionTitle icon={Bot} label="Strategy engine" />
                            <div className="flex rounded-2xl border border-white/10 bg-[#09141f] p-1">
                                {MODES.map((mode) => (
                                    <button
                                        key={mode.id}
                                        type="button"
                                        onClick={() => setMode(mode.id)}
                                        className={`flex-1 rounded-xl px-3 py-2 text-xs font-bold uppercase tracking-[0.16em] transition ${
                                            config.mode === mode.id
                                                ? "bg-[#d6f36e] text-[#0d131a]"
                                                : "text-slate-400 hover:text-white"
                                        }`}
                                    >
                                        {mode.label}
                                    </button>
                                ))}
                            </div>

                            <div className="rounded-2xl border border-white/5 bg-[#08131d] p-4">
                                {config.mode === "template" && <StrategyTemplates />}
                                {config.mode === "rules" && (
                                    <div className="h-[520px]">
                                        <RuleBuilder />
                                    </div>
                                )}
                                {config.mode === "code" && <CodeEditorStrategy />}
                            </div>
                        </section>

                        <section className="space-y-4">
                            <SectionTitle icon={Shield} label="Risk" />
                            <div className="grid grid-cols-2 gap-3">
                                <Field label="Stop loss %">
                                    <input
                                        type="number"
                                        min="0"
                                        step="0.1"
                                        value={stopLossPct}
                                        onChange={(event) => setStopLossPct(Number(event.target.value))}
                                        className="w-full rounded-xl border border-white/10 bg-[#0b1823] px-3 py-2.5 text-sm text-white outline-none transition focus:border-lime-300/40"
                                    />
                                </Field>
                                <Field label="Take profit %">
                                    <input
                                        type="number"
                                        min="0"
                                        step="0.1"
                                        value={takeProfitPct}
                                        onChange={(event) => setTakeProfitPct(Number(event.target.value))}
                                        className="w-full rounded-xl border border-white/10 bg-[#0b1823] px-3 py-2.5 text-sm text-white outline-none transition focus:border-lime-300/40"
                                    />
                                </Field>
                            </div>
                        </section>
                    </div>

                    <div className="mt-auto border-t border-white/5 bg-[#050d14] p-6">
                        <button
                            type="button"
                            onClick={handlePrepareReplay}
                            disabled={loadingReplay || !selectedAsset}
                            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#d6f36e] px-4 py-3 text-sm font-black uppercase tracking-[0.2em] text-[#0c1218] transition hover:bg-[#e2f78e] disabled:cursor-not-allowed disabled:opacity-40"
                        >
                            <PlayCircle size={16} />
                            {loadingReplay ? "Preparing..." : "Prepare Replay"}
                        </button>

                        <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-semibold">
                            <StatusPill tone={selectedAsset ? "ready" : "idle"}>
                                {selectedAsset ? selectedAsset.symbol : "No dataset"}
                            </StatusPill>
                            <StatusPill tone={replayReady ? "ready" : "idle"}>
                                {replayReady ? `${replayCandles.length} candles` : "Replay empty"}
                            </StatusPill>
                            {replayStale && <StatusPill tone="warning">Settings changed</StatusPill>}
                        </div>
                    </div>
                </aside>

                <main className="flex min-w-0 flex-1 flex-col bg-[#040c13]">
                    <div className="flex items-center justify-between border-b border-white/5 px-6 py-5">
                        <div>
                            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-sky-300">Replay workspace</p>
                            <h2 className="mt-2 text-2xl font-black text-white">
                                {selectedAsset?.symbol || "Awaiting dataset"}
                            </h2>
                            <p className="mt-1 text-sm text-slate-400">
                                {currentCandle ? formatReplayTime(currentCandle.time) : "Prepare the replay to load chart data."}
                            </p>
                        </div>

                        <div className="grid grid-cols-3 gap-3 text-right">
                            <MiniStat label="Current close" value={currentCandle ? formatPrice(currentCandle.close) : "—"} />
                            <MiniStat label="Live PnL" value={openTrade ? formatPercent(openTradePnl) : "Flat"} />
                            <MiniStat label="Replay speed" value={`${speed}x`} />
                        </div>
                    </div>

                    <div className="flex min-h-0 flex-1 flex-col gap-5 p-6">
                        <ReplayControls
                            isPlaying={isPlaying}
                            speed={speed}
                            cursor={cursor}
                            totalCandles={replayCandles.length}
                            canStep={canStep}
                            onPlay={play}
                            onPause={pause}
                            onStep={step}
                            onReset={() => reset(initialCursor)}
                            onSpeedChange={setSpeed}
                        />

                        <div className="min-h-0 flex-1 overflow-hidden rounded-[28px] border border-[#123246] bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.08),transparent_45%),linear-gradient(180deg,#06111a,#040a10)]">
                            {replayReady ? (
                                <ReplayChart
                                    datasetKey={chartKey}
                                    candles={replayCandles}
                                    cursor={cursor}
                                    buySignals={runtime.buySignals}
                                    sellSignals={runtime.sellSignals}
                                    completedTrades={completedTrades}
                                />
                            ) : (
                                <EmptyChartState />
                            )}
                        </div>
                    </div>
                </main>

                <aside className="flex w-[340px] shrink-0 flex-col overflow-y-auto border-l border-white/5 bg-[#071018] p-6">
                    <div className="space-y-6">
                        <div>
                            <p className="text-[11px] font-bold uppercase tracking-[0.24em] text-[#facc15]">Replay analytics</p>
                            <h3 className="mt-2 text-2xl font-black text-white">Live strategy state</h3>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <AnalyticsCard icon={BarChart3} label="Trades" value={String(metrics.total_trades)} />
                            <AnalyticsCard icon={TrendingUp} label="Win rate" value={`${(metrics.win_rate * 100).toFixed(1)}%`} />
                            <AnalyticsCard icon={Activity} label="Signals" value={String(visibleSignals)} />
                            <AnalyticsCard icon={Clock3} label="Cursor" value={replayReady ? `${cursor + 1}` : "0"} />
                        </div>

                        <div className="rounded-2xl border border-white/5 bg-[#08131d] p-4">
                            <PanelTitle label="Performance" />
                            <MetricRow label="Total return" value={formatPercent(metrics.total_return)} />
                            <MetricRow label="Average trade" value={formatPercent(metrics.avg_trade)} />
                            <MetricRow label="Profit factor" value={formatMetric(metrics.profit_factor)} />
                            <MetricRow label="Max drawdown" value={formatPercent(metrics.max_drawdown)} />
                            <MetricRow label="Simulated balance" value={`$${liveBalance.toFixed(2)}`} />
                        </div>

                        <div className="rounded-2xl border border-white/5 bg-[#08131d] p-4">
                            <PanelTitle label="Open position" />
                            {openTrade && currentCandle ? (
                                <div className="space-y-3">
                                    <MetricRow label="Side" value={openTrade.type} />
                                    <MetricRow label="Entry" value={formatPrice(openTrade.entry_price)} />
                                    <MetricRow label="Marked PnL" value={formatPercent(openTradePnl)} />
                                    <MetricRow label="Opened" value={formatReplayTime(openTrade.entry_time)} />
                                </div>
                            ) : (
                                <p className="text-sm text-slate-400">No open trade at the current replay cursor.</p>
                            )}
                        </div>

                        <div className="rounded-2xl border border-white/5 bg-[#08131d] p-4">
                            <PanelTitle label="Last event" />
                            {runtime.lastEvent ? (
                                <div className="space-y-2 text-sm text-slate-300">
                                    <p className="font-semibold uppercase tracking-[0.18em] text-sky-300">
                                        {runtime.lastEvent.type === "exit" ? "Trade exit" : `${runtime.lastEvent.type} signal`}
                                    </p>
                                    <p>{formatReplayTime(runtime.lastEvent.candle?.time)}</p>
                                    <p className="text-slate-400">
                                        Close {runtime.lastEvent.candle?.close ? formatPrice(runtime.lastEvent.candle.close) : "—"}
                                    </p>
                                </div>
                            ) : (
                                <p className="text-sm text-slate-400">No strategy event has fired yet.</p>
                            )}
                        </div>

                        <div className="rounded-2xl border border-white/5 bg-[#08131d] p-4">
                            <PanelTitle label="Recent trades" />
                            {completedTrades.length > 0 ? (
                                <div className="space-y-3">
                                    {completedTrades.slice(-5).reverse().map((trade) => (
                                        <div
                                            key={trade.id}
                                            className="rounded-xl border border-white/5 bg-[#0b1823] px-3 py-2.5"
                                        >
                                            <div className="flex items-center justify-between gap-3">
                                                <span className="text-xs font-bold uppercase tracking-[0.18em] text-white">{trade.type}</span>
                                                <span className={`text-xs font-bold ${Number(trade.pnl) >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                                                    {formatPercent(trade.pnl)}
                                                </span>
                                            </div>
                                            <div className="mt-2 text-xs text-slate-400">
                                                {formatReplayTime(trade.entry_time)} to {formatReplayTime(trade.exit_time)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-sm text-slate-400">Trades will appear here as replayed candles complete them.</p>
                            )}
                        </div>
                    </div>
                </aside>
            </GlassPanel>
        </PageTransition>
    );
}

function SectionTitle({ icon: Icon, label }) {
    return (
        <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-[#0b1823] text-sky-300">
                <Icon size={15} />
            </span>
            <h2 className="text-xs font-black uppercase tracking-[0.22em] text-slate-200">{label}</h2>
        </div>
    );
}

function Field({ label, children }) {
    return (
        <label className="block space-y-2">
            <span className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">{label}</span>
            {children}
        </label>
    );
}

function StatusPill({ children, tone }) {
    const styles = {
        ready: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
        warning: "border-amber-400/25 bg-amber-400/10 text-amber-200",
        idle: "border-white/10 bg-white/5 text-slate-400",
    };

    return (
        <span className={`rounded-full border px-3 py-1 ${styles[tone] || styles.idle}`}>
            {children}
        </span>
    );
}

function MiniStat({ label, value }) {
    return (
        <div className="rounded-2xl border border-white/5 bg-[#08131d] px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">{label}</p>
            <p className="mt-2 text-sm font-bold text-white">{value}</p>
        </div>
    );
}

function AnalyticsCard({ icon: Icon, label, value }) {
    return (
        <div className="rounded-2xl border border-white/5 bg-[#08131d] p-4">
            <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">{label}</p>
                <Icon size={14} className="text-slate-500" />
            </div>
            <p className="mt-3 text-xl font-black text-white">{value}</p>
        </div>
    );
}

function PanelTitle({ label }) {
    return <h4 className="mb-4 text-[11px] font-black uppercase tracking-[0.22em] text-slate-300">{label}</h4>;
}

function MetricRow({ label, value }) {
    return (
        <div className="flex items-center justify-between gap-4 py-1.5 text-sm">
            <span className="text-slate-400">{label}</span>
            <span className="font-semibold text-white">{value}</span>
        </div>
    );
}

function EmptyChartState() {
    return (
        <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-white/5 text-sky-300">
                <PlayCircle size={28} />
            </div>
            <div>
                <h3 className="text-xl font-black text-white">Replay not loaded</h3>
                <p className="mt-2 max-w-sm text-sm leading-6 text-slate-400">
                    Upload a dataset, choose a strategy, then prepare replay to seed the chart and strategy events.
                </p>
            </div>
        </div>
    );
}

function formatMetric(value) {
    if (value === null || value === undefined) {
        return "—";
    }
    if (value === Number.POSITIVE_INFINITY) {
        return "∞";
    }
    return Number(value).toFixed(2);
}
