/**
 * TradingChart.jsx
 * ----------------
 * Standalone professional chart component with:
 *   - Broker / Symbol / Timeframe toolbar
 *   - Lightweight Charts candlestick + volume
 *   - Fetches market or dataset candles on demand
 *   - Timeframes: 1m 5m 15m 30m 1h 4h 1d
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";

import StatusMessageCard from "../ui/StatusMessageCard";
import { apiGet, buildApiErrorState } from "../../lib/api";
import { normalizeCandles, normalizeSignal } from "../../lib/candleData";

const TIMEFRAMES = [
    { label: "1m", value: "1m" },
    { label: "5m", value: "5m" },
    { label: "15m", value: "15m" },
    { label: "30m", value: "30m" },
    { label: "1h", value: "1h" },
    { label: "4h", value: "4h" },
    { label: "1d", value: "1d" },
];

const VALID_BROKERS = ["oanda", "dukascopy", "fxcm", "binance", "coinbase", "yahoo", "local"];

export default function TradingChart({
    broker = "oanda",
    symbol = "",
    candles: overrideCandles = null,
    buySignals = [],
    sellSignals = [],
    showToolbar = true,
}) {
    const containerRef = useRef(null);
    const chartRef = useRef(null);

    const [activeTimeframe, setActiveTimeframe] = useState("1h");
    const [candles, setCandles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [errorState, setErrorState] = useState(null);

    const fetchCandles = useCallback(async (timeframe) => {
        if (!symbol || !symbol.trim()) {
            return;
        }

        if (!broker || !broker.trim()) {
            setErrorState({
                title: "Dataset not loaded",
                description: "Missing broker. Select a data source and retry.",
            });
            return;
        }

        if (!VALID_BROKERS.includes(broker.toLowerCase())) {
            setErrorState({
                title: "Dataset not loaded",
                description: `Invalid broker "${broker}".`,
            });
            console.error(`[TradingChart] broker prop received "${broker}" which is not valid.`);
            return;
        }

        setLoading(true);
        setErrorState(null);

        try {
            let rawData = [];
            if (broker.toLowerCase() === "local") {
                rawData = await apiGet(`/dataset/${symbol}/${timeframe}?limit=1000`, {
                    timeout: 30000,
                });
            } else {
                const params = new URLSearchParams({
                    broker: broker.toLowerCase(),
                    symbol: symbol.toUpperCase(),
                    timeframe,
                });
                rawData = await apiGet(`/market-data?${params.toString()}`, {
                    timeout: 30000,
                });
            }

            const rows = Array.isArray(rawData)
                ? rawData
                : Array.isArray(rawData?.candles)
                    ? rawData.candles
                    : [];
            const normalized = normalizeCandles(rows, "TradingChart fetch");

            if (rows.length > 0 && normalized.length === 0) {
                setCandles([]);
                setErrorState({
                    title: "Dataset not loaded",
                    description: "No valid candles were available for this chart view.",
                });
                return;
            }

            setCandles(normalized);
        } catch (error) {
            setCandles([]);
            setErrorState(buildApiErrorState(error, "Dataset not loaded", "Unable to load chart data."));
        } finally {
            setLoading(false);
        }
    }, [broker, symbol]);

    useEffect(() => {
        if (overrideCandles) {
            const normalized = normalizeCandles(overrideCandles, "TradingChart override");
            setCandles(normalized);
            setErrorState(
                overrideCandles.length > 0 && normalized.length === 0
                    ? { title: "Dataset not loaded", description: "Override dataset contains no valid candles." }
                    : null,
            );
            return;
        }

        void fetchCandles(activeTimeframe);
    }, [activeTimeframe, broker, fetchCandles, overrideCandles, symbol]);

    useEffect(() => {
        if (!containerRef.current) {
            return;
        }

        if (chartRef.current) {
            chartRef.current.remove();
            chartRef.current = null;
        }

        if (!Array.isArray(candles) || candles.length === 0) {
            return;
        }

        const bg = "#0a0a0a";
        const txt = "#888888";
        const grid = "rgba(255,255,255,0.03)";

        try {
            const chart = createChart(containerRef.current, {
                layout: { background: { type: "solid", color: bg }, textColor: txt, fontSize: 11 },
                crosshair: { mode: CrosshairMode.Normal },
                grid: { vertLines: { color: grid }, horzLines: { color: grid } },
                rightPriceScale: { borderColor: "rgba(255,255,255,0.04)" },
                timeScale: { borderColor: "rgba(255,255,255,0.04)", timeVisible: true, rightOffset: 5 },
                width: containerRef.current.clientWidth,
                height: containerRef.current.clientHeight || 400,
            });

            chartRef.current = chart;

            const candleSeries = chart.addCandlestickSeries({
                upColor: "#10b981",
                downColor: "#ef4444",
                borderUpColor: "#10b981",
                borderDownColor: "#ef4444",
                wickUpColor: "#10b981",
                wickDownColor: "#ef4444",
            });
            candleSeries.setData(candles);

            const volumeSeries = chart.addHistogramSeries({
                color: "rgba(16,185,129,0.2)",
                priceFormat: { type: "volume" },
                priceScaleId: "vol",
            });
            chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
            volumeSeries.setData(candles.map((candle) => ({
                time: candle.time,
                value: candle.volume,
                color: candle.close >= candle.open ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)",
            })));

            const markers = [];
            (buySignals || [])
                .map((signal) => normalizeSignal(signal))
                .filter(Boolean)
                .forEach((signal) => markers.push({ time: signal.time, position: "belowBar", color: "#10b981", shape: "arrowUp", text: "BUY" }));
            (sellSignals || [])
                .map((signal) => normalizeSignal(signal))
                .filter(Boolean)
                .forEach((signal) => markers.push({ time: signal.time, position: "aboveBar", color: "#ef4444", shape: "arrowDown", text: "SELL" }));
            if (markers.length > 0) {
                candleSeries.setMarkers(markers.sort((left, right) => left.time - right.time));
            }

            chart.timeScale().fitContent();

            const resizeObserver = new ResizeObserver(() => {
                if (containerRef.current && chartRef.current) {
                    chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
                }
            });
            resizeObserver.observe(containerRef.current);

            return () => {
                resizeObserver.disconnect();
                if (chartRef.current) {
                    chartRef.current.remove();
                    chartRef.current = null;
                }
            };
        } catch (error) {
            console.error("[TradingChart] Failed to render chart", error);
            setErrorState({
                title: "Dataset not loaded",
                description: "Chart rendering failed. Check the uploaded dataset values.",
            });
            return undefined;
        }
    }, [buySignals, candles, sellSignals]);

    const handleRetry = useCallback(() => {
        void fetchCandles(activeTimeframe);
    }, [activeTimeframe, fetchCandles]);

    return (
        <div className="flex h-full w-full flex-col bg-[#0a0a0a]">
            {showToolbar && (
                <div className="shrink-0 border-b border-white/5 bg-[#0d0d0d] px-4 py-2">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            {symbol ? (
                                <>
                                    <span className="text-sm font-bold text-white">{symbol}</span>
                                    <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-bold uppercase text-textSecondary">{broker}</span>
                                </>
                            ) : (
                                <span className="text-xs italic text-textSecondary">No asset selected</span>
                            )}
                            {loading && <span className="ml-2 animate-pulse text-[10px] text-emerald-400">Loading...</span>}
                        </div>

                        <div className="flex gap-1">
                            {TIMEFRAMES.map((timeframe) => (
                                <button
                                    key={timeframe.value}
                                    type="button"
                                    onClick={() => setActiveTimeframe(timeframe.value)}
                                    className={`rounded px-2.5 py-1 text-[10px] font-bold transition-all duration-150 ${
                                        activeTimeframe === timeframe.value
                                            ? "bg-emerald-500 text-black"
                                            : "text-textSecondary hover:bg-white/5 hover:text-textPrimary"
                                    }`}
                                >
                                    {timeframe.label}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            <div className="relative flex-1 min-h-0">
                {errorState && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center p-6">
                        <StatusMessageCard
                            title={errorState.title}
                            description={errorState.description}
                            actionLabel="Retry Load"
                            onAction={symbol ? handleRetry : undefined}
                            tone="error"
                            className="w-full max-w-sm"
                        />
                    </div>
                )}

                {!errorState && symbol && !loading && (!candles || candles.length === 0) && (
                    <div className="absolute inset-0 z-10 flex items-center justify-center p-6">
                        <StatusMessageCard
                            title="Dataset not loaded"
                            description="No valid dataset candles are available yet."
                            actionLabel="Retry Load"
                            onAction={handleRetry}
                            className="w-full max-w-sm"
                        />
                    </div>
                )}

                {!symbol && !errorState && (
                    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center text-textSecondary">
                        <svg className="mb-3 h-10 w-10 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                        </svg>
                        <p className="text-xs">Select a dataset to load chart data</p>
                    </div>
                )}

                <div ref={containerRef} className="absolute inset-0" />
            </div>
        </div>
    );
}
