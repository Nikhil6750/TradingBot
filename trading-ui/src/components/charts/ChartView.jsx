import ForexChart from "./ForexChart";

/**
 * ChartView — price chart with guaranteed fixed height so the
 * inner Lightweight Charts canvas never collapses.
 */
export default function ChartView({ candles, trades, indicators }) {
    const overlayKeys = indicators
        ? Object.keys(indicators).filter(k => Array.isArray(indicators[k]))
        : [];

    return (
        <div className="w-full flex flex-col" style={{ height: "420px" }}>
            {/* Label */}
            <div
                className="flex items-center gap-2 px-3 py-2 flex-shrink-0"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}
            >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">
                    Price Action
                </span>
                {overlayKeys.length > 0 && (
                    <span className="ml-auto text-[10px] text-textSecondary opacity-50">
                        {overlayKeys.join(" · ")}
                    </span>
                )}
            </div>

            {/* Chart canvas ─ fills remaining height */}
            <div
                className="flex-1 overflow-hidden"
                style={{ background: "#0f0f0f", borderRadius: "0 0 10px 10px", minHeight: 0 }}
            >
                <ForexChart candles={candles} trades={trades} indicators={indicators} />
            </div>
        </div>
    );
}
