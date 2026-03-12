import { useEffect, useMemo, useRef, useState } from "react";
import { FixedSizeList } from "react-window";

import { useStrategy } from "../context/StrategyContext";
import { apiPost, getApiErrorMessage, getConnectivityMessage, isServerUnavailableError } from "../lib/api";
import useReplayEngine from "../replay/useReplayEngine";
import DatasetUploader from "../components/trading/DatasetUploader";
import ReplayControls from "../components/trading/ReplayControls";
import ReplayChart from "../components/charts/ReplayChart";
import EquityChart from "../components/charts/EquityChart";
import DrawdownChart from "../components/charts/DrawdownChart";
import StatusMessageCard from "../components/ui/StatusMessageCard";
import PageTransition from "../components/ui/PageTransition";

const WORKFLOW_TABS = ["Build Strategy", "Chart Replay", "Setups", "Results & Metrics"];
const STRATEGY_TYPE_TABS = [
    { id: "template", label: "Template Strategy" },
    { id: "rules", label: "Visual Rule Builder" },
    { id: "pine", label: "Pine Script Strategy" },
];
const TEMPLATE_STRATEGIES = [
    { id: "ma_crossover", label: "Moving Average Crossover" },
    { id: "rsi_reversal", label: "RSI Strategy" },
    { id: "mean_reversion", label: "Mean Reversion" },
    { id: "breakout", label: "Breakout" },
];
const TIMEFRAME_OPTIONS = ["1m", "5m", "15m", "30m", "1h", "4h"];
const RULE_INDICATORS = ["close", "open", "high", "low", "rsi", "sma20", "sma50", "ema20", "ema50"];
const OPERATORS = [">", "<", ">=", "<=", "=="];
const UI_THEME = {
    background: "#0a0a0a",
    panel: "#111111",
    border: "#1f1f1f",
    text: "#e5e5e5",
    secondaryText: "#8a8a8a",
    bull: "#22c55e",
    bear: "#ef4444",
};
const SETUP_LIST_ROW_HEIGHT = 108;
const TEMPLATE_PARAMETER_SCHEMAS = {
    ma_crossover: {
        columns: "sm:grid-cols-3",
        fields: [
            { key: "fast_period", label: "Fast MA Period", type: "number", min: 1 },
            { key: "slow_period", label: "Slow MA Period", type: "number", min: 2 },
            {
                key: "ma_type",
                label: "MA Type",
                type: "select",
                options: [
                    { value: "EMA", label: "EMA" },
                    { value: "SMA", label: "SMA" },
                ],
            },
        ],
    },
    rsi_reversal: {
        columns: "sm:grid-cols-3",
        fields: [
            { key: "rsi_length", label: "RSI Length", type: "number", min: 1 },
            { key: "overbought", label: "Overbought", type: "number" },
            { key: "oversold", label: "Oversold", type: "number" },
        ],
    },
    breakout: {
        columns: "sm:grid-cols-2",
        fields: [
            { key: "lookback_period", label: "Lookback Period", type: "number", min: 2 },
            { key: "breakout_threshold", label: "Breakout Threshold (%)", type: "number", min: 0, step: 0.1, hint: "Percent beyond the prior range required to trigger a signal." },
        ],
    },
    mean_reversion: {
        columns: "sm:grid-cols-2",
        fields: [
            { key: "lookback_period", label: "Lookback Period", type: "number", min: 2 },
            { key: "deviation_threshold", label: "Deviation Threshold", type: "number", min: 0.1, step: 0.1 },
        ],
    },
};
const DEFAULT_TEMPLATE_PARAMS = {
    fast_period: 10,
    slow_period: 30,
    ma_type: "EMA",
    rsi_length: 14,
    overbought: 70,
    oversold: 30,
    lookback_period: 20,
    breakout_threshold: 0.25,
    deviation_threshold: 2,
};
const EMPTY_RESULT = {
    candles: [],
    buySignals: [],
    sellSignals: [],
    trades: [],
    metrics: null,
};
const CHART_PALETTE = {
    background: UI_THEME.background,
    text: UI_THEME.text,
    grid: "rgba(255,255,255,0.08)",
    border: UI_THEME.border,
    upCandle: UI_THEME.bull,
    downCandle: UI_THEME.bear,
    upVolume: "rgba(34,197,94,0.28)",
    downVolume: "rgba(239,68,68,0.28)",
    buyMarker: UI_THEME.bull,
    sellMarker: UI_THEME.bear,
    exitBuyMarker: UI_THEME.text,
    exitSellMarker: UI_THEME.secondaryText,
};
const METRIC_CHART_PALETTE = {
    backgroundDark: UI_THEME.background,
    backgroundLight: UI_THEME.background,
    textDark: UI_THEME.text,
    textLight: UI_THEME.text,
    gridDark: "rgba(255,255,255,0.08)",
    gridLight: "rgba(255,255,255,0.08)",
    positiveLine: UI_THEME.text,
    positiveTop: "rgba(255,255,255,0.18)",
    negativeLine: UI_THEME.secondaryText,
    negativeTop: "rgba(138,138,138,0.18)",
    bottom: "rgba(0,0,0,0)",
    drawdownLine: "rgba(255,255,255,0)",
    drawdownTop: "rgba(42,42,42,0.8)",
    drawdownBottom: "rgba(17,17,17,0.55)",
};
const DRAWDOWN_PALETTE = {
    background: UI_THEME.background,
    text: UI_THEME.text,
    grid: "rgba(255,255,255,0.08)",
    line: UI_THEME.text,
    top: "rgba(42,42,42,0.8)",
    bottom: "rgba(17,17,17,0.55)",
};
const SETUPS_CHART_PALETTE = {
    background: UI_THEME.background,
    text: UI_THEME.text,
    grid: "rgba(255,255,255,0.08)",
    border: UI_THEME.border,
    upCandle: UI_THEME.text,
    downCandle: "#2a2a2a",
    upVolume: "rgba(229,229,229,0.2)",
    downVolume: "rgba(42,42,42,0.9)",
    buyMarker: "#2a2a2a",
    sellMarker: "#2a2a2a",
    exitBuyMarker: UI_THEME.text,
    exitSellMarker: UI_THEME.text,
    highlightMarker: UI_THEME.text,
};
const GLASS_PANEL_CLASS = "rounded-[12px] border border-[#1f1f1f] bg-[rgba(20,20,20,0.7)] backdrop-blur-[12px]";
const DEFAULT_PINE_SCRIPT = `//@version=5
strategy("MA Crossover", overlay=true)
fastLength = input.int(12, "Fast Length")
slowLength = input.int(26, "Slow Length")
fast = ta.ema(close, fastLength)
slow = ta.ema(close, slowLength)
longCondition = ta.crossover(fast, slow)
shortCondition = ta.crossunder(fast, slow)

if longCondition
    strategy.entry("Long", strategy.long)

if shortCondition
    strategy.entry("Short", strategy.short)
`;

