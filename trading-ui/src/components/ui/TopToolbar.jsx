import { Settings, BarChart } from "lucide-react";

export default function TopToolbar({ session, timeframe, setTimeframe }) {
    if (!session) return null;

    return (
        <div className="h-[46px] shrink-0 border-b border-white/5 bg-[#121212] px-4 flex items-center justify-between z-10 shadow-sm">
            <div className="flex items-center gap-4">
                <span className="text-[13px] font-bold text-white uppercase tracking-wider">{session.symbol}</span>
                <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 text-[10px] font-bold uppercase">{session.session_name}</span>
            </div>

            <div className="flex items-center gap-1">
                {['1m', '5m', '15m', '1H', '4H', '1D'].map(tf => {
                    const isActive = timeframe === tf.toUpperCase();
                    return (
                        <button
                            key={tf}
                            onClick={() => setTimeframe(tf.toUpperCase())}
                            className={`px-2 py-1 text-[11px] font-bold rounded uppercase transition-colors ${isActive ? 'bg-blue-500/20 text-blue-400' : 'text-[#666] hover:text-white hover:bg-[#222]'}`}
                        >
                            {tf}
                        </button>
                    )
                })}
            </div>

            <div className="flex items-center gap-3">
                <button className="text-[#888] hover:text-white transition-colors" title="Chart Settings">
                    <Settings size={14} />
                </button>
            </div>
        </div>
    );
}
