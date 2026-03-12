import { useStrategy } from "../../context/StrategyContext";

// Shared input style — no visible border, dark recessed field
const inputCls =
    "w-full bg-[#0f0f0f] rounded-lg px-3 py-2 text-sm text-textPrimary " +
    "focus:outline-none transition-shadow duration-150 " +
    "focus:shadow-[0_0_0_2px_rgba(255,255,255,0.06)]";

const selectCls = inputCls + " appearance-none cursor-pointer";

export default function StrategyTemplates() {
    const { config, setConfig } = useStrategy();

    const handleTemplateChange = (e) => {
        setConfig((prev) => ({ ...prev, strategyTemplate: e.target.value }));
    };

    const handleParamChange = (key, val) => {
        setConfig((prev) => ({
            ...prev,
            templateParams: { ...prev.templateParams, [key]: parseFloat(val) || 0 },
        }));
    };

    const p = config.templateParams;

    return (
        <div className="flex flex-col gap-6 animate-fade-in">
            {/* Template selector */}
            <div className="flex flex-col gap-2">
                <label className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary">
                    Select Template
                </label>
                <select
                    value={config.strategyTemplate}
                    onChange={handleTemplateChange}
                    className={selectCls}
                >
                    <option value="ma_crossover">Moving Average Crossover</option>
                    <option value="rsi_reversal">RSI Reversal</option>
                    <option value="breakout">Bollinger Breakout</option>
                </select>
            </div>

            {/* Parameter block — no border, subtle background */}
            <div className="rounded-xl p-4" style={{ background: "#1C1C1C" }}>
                <h4 className="text-[10px] font-semibold uppercase tracking-widest text-textSecondary mb-4">
                    Template Parameters
                </h4>

                {config.strategyTemplate === "ma_crossover" && (
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Short MA Period">
                            <input type="number" className={inputCls} value={p.short_ma_period}
                                onChange={e => handleParamChange("short_ma_period", e.target.value)} />
                        </Field>
                        <Field label="Long MA Period">
                            <input type="number" className={inputCls} value={p.long_ma_period}
                                onChange={e => handleParamChange("long_ma_period", e.target.value)} />
                        </Field>
                    </div>
                )}

                {config.strategyTemplate === "rsi_reversal" && (
                    <div className="flex flex-col gap-4">
                        <Field label="RSI Period">
                            <input type="number" className={inputCls} value={p.rsi_period}
                                onChange={e => handleParamChange("rsi_period", e.target.value)} />
                        </Field>
                        <div className="grid grid-cols-2 gap-4">
                            <Field label="Oversold Level">
                                <input type="number" className={inputCls} value={p.oversold_level}
                                    onChange={e => handleParamChange("oversold_level", e.target.value)} />
                            </Field>
                            <Field label="Overbought Level">
                                <input type="number" className={inputCls} value={p.overbought_level}
                                    onChange={e => handleParamChange("overbought_level", e.target.value)} />
                            </Field>
                        </div>
                    </div>
                )}

                {config.strategyTemplate === "breakout" && (
                    <div className="grid grid-cols-2 gap-4">
                        <Field label="Bollinger Period">
                            <input type="number" className={inputCls} value={p.breakout_period}
                                onChange={e => handleParamChange("breakout_period", e.target.value)} />
                        </Field>
                        <Field label="Deviation Threshold">
                            <input type="number" step="0.1" className={inputCls} value={p.deviation_threshold || 2.0}
                                onChange={e => handleParamChange("deviation_threshold", e.target.value)} />
                        </Field>
                    </div>
                )}
            </div>
        </div>
    );
}

function Field({ label, children }) {
    return (
        <div className="flex flex-col gap-1.5">
            <label className="text-[10px] font-medium text-textSecondary uppercase tracking-wider">{label}</label>
            {children}
        </div>
    );
}
