import { memo, useEffect, useRef } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";

const DEFAULT_PALETTE = {
    background: "#081018",
    text: "#8CA3B8",
    grid: "rgba(140,163,184,0.08)",
    border: "rgba(140,163,184,0.12)",
    upCandle: "#16a34a",
    downCandle: "#dc2626",
    upVolume: "rgba(16,185,129,0.28)",
    downVolume: "rgba(239,68,68,0.28)",
    buyMarker: "#10b981",
    sellMarker: "#ef4444",
    exitBuyMarker: "#f59e0b",
    exitSellMarker: "#60a5fa",
    highlightMarker: "#ffffff",
};
const INSPECTION_WINDOW_SIZE = 72;

function getVolumePoint(candle, palette) {
    return {
        time: candle.time,
        value: candle.volume,
        color: candle.close >= candle.open ? palette.upVolume : palette.downVolume,
    };
}

function findCandleIndex(candles, timestamp) {
    const normalizedTimestamp = Number(timestamp);
    if (!Array.isArray(candles) || candles.length === 0 || !Number.isFinite(normalizedTimestamp)) {
        return -1;
    }

    let closestIndex = 0;
    let closestDistance = Math.abs(Number(candles[0]?.time) - normalizedTimestamp);

    for (let index = 1; index < candles.length; index += 1) {
        const nextDistance = Math.abs(Number(candles[index]?.time) - normalizedTimestamp);
        if (nextDistance < closestDistance) {
            closestDistance = nextDistance;
            closestIndex = index;
        }
    }

    return closestIndex;
}

function buildMarkers({ candles, buySignals, sellSignals, completedTrades, highlightedSetup, palette }) {
    const markers = [];
    const highlightedIndex = Number(highlightedSetup?.index);
    const highlightedType = String(highlightedSetup?.type || "").toUpperCase();

    buySignals.forEach((signal) => {
        const isHighlighted = highlightedType === "BUY" && highlightedIndex === findCandleIndex(candles, signal.time);
        markers.push({
            time: signal.time,
            position: "belowBar",
            color: isHighlighted ? palette.highlightMarker : palette.buyMarker,
            shape: "arrowUp",
            text: isHighlighted ? "ACTIVE BUY" : "BUY",
        });
        if (isHighlighted) {
            markers.push({
                time: signal.time,
                position: "inBar",
                color: palette.highlightMarker,
                shape: "circle",
                text: "SELECTED",
            });
        }
    });

    sellSignals.forEach((signal) => {
        const isHighlighted = highlightedType === "SELL" && highlightedIndex === findCandleIndex(candles, signal.time);
        markers.push({
            time: signal.time,
            position: "aboveBar",
            color: isHighlighted ? palette.highlightMarker : palette.sellMarker,
            shape: "arrowDown",
            text: isHighlighted ? "ACTIVE SELL" : "SELL",
        });
        if (isHighlighted) {
            markers.push({
                time: signal.time,
                position: "inBar",
                color: palette.highlightMarker,
                shape: "circle",
                text: "SELECTED",
            });
        }
    });

    completedTrades.forEach((trade) => {
        markers.push({
            time: trade.exit_time,
            position: trade.type === "BUY" ? "aboveBar" : "belowBar",
            color: trade.type === "BUY" ? palette.exitBuyMarker : palette.exitSellMarker,
            shape: "circle",
            text: "EXIT",
        });
    });

    return markers.sort((left, right) => left.time - right.time);
}

function buildInspectionRange(centerIndex, candleCount) {
    if (!Number.isFinite(centerIndex) || centerIndex < 0 || candleCount <= 0) {
        return null;
    }

    const windowSize = Math.min(INSPECTION_WINDOW_SIZE, candleCount);
    const maxStart = Math.max(candleCount - windowSize, 0);
    const start = Math.max(0, Math.min(centerIndex - Math.floor(windowSize / 2), maxStart));

    return {
        from: start,
        to: start + windowSize - 1,
    };
}