let ruleId = 0;

function createRule(defaults = {}) {
    ruleId += 1;
    return {
        id: `rule-${ruleId}`,
        indicator: defaults.indicator || "rsi",
        operator: defaults.operator || "<",
        value: defaults.value || "30",
    };
}

function formatPercent(value) {
    const numeric = Number(value || 0) * 100;
    return `${numeric >= 0 ? "+" : ""}${numeric.toFixed(2)}%`;
}

function formatMetric(value, digits = 2) {
    if (value === null || value === undefined) {
        return "0.00";
    }
    if (value === Number.POSITIVE_INFINITY) {
        return "INF";
    }
    return Number(value).toFixed(digits);
}

function buildMetrics(result) {
    const trades = Array.isArray(result?.trades) ? result.trades : [];
    const metrics = result?.metrics || {};
    const pnlValues = trades.map((trade) => Number(trade.pnl || 0));
    const totalTrades = metrics.total_trades ?? trades.length;
    const avgTrade = metrics.avg_trade ?? (pnlValues.length ? pnlValues.reduce((sum, pnl) => sum + pnl, 0) / pnlValues.length : 0);

    return [
        { label: "Total Trades", value: totalTrades ? String(totalTrades) : "0" },
        { label: "Win Rate", value: `${((metrics.win_rate || 0) * 100).toFixed(1)}%` },
        { label: "Profit Factor", value: formatMetric(metrics.profit_factor) },
        { label: "Max Drawdown", value: `${Math.abs(Number(metrics.max_drawdown || 0) * 100).toFixed(2)}%` },
        { label: "Net Profit", value: formatPercent(metrics.total_return || 0) },
        { label: "Average Trade", value: formatPercent(avgTrade || 0) },
    ];
}

function normalizeRule(rule) {
    const normalizedValue = `${rule.value ?? ""}`.trim();
    const numericValue = Number(normalizedValue);
    return {
        indicator: rule.indicator,
        operator: rule.operator,
        value: normalizedValue !== "" && Number.isFinite(numericValue) ? numericValue : normalizedValue,
    };
}

function normalizeResult(data) {
    return {
        candles: Array.isArray(data?.candles) ? data.candles : [],
        buySignals: Array.isArray(data?.buy_signals) ? data.buy_signals : [],
        sellSignals: Array.isArray(data?.sell_signals) ? data.sell_signals : [],
        trades: Array.isArray(data?.trades) ? data.trades : [],
        metrics: data?.metrics || null,
    };
}

function findCandleIndex(candles, timestamp) {
    const normalizedTimestamp = Number(timestamp || 0);
    if (!Array.isArray(candles) || candles.length === 0) {
        return -1;
    }

    const exactIndex = candles.findIndex((candle) => Number(candle.time) === normalizedTimestamp);
    if (exactIndex >= 0) {
        return exactIndex;
    }

    let closestIndex = 0;
    let smallestDistance = Math.abs(Number(candles[0].time) - normalizedTimestamp);
    for (let index = 1; index < candles.length; index += 1) {
        const distance = Math.abs(Number(candles[index].time) - normalizedTimestamp);
        if (distance < smallestDistance) {
            smallestDistance = distance;
            closestIndex = index;
        }
    }
    return closestIndex;
}

function buildTradeSetupsFromResult(result) {
    const candles = Array.isArray(result?.candles) ? result.candles : [];
    const combinedSignals = [
        ...((result?.buySignals || []).map((signal) => ({ ...signal, type: "BUY" }))),
        ...((result?.sellSignals || []).map((signal) => ({ ...signal, type: "SELL" }))),
    ].sort((left, right) => Number(left.time || 0) - Number(right.time || 0));

    return combinedSignals
        .map((signal, sequence) => {
            const signalIndex = findCandleIndex(candles, signal.time);
            const referenceCandle = candles[signalIndex] || null;
            return {
                id: `${String(signal.type || "").toLowerCase()}-${signalIndex}-${sequence}`,
                index: signalIndex,
                timestamp: Number(referenceCandle?.time || signal.time || 0),
                price: Number(signal.price || referenceCandle?.close || 0),
                type: signal.type,
            };
        })
        .filter((setup) => Number.isFinite(setup.index) && setup.index >= 0);
}

function normalizeTradeSetups(payload, candles, fallbackResult = null) {
    const source = Array.isArray(payload?.setups)
        ? payload.setups
        : Array.isArray(payload)
            ? payload
            : [];

    if (source.length === 0 && fallbackResult) {
        return buildTradeSetupsFromResult(fallbackResult);
    }

    return source
        .map((setup, sequence) => {
            const type = String(setup?.type || "").toUpperCase() === "SELL" ? "SELL" : "BUY";
            const signalIndex = Number.isFinite(Number(setup?.index))
                ? Number(setup.index)
                : Number.isFinite(Number(setup?.candle_index))
                    ? Number(setup.candle_index)
                    : findCandleIndex(candles, setup?.timestamp || setup?.time);
            const referenceCandle = candles[signalIndex] || null;

            return {
                id: String(setup?.id || `${type.toLowerCase()}-${signalIndex}-${sequence}`),
                index: signalIndex,
                timestamp: Number(setup?.timestamp || setup?.time || referenceCandle?.time || 0),
                price: Number(setup?.price || referenceCandle?.close || 0),
                type,
            };
        })
        .filter((setup) => Number.isFinite(setup.index) && setup.index >= 0)
        .sort((left, right) => left.index - right.index);
}

