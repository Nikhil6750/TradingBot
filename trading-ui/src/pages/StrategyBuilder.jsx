import axios from "axios";
import { useMemo, useState } from "react";
import { BASE_URL } from "../lib/api";
import ForexChart from "../components/charts/ForexChart";
import SetupDetailChart from "../components/charts/SetupDetailChart";

function formatTime(sec) {
  const v = Number(sec);
  if (!Number.isFinite(v)) return "-";
  return new Date(v * 1000).toISOString().replace("T", " ").replace(".000Z", "Z");
}

function extractBackendError(err) {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status;
    const data = err.response?.data;
    if (typeof data === "string" && data.trim()) return data;
    if (data?.detail) return String(data.detail);
    if (data?.error) return String(data.error);
    if (status) return `HTTP ${status}`;
    return err.message || "Request failed";
  }
  return String(err?.message || err || "Unknown error");
}

function inferMarketPairFromFilename(filename) {
  const name = String(filename || "");
  if (!name) return { market: "", pair: "", error: "" };
  if (name.slice(-4).toLowerCase() !== ".csv") {
    return { market: "", pair: "", error: "Invalid CSV filename format" };
  }
  const stem = name.slice(0, -4);
  if (stem.startsWith("FX_")) {
    const rest = stem.slice("FX_".length);
    const pair = rest.split("_", 1)[0] || "";
    if (!pair) return { market: "", pair: "", error: "Invalid CSV filename format" };
    return { market: "forex", pair, error: "" };
  }
  if (stem.startsWith("BINANCE_")) {
    const rest = stem.slice("BINANCE_".length);
    const pair = rest.split("_", 1)[0] || "";
    if (!pair) return { market: "", pair: "", error: "Invalid CSV filename format" };
    return { market: "crypto", pair, error: "" };
  }
  return { market: "", pair: "", error: "Invalid CSV filename format" };
}