function ReplayChart({
    datasetKey,
    candles,
    cursor,
    buySignals,
    sellSignals,
    completedTrades,
    highlightedSetup = null,
    palette = DEFAULT_PALETTE,
    mode = "replay",
    centerOnIndex = null,
}) {
    const containerRef = useRef(null);
    const chartRef = useRef(null);
    const candleSeriesRef = useRef(null);
    const volumeSeriesRef = useRef(null);
    const resizeObserverRef = useRef(null);
    const renderedCursorRef = useRef(-1);
    const datasetKeyRef = useRef(null);

    useEffect(() => {
        if (!containerRef.current || chartRef.current) {
            return undefined;
        }

        const chart = createChart(containerRef.current, {
            layout: {
                background: { type: "solid", color: palette.background },
                textColor: palette.text,
                fontSize: 11,
            },
            crosshair: { mode: CrosshairMode.Normal },
            grid: {
                vertLines: { color: palette.grid },
                horzLines: { color: palette.grid },
            },
            rightPriceScale: { borderColor: palette.border },
            timeScale: {
                borderColor: palette.border,
                timeVisible: true,
                rightOffset: 8,
            },
            width: containerRef.current.clientWidth,
            height: containerRef.current.clientHeight || 520,
        });

        const candleSeries = chart.addCandlestickSeries({
            upColor: palette.upCandle,
            downColor: palette.downCandle,
            borderUpColor: palette.upCandle,
            borderDownColor: palette.downCandle,
            wickUpColor: palette.upCandle,
            wickDownColor: palette.downCandle,
        });

        const volumeSeries = chart.addHistogramSeries({
            color: palette.upVolume,
            priceFormat: { type: "volume" },
            priceScaleId: "volume",
        });

        chart.priceScale("volume").applyOptions({
            scaleMargins: { top: 0.82, bottom: 0 },
        });

        chartRef.current = chart;
        candleSeriesRef.current = candleSeries;
        volumeSeriesRef.current = volumeSeries;

        resizeObserverRef.current = new ResizeObserver(() => {
            if (!containerRef.current || !chartRef.current) {
                return;
            }

            chartRef.current.applyOptions({
                width: containerRef.current.clientWidth,
                height: containerRef.current.clientHeight || 520,
            });
        });
        resizeObserverRef.current.observe(containerRef.current);

        return () => {
            resizeObserverRef.current?.disconnect();
            resizeObserverRef.current = null;
            chart.remove();
            chartRef.current = null;
            candleSeriesRef.current = null;
            volumeSeriesRef.current = null;
            renderedCursorRef.current = -1;
            datasetKeyRef.current = null;
        };
    }, [palette.background, palette.border, palette.downCandle, palette.grid, palette.text, palette.upCandle, palette.upVolume]);

    useEffect(() => {
        if (!candleSeriesRef.current || !volumeSeriesRef.current) {
            return;
        }

        if (!Array.isArray(candles) || candles.length === 0) {
            candleSeriesRef.current.setData([]);
            volumeSeriesRef.current.setData([]);
            renderedCursorRef.current = -1;
            datasetKeyRef.current = datasetKey;
            return;
        }

        const normalizedCursor = Math.max(0, Math.min(cursor, candles.length - 1));
        const datasetChanged = datasetKeyRef.current !== datasetKey;
        const cursorMovedBack = normalizedCursor < renderedCursorRef.current;
        const needsReset = datasetChanged || cursorMovedBack || renderedCursorRef.current === -1;

        if (mode === "inspect") {
            candleSeriesRef.current.setData(candles);
            volumeSeriesRef.current.setData(candles.map((candle) => getVolumePoint(candle, palette)));
            renderedCursorRef.current = candles.length - 1;
            datasetKeyRef.current = datasetKey;
            return;
        }

        if (needsReset) {
            const initialCandles = candles.slice(0, normalizedCursor + 1);
            candleSeriesRef.current.setData(initialCandles);
            volumeSeriesRef.current.setData(initialCandles.map((candle) => getVolumePoint(candle, palette)));
            chartRef.current?.timeScale().fitContent();
            datasetKeyRef.current = datasetKey;
            renderedCursorRef.current = normalizedCursor;
            return;
        }

        for (let index = renderedCursorRef.current + 1; index <= normalizedCursor; index += 1) {
            candleSeriesRef.current.update(candles[index]);
            volumeSeriesRef.current.update(getVolumePoint(candles[index], palette));
        }

        renderedCursorRef.current = normalizedCursor;
    }, [candles, cursor, datasetKey, mode, palette]);

    useEffect(() => {
        if (!candleSeriesRef.current) {
            return;
        }

        candleSeriesRef.current.setMarkers(buildMarkers({
            candles: Array.isArray(candles) ? candles : [],
            buySignals: Array.isArray(buySignals) ? buySignals : [],
            sellSignals: Array.isArray(sellSignals) ? sellSignals : [],
            completedTrades: Array.isArray(completedTrades) ? completedTrades : [],
            highlightedSetup,
            palette,
        }));
    }, [buySignals, candles, completedTrades, highlightedSetup, palette, sellSignals]);

    useEffect(() => {
        if (!chartRef.current || mode !== "inspect" || !Array.isArray(candles) || candles.length === 0) {
            return;
        }

        const normalizedIndex = centerOnIndex === null || centerOnIndex === undefined
            ? Number.NaN
            : Number(centerOnIndex);
        const visibleRange = buildInspectionRange(normalizedIndex, candles.length);

        if (visibleRange) {
            chartRef.current.timeScale().setVisibleLogicalRange(visibleRange);
            return;
        }

        chartRef.current.timeScale().fitContent();
    }, [candles, centerOnIndex, datasetKey, mode]);

    return <div ref={containerRef} className="h-full w-full" />;
}

export default memo(ReplayChart);