function formatSetupTimestamp(timestamp) {
    const numeric = Number(timestamp || 0);
    if (!Number.isFinite(numeric) || numeric <= 0) {
        return "Unknown time";
    }

    const date = new Date(numeric * 1000);
    const year = date.getFullYear();
    const month = `${date.getMonth() + 1}`.padStart(2, "0");
    const day = `${date.getDate()}`.padStart(2, "0");
    const hours = `${date.getHours()}`.padStart(2, "0");
    const minutes = `${date.getMinutes()}`.padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${minutes}`;
}

function coerceParameterValue(field, rawValue) {
    if (field.type === "number") {
        return Number(rawValue) || 0;
    }
    return rawValue;
}

export default function StrategyLab() {
    const { setResults } = useStrategy();

    const [activeTab, setActiveTab] = useState("Build Strategy");
    const [selectedAsset, setSelectedAsset] = useState(null);
    const [strategyMode, setStrategyMode] = useState("template");
    const [strategyType, setStrategyType] = useState("ma_crossover");
    const [timeframe, setTimeframe] = useState("1h");
    const [running, setRunning] = useState(false);
    const [runError, setRunError] = useState("");
    const [hasRun, setHasRun] = useState(false);
    const [strategyResult, setStrategyResult] = useState(EMPTY_RESULT);
    const [tradeSetups, setTradeSetups] = useState([]);
    const [highlightedSetupId, setHighlightedSetupId] = useState("");
    const [templateParams, setTemplateParams] = useState(DEFAULT_TEMPLATE_PARAMS);
    const [buyRules, setBuyRules] = useState([createRule({ indicator: "rsi", operator: "<", value: "30" })]);
    const [sellRules, setSellRules] = useState([createRule({ indicator: "rsi", operator: ">", value: "70" })]);
    const [pineScript, setPineScript] = useState(DEFAULT_PINE_SCRIPT);

    const metrics = useMemo(() => buildMetrics(strategyResult), [strategyResult]);
    const replayCandles = Array.isArray(strategyResult.candles) ? strategyResult.candles : [];
    const activeTradeSetup = useMemo(
        () => tradeSetups.find((setup) => setup.id === highlightedSetupId) || null,
        [highlightedSetupId, tradeSetups],
    );
    const totalSignalCount = (strategyResult.buySignals || []).length + (strategyResult.sellSignals || []).length;
    const chartKey = `${selectedAsset?.id || "dataset"}-${timeframe}-${replayCandles.length}-${strategyMode}-${strategyType}`;
    const setupChartKey = `${selectedAsset?.id || "dataset"}-${timeframe}-${replayCandles.length}-${strategyMode}-${strategyType}-setups`;
    const currentStrategyLabel = useMemo(() => labelForStrategyType(strategyType, strategyMode), [strategyMode, strategyType]);
    const configError = useMemo(
        () => validateConfig({ selectedAsset, strategyMode, strategyType, templateParams, buyRules, sellRules, pineScript }),
        [buyRules, pineScript, selectedAsset, sellRules, strategyMode, strategyType, templateParams],
    );
    const canRun = !running && !configError;

    const {
        cursor,
        isPlaying,
        speed,
        setSpeed,
        play,
        pause,
        step,
        reset,
        seek,
    } = useReplayEngine({
        candles: replayCandles,
        initialCursor: 0,
    });

    const currentReplayTime = replayCandles[cursor]?.time ?? null;
    const visibleBuySignals = useMemo(() => {
        if (!currentReplayTime) {
            return [];
        }
        return (strategyResult.buySignals || []).filter((signal) => Number(signal.time) <= currentReplayTime);
    }, [currentReplayTime, strategyResult.buySignals]);

    const visibleSellSignals = useMemo(() => {
        if (!currentReplayTime) {
            return [];
        }
        return (strategyResult.sellSignals || []).filter((signal) => Number(signal.time) <= currentReplayTime);
    }, [currentReplayTime, strategyResult.sellSignals]);

    function handleSelectTradeSetup(setup, options = {}) {
        if (!setup) {
            return;
        }

        setHighlightedSetupId(setup.id);
        if (options.syncReplay) {
            pause();
            seek(Math.max(Number(setup.index) || 0, 0));
        }
    }

    function applyResult(normalizedResult) {
        setStrategyResult(normalizedResult);
        setResults(normalizedResult);
        setHasRun(true);
        setHighlightedSetupId("");
        pause();
        reset(0);
    }

    async function executeStrategy(nextTimeframe = timeframe, switchToSetups = true, silent = false) {
        const validationMessage = validateConfig({
            selectedAsset,
            strategyMode,
            strategyType,
            templateParams,
            buyRules,
            sellRules,
            pineScript,
        });
        if (validationMessage) {
            setRunError(validationMessage);
            return;
        }

        setRunning(true);
        setRunError("");

        try {
            const data = await apiPost("/run-strategy", {
                symbol: selectedAsset.id,
                timeframe: nextTimeframe,
                config: buildConfig({
                    strategyMode,
                    strategyType,
                    templateParams,
                    buyRules,
                    sellRules,
                    pineScript,
                }),
            });

            const normalizedResult = normalizeResult(data);
            applyResult(normalizedResult);
            const nextTradeSetups = normalizeTradeSetups(data?.trade_setups, normalizedResult.candles, normalizedResult);
            setTradeSetups(nextTradeSetups);
            setHighlightedSetupId("");

            if (switchToSetups) {
                setActiveTab("Setups");
            }

            if (!silent && normalizedResult.candles.length === 0) {
                setRunError("Strategy completed, but no candles were returned.");
            }
        } catch (error) {
            const message = isServerUnavailableError(error)
                ? getConnectivityMessage()
                : getApiErrorMessage(error, "Strategy evaluation failed.");
            setRunError(message);
        } finally {
            setRunning(false);
        }
    }

    function handleDatasetChange(asset) {
        setSelectedAsset(asset);
        setRunError("");
        setHasRun(false);
        setStrategyResult(EMPTY_RESULT);
        setResults(EMPTY_RESULT);
        setTradeSetups([]);
        setHighlightedSetupId("");
        setActiveTab("Build Strategy");
        pause();
        reset(0);
    }

    function handleTimeframeChange(nextTimeframe) {
        setTimeframe(nextTimeframe);
        pause();
        reset(0);
        if (hasRun && selectedAsset) {
            void executeStrategy(nextTimeframe, false, true);
        }
    }

    function updateTemplateParam(key, value) {
        setTemplateParams((current) => ({
            ...current,
            [key]: value,
        }));
    }

    return (
        <PageTransition className="min-h-screen bg-[#0a0a0a] p-6 text-[#e5e5e5]">
            <div className="min-h-[calc(100vh-3rem)] overflow-hidden rounded-[20px] border border-[#1f1f1f] bg-[#0a0a0a] shadow-[0_24px_80px_rgba(0,0,0,0.45)]">
                <header className="border-b border-[#1f1f1f] px-6 py-5">
                    <div className="flex flex-wrap items-end justify-between gap-5">
                        <div className="space-y-2">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8a8a8a]">Strategy Lab</p>
                            <h1 className="text-3xl font-semibold tracking-tight text-[#e5e5e5]">Quant Research Terminal</h1>
                            <p className="max-w-2xl text-sm leading-6 text-[#8a8a8a]">
                                Run backend-evaluated strategies, inspect indexed signals instantly, and keep chart interaction focused on setup analysis.
                            </p>
                        </div>
                        <nav className="rounded-xl border border-[#1f1f1f] bg-[#111111] p-1.5">
                            <div className="flex flex-wrap gap-1.5">
                                {WORKFLOW_TABS.map((tab) => (
                                    <TabButton
                                        key={tab}
                                        active={activeTab === tab}
                                        onClick={() => setActiveTab(tab)}
                                    >
                                        {tab}
                                    </TabButton>
                                ))}
                            </div>
                        </nav>
                    </div>
                </header>

                <div className="min-h-[calc(100vh-11rem)] bg-[#0a0a0a]">
                    {activeTab === "Build Strategy" && (
                        <div className="grid min-h-[calc(100vh-11rem)] grid-cols-[390px_minmax(0,1fr)]">
                            <aside className="border-r border-[#1f1f1f] bg-[#111111] p-6">
                                <div className="space-y-5">
                                    <SectionLabel>CSV Upload</SectionLabel>
                                    <DatasetUploader
                                        onUploadSuccess={handleDatasetChange}
                                        appearance="monochrome"
                                        showSuccessToast={false}
                                    />

                                    <Panel title="Strategy Type">
                                        <div className="grid gap-2">
                                            {STRATEGY_TYPE_TABS.map((tab) => (
                                                <button
                                                    key={tab.id}
                                                    type="button"
                                                    onClick={() => setStrategyMode(tab.id)}
                                                    className={`rounded-2xl border px-4 py-3 text-left text-sm transition ${
                                                        strategyMode === tab.id
                                                            ? "border-[#e5e5e5] bg-[#e5e5e5] text-[#0a0a0a]"
                                                            : "border-[#1f1f1f] bg-[#111111] text-[#8a8a8a] hover:border-[#e5e5e5]/25 hover:text-[#e5e5e5]"
                                                    }`}
                                                >
                                                    {tab.label}
                                                </button>
                                            ))}
                                        </div>
                                    </Panel>

                                    {strategyMode === "template" && (
                                        <TemplateStrategyPanel
                                            strategyType={strategyType}
                                            templateParams={templateParams}
                                            onStrategyTypeChange={setStrategyType}
                                            onParamChange={updateTemplateParam}
                                        />
                                    )}

                                    {strategyMode === "rules" && (
                                        <RuleBuilderPanel
                                            buyRules={buyRules}
                                            sellRules={sellRules}
                                            onBuyRulesChange={setBuyRules}
                                            onSellRulesChange={setSellRules}
                                        />
                                    )}

                                    {strategyMode === "pine" && (
                                        <PineScriptPanel
                                            pineScript={pineScript}
                                            onPineScriptChange={setPineScript}
                                        />
                                    )}

                                    <button
                                        type="button"
                                        onClick={() => void executeStrategy(timeframe, true, false)}
                                        disabled={!canRun}
                                        className={`w-full rounded-2xl border px-4 py-3 text-sm font-semibold transition ${
                                            canRun
                                                ? "border-[#e5e5e5] bg-[#e5e5e5] text-[#0a0a0a] hover:bg-[#e5e5e5]/90"
                                                : "cursor-not-allowed border-[#1f1f1f] bg-[#111111] text-[#8a8a8a]/60"
                                        }`}
                                    >
                                        {running ? "Running Strategy..." : "Run Strategy"}
                                    </button>

                                    {runError && (
                                        <StatusMessageCard
                                            title="Strategy evaluation unavailable"
                                            description={runError}
                                            actionLabel={canRun ? "Retry Run" : ""}
                                            onAction={canRun ? (() => void executeStrategy(timeframe, true, false)) : undefined}
                                            tone="neutral"
                                        />
                                    )}
                                </div>
                            </aside>

                            <main className="p-6">
                                <div className="grid h-full gap-6 xl:grid-cols-[minmax(0,1.15fr)_360px]">
                                    <div className="grid gap-6 md:grid-cols-2">
                                        <Panel title="Workflow">
                                            <p className="text-sm leading-7 text-[#8a8a8a]">
                                                CSV upload feeds normalized candles into the selected strategy mode. Backend evaluation returns candles, BUY and SELL signals, trades, and metrics for the replay and results tabs.
                                            </p>
                                        </Panel>
                                        <Panel title="Current Dataset">
                                            <DataRow label="Dataset" value={selectedAsset?.symbol || "Not loaded"} />
                                            <DataRow label="Rows" value={selectedAsset?.rows ? `${selectedAsset.rows}` : "0"} />
                                            <DataRow label="Timeframe" value={timeframe} />
                                        </Panel>
                                        <Panel title="Current Strategy">
                                            <DataRow label="Mode" value={labelForStrategyMode(strategyMode)} />
                                            <DataRow label="Strategy" value={labelForStrategyType(strategyType, strategyMode)} />
                                            <DataRow label="Status" value={hasRun ? "Evaluated" : "Waiting to run"} />
                                        </Panel>
                                        <Panel title="Run Readiness">
                                            <p className="text-sm leading-7 text-[#8a8a8a]">
                                                {configError || "Configuration is valid. Run the strategy to populate Chart Replay and Results & Metrics."}
                                            </p>
                                        </Panel>
                                    </div>

                                    <div className="space-y-6">
                                        <Panel title="Latest Evaluation">
                                            <OverviewStat label="Strategy" value={currentStrategyLabel} />
                                            <OverviewStat label="Detected Setups" value={`${tradeSetups.length}`} />
                                            <OverviewStat label="Signals" value={`${(strategyResult.buySignals || []).length + (strategyResult.sellSignals || []).length}`} />
                                            <OverviewStat label="Trades" value={`${strategyResult.trades?.length || 0}`} />
                                            <OverviewStat label="Net Profit" value={formatPercent(strategyResult.metrics?.total_return || 0)} />
                                        </Panel>
                                        <Panel title="Pine Script Support">
                                            <p className="text-sm leading-7 text-[#8a8a8a]">
                                                Supported Pine subset: <span className="font-mono text-[#e5e5e5]">input.int</span>, <span className="font-mono text-[#e5e5e5]">input.float</span>, <span className="font-mono text-[#e5e5e5]">ta.sma</span>, <span className="font-mono text-[#e5e5e5]">ta.ema</span>, <span className="font-mono text-[#e5e5e5]">ta.rsi</span>, <span className="font-mono text-[#e5e5e5]">ta.crossover</span>, <span className="font-mono text-[#e5e5e5]">ta.crossunder</span>, <span className="font-mono text-[#e5e5e5]">strategy.entry</span>, and <span className="font-mono text-[#e5e5e5]">strategy.close</span>.
                                            </p>
                                        </Panel>
                                    </div>
                                </div>
                            </main>
                        </div>
                    )}

                    {activeTab === "Chart Replay" && (
                        <div className="grid min-h-[calc(100vh-11rem)] grid-cols-[300px_minmax(0,1fr)]">
                            <aside className="border-r border-[#1f1f1f] bg-[#111111] p-6">
                                <div className="space-y-5">
                                    <TradeSetupListPanel
                                        setups={tradeSetups}
                                        activeSetupId={highlightedSetupId}
                                        running={running}
                                        emptyMessage={hasRun ? "No trade setups were detected for the current strategy." : "Run the strategy to generate trade setups from BUY and SELL signals."}
                                        onSelect={(setup) => handleSelectTradeSetup(setup, { syncReplay: true })}
                                    />

                                    <Panel title="Timeframe">
                                        <div className="grid grid-cols-3 gap-2">
                                            {TIMEFRAME_OPTIONS.map((option) => (
                                                <button
                                                    key={option}
                                                    type="button"
                                                    onClick={() => handleTimeframeChange(option)}
                                                    className={`rounded-xl border px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] transition ${
                                                        timeframe === option
                                                            ? "border-[#e5e5e5] bg-[#e5e5e5] text-[#0a0a0a]"
                                                            : "border-[#1f1f1f] bg-[#0a0a0a] text-[#8a8a8a] hover:border-[#e5e5e5]/20 hover:text-[#e5e5e5]"
                                                    }`}
                                                >
                                                    {option}
                                                </button>
                                            ))}
                                        </div>
                                    </Panel>

                                    <ReplayControls
                                        isPlaying={isPlaying}
                                        speed={speed}
                                        cursor={cursor}
                                        totalCandles={replayCandles.length}
                                        canStep={replayCandles.length > 0 && cursor < replayCandles.length - 1}
                                        onPlay={play}
                                        onPause={pause}
                                        onStep={step}
                                        onReset={() => reset(0)}
                                        onSpeedChange={setSpeed}
                                        appearance="monochrome"
                                    />

                                    <Panel title="Replay Status">
                                        <DataRow label="Dataset" value={selectedAsset?.symbol || "Not loaded"} />
                                        <DataRow label="Strategy" value={currentStrategyLabel} />
                                        <DataRow label="Selected Setup" value={activeTradeSetup ? `${activeTradeSetup.type} ${formatSetupTimestamp(activeTradeSetup.timestamp)}` : "None"} />
                                        <DataRow label="Signals" value={`${totalSignalCount}`} />
                                        <DataRow
                                            label="Visible Candle"
                                            value={replayCandles.length ? `${Math.min(cursor + 1, replayCandles.length)} / ${replayCandles.length}` : "0 / 0"}
                                        />
                                    </Panel>
                                </div>
                            </aside>

                            <main className="flex min-h-0 flex-col p-6">
                                <div className="mb-5">
                                    <h2 className="text-2xl font-semibold tracking-tight text-[#e5e5e5]">Chart Replay</h2>
                                    <p className="mt-2 max-w-2xl text-sm leading-6 text-[#8a8a8a]">
                                        Replay the evaluated candles, inspect the generated BUY and SELL markers, and step through the strategy one candle at a time.
                                    </p>
                                </div>

                                <div className="min-h-0 flex-1 overflow-hidden rounded-[12px] border border-[#1f1f1f] bg-[#0a0a0a]">
                                    {replayCandles.length > 0 ? (
                                        <ReplayChart
                                            datasetKey={chartKey}
                                            candles={replayCandles}
                                            cursor={cursor}
                                            buySignals={visibleBuySignals}
                                            sellSignals={visibleSellSignals}
                                            completedTrades={[]}
                                            highlightedSetup={activeTradeSetup}
                                            palette={CHART_PALETTE}
                                        />
                                    ) : (
                                        <div className="flex h-full items-center justify-center p-8">
                                            <StatusMessageCard
                                                title="Chart not ready"
                                                description="Run a strategy first. The evaluated candles and markers will appear here after the backend returns results."
                                                tone="neutral"
                                                className="w-full max-w-lg"
                                            />
                                        </div>
                                    )}
                                </div>
                            </main>
                        </div>
                    )}

                    {activeTab === "Setups" && (
                        <div className="flex min-h-[calc(100vh-11rem)] flex-col gap-6 p-6">
                            <div className="grid gap-4 xl:grid-cols-3">
                                <OverviewStat label="Dataset" value={selectedAsset?.symbol || "Not loaded"} />
                                <OverviewStat
                                    label="Selected Setup"
                                    value={activeTradeSetup ? `${activeTradeSetup.type} #${activeTradeSetup.index + 1}` : "None"}
                                    detail={activeTradeSetup ? formatSetupTimestamp(activeTradeSetup.timestamp) : "Select a setup from the list"}
                                />
                                <OverviewStat
                                    label="Signals Count"
                                    value={`${totalSignalCount}`}
                                    detail={`BUY ${(strategyResult.buySignals || []).length} · SELL ${(strategyResult.sellSignals || []).length}`}
                                />
                            </div>

                            <div className="grid min-h-0 flex-1 gap-6 xl:grid-cols-[360px_minmax(0,1fr)]">
                                <div className="min-h-0">
                                    <TradeSetupListPanel
                                        setups={tradeSetups}
                                        activeSetupId={highlightedSetupId}
                                        running={running}
                                        emptyMessage={hasRun ? "No setups were detected for the current strategy." : "Run the strategy to populate detected trade setups."}
                                        onSelect={handleSelectTradeSetup}
                                    />
                                </div>

                                <section className={`${GLASS_PANEL_CLASS} flex min-h-[540px] min-w-0 flex-col overflow-hidden`}>
                                    <div className="flex items-center justify-between gap-4 border-b border-[#1f1f1f] px-5 py-4">
                                        <SectionLabel>Signal Inspection</SectionLabel>
                                        <span className="rounded-full border border-[#1f1f1f] bg-[#111111] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#e5e5e5]">
                                            {activeTradeSetup ? `${activeTradeSetup.type} · #${activeTradeSetup.index + 1}` : "Awaiting Selection"}
                                        </span>
                                    </div>

                                    <div className="min-h-0 flex-1 p-4">
                                        {replayCandles.length > 0 ? (
                                            <ReplayChart
                                                datasetKey={setupChartKey}
                                                candles={replayCandles}
                                                cursor={replayCandles.length - 1}
                                                buySignals={strategyResult.buySignals || []}
                                                sellSignals={strategyResult.sellSignals || []}
                                                completedTrades={[]}
                                                highlightedSetup={activeTradeSetup}
                                                palette={SETUPS_CHART_PALETTE}
                                                mode="inspect"
                                                centerOnIndex={activeTradeSetup?.index ?? null}
                                            />
                                        ) : (
                                            <div className="flex h-full items-center justify-center">
                                                <StatusMessageCard
                                                    title="Chart not ready"
                                                    description="Run a strategy first. The detected setup signals will appear here once the backend returns candles."
                                                    tone="neutral"
                                                    className="w-full max-w-lg"
                                                />
                                            </div>
                                        )}
                                    </div>
                                </section>
                            </div>
                        </div>
                    )}

                    {activeTab === "Results & Metrics" && (
                        <div className="p-6">
                            {hasRun ? (
                                <div className="space-y-6">
                                    <div className="space-y-2">
                                        <h2 className="text-2xl font-semibold tracking-tight text-[#e5e5e5]">Results & Metrics</h2>
                                        <p className="text-sm leading-6 text-[#8a8a8a]">
                                            Review total trades, win rate, profit factor, drawdown, and the equity path generated by the selected strategy mode.
                                        </p>
                                    </div>

                                    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                                        {metrics.map((metric) => (
                                            <MetricCard key={metric.label} label={metric.label} value={metric.value} />
                                        ))}
                                    </div>

                                    <div className="grid gap-6 xl:grid-cols-2">
                                        <ChartPanel title="Equity Curve">
                                            <EquityChart trades={strategyResult.trades} palette={METRIC_CHART_PALETTE} />
                                        </ChartPanel>
                                        <ChartPanel title="Drawdown Chart">
                                            <DrawdownChart trades={strategyResult.trades} palette={DRAWDOWN_PALETTE} />
                                        </ChartPanel>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex min-h-[calc(100vh-16rem)] items-center justify-center">
                                    <StatusMessageCard
                                        title="Results not available"
                                        description="Run a strategy to populate performance metrics, the equity curve, and the drawdown chart."
                                        tone="neutral"
                                        className="w-full max-w-xl"
                                    />
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </PageTransition>
    );
}

function validateConfig({ selectedAsset, strategyMode, strategyType, templateParams, buyRules, sellRules, pineScript }) {
    if (!selectedAsset) {
        return "Upload a CSV dataset before running the strategy.";
    }

    if (strategyMode === "template") {
        if (strategyType === "ma_crossover") {
            if (Number(templateParams.fast_period) <= 0 || Number(templateParams.slow_period) <= 0) {
                return "Fast and slow MA periods must be positive integers.";
            }
            if (Number(templateParams.fast_period) >= Number(templateParams.slow_period)) {
                return "Fast MA period must be smaller than slow MA period.";
            }
            if (!["EMA", "SMA"].includes(String(templateParams.ma_type || "").toUpperCase())) {
                return "MA type must be EMA or SMA.";
            }
        }

        if (strategyType === "rsi_reversal") {
            if (Number(templateParams.rsi_length) <= 0) {
                return "RSI length must be a positive integer.";
            }
            if (Number(templateParams.oversold) >= Number(templateParams.overbought)) {
                return "Oversold level must be smaller than overbought level.";
            }
        }

        if (strategyType === "mean_reversion") {
            if (Number(templateParams.lookback_period) <= 1) {
                return "Lookback period must be greater than 1.";
            }
            if (Number(templateParams.deviation_threshold) <= 0) {
                return "Deviation threshold must be greater than 0.";
            }
        }

        if (strategyType === "breakout") {
            if (Number(templateParams.lookback_period) <= 1) {
                return "Lookback period must be greater than 1.";
            }
            if (Number(templateParams.breakout_threshold) < 0) {
                return "Breakout threshold must be zero or greater.";
            }
        }
    }

    if (strategyMode === "rules") {
        const normalizedBuy = sanitizeRules(buyRules);
        const normalizedSell = sanitizeRules(sellRules);
        if (normalizedBuy.length === 0 && normalizedSell.length === 0) {
            return "Add at least one BUY or SELL rule.";
        }
        const invalidRule = [...buyRules, ...sellRules].find((rule) => !rule.indicator || !rule.operator || `${rule.value ?? ""}`.trim() === "");
        if (invalidRule) {
            return "Every rule needs an indicator, operator, and value.";
        }
    }

    if (strategyMode === "pine" && !pineScript.trim()) {
        return "Paste a Pine Script strategy before running.";
    }

    return "";
}

function buildConfig({ strategyMode, strategyType, templateParams, buyRules, sellRules, pineScript }) {
    if (strategyMode === "template") {
        if (strategyType === "ma_crossover") {
            return {
                mode: "template",
                strategy: "ma_crossover",
                parameters: {
                    fast_period: Number(templateParams.fast_period),
                    slow_period: Number(templateParams.slow_period),
                    ma_type: String(templateParams.ma_type || "EMA").toUpperCase(),
                },
            };
        }

        if (strategyType === "rsi_reversal") {
            return {
                mode: "template",
                strategy: "rsi_reversal",
                parameters: {
                    rsi_length: Number(templateParams.rsi_length),
                    oversold: Number(templateParams.oversold),
                    overbought: Number(templateParams.overbought),
                },
            };
        }

        if (strategyType === "breakout") {
            return {
                mode: "template",
                strategy: "breakout",
                parameters: {
                    lookback_period: Number(templateParams.lookback_period),
                    breakout_threshold: Number(templateParams.breakout_threshold),
                },
            };
        }

        return {
            mode: "template",
            strategy: "mean_reversion",
            parameters: {
                lookback_period: Number(templateParams.lookback_period),
                deviation_threshold: Number(templateParams.deviation_threshold),
            },
        };
    }

    if (strategyMode === "rules") {
        return {
            mode: "rules",
            buy_rules: sanitizeRules(buyRules).map(normalizeRule),
            sell_rules: sanitizeRules(sellRules).map(normalizeRule),
        };
    }

    return {
        mode: "pine",
        pine_script: pineScript,
    };
}

function sanitizeRules(rules) {
    return (Array.isArray(rules) ? rules : []).filter(
        (rule) => rule && rule.indicator && rule.operator && `${rule.value ?? ""}`.trim() !== "",
    );
}

function labelForStrategyMode(mode) {
    if (mode === "rules") {
        return "Visual Rule Builder";
    }
    if (mode === "pine") {
        return "Pine Script Strategy";
    }
    return "Template Strategy";
}

function labelForStrategyType(strategyType, strategyMode) {
    if (strategyMode !== "template") {
        return labelForStrategyMode(strategyMode);
    }
    const match = TEMPLATE_STRATEGIES.find((strategy) => strategy.id === strategyType);
    return match ? match.label : "Moving Average Crossover";
}

function TabButton({ active, children, onClick }) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`rounded-xl px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] transition ${
                active
                    ? "bg-[#e5e5e5] text-[#0a0a0a]"
                    : "text-[#8a8a8a] hover:bg-[#111111] hover:text-[#e5e5e5]"
            }`}
        >
            {children}
        </button>
    );
}

