import { useState, useMemo } from "react";
import { allAssets } from "../../data/assets";

export default function AssetSelector({ value, onSelect }) {
    const [searchTerm, setSearchTerm] = useState("");

    const filtered = useMemo(() => {
        if (!searchTerm.trim()) return allAssets;
        const q = searchTerm.toLowerCase();
        return allAssets.filter(a => 
            a.symbol.toLowerCase().includes(q) ||
            a.broker.toLowerCase().includes(q)
        );
    }, [searchTerm]);

    return (
        <div className="flex flex-col gap-3">
            <input 
                type="text" 
                placeholder="Search assets (e.g. EURUSD, Binance)..." 
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="w-full bg-[#0f0f0f] border border-white/5 rounded-lg px-3 py-2.5 text-sm text-textPrimary focus:outline-none focus:border-emerald-500/40 transition-all font-medium"
            />
            
            <div className="flex flex-col gap-1 max-h-64 overflow-y-auto custom-scrollbar border border-white/5 rounded-xl p-1.5 bg-[#0a0a0a]">
                {filtered.map(asset => {
                    const isSelected = value?.symbol === asset.symbol && value?.broker === asset.broker;
                    return (
                        <button
                            key={`${asset.symbol}-${asset.broker}`}
                            onClick={() => onSelect(asset)}
                            className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm transition-colors cursor-pointer ${
                                isSelected 
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                                : "text-textPrimary hover:bg-white/5 border border-transparent"
                            }`}
                        >
                            <span className="font-bold flex items-center gap-2">
                                {asset.symbol}
                                {isSelected && <span className="text-[10px] text-emerald-500">✓</span>}
                            </span>
                            <span className="text-[9px] font-black px-2 py-0.5 rounded-sm bg-white/5 text-textSecondary uppercase tracking-widest border border-white/10">
                                {asset.broker}
                            </span>
                        </button>
                    );
                })}
                
                {filtered.length === 0 && (
                    <div className="py-6 text-center text-xs text-textSecondary italic">
                        No assets found matching "{searchTerm}"
                    </div>
                )}
            </div>
        </div>
    );
}
