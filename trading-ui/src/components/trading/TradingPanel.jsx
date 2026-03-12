export default function TradingPanel({ currentCandle, openPosition, handleBuy, handleSell, closePosition }) {
    if (!currentCandle) return <div className="p-4 text-[#666] text-xs">Waiting for market data...</div>;

    const spread = (currentCandle.close * 0.0001).toFixed(4); // Synthetic spread
    const ask = (currentCandle.close + Number(spread)).toFixed(4);
    const bid = (currentCandle.close - Number(spread)).toFixed(4);

    return (
        <div className="flex flex-col h-full bg-[#0a0a0a] border-l border-white/5 w-[280px] shrink-0">
            <div className="px-5 py-4 border-b border-white/5 bg-[#121212]">
                <h3 className="text-sm font-bold text-white tracking-tight uppercase">Execution</h3>
            </div>

            <div className="p-5 flex flex-col gap-4">
                {/* One Click Trading Tickets */}
                <div className="grid grid-cols-2 gap-3">
                    <button
                        onClick={handleSell}
                        className="flex flex-col items-center justify-center py-3 px-2 rounded bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-colors"
                    >
                        <span className="text-[10px] font-bold text-red-400 mb-1 uppercase tracking-widest">Sell Mkt</span>
                        <span className="text-lg font-mono font-bold text-white">{bid}</span>
                    </button>

                    <button
                        onClick={handleBuy}
                        className="flex flex-col items-center justify-center py-3 px-2 rounded bg-green-500/10 hover:bg-green-500/20 border border-green-500/20 transition-colors"
                    >
                        <span className="text-[10px] font-bold text-green-400 mb-1 uppercase tracking-widest">Buy Mkt</span>
                        <span className="text-lg font-mono font-bold text-white">{ask}</span>
                    </button>
                </div>

                {/* Open Position Tracker */}
                <div className="mt-4 p-4 rounded border border-white/5 bg-[#111]">
                    <h4 className="text-[11px] font-bold text-[#888] uppercase tracking-wider mb-3">Open Position</h4>

                    {openPosition ? (
                        <div className="flex flex-col gap-3">
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-[#aaa]">Side</span>
                                <span className={`text-xs font-bold px-2 py-0.5 rounded ${openPosition.side === "BUY" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                                    {openPosition.side}
                                </span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-[#aaa]">Entry Price</span>
                                <span className="text-sm font-mono text-white">{openPosition.entry_price.toFixed(4)}</span>
                            </div>
                            <div className="flex justify-between items-center">
                                <span className="text-xs text-[#aaa]">Current Price</span>
                                <span className="text-sm font-mono text-white">{currentCandle.close.toFixed(4)}</span>
                            </div>

                            <div className="w-full h-[1px] bg-white/10 my-1" />

                            <div className="flex justify-between items-center">
                                <span className="text-xs text-[#aaa]">Quantity</span>
                                <span className="text-sm font-mono text-white">{openPosition.quantity}</span>
                            </div>

                            <button
                                onClick={() => closePosition(currentCandle)}
                                className="mt-2 w-full py-2 bg-yellow-500/10 hover:bg-yellow-500/20 border border-yellow-500/20 text-yellow-500 text-xs font-bold uppercase tracking-wider rounded transition-colors"
                            >
                                Close Position
                            </button>
                        </div>
                    ) : (
                        <div className="text-xs text-[#666] text-center py-6 font-medium">
                            No active positions
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