function SectionLabel({ children }) {
    return <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8a8a8a]">{children}</p>;
}

function Panel({ title, children, className = "", bodyClassName = "" }) {
    return (
        <section className={`${GLASS_PANEL_CLASS} p-5 ${className}`.trim()}>
            <SectionLabel>{title}</SectionLabel>
            <div className={`mt-4 space-y-3 ${bodyClassName}`.trim()}>{children}</div>
        </section>
    );
}

function Field({ label, children, hint = "" }) {
    return (
        <label className="block space-y-2">
            <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8a8a8a]">{label}</span>
            {children}
            {hint ? <p className="text-xs leading-5 text-[#8a8a8a]">{hint}</p> : null}
        </label>
    );
}

function Input(props) {
    return (
        <input
            {...props}
            className={`w-full rounded-xl border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2.5 text-sm text-[#e5e5e5] outline-none transition placeholder:text-[#8a8a8a] focus:border-[#e5e5e5]/30 ${props.className || ""}`}
        />
    );
}

function Select(props) {
    return (
        <select
            {...props}
            className={`w-full rounded-xl border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2.5 text-sm text-[#e5e5e5] outline-none transition focus:border-[#e5e5e5]/30 ${props.className || ""}`}
        />
    );
}

function DataRow({ label, value }) {
    return (
        <div className="flex items-center justify-between gap-4 text-sm">
            <span className="text-[#8a8a8a]">{label}</span>
            <span className="text-right font-medium text-[#e5e5e5]">{value}</span>
        </div>
    );
}

