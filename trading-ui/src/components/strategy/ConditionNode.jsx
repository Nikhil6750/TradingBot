import { memo } from "react";
import { Handle, Position } from "reactflow";

const OPERATORS = [
    { value: "<", label: "< (less than)" },
    { value: "<=", label: "≤ (less or equal)" },
    { value: ">", label: "> (greater than)" },
    { value: ">=", label: "≥ (greater or equal)" },
    { value: "==", label: "= (equal)" },
];

function ConditionNode({ data, selected }) {
    const { operator, value, onChange } = data;

    return (
        <div className={`relative rounded-xl border transition-all duration-200 min-w-[170px] ${selected ? "border-violet-400/60 shadow-[0_0_18px_rgba(139,92,246,0.3)]" : "border-border shadow-soft"} bg-panel/90 backdrop-blur-sm`}>
            {/* Input handle */}
            <Handle
                type="target"
                position={Position.Left}
                className="w-3 h-3 !border-2 !border-violet-400 !bg-panel rounded-full"
            />

            {/* Header */}
            <div className="px-3 py-2 border-b border-border/60 flex items-center gap-2 rounded-t-xl bg-violet-500/10">
                <div className="w-2 h-2 rounded-full bg-violet-400" />
                <span className="text-xs font-semibold text-violet-300 uppercase tracking-wider">Condition</span>
            </div>

            <div className="p-3 flex flex-col gap-2">
                {/* Operator */}
                <select
                    className="w-full bg-background border border-border text-textPrimary text-xs rounded-md px-2 py-1.5 focus:outline-none focus:border-violet-400/60 transition-colors"
                    value={operator}
                    onChange={(e) => onChange?.("operator", e.target.value)}
                >
                    {OPERATORS.map(({ value, label }) => (
                        <option key={value} value={value}>{label}</option>
                    ))}
                </select>

                {/* Value */}
                <input
                    type="text"
                    className="w-full bg-background border border-border text-textPrimary text-xs rounded-md px-2 py-1.5 focus:outline-none focus:border-violet-400/60 transition-colors"
                    placeholder="Value (e.g. 30 or EMA200)"
                    value={value ?? ""}
                    onChange={(e) => onChange?.("value", e.target.value)}
                />
            </div>

            {/* Output handle */}
            <Handle
                type="source"
                position={Position.Right}
                className="w-3 h-3 !border-2 !border-violet-400 !bg-panel rounded-full"
            />
        </div>
    );
}

export default memo(ConditionNode);
