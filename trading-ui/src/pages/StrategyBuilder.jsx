import axios from "axios";
import { useMemo, useState } from "react";
import { BASE_URL } from "../lib/api";
import ForexChart from "../components/ForexChart";
import SetupDetailChart from "../components/SetupDetailChart";

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

  // Strict filename formats:
  // - FX_<PAIR>.csv or FX_<PAIR>_<ANY>.csv
  // - BINANCE_<PAIR>.csv or BINANCE_<PAIR>_<ANY>.csv
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
  const [setups, setSetups] = useState([]);
  const [trades, setTrades] = useState([]);
  const [selectedSetup, setSelectedSetup] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const inferred = useMemo(() => inferMarketPairFromFilename(csvFile?.name), [csvFile]);

  const canRun = Boolean(csvFile) && !loading;

  const onRun = async () => {
    setError("");
    setLoading(true);
    setCandles([]);
    setSetups([]);
    setTrades([]);
    setSelectedSetup(null);
    try {
      const form = new FormData();
      form.append("file", csvFile);

      const res = await axios.post(`${BASE_URL}/run-backtest`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const data = res?.data || {};
      setCandles(Array.isArray(data.candles) ? data.candles : []);
      setSetups(Array.isArray(data.setups) ? data.setups : []);
      setTrades(Array.isArray(data.trades) ? data.trades : []);
    } catch (err) {
      setError(extractBackendError(err));
    } finally {
      setLoading(false);
    }
  };

  const sortedSetups = useMemo(() => {
    const list = Array.isArray(setups) ? setups : [];
    return [...list].sort((a, b) => Number(a?.time) - Number(b?.time));
  }, [setups]);

  const selectedTrade = useMemo(() => {
    const st = Number(selectedSetup?.time);
    if (!Number.isFinite(st)) return null;
    return (Array.isArray(trades) ? trades : []).find((t) => Number(t?.breaking_candle_time) === st) || null;
  }, [selectedSetup, trades]);

  return (
    <div className="h-screen flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-neutral-800 bg-neutral-950">
        <div className="flex items-center gap-3 min-w-0">
          <div className="text-lg font-semibold tracking-tight">AlgoTradeX</div>
          <div className="hidden md:flex items-center gap-2 text-xs text-neutral-500">
            <span className="px-2 py-1 rounded border border-neutral-800 bg-neutral-900">Timeframe: 5m</span>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          <label className="flex items-center gap-2 bg-neutral-900 border border-neutral-800 rounded-md px-3 py-2 text-sm text-neutral-300">
            <span className="text-neutral-500">CSV</span>
            <input
              type="file"
              accept=".csv,text/csv"
              className="text-sm file:mr-3 file:rounded-md file:border-0 file:bg-neutral-800 file:px-3 file:py-1.5 file:text-neutral-200 file:hover:bg-neutral-700"
              onChange={(e) => {
                const f = e.target.files?.[0] || null;
                setCsvFile(f);
                setCandles([]);
                setSetups([]);
                setTrades([]);
                setSelectedSetup(null);
                setError("");
              }}
            />
          </label>

          <div className="px-3 py-2 text-sm text-neutral-400 border border-neutral-800 rounded-md bg-neutral-900">
            {inferred.market ? `Market: ${inferred.market}` : "Market: -"}
          </div>

          <div className="px-3 py-2 text-sm text-neutral-400 border border-neutral-800 rounded-md bg-neutral-900">
            {inferred.pair ? `Pair: ${inferred.pair}` : "Pair: -"}
          </div>

          <div className="px-3 py-2 text-sm text-neutral-400 border border-neutral-800 rounded-md bg-neutral-900">
            5m
          </div>

          <button
            onClick={onRun}
            disabled={!canRun}
            className="rounded-md bg-emerald-500 disabled:bg-neutral-700 disabled:text-neutral-400 text-black font-semibold px-4 py-2 text-sm"
          >
            {loading ? "RUNNING..." : "RUN"}
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
      <div className="flex-1 min-h-0 grid gap-3 p-3" style={{ gridTemplateColumns: "1fr 420px" }}>
        {/* Left column */}
        <div className="min-h-0 flex flex-col gap-3">
          {/* Main Chart (candles only) */}
          <div className="flex-1 min-h-0 bg-neutral-900 border border-neutral-800 rounded-lg p-3 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-neutral-200">Main Chart</div>
              <div className="text-xs text-neutral-500">Candles: {candles.length}</div>
            </div>
            <div className="flex-1 min-h-0">
              <ForexChart candles={candles} />
            </div>
          </div>

          {/* Setup Detail (one setup per chart) */}
          <div className="flex-1 min-h-0 bg-neutral-900 border border-neutral-800 rounded-lg p-3 flex flex-col gap-2">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="text-sm font-semibold text-neutral-200">Setup Detail</div>
                <div className="text-xs text-neutral-500">
                  {selectedSetup ? (
                    <>
                      {formatTime(selectedSetup.time)} · {selectedSetup.direction} · Streak {selectedSetup.streak_length} · PB{" "}
                      {selectedSetup.pullback_length} · Target {Number(selectedSetup.target).toFixed(5)}
                      {selectedTrade ? " · Trade: YES" : " · Trade: NO"}
                    </>
                  ) : (
                    "Click a setup to open a dedicated chart."
                  )}
                </div>
              </div>

              {selectedSetup && (
                <button
                  type="button"
                  onClick={() => setSelectedSetup(null)}
                  className="shrink-0 rounded-md border border-neutral-700 bg-neutral-900 px-3 py-1.5 text-xs text-neutral-200 hover:bg-neutral-800/60"
                >
                  Close
                </button>
              )}
            </div>

            <div className="flex-1 min-h-0 border border-neutral-800 rounded-md overflow-hidden bg-neutral-950">
              {selectedSetup ? (
                <SetupDetailChart candles={candles} setup={selectedSetup} trade={selectedTrade} />
              ) : (
                <div className="h-full w-full flex items-center justify-center text-sm text-neutral-500">
                  No setup selected.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right column: Setup Explorer */}
        <div className="min-h-0 bg-neutral-900 border border-neutral-800 rounded-lg p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-semibold text-neutral-200">Setup Explorer</div>
            <div className="text-xs text-neutral-500">
              Setups: {sortedSetups.length} · Trades: {trades.length}
            </div>
          </div>

          {sortedSetups.length === 0 ? (
            <div className="text-sm text-neutral-500 px-1 py-6">No setups.</div>
          ) : (
            <div className="flex-1 min-h-0 overflow-auto border border-neutral-800 rounded-md">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-neutral-900 border-b border-neutral-800 text-neutral-400">
                  <tr>
                    <th className="text-left font-medium px-3 py-2">#</th>
                    <th className="text-left font-medium px-3 py-2">Time</th>
                    <th className="text-left font-medium px-3 py-2">Dir</th>
                    <th className="text-right font-medium px-3 py-2">Streak</th>
                    <th className="text-right font-medium px-3 py-2">PB</th>
                    <th className="text-right font-medium px-3 py-2">Target</th>
                    <th className="text-right font-medium px-3 py-2">Trade</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedSetups.map((s, idx) => {
                    const isSelected = Number(selectedSetup?.time) === Number(s?.time);
                    const hasTrade =
                      (Array.isArray(trades) ? trades : []).find((t) => Number(t?.breaking_candle_time) === Number(s?.time)) != null;
                    return (
                      <tr
                        key={`${s?.time}-${idx}`}
                        className={[
                          "border-t border-neutral-800 cursor-pointer",
                          isSelected ? "bg-neutral-800/40" : "hover:bg-neutral-800/30",
                        ].join(" ")}
                        onClick={() => setSelectedSetup(s)}
                      >
                        <td className="px-3 py-2 text-neutral-300">{idx + 1}</td>
                        <td className="px-3 py-2 text-neutral-300">
                          <div className="text-xs text-neutral-500">{formatTime(s?.time)}</div>
                          <div className="text-xs text-neutral-600">{s?.time}</div>
                        </td>
                        <td className={`px-3 py-2 font-semibold ${s?.direction === "BUY" ? "text-emerald-300" : "text-red-300"}`}>
                          {s?.direction}
                        </td>
                        <td className="px-3 py-2 text-right text-neutral-300">{s?.streak_length}</td>
                        <td className="px-3 py-2 text-right text-neutral-300">{s?.pullback_length}</td>
                        <td className="px-3 py-2 text-right text-neutral-300">{Number(s?.target).toFixed(5)}</td>
                        <td className="px-3 py-2 text-right text-neutral-300">{hasTrade ? "YES" : "NO"}</td>
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