function OverviewStat({ label, value, detail = "" }) {
    return (
        <div className={`${GLASS_PANEL_CLASS} px-4 py-3`}>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8a8a8a]">{label}</p>
            <p className="mt-2 text-xl font-semibold text-[#e5e5e5]">{value}</p>
            {detail ? <p className="mt-1 text-xs text-[#8a8a8a]">{detail}</p> : null}
        </div>
    );
}

function MetricCard({ label, value }) {
    return (
        <div className={`${GLASS_PANEL_CLASS} p-5`}>
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a8a8a]">{label}</p>
            <p className="mt-4 text-3xl font-semibold tracking-tight text-[#e5e5e5]">{value}</p>
        </div>
    );
}

function ChartPanel({ title, children }) {
    return (
        <section className={`${GLASS_PANEL_CLASS} overflow-hidden`}>
            <div className="border-b border-[#1f1f1f] px-5 py-4">
                <SectionLabel>{title}</SectionLabel>
            </div>
            <div className="h-[340px] p-4">{children}</div>
        </section>
    );
}

function useMeasuredHeight() {
    const containerRef = useRef(null);
    const [height, setHeight] = useState(0);

    useEffect(() => {
        if (!containerRef.current) {
            return undefined;
        }

        const node = containerRef.current;
        const resizeObserver = new ResizeObserver(() => {
            setHeight(node.clientHeight);
        });

        setHeight(node.clientHeight);
        resizeObserver.observe(node);

        return () => resizeObserver.disconnect();
    }, []);

    return [containerRef, height];
}