export default function StrategyBuilder() {
  const [csvFile, setCsvFile] = useState(null);

  const [candles, setCandles] = useState([]);
  const [buySignals, setBuySignals] = useState([]);
  const [sellSignals, setSellSignals] = useState([]);
  const [trades, setTrades] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [selectedTrade, setSelectedTrade] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const inferred = useMemo(() => inferMarketPairFromFilename(csvFile?.name), [csvFile]);

  // Strategy Configuration State
  const [mode, setMode] = useState("template"); // template, parameter, rules
  const [strategyTemplate, setStrategyTemplate] = useState("ma_crossover");
  const [templateParams, setTemplateParams] = useState({
    short_ma_period: 10, long_ma_period: 50,
    lookback_period: 20, deviation_threshold: 2.0,
    rsi_period: 14, oversold_level: 30, overbought_level: 70,
    breakout_period: 20, volume_confirmation: true,
    stop_loss: 0.02, take_profit: 0.04
  });

  const [customRules, setCustomRules] = useState({
    buy: "rsi < 30 AND close > ma50",
    sell: "rsi > 70"
  });

  const [jsonRules, setJsonRules] = useState(JSON.stringify({
    buy_rules: [{ "indicator": "rsi", "operator": "<", "value": 30 }],
    sell_rules: [{ "indicator": "rsi", "operator": ">", "value": 70 }]
  }, null, 2));

  const canRun = Boolean(csvFile) && !loading;

  const onRun = async () => {
    setError("");
    setLoading(true);
    setCandles([]);
    setBuySignals([]);
    setSellSignals([]);
    setTrades([]);
    setMetrics(null);
    setSelectedTrade(null);

    try {
      const form = new FormData();
      form.append("file", csvFile);

      let configObj = { mode, stop_loss: Number(templateParams.stop_loss), take_profit: Number(templateParams.take_profit) };

      if (mode === "template") {
        configObj.strategy = strategyTemplate;
        configObj.parameters = templateParams;
      } else if (mode === "parameter") {
        configObj.rules = customRules;
        configObj.indicators = { "rsi": { period: 14 }, "ma50": { period: 50 } }; // simplification
      } else if (mode === "rules") {
        try {
          const parsed = JSON.parse(jsonRules);
          configObj.buy_rules = parsed.buy_rules || [];
          configObj.sell_rules = parsed.sell_rules || [];
        } catch (e) {
          throw new Error("Invalid JSON in Rule Builder");
        }
      } else if (mode === "code") {
        configObj.code_string = config.codeString || "";
      }

      form.append("config", JSON.stringify(configObj));

      const res = await axios.post(`${BASE_URL}/run-backtest`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = res?.data || {};
      setCandles(Array.isArray(data.candles) ? data.candles : []);
      setBuySignals(Array.isArray(data.buy_signals) ? data.buy_signals : []);
      setSellSignals(Array.isArray(data.sell_signals) ? data.sell_signals : []);
      setTrades(Array.isArray(data.trades) ? data.trades : []);
      setMetrics(data.metrics || null);
    } catch (err) {
      setError(extractBackendError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen flex flex-col bg-neutral-950 text-neutral-300">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-neutral-800 bg-neutral-950">
        <div className="flex items-center gap-3 min-w-0">
          <div className="text-lg font-semibold tracking-tight text-white">AlgoTradeX Strategy Engine</div>
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          <label className="flex items-center gap-2 bg-neutral-900 border border-neutral-800 rounded-md px-3 py-2 text-sm text-neutral-300">
            <span className="text-neutral-500">CSV</span>
            <input
              type="file"
              accept=".csv,text/csv"
              className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-neutral-800 file:px-3 file:py-1 file:text-neutral-200 file:hover:bg-neutral-700"
              onChange={(e) => {
                setCsvFile(e.target.files?.[0] || null);
                setError("");
              }}
            />
          </label>
          <button
            onClick={onRun}
            disabled={!canRun}
            className="rounded-md bg-emerald-500 hover:bg-emerald-400 disabled:bg-neutral-700 disabled:text-neutral-500 text-black font-semibold px-6 py-2 text-sm transition-colors cursor-pointer"
          >
            {loading ? "RUNNING..." : "RUN BACKTEST"}
          </button>
        </div>
      </div>

      {(inferred.error || error) && (
        <div className="px-3 pt-3">
          <div className="rounded-md border border-red-900 bg-red-950/40 px-3 py-2 text-sm text-red-200">
            {inferred.error || error}
          </div>
        </div>
      )}

      {/* Panels */}
      <div className="flex-1 min-h-0 grid gap-3 p-3 overflow-hidden" style={{ gridTemplateColumns: "350px 1fr 350px" }}>

        {/* Left column: Strategy Configuration */}
        <div className="min-h-0 bg-neutral-900 border border-neutral-800 rounded-lg p-4 flex flex-col gap-4 overflow-y-auto custom-scrollbar">
          <div className="text-md font-semibold text-white border-b border-neutral-800 pb-2">Strategy Configuration</div>

          <div className="flex flex-col gap-2">
            <label className="text-sm text-neutral-400">Creation Mode</label>
            <select
              value={mode}
              onChange={e => setMode(e.target.value)}
              className="bg-neutral-950 border border-neutral-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            >
              <option value="template">Strategy Templates</option>
              <option value="parameter">Parameter Customization</option>
              <option value="rules">Rule Builder</option>
            </select>
          </div>

          {mode === "template" && (
            <div className="flex flex-col gap-4 animate-fade-in">
              <div className="flex flex-col gap-2">
                <label className="text-sm text-neutral-400">Template</label>
                <select
                  value={strategyTemplate}
                  onChange={e => setStrategyTemplate(e.target.value)}
                  className="bg-neutral-950 border border-neutral-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="ma_crossover">Moving Average Crossover</option>
                  <option value="mean_reversion">Mean Reversion</option>
                  <option value="rsi_reversal">RSI Reversal</option>
                  <option value="breakout">Breakout Strategy</option>
                </select>
              </div>

              {strategyTemplate === "ma_crossover" && (
                <>
                  <div className="flex gap-2">
                    <div className="flex-1 flex flex-col gap-1"><label className="text-xs text-neutral-500">Short MA</label><input type="number" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-sm" value={templateParams.short_ma_period} onChange={e => setTemplateParams({ ...templateParams, short_ma_period: e.target.value })} /></div>
                    <div className="flex-1 flex flex-col gap-1"><label className="text-xs text-neutral-500">Long MA</label><input type="number" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-sm" value={templateParams.long_ma_period} onChange={e => setTemplateParams({ ...templateParams, long_ma_period: e.target.value })} /></div>
                  </div>
                </>
              )}
              {strategyTemplate === "mean_reversion" && (
                <>
                  <div className="flex gap-2">
                    <div className="flex-1 flex flex-col gap-1"><label className="text-xs text-neutral-500">Lookback</label><input type="number" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-sm" value={templateParams.lookback_period} onChange={e => setTemplateParams({ ...templateParams, lookback_period: e.target.value })} /></div>
                    <div className="flex-1 flex flex-col gap-1"><label className="text-xs text-neutral-500">Dev Thresh</label><input type="number" step="0.1" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-sm" value={templateParams.deviation_threshold} onChange={e => setTemplateParams({ ...templateParams, deviation_threshold: e.target.value })} /></div>
                  </div>
                </>
              )}
              {strategyTemplate === "rsi_reversal" && (
                <>
                  <div className="flex gap-2">
                    <div className="flex-1 flex flex-col gap-1"><label className="text-xs text-neutral-500">RSI Period</label><input type="number" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-sm" value={templateParams.rsi_period} onChange={e => setTemplateParams({ ...templateParams, rsi_period: e.target.value })} /></div>
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1 flex flex-col gap-1"><label className="text-xs text-neutral-500">Oversold</label><input type="number" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-sm" value={templateParams.oversold_level} onChange={e => setTemplateParams({ ...templateParams, oversold_level: e.target.value })} /></div>
                    <div className="flex-1 flex flex-col gap-1"><label className="text-xs text-neutral-500">Overbought</label><input type="number" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-sm" value={templateParams.overbought_level} onChange={e => setTemplateParams({ ...templateParams, overbought_level: e.target.value })} /></div>
                  </div>
                </>
              )}
            </div>
          )}

          {mode === "parameter" && (
            <div className="flex flex-col gap-3 animate-fade-in">
              <p className="text-xs text-neutral-500">Write boolean logic using indicator names, `AND`, and `OR`.</p>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-emerald-400">Buy Condition</label>
                <input type="text" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-2 text-sm font-mono" placeholder="rsi < 30 AND close > ma50" value={customRules.buy} onChange={e => setCustomRules({ ...customRules, buy: e.target.value })} />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-xs text-red-400">Sell Condition</label>
                <input type="text" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-2 text-sm font-mono" placeholder="rsi > 70" value={customRules.sell} onChange={e => setCustomRules({ ...customRules, sell: e.target.value })} />
              </div>
            </div>
          )}

          {mode === "rules" && (
            <div className="flex flex-col gap-2 animate-fade-in h-64">
              <p className="text-xs text-neutral-500 pb-2">Direct JSON Rule Engine Definition.</p>
              <textarea
                className="flex-1 bg-neutral-950 border border-neutral-800 rounded px-3 py-2 text-xs font-mono text-neutral-300 resize-none focus:outline-none focus:border-blue-500"
                value={jsonRules}
                onChange={e => setJsonRules(e.target.value)}
                spellCheck={false}
              />
            </div>
          )}

          <div className="border-t border-neutral-800 pt-4 mt-2 flex gap-2">
            <div className="flex-1 flex flex-col gap-1"><label className="text-xs text-neutral-500">Stop Loss (%)</label><input type="number" step="0.01" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-sm" value={templateParams.stop_loss} onChange={e => setTemplateParams({ ...templateParams, stop_loss: e.target.value })} /></div>
            <div className="flex-1 flex flex-col gap-1"><label className="text-xs text-neutral-500">Take Profit (%)</label><input type="number" step="0.01" className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-sm" value={templateParams.take_profit} onChange={e => setTemplateParams({ ...templateParams, take_profit: e.target.value })} /></div>
          </div>
        </div>

        {/* Center column: Charts */}
        <div className="min-h-0 flex flex-col gap-3">
          <div className="flex-1 min-h-0 bg-neutral-900 border border-neutral-800 rounded-lg p-3 flex flex-col gap-2 relative">
            <div className="absolute top-4 right-4 z-10 flex gap-4 bg-neutral-950/80 px-4 py-2 rounded-full border border-neutral-800 backdrop-blur-sm shadow-xl">
              <div className="flex flex-col items-center"><span className="text-[10px] text-neutral-500 uppercase font-bold tracking-wider">Win Rate</span><span className={`text-sm font-bold ${metrics?.win_rate > 0.5 ? 'text-emerald-400' : 'text-neutral-300'}`}>{metrics ? (metrics.win_rate * 100).toFixed(1) + "%" : "-"}</span></div>
              <div className="flex flex-col items-center"><span className="text-[10px] text-neutral-500 uppercase font-bold tracking-wider">Return</span><span className={`text-sm font-bold ${metrics?.total_return > 0 ? 'text-emerald-400' : (metrics?.total_return < 0 ? 'text-red-400' : 'text-neutral-300')}`}>{metrics ? (metrics.total_return * 100).toFixed(2) + "%" : "-"}</span></div>
              <div className="flex flex-col items-center"><span className="text-[10px] text-neutral-500 uppercase font-bold tracking-wider">Trades</span><span className="text-sm font-bold text-neutral-300">{trades.length || "-"}</span></div>
            </div>
            <div className="text-sm font-semibold text-neutral-200">Price Chart</div>
            <div className="flex-1 min-h-0 rounded-md overflow-hidden">
              <ForexChart candles={candles} />
            </div>
          </div>
        </div>

        {/* Right column: Trades Explorer */}
        <div className="min-h-0 bg-neutral-900 border border-neutral-800 rounded-lg p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between border-b border-neutral-800 pb-2">
            <div className="text-sm font-semibold text-white">Trade History</div>
          </div>

          {trades.length === 0 ? (
            <div className="text-sm text-neutral-500 px-1 py-6 flex flex-col items-center justify-center h-full gap-2">
              <svg className="w-8 h-8 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>
              <span>No trades executed.</span>
            </div>
          ) : (
            <div className="flex-1 min-h-0 overflow-auto custom-scrollbar">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-neutral-900 shadow-md text-neutral-500 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="text-left font-medium px-2 py-3">Time</th>
                    <th className="text-left font-medium px-2 py-3">Type</th>
                    <th className="text-right font-medium px-2 py-3">Entry</th>
                    <th className="text-right font-medium px-2 py-3">PnL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-800/50">
                  {trades.map((t, idx) => {
                    const isWin = t.pnl > 0;
                    return (
                      <tr
                        key={idx}
                        className="hover:bg-neutral-800/40 transition-colors cursor-pointer"
                        onClick={() => setSelectedTrade(t)}
                      >
                        <td className="px-2 py-3 text-neutral-400 whitespace-nowrap">
                          {formatTime(t.exit_time).split(' ')[1].slice(0, 5)}
                        </td>
                        <td className={`px-2 py-3 font-semibold text-xs ${t.type === "BUY" ? "text-emerald-400/90" : "text-red-400/90"}`}>
                          {t.type}
                        </td>
                        <td className="px-2 py-3 text-right text-neutral-300 font-mono text-xs">{t.entry_price.toFixed(5)}</td>
                        <td className={`px-2 py-3 text-right font-mono text-xs font-semibold ${isWin ? 'text-emerald-400' : 'text-red-400'}`}>
                          {isWin ? '+' : ''}{(t.pnl * 100).toFixed(2)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
