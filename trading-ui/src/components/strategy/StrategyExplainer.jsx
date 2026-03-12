import { useState, useEffect, useRef } from "react";
import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const LOADING_PLACEHOLDER = "Analysing your strategy logic…";

/**
 * Renders the AI Strategy Explanation panel.
 * Props:
 *   rules  — array of { indicator, operator, value } objects
 *   side   — "buy" | "sell"  (default "buy")
 */
export default function StrategyExplainer({ rules = [], side = "buy" }) {
    const [explanation, setExplanation] = useState("");
    const [riskNote, setRiskNote] = useState("");
    const [loading, setLoading] = useState(false);
    const debounceRef = useRef(null);

    useEffect(() => {
        // Debounce rapid rule changes by 600 ms
        if (debounceRef.current) clearTimeout(debounceRef.current);

        debounceRef.current = setTimeout(async () => {
            if (!rules || rules.length === 0) {
                setExplanation("");
                setRiskNote("");
                return;
            }

            setLoading(true);
            try {
                const { data } = await axios.post(`${API_BASE}/explain_strategy`, {
                    rules,
                    side,
                });
                setExplanation(data.explanation ?? "");
                setRiskNote(data.risk_note ?? "");
            } catch {
                setExplanation("Unable to generate explanation. Please check your connection.");
                setRiskNote("");
            } finally {
                setLoading(false);
            }
        }, 600);

        return () => clearTimeout(debounceRef.current);
    }, [rules, side]);

    const hasContent = explanation || loading;

    if (!hasContent) return null;

    return (
        <div className="mt-6 rounded-xl border border-border bg-surface/60 backdrop-blur-sm overflow-hidden transition-all duration-300 shadow-soft">
            {/* Header */}
            <div className="flex items-center gap-2 px-5 py-3 border-b border-border bg-panel/40">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-semibold uppercase tracking-widest text-textSecondary">
                    AI Strategy Explanation
                </span>
            </div>

            <div className="p-5 flex flex-col gap-4">
                {/* Explanation */}
                <div className="flex gap-3">
                    <div className="mt-0.5 w-5 h-5 shrink-0 text-textSecondary">
                        <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5">
                            <circle cx="10" cy="10" r="8" />
                            <path strokeLinecap="round" d="M10 7v4m0 2.5v.5" />
                        </svg>
                    </div>
                    <p className="text-sm leading-relaxed text-textPrimary">
                        {loading ? (
                            <span className="text-textSecondary italic">{LOADING_PLACEHOLDER}</span>
                        ) : explanation}
                    </p>
                </div>

                {/* Risk Note */}
                {!loading && riskNote && (
                    <div className="flex gap-3 rounded-lg bg-amber-500/10 border border-amber-500/20 px-4 py-3">
                        <div className="mt-0.5 w-4 h-4 shrink-0 text-amber-400">
                            <svg viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                            </svg>
                        </div>
                        <p className="text-xs leading-relaxed text-amber-300">{riskNote}</p>
                    </div>
                )}
            </div>
        </div>
    );
}
