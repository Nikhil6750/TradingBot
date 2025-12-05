import React, { useEffect, useRef, useState } from "react";
import { BASE_URL } from "../lib/api";
import { createChart, CrosshairMode } from "lightweight-charts";
import ErrorBoundary from "../components/ErrorBoundary";

export default function CSVWindowChart() {
  const [symbol, setSymbol] = useState("AUDCAD");
  const [tz, setTz] = useState("UTC");
  const [file, setFile] = useState(null);

  const [startTime, setStartTime] = useState("06:00");
  const [endTime, setEndTime] = useState("08:00");
  const [date, setDate] = useState("");

  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [rows, setRows] = useState([]);
  const [uploadedSymbols, setUploadedSymbols] = useState([]);

  const chartRef = useRef(null);
  const chartApiRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const volSeriesRef = useRef(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(120);
  const timerRef = useRef(null);
  const cachedCandlesRef = useRef([]);
  const cachedVolsRef = useRef([]);

  useEffect(() => {
    if (!chartRef.current || chartApiRef.current) return;
    const ch = createChart(chartRef.current, {
      layout: { background: { color: "#0b1220" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#1f2937" }, horzLines: { color: "#1f2937" } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
      autoSize: true,
    });
    const cs = ch.addCandlestickSeries({ upColor: "#22c55e", downColor: "#ef4444", borderVisible: false, wickUpColor: "#22c55e", wickDownColor: "#ef4444" });
    const vs = ch.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "", color: "#60a5fa" });
    chartApiRef.current = ch;
    candleSeriesRef.current = cs;
    volSeriesRef.current = vs;
    const onResize = () => ch.timeScale().fitContent();
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); ch.remove(); chartApiRef.current = null; };
  }, []);

  function deriveSymbolFromFilename(name = "") {
    const base = String(name).toUpperCase();
    let m = base.match(/FX_([A-Z]{3,12})/);
    if (m) return m[1];
    m = base.match(/BINANCE_([A-Z]{3,20})/);
    if (m) return m[1];
    m = base.match(/\b([A-Z]{3,12})\b/);
    return m ? m[1] : symbol;
  }

  const doUpload = async () => {
    setError("");
    setStatus("");
    if (!file) { setError("Choose a CSV first."); return; }
    const fd = new FormData();
    fd.append("file", file);
    try {
      const q = new URLSearchParams();
      if (symbol) q.set("symbol", symbol);
      if (tz) q.set("tz", tz);
      const res = await fetch(`${BASE_URL}/upload-csv?${q.toString()}`, { method: "POST", body: fd });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.error || data?.detail || res.statusText);
      const list = Array.isArray(data.symbols_loaded) ? data.symbols_loaded : [symbol];
      setUploadedSymbols(list);
      setStatus(`Loaded: ${list.join(", ")}`);
      if (list.length) setSymbol(list[0]);
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  const showChart = async () => {
    setError("");
    setStatus("");
    setRows([]);
    try {
      const q = new URLSearchParams();
      q.set("symbol", symbol);
      q.set("start_time", startTime);
      q.set("end_time", endTime);
      if (date) q.set("date", date);
      const res = await fetch(`${BASE_URL}/chart-data?${q.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data?.error || data?.detail || res.statusText);
      setRows(Array.isArray(data.rows) ? data.rows : []);
      if (chartApiRef.current && candleSeriesRef.current && volSeriesRef.current) {
        const candles = data.rows.map(r => ({
          time: Math.floor(new Date(r.time).getTime() / 1000),
          open: r.open, high: r.high, low: r.low, close: r.close,
        }));
        const vols = data.rows.map(r => ({ time: Math.floor(new Date(r.time).getTime() / 1000), value: r.volume }));
        cachedCandlesRef.current = candles;
        cachedVolsRef.current = vols;
        candleSeriesRef.current.setData(candles);
        volSeriesRef.current.setData(vols);
        chartApiRef.current.timeScale().fitContent();
      }
      if ((data.count || 0) === 0) setStatus("No data for that window/date.");
    } catch (e) {
      setError(String(e.message || e));
    }
  };

  return (
    <ErrorBoundary>
    <div className="p-4 grid gap-4" style={{ gridTemplateColumns: "320px 1fr" }}>
      {/* Left controls */}
      <div className="bg-neutral-900 border border-neutral-800 rounded p-3">
        <h3 className="text-lg mb-3">CSV Time Window</h3>
        <label className="block text-sm text-neutral-400">Symbol</label>
        <input className="w-full mb-2 px-2 py-1 bg-neutral-950 border border-neutral-700 rounded"
               value={symbol} onChange={e=>setSymbol(e.target.value)} placeholder="AUDCAD" />

        <label className="block text-sm text-neutral-400">Time Zone</label>
        <input className="w-full mb-2 px-2 py-1 bg-neutral-950 border border-neutral-700 rounded"
               value={tz} onChange={e=>setTz(e.target.value)} placeholder="UTC or Asia/Kolkata" />

        <label className="block text-sm text-neutral-400">CSV File</label>
        <input
          className="w-full mb-2 text-sm"
          type="file"
          accept=".csv"
          onChange={(e)=>{
            const f = e.target.files?.[0] || null;
            setFile(f);
            if (f) {
              const guess = deriveSymbolFromFilename(f.name);
              if (guess) setSymbol(guess);
            }
          }}
        />
        <button className="w-full mb-3 bg-emerald-600 text-white rounded px-3 py-2" onClick={doUpload}>Upload CSV</button>

        <label className="block text-sm text-neutral-400">Start Time (HH:MM)</label>
        <input className="w-full mb-2 px-2 py-1 bg-neutral-950 border border-neutral-700 rounded" type="time" value={startTime} onChange={e=>setStartTime(e.target.value)} />
        <label className="block text-sm text-neutral-400">End Time (HH:MM)</label>
        <input className="w-full mb-2 px-2 py-1 bg-neutral-950 border border-neutral-700 rounded" type="time" value={endTime} onChange={e=>setEndTime(e.target.value)} />

        <label className="block text-sm text-neutral-400">Date (optional)</label>
        <input className="w-full mb-3 px-2 py-1 bg-neutral-950 border border-neutral-700 rounded" type="date" value={date} onChange={e=>setDate(e.target.value)} />

        <button
          className="w-full bg-sky-600 text-white rounded px-3 py-2 disabled:opacity-60"
          onClick={showChart}
          disabled={uploadedSymbols.length === 0 || !symbol}
          title={uploadedSymbols.length ? "" : "Upload a CSV first"}
        >
          Show Chart
        </button>

        {rows.length > 0 && (
          <div className="mt-3 flex items-center gap-2 flex-wrap">
            <button className="bg-emerald-600 text-white rounded px-3 py-1 disabled:opacity-60" onClick={()=>{
              if (!cachedCandlesRef.current.length || isPlaying) return;
              setIsPlaying(true);
              // prime with first bar
              candleSeriesRef.current.setData([cachedCandlesRef.current[0]]);
              volSeriesRef.current.setData([cachedVolsRef.current[0]]);
              chartApiRef.current.timeScale().fitContent();
              let i = 1;
              clearInterval(timerRef.current);
              timerRef.current = setInterval(()=>{
                if (i >= cachedCandlesRef.current.length) {
                  clearInterval(timerRef.current);
                  setIsPlaying(false);
                  return;
                }
                candleSeriesRef.current.update(cachedCandlesRef.current[i]);
                volSeriesRef.current.update(cachedVolsRef.current[i]);
                chartApiRef.current.timeScale().fitContent();
                i += 1;
              }, speedMs);
            }} disabled={isPlaying}>Play</button>

            <button className="bg-neutral-700 text-white rounded px-3 py-1" onClick={()=>{ clearInterval(timerRef.current); setIsPlaying(false); }}>Pause</button>
            <button className="bg-neutral-700 text-white rounded px-3 py-1" onClick={()=>{
              clearInterval(timerRef.current);
              setIsPlaying(false);
              if (cachedCandlesRef.current.length) {
                candleSeriesRef.current.setData(cachedCandlesRef.current);
                volSeriesRef.current.setData(cachedVolsRef.current);
                chartApiRef.current.timeScale().fitContent();
              }
            }}>Reset</button>

            <label className="text-sm text-neutral-400 ml-2">Speed</label>
            <select className="bg-neutral-950 border border-neutral-700 rounded px-2 py-1 text-sm" value={speedMs} onChange={(e)=>setSpeedMs(Number(e.target.value))}>
              <option value={60}>60 ms</option>
              <option value={120}>120 ms</option>
              <option value={250}>250 ms</option>
              <option value={500}>500 ms</option>
            </select>
          </div>
        )}

        {status && <div className="mt-2 text-sm text-neutral-400">{status}</div>}
        {error && <div className="mt-2 text-sm text-red-400">{error}</div>}
      </div>

      {/* Right chart */}
      <div className="bg-neutral-900 border border-neutral-800 rounded p-2">
        <div ref={chartRef} style={{ width: "100%", height: "540px" }} />
      </div>
    </div>
    </ErrorBoundary>
  );
}