function SetupListRow({ index, style, data }) {
    const { setups, activeSetupId, running, onSelect } = data;
    const setup = setups[index];

    if (!setup) {
        return null;
    }

    const isActive = activeSetupId === setup.id;

    return (
        <div style={{ ...style, paddingBottom: 8 }}>
            <button
                type="button"
                onClick={() => onSelect(setup)}
                disabled={running}
                className={`w-full rounded-xl border px-4 py-3 text-left transition disabled:cursor-not-allowed disabled:opacity-55 ${
                    isActive
                        ? "border-[#e5e5e5] bg-[#e5e5e5] text-[#0a0a0a] shadow-[0_16px_40px_rgba(255,255,255,0.08)]"
                        : "border-[#1f1f1f] bg-[#111111] text-[#e5e5e5] hover:border-[#e5e5e5]/20 hover:bg-[#161616]"
                }`}
            >
                <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold">{setup.type}</p>
                    <span className={`text-[10px] font-semibold uppercase tracking-[0.18em] ${isActive ? "text-[#0a0a0a]/60" : "text-[#8a8a8a]"}`}>
                        #{Number(setup.index) + 1}
                    </span>
                </div>
                <p className={`mt-2 text-sm ${isActive ? "text-[#0a0a0a]/80" : "text-[#8a8a8a]"}`}>
                    {formatSetupTimestamp(setup.timestamp)}
                </p>
                <p className={`mt-1 text-[11px] uppercase tracking-[0.16em] ${isActive ? "text-[#0a0a0a]/60" : "text-[#8a8a8a]"}`}>
                    price {Number(setup.price || 0).toFixed(4)} · index {Number(setup.index)}
                </p>
            </button>
        </div>
    );
}

