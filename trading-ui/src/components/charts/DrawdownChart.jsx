import { useEffect, useMemo, useRef } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";

const DEFAULT_PALETTE = {
    background: "#0b0f14",
    text: "#8b98a7",
    grid: "rgba(255,255,255,0.05)",
    line: "#ef4444",
    top: "rgba(239,68,68,0.25)",
    bottom: "rgba(239,68,68,0.02)",
};

function buildDrawdownData(trades, initialBalance) {
    if (!Array.isArray(trades) || trades.length === 0) {
        return [];
    }

    let balance = initialBalance;
    let peak = initialBalance;

    const orderedTrades = [...trades].sort(
        (left, right) => (left.exit_time || left.entry_time || 0) - (right.exit_time || right.entry_time || 0),
    );

    return orderedTrades
        .map((trade) => {
            const time = trade.exit_time || trade.entry_time;
            if (!time) {
                return null;
            }

            balance = balance * (1 + Number(trade.pnl || 0));
            peak = Math.max(peak, balance);
            return {
                time,
                value: peak > 0 ? (balance / peak - 1) * 100 : 0,
            };
        })
        .filter(Boolean);
}

export default function DrawdownChart({ trades, initialBalance = 10000, palette = null }) {
    const containerRef = useRef(null);
    const chartRef = useRef(null);
    const seriesRef = useRef(null);
    const colors = { ...DEFAULT_PALETTE, ...(palette || {}) };

    const drawdownData = useMemo(
        () => buildDrawdownData(trades, initialBalance),
        [initialBalance, trades],
    );

    useEffect(() => {
        if (!containerRef.current || chartRef.current) {
            return undefined;
        }

        const chart = createChart(containerRef.current, {
            layout: {
                background: { type: "solid", color: colors.background },
                textColor: colors.text,
                fontSize: 11,
            },
            grid: {
                vertLines: { color: colors.grid },
                horzLines: { color: colors.grid },
            },
            crosshair: { mode: CrosshairMode.Normal },
            rightPriceScale: { borderVisible: false },
            timeScale: { borderVisible: false, timeVisible: true },
            autoSize: true,
        });

        const series = chart.addAreaSeries({
            lineColor: colors.line,
            topColor: colors.top,
            bottomColor: colors.bottom,
            lineWidth: 2,
            priceLineVisible: false,
        });

        chartRef.current = chart;
        seriesRef.current = series;

        return () => {
            chart.remove();
            chartRef.current = null;
            seriesRef.current = null;
        };
    }, [colors.background, colors.bottom, colors.grid, colors.line, colors.text, colors.top]);

    useEffect(() => {
        if (!seriesRef.current) {
            return;
        }

        seriesRef.current.setData(drawdownData);
        chartRef.current?.timeScale().fitContent();
    }, [drawdownData]);

    return <div ref={containerRef} className="h-full w-full" />;
}
