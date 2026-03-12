import { memo } from "react";
import { Handle, Position } from "reactflow";

const INDICATORS = [
    { value: "RSI", label: "RSI" },
    { value: "SMA", label: "SMA" },
    { value: "EMA", label: "EMA" },
    { value: "MACD", label: "MACD" },
    { value: "BB", label: "Bollinger Bands" },
    { value: "Price", label: "Price / Close" },
];

function IndicatorNode({ data, selected }) {
    const { indicator, period, onChange } = data;

    return (
        <div className={`relative rounded-xl border transition-all duration-200 min-w-[170px] ${selected ? "border-blue-400/60 shadow-[0_0_18px_rgba(59,130,246,0.3)]" : "border-border shadow-soft"} bg-panel/90 backdrop-blur-sm`}>
            {/* Header */}
            <div className="px-3 py-2 border-b border-border/60 flex items-center gap-2 rounded-t-xl bg-blue-500/10">
                <div className="w-2 h-2 rounded-full bg-blue-400" />
                <span className="text-xs font-semibold text-blue-300 uppercase tracking-wider">Indicator</span>
            </div>

            <div className="p-3 flex flex-col gap-2">
                {/* Indicator Selector */}
                <select
                    className="w-full bg-background border border-border text-textPrimary text-xs rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-400/60 transition-colors"
                    value={indicator}
                    onChange={(e) => onChange?.("indicator", e.target.value)}
                >
                    {INDICATORS.map(({ value, label }) => (
                        <option key={value} value={value}>{label}</option>
                    ))}
                </select>

                {/* Period (hide for Price / BB) */}
                {!["Price", "BB", "MACD"].includes(indicator) && (
                    <input
                        type="number"
                        min={1}
                        max={500}
                        className="w-full bg-background border border-border text-textPrimary text-xs rounded-md px-2 py-1.5 focus:outline-none focus:border-blue-400/60 transition-colors"
                        placeholder="Period (e.g. 14)"
                        value={period ?? ""}
                        onChange={(e) => onChange?.("period", e.target.value)}
                    />
                )}
            </div>

            {/* Output handle */}
            <Handle
                type="source"
                position={Position.Right}
                className="w-3 h-3 !border-2 !border-blue-400 !bg-panel rounded-full"
            />
        </div>
    );
}

export default memo(IndicatorNode);
