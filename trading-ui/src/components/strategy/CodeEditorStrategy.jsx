import { useStrategy } from "../../context/StrategyContext";
import { Info } from "lucide-react";

export default function CodeEditorStrategy() {
    const { config, setConfig } = useStrategy();

    const handleCodeChange = (e) => {
        setConfig(prev => ({ ...prev, codeString: e.target.value }));
    };

    // Default code snippet
    if (config.codeString === undefined) {
        setTimeout(() => {
            setConfig(prev => ({
                ...prev,
                codeString: "# Available variables: close, open, high, low, volume\n# Also indicators like: sma_fast, sma_slow, rsi\n\nif close > sma_fast and rsi < 30:\n    buy()\n\nif close < sma_slow and rsi > 70:\n    sell()\n"
            }));
        }, 0);
    }

    return (
        <div className="flex flex-col gap-4 animate-fade-in h-[350px]">
            <div className="flex items-center gap-2 p-3 rounded-lg border" style={{ background: "rgba(37,99,235,0.05)", borderColor: "rgba(37,99,235,0.15)", color: "#93c5fd" }}>
                <Info size={14} className="shrink-0" />
                <span className="text-xs leading-relaxed">
                    Write Python-like logic. Extracted variables available: <strong>close, open, high, low, volume, rsi, sma_fast, sma_slow</strong>. Call <strong>buy()</strong> or <strong>sell()</strong> to emit signals.
                </span>
            </div>

            <div className="flex-1 flex flex-col rounded-lg border overflow-hidden" style={{ borderColor: "rgba(255,255,255,0.08)", background: "#0a0a0a" }}>
                <div className="px-3 py-2 border-b flex items-center" style={{ borderColor: "rgba(255,255,255,0.05)", background: "#0f0f0f" }}>
                    <span className="text-[10px] uppercase tracking-widest text-textSecondary font-semibold">Strategy Logic (Python)</span>
                </div>
                <textarea
                    className="flex-1 w-full bg-transparent text-sm text-[13px] text-textPrimary p-4 font-mono focus:outline-none resize-none"
                    style={{ lineHeight: "1.6" }}
                    spellCheck="false"
                    value={config.codeString || ""}
                    onChange={handleCodeChange}
                    placeholder="# Write your logic here..."
                />
            </div>
        </div>
    );
}