function TradeSetupListPanel({ setups, activeSetupId, running, emptyMessage, onSelect }) {
    const normalizedSetups = Array.isArray(setups) ? setups : [];
    const [listRef, listHeight] = useMeasuredHeight();
    const listData = useMemo(
        () => ({
            setups: normalizedSetups,
            activeSetupId,
            running,
            onSelect,
        }),
        [activeSetupId, normalizedSetups, onSelect, running],
    );

    return (
        <Panel title="Detected Setups" className="flex h-full min-h-0 flex-col" bodyClassName="flex min-h-0 flex-1 flex-col gap-3">
            <div className="flex items-center justify-between gap-3">
                <span className="text-xs text-[#8a8a8a]">{normalizedSetups.length} signals</span>
                <span className="rounded-full border border-[#1f1f1f] bg-[#111111] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#8a8a8a]">
                    Indexed
                </span>
            </div>

            {normalizedSetups.length === 0 ? (
                <StatusMessageCard
                    title="No setups detected"
                    description={emptyMessage}
                    tone="neutral"
                />
            ) : null}

            <div ref={listRef} className="min-h-0 flex-1">
                {listHeight > 0 && normalizedSetups.length > 0 ? (
                    <FixedSizeList
                        height={listHeight}
                        width="100%"
                        itemCount={normalizedSetups.length}
                        itemSize={SETUP_LIST_ROW_HEIGHT}
                        itemData={listData}
                    >
                        {SetupListRow}
                    </FixedSizeList>
                ) : null}
            </div>
        </Panel>
    );
}

