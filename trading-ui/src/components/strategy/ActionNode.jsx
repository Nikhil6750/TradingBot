import { memo } from "react";
import { Handle, Position } from "reactflow";

const ACTIONS = [
    { value: "BUY", label: "BUY", color: "emerald" },
    { value: "SELL", label: "SELL", color: "red" },
    { value: "HOLD", label: "HOLD", color: "amber" },
];

const ACTION_COLORS = {
    BUY: { border: "border-emerald-400/60", glow: "shadow-[0_0_18px_rgba(16,185,129,0.3)]", header: "bg-emerald-500/10", dot: "bg-emerald-400", text: "text-emerald-300" },
    SELL: { border: "border-red-400/60", glow: "shadow-[0_0_18px_rgba(239,68,68,0.3)]", header: "bg-red-500/10", dot: "bg-red-400", text: "text-red-300" },
    HOLD: { border: "border-amber-400/60", glow: "shadow-[0_0_18px_rgba(245,158,11,0.3)]", header: "bg-amber-500/10", dot: "bg-amber-400", text: "text-amber-300" },
};

function ActionNode({ data, selected }) {
    const { action, onChange } = data;
    const colors = ACTION_COLORS[action] ?? ACTION_COLORS.BUY;

    return (
        <div className={`relative rounded-xl border transition-all duration-200 min-w-[150px] ${selected ? `${colors.border} ${colors.glow}` : "border-border shadow-soft"} bg-panel/90 backdrop-blur-sm`}>
            {/* Input handle */}
            <Handle
                type="target"
                position={Position.Left}
                className={`w-3 h-3 !border-2 !bg-panel rounded-full ${action === "BUY" ? "!border-emerald-400" :
                        action === "SELL" ? "!border-red-400" : "!border-amber-400"
                    }`}
            />

            {/* Header */}
            <div className={`px-3 py-2 border-b border-border/60 flex items-center gap-2 rounded-t-xl ${colors.header}`}>
                <div className={`w-2 h-2 rounded-full ${colors.dot}`} />
                <span className={`text-xs font-semibold uppercase tracking-wider ${colors.text}`}>Action</span>
            </div>

            <div className="p-3">
                {/* Action selector */}
                <div className="flex gap-2 justify-center">
                    {ACTIONS.map(({ value, label }) => (
                        <button
                            key={value}
                            onClick={() => onChange?.("action", value)}
                            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border transition-all duration-150 cursor-pointer ${action === value
                                    ? value === "BUY" ? "bg-emerald-500/30 border-emerald-400/60 text-emerald-300"
                                        : value === "SELL" ? "bg-red-500/30 border-red-400/60 text-red-300"
                                            : "bg-amber-500/30 border-amber-400/60 text-amber-300"
                                    : "bg-background border-border text-textSecondary hover:border-textSecondary"
                                }`}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default memo(ActionNode);
