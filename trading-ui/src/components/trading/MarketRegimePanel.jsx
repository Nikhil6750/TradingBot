import { useMemo } from "react";

// Regime → neutral indicator dot color (no bright borders/banners)
const REGIME_META = {
    "Trending": { dot: "#60A5FA", label: "Trending Market", strategy: "Trend Following (MA Crossover / Breakout)" },
    "Sideways": { dot: "#FBBF24", label: "Sideways Market", strategy: "Mean Reversion (RSI / Bollinger Bands)" },
    "High Volatility": { dot: "#F87171", label: "High Volatility Market", strategy: "Widen stops. Reduce position size." },
    "Low Volatility": { dot: "#34D399", label: "Low Volatility Market", strategy: "Breakout setups offer best risk/reward." },
};

const DEFAULT_META = { dot: "#A3A3A3", label: "Unknown", strategy: "—" };

function SparkBar({ bars }) {
    const DOT_COLORS = {
        "Trending": "#60A5FA",
        "Sideways": "#FBBF24",
        "High Volatility": "#F87171",
        "Low Volatility": "#34D399",
    };
    return (
        <div className="flex items-end gap-px h-4">
            {bars.map((r, i) => (
                <div
                    key={i}
                    className="flex-1 rounded-sm opacity-60"
                    style={{ background: DOT_COLORS[r] ?? "#A3A3A3", height: "100%" }}
                    title={r}
                />
            ))}
        </div>
    );
}

/**
 * MarketRegimePanel — clean professional analysis card.
 * No colored backgrounds, no warning banners.
 */
export default function MarketRegimePanel({ regimeData }) {
    if (!regimeData) return null;

    const { regime, confidence, regime_history = [] } = regimeData;
    const meta = REGIME_META[regime] ?? DEFAULT_META;
    const pct = Math.round((confidence ?? 0) * 100);

    const sparkBars = useMemo(() => regime_history.slice(-24), [regime_history]);

    return (
        <div
            className="rounded-xl overflow-hidden"
            style={{ background: "#141414", boxShadow: "0 8px 24px rgba(0,0,0,0.4)" }}
        >
            {/* ── Header ──────────────────────────────────────────── */}
            <div
                className="flex items-center justify-between px-4 py-3"
                style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}
            >
                <span className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">
                    Market Regime
                </span>
                <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-[10px] text-textSecondary font-medium">LIVE</span>
                </div>
            </div>

            {/* ── Body ────────────────────────────────────────────── */}
            <div className="px-4 py-4 flex flex-col gap-4">
                {/* Regime label + dot */}
                <div className="flex items-center gap-2">
                    <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ background: meta.dot }}
                    />
                    <span className="text-base font-bold text-textPrimary tracking-tight">{meta.label}</span>
                </div>

                {/* Confidence */}
                <div className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] text-textSecondary uppercase tracking-widest">Confidence</span>
                        <span className="text-xs font-semibold text-textPrimary tabular-nums">{pct}%</span>
                    </div>
                    <div className="h-1 w-full rounded-full overflow-hidden" style={{ background: "#262626" }}>
                        <div
                            className="h-full rounded-full transition-all duration-700"
                            style={{ width: `${pct}%`, background: meta.dot }}
                        />
                    </div>
                </div>

                {/* Sparkline history */}
                {sparkBars.length > 0 && <SparkBar bars={sparkBars} />}

                {/* Recommended strategy */}
                <div className="flex flex-col gap-1" style={{ borderTop: "1px solid rgba(255,255,255,0.06)", paddingTop: "12px" }}>
                    <span className="text-[10px] text-textSecondary uppercase tracking-widest">Recommended Strategy</span>
                    <span className="text-xs text-textPrimary leading-relaxed">{meta.strategy}</span>
                </div>
            </div>
        </div>
    );
}
