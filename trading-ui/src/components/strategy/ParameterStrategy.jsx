import { useState, useEffect } from "react";
import { useStrategy } from "../../context/StrategyContext";

// Shared styles — no borders
const inputCls =
    "bg-[#0f0f0f] rounded-lg px-2 py-1.5 text-sm text-textPrimary " +
    "focus:outline-none focus:shadow-[0_0_0_2px_rgba(255,255,255,0.06)] " +
    "transition-shadow duration-150 appearance-none";

const INDICATORS = ["rsi", "close", "sma50", "sma200", "ema20", "macd", "atr"];
const OPERATORS = ["<", ">", "<=", ">=", "=="];

export default function ParameterStrategy() {
    const { setConfig } = useStrategy();

    const [buyRules, setBuyRules] = useState([{ id: 1, indicator: "rsi", operator: "<", value: "30" }]);
    const [sellRules, setSellRules] = useState([{ id: 1, indicator: "rsi", operator: ">", value: "70" }]);

    useEffect(() => {
        const str = (rules) => rules.map(r => `${r.indicator} ${r.operator} ${r.value}`).join(" AND ");
        setConfig(prev => ({ ...prev, customRules: { buy: str(buyRules), sell: str(sellRules) } }));
    }, [buyRules, sellRules, setConfig]);

    const update = (rules, set, id, field, val) =>
        set(rules.map(r => r.id === id ? { ...r, [field]: val } : r));

    const add = (rules, set) => set([...rules, { id: Date.now(), indicator: "close", operator: ">", value: "sma50" }]);
    const remove = (rules, set, id) => rules.length > 1 && set(rules.filter(r => r.id !== id));

    return (
        <div className="flex flex-col gap-8 animate-fade-in">
            <RuleList
                title="Buy Conditions" dot="bg-emerald-500"
                rules={buyRules} setRules={setBuyRules}
                onUpdate={update} onAdd={add} onRemove={remove}
            />
            <RuleList
                title="Sell Conditions" dot="bg-red-500"
                rules={sellRules} setRules={setSellRules}
                onUpdate={update} onAdd={add} onRemove={remove}
            />
        </div>
    );
}

function RuleList({ title, dot, rules, setRules, onUpdate, onAdd, onRemove }) {
    return (
        <div className="flex flex-col gap-3">
            {/* Section header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
                    <span className="text-[10px] font-bold uppercase tracking-widest text-textSecondary">{title}</span>
                </div>
                <button
                    onClick={() => onAdd(rules, setRules)}
                    className="flex items-center gap-1 text-[10px] text-textSecondary hover:text-textPrimary transition-colors cursor-pointer"
                >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    ADD
                </button>
            </div>

            {/* Rules */}
            {rules.map((rule, idx) => (
                <div key={rule.id} className="flex flex-col gap-1.5">
                    {idx > 0 && (
                        <span className="text-[10px] text-textSecondary font-mono ml-2">AND</span>
                    )}
                    {/* Rule row — subtle dark bg, no border */}
                    <div
                        className="flex gap-2 items-center px-3 py-2 rounded-xl"
                        style={{ background: "#1C1C1C" }}
                    >
                        <select
                            className={`${inputCls} flex-1`}
                            value={rule.indicator}
                            onChange={e => onUpdate(rules, setRules, rule.id, "indicator", e.target.value)}
                        >
                            {INDICATORS.map(i => <option key={i} value={i}>{i.toUpperCase()}</option>)}
                        </select>

                        <select
                            className={`${inputCls} w-16`}
                            value={rule.operator}
                            onChange={e => onUpdate(rules, setRules, rule.id, "operator", e.target.value)}
                        >
                            {OPERATORS.map(o => <option key={o} value={o}>{o}</option>)}
                        </select>

                        <input
                            type="text"
                            className={`${inputCls} w-20`}
                            value={rule.value}
                            onChange={e => onUpdate(rules, setRules, rule.id, "value", e.target.value)}
                        />

                        <button
                            onClick={() => onRemove(rules, setRules, rule.id)}
                            disabled={rules.length === 1}
                            className="text-textSecondary hover:text-red-400 transition-colors p-1 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer"
                        >
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
}