function TemplateStrategyPanel({
    strategyType,
    templateParams,
    onStrategyTypeChange,
    onParamChange,
}) {
    const schema = TEMPLATE_PARAMETER_SCHEMAS[strategyType] || TEMPLATE_PARAMETER_SCHEMAS.ma_crossover;

    return (
        <Panel title="Strategy Parameters">
            <Field label="Strategy Selector">
                <Select value={strategyType} onChange={(event) => onStrategyTypeChange(event.target.value)}>
                    {TEMPLATE_STRATEGIES.map((strategy) => (
                        <option key={strategy.id} value={strategy.id}>
                            {strategy.label}
                        </option>
                    ))}
                </Select>
            </Field>

            <div className={`grid gap-3 ${schema.columns}`}>
                {schema.fields.map((field) => (
                    <Field key={field.key} label={field.label} hint={field.hint || ""}>
                        {field.type === "select" ? (
                            <Select
                                value={templateParams[field.key]}
                                onChange={(event) => onParamChange(field.key, event.target.value)}
                            >
                                {field.options.map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </Select>
                        ) : (
                            <Input
                                type="number"
                                min={field.min}
                                step={field.step}
                                value={templateParams[field.key]}
                                onChange={(event) => onParamChange(field.key, coerceParameterValue(field, event.target.value))}
                            />
                        )}
                    </Field>
                ))}
            </div>
        </Panel>
    );
}

function RuleBuilderPanel({ buyRules, sellRules, onBuyRulesChange, onSellRulesChange }) {
    return (
        <Panel title="Strategy Parameters">
            <p className="text-sm leading-6 text-[#8a8a8a]">
                Build a custom rule set by stacking indicator conditions. Rules in the same block are combined with AND logic.
            </p>

            <RuleSection
                title="BUY Rules"
                rules={buyRules}
                onChange={onBuyRulesChange}
                defaultRule={{ indicator: "rsi", operator: "<", value: "30" }}
            />

            <RuleSection
                title="SELL Rules"
                rules={sellRules}
                onChange={onSellRulesChange}
                defaultRule={{ indicator: "rsi", operator: ">", value: "70" }}
            />
        </Panel>
    );
}

function RuleSection({ title, rules, onChange, defaultRule }) {
    function updateRule(id, key, value) {
        onChange((current) => current.map((rule) => (rule.id === id ? { ...rule, [key]: value } : rule)));
    }

    function addRule() {
        onChange((current) => [...current, createRule(defaultRule)]);
    }

    function removeRule(id) {
        onChange((current) => current.filter((rule) => rule.id !== id));
    }

    return (
        <div className="space-y-3 rounded-xl border border-[#1f1f1f] bg-[#0a0a0a] p-4">
            <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-[#e5e5e5]">{title}</p>
                <button
                    type="button"
                    onClick={addRule}
                    className="rounded-xl border border-[#1f1f1f] bg-[#111111] px-3 py-2 text-xs font-semibold text-[#e5e5e5] transition hover:border-[#e5e5e5]/25"
                >
                    Add Rule
                </button>
            </div>

            <div className="space-y-3">
                {rules.map((rule) => (
                    <div key={rule.id} className="grid gap-2 rounded-xl border border-[#1f1f1f] bg-[#111111] p-3 sm:grid-cols-[1.1fr_110px_1fr_88px]">
                        <Select value={rule.indicator} onChange={(event) => updateRule(rule.id, "indicator", event.target.value)}>
                            {RULE_INDICATORS.map((indicator) => (
                                <option key={indicator} value={indicator}>
                                    {indicator}
                                </option>
                            ))}
                        </Select>
                        <Select value={rule.operator} onChange={(event) => updateRule(rule.id, "operator", event.target.value)}>
                            {OPERATORS.map((operator) => (
                                <option key={operator} value={operator}>
                                    {operator}
                                </option>
                            ))}
                        </Select>
                        <Input
                            value={rule.value}
                            onChange={(event) => updateRule(rule.id, "value", event.target.value)}
                            placeholder="30 or sma50"
                        />
                        <button
                            type="button"
                            onClick={() => removeRule(rule.id)}
                            className="rounded-xl border border-[#1f1f1f] bg-[#0a0a0a] px-3 py-2 text-xs font-semibold text-[#8a8a8a] transition hover:border-[#e5e5e5]/25 hover:text-[#e5e5e5]"
                        >
                            Remove
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}

function PineScriptPanel({ pineScript, onPineScriptChange }) {
    return (
        <Panel title="Strategy Parameters">
            <p className="text-sm leading-6 text-[#8a8a8a]">
                Paste a Pine Script strategy. The backend parses supported Pine syntax and returns BUY and SELL signals from the uploaded dataset.
            </p>
            <div className="overflow-hidden rounded-[12px] border border-[#1f1f1f] bg-[#0a0a0a]">
                <div className="border-b border-[#1f1f1f] px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a8a8a]">
                    Pine Script Editor
                </div>
                <textarea
                    value={pineScript}
                    onChange={(event) => onPineScriptChange(event.target.value)}
                    spellCheck="false"
                    className="min-h-[300px] w-full resize-none bg-[#0a0a0a] px-4 py-4 font-mono text-[13px] leading-7 text-[#e5e5e5] outline-none placeholder:text-[#8a8a8a]"
                    placeholder="// Paste Pine Script here"
                />
            </div>
        </Panel>
    );
}
