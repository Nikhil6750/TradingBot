import { useEffect, useRef, useMemo } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";
import { useTheme } from "../../context/ThemeContext";
import { X } from "lucide-react";

// ── Duration helper ───────────────────────────────────────────────────────────
function formatDuration(sec) {
    if (!sec || sec <= 0) return "—";
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
}

function formatDate(sec) {
    const v = Number(sec);
    if (!Number.isFinite(v)) return "—";
    return new Date(v * 1000).toISOString().replace("T", " ").slice(0, 16);
}

// ── Confidence bar ────────────────────────────────────────────────────────────
function ConfidenceBar({ score, riskLevel }) {
    const pct = Math.round((score ?? 0.5) * 100);
    const barColor =
        riskLevel === "Low" ? "#34d399" :
            riskLevel === "Medium" ? "#fbbf24" : "#f87171";
    return (
        <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
                <span className="text-[10px] uppercase tracking-widest text-textSecondary font-medium">AI Confidence</span>
                <span className="text-sm font-black text-textPrimary">{pct}%</span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-border overflow-hidden">
                <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${pct}%`, background: barColor }}
                />
            </div>
            <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: barColor }} />
                <span className="text-[10px] text-textSecondary">{riskLevel ?? "—"} Risk</span>
            </div>
        </div>
    );
}

// ── Zoomed chart around a single trade ───────────────────────────────────────
function ZoomedTradeChart({ candles, trade }) {
    const containerRef = useRef(null);
    const chartRef = useRef(null);
    const seriesRef = useRef(null);
    const { theme } = useTheme();

    const WINDOW = 40; // candles before and after the trade

    const { slicedCandles, entryIdx, exitIdx } = useMemo(() => {
        if (!candles?.length || !trade) return { slicedCandles: [], entryIdx: -1, exitIdx: -1 };
        const times = candles.map(c => c.time);
        const nearestIdx = (t) => {
            if (t == null) return -1;
            let best = 0, bestDiff = Infinity;
            times.forEach((tc, i) => { const d = Math.abs(tc - t); if (d < bestDiff) { bestDiff = d; best = i; } });
            return best;
        };
        const eIdx = nearestIdx(trade.entry_time);
        const xIdx = nearestIdx(trade.exit_time);
        const start = Math.max(0, Math.min(eIdx, xIdx) - WINDOW);
        const end = Math.min(candles.length - 1, Math.max(eIdx, xIdx) + WINDOW);
        return {
            slicedCandles: candles.slice(start, end + 1),
            entryIdx: eIdx - start,
            exitIdx: xIdx - start,
        };
    }, [candles, trade]);

    useEffect(() => {
        if (!containerRef.current || chartRef.current || slicedCandles.length === 0) return;

        const isDark = document.documentElement.classList.contains("dark");
        const ch = createChart(containerRef.current, {
            layout: { background: { type: "solid", color: isDark ? "#0b0f14" : "#f4f6f8" }, textColor: isDark ? "#9aa4af" : "#6b7280" },
            grid: { vertLines: { color: "rgba(255,255,255,0.04)" }, horzLines: { color: "rgba(255,255,255,0.04)" } },
            crosshair: { mode: CrosshairMode.Normal },
            rightPriceScale: { borderVisible: false },
            timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
            handleScroll: { mouseWheel: true, pressedMouseMove: true },
            handleScale: { mouseWheel: true, pinch: true },
            autoSize: true,
        });

        const cs = ch.addCandlestickSeries({
            upColor: "#10b981", downColor: "#ef4444",
            borderVisible: false,
            wickUpColor: "#10b981", wickDownColor: "#ef4444",
        });

        const data = slicedCandles.map(c => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close }));
        cs.setData(data);

        // Entry + exit markers
        const markers = [];
        if (entryIdx >= 0 && slicedCandles[entryIdx]) {
            markers.push({ time: slicedCandles[entryIdx].time, position: trade.type === "BUY" ? "belowBar" : "aboveBar", color: "#10b981", shape: "arrowUp", text: "Entry", size: 1 });
        }
        if (exitIdx >= 0 && slicedCandles[exitIdx]) {
            markers.push({ time: slicedCandles[exitIdx].time, position: "aboveBar", color: "#ef4444", shape: "arrowDown", text: "Exit", size: 1 });
        }
        const uniqueMarkers = [...new Map(markers.map(m => [m.time, m])).values()].sort((a, b) => a.time - b.time);
        if (uniqueMarkers.length) cs.setMarkers(uniqueMarkers);

        // Stop loss / take profit lines
        if (trade.stop_loss) {
            const slSeries = ch.addLineSeries({ color: "rgba(239,68,68,0.7)", lineWidth: 1, lineStyle: 2 });
            slSeries.setData(data.map(d => ({ time: d.time, value: trade.stop_loss })));
        }
        if (trade.take_profit) {
            const tpSeries = ch.addLineSeries({ color: "rgba(52,211,153,0.7)", lineWidth: 1, lineStyle: 2 });
            tpSeries.setData(data.map(d => ({ time: d.time, value: trade.take_profit })));
        }

        ch.timeScale().fitContent();
        chartRef.current = ch;
        seriesRef.current = cs;

        return () => { ch.remove(); chartRef.current = null; seriesRef.current = null; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [slicedCandles]);

    // Theme update
    useEffect(() => {
        if (!chartRef.current) return;
        const isDark = theme === "dark";
        chartRef.current.applyOptions({
            layout: { background: { type: "solid", color: isDark ? "#0b0f14" : "#f4f6f8" }, textColor: isDark ? "#9aa4af" : "#6b7280" },
        });
    }, [theme]);

    if (!slicedCandles.length) return null;
    return <div ref={containerRef} className="w-full h-full" />;
}

// ── Main panel ────────────────────────────────────────────────────────────────
export default function TradeDetailPanel({ trade, candles, onClose }) {
    if (!trade) return null;

    const isWin = (trade.pnl ?? 0) > 0;
    const duration = trade.exit_time && trade.entry_time ? trade.exit_time - trade.entry_time : null;
    const pnlDisplay = `${isWin ? "+" : ""}${((trade.pnl ?? 0) * 100).toFixed(2)}%`;

    const rows = [
        { label: "Entry Price", value: trade.entry_price?.toFixed(5) ?? "—" },
        { label: "Exit Price", value: trade.exit_price?.toFixed(5) ?? "—" },
        { label: "Duration", value: formatDuration(duration) },
        { label: "PnL", value: pnlDisplay, color: isWin ? "text-emerald-400" : "text-red-400" },
        { label: "Stop Loss", value: trade.stop_loss?.toFixed(5) ?? "—" },
        { label: "Take Profit", value: trade.take_profit?.toFixed(5) ?? "—" },
    ];

    return (
        <div
            className="rounded-xl border border-card-border bg-card p-5 flex flex-col gap-5 shadow-card transition-all duration-300"
        >
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-widest uppercase
                        ${trade.type === "BUY" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                        {trade.type}
                    </span>
                    <span className="text-xs text-textSecondary font-mono">{formatDate(trade.entry_time)}</span>
                    <span className="text-[10px] text-textSecondary">→</span>
                    <span className="text-xs text-textSecondary font-mono">{formatDate(trade.exit_time)}</span>
                </div>
                <button
                    onClick={onClose}
                    className="text-textSecondary hover:text-textPrimary transition-colors cursor-pointer p-1 rounded"
                >
                    <X size={14} />
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
                {/* Left: details grid */}
                <div className="lg:col-span-1 flex flex-col gap-4">
                    <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                        {rows.map(r => (
                            <div key={r.label} className="flex flex-col gap-0.5">
                                <span className="text-[10px] uppercase tracking-widest text-textSecondary font-medium">{r.label}</span>
                                <span className={`text-sm font-semibold tabular-nums ${r.color ?? "text-textPrimary"}`}>{r.value}</span>
                            </div>
                        ))}
                    </div>

                    {/* AI score */}
                    {trade.trade_score != null && (
                        <div
                            className="rounded-lg p-3"
                            style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.07)" }}
                        >
                            <ConfidenceBar score={trade.trade_score} riskLevel={trade.risk_level} />
                        </div>
                    )}
                </div>

                {/* Right: zoomed price chart */}
                <div className="lg:col-span-2 rounded-lg overflow-hidden" style={{ height: "240px", background: "#0b0f14" }}>
                    <ZoomedTradeChart candles={candles} trade={trade} />
                </div>
            </div>
        </div>
    );
}
