import React, { useEffect, useRef, useState } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";

function guessSymbolFromName(name) {
  const u = String(name || "").toUpperCase();
  let m = u.match(/FX_([A-Z]{3,12})/); if (m) return m[1];
  m = u.match(/BINANCE_([A-Z0-9]{3,20})/); if (m) return m[1];
  m = u.match(/\b([A-Z]{3,12})\b/); return m ? m[1] : "";
}

function parseCSV(text) {
  const lines = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split(/\n+/).filter(Boolean);
  if (lines.length < 2) throw new Error("CSV has no data");
  const header = lines[0].split(",").map(h => h.trim().toLowerCase());
  const idx = (name) => header.findIndex(h => h === name);
  const timeIdx = idx("timestamp") >= 0 ? idx("timestamp") : idx("time");
  const oIdx = idx("open"), hIdx = idx("high"), lIdx = idx("low"), cIdx = idx("close");
  let vIdx = idx("volume"); if (vIdx < 0) vIdx = header.findIndex(h => h === "vol" || h === "volume_usd");
  if (timeIdx < 0 || oIdx < 0 || hIdx < 0 || lIdx < 0 || cIdx < 0) {
    throw new Error("CSV must have time/timestamp, open, high, low, close columns");
  }
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(",");
    if (parts.length < 5) continue;
    const tRaw = (parts[timeIdx] || "").trim();
    let tms;
    if (/^\d+$/.test(tRaw)) {
      // epoch seconds vs millis vs nanos
      const num = Number(tRaw);
      if (tRaw.length >= 13) tms = Math.floor(num); // ms or ns approximated
      else tms = num * 1000;
    } else {
      tms = Date.parse(tRaw);
    }
    if (!Number.isFinite(tms)) continue;
    const open = Number(parts[oIdx]);
    const high = Number(parts[hIdx]);
    const low  = Number(parts[lIdx]);
    const close = Number(parts[cIdx]);
    const vol = vIdx >= 0 ? Number(parts[vIdx]) : 0;
    if ([open,high,low,close].some(x => !Number.isFinite(x))) continue;
    rows.push({
      timeSec: Math.floor(tms/1000),
      open, high, low, close, volume: Number.isFinite(vol) ? vol : 0,
      iso: new Date(tms).toISOString(),
    });
  }
  rows.sort((a,b) => a.timeSec - b.timeSec);
  return rows;
}

export default function CSVPlotter() {
  const canvasRef = useRef(null);
  const chartRef = useRef(null);
  const candleRef = useRef(null);
  const volRef = useRef(null);
  const [file, setFile] = useState(null);
  const [symbol, setSymbol] = useState("");
  const [allRows, setAllRows] = useState([]);
  const [rows, setRows] = useState([]);
  const [from, setFrom] = useState(""); // datetime-local
  const [to, setTo] = useState("");   // datetime-local
  const [goto, setGoto] = useState("");
  const [replay, setReplay] = useState(true);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(800);
  const timer = useRef(null);
  const replayIndexRef = useRef(0);
  const [barInfo, setBarInfo] = useState(null);
  const [showVolume, setShowVolume] = useState(true);
  const [density, setDensity] = useState(10); // bar spacing
  const priceLinesRef = useRef([]);
  // Strategy v2 controls/state
  const [useStrategy, setUseStrategy] = useState(false);
  const [signalsOnly, setSignalsOnly] = useState(false);
  const [showMarkers, setShowMarkers] = useState(true);
  const [showLevels, setShowLevels] = useState(true);
  const [autoZoom, setAutoZoom] = useState(true);
  const [tickSize, setTickSize] = useState(0.0001);
  const [params, setParams] = useState({
    min_streak: 4,
    pullback_max: 2,
    atr_period: 14,
    sl_atr_k: 1.6,
    tp_rr: 1.8,
    entry_type: 'stop', // or 'close_break'
  });
  const [signals, setSignals] = useState([]);
  const keepIndexSetRef = useRef(new Set());
  const signalByFillIndexRef = useRef(new Map());

  useEffect(() => {
    if (!canvasRef.current || chartRef.current) return;
    const ch = createChart(canvasRef.current, {
      layout: { background: { color: "#0b1220" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#172036" }, horzLines: { color: "#172036" } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, rightOffset: 8, barSpacing: density, timeVisible: true },
      autoSize: true,
    });
    const cs = ch.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      priceScaleId: 'right',
      scaleMargins: { top: 0.08, bottom: 0.22 },
    });
    const vs = ch.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
      color: "#3b82f6",
      scaleMargins: { top: 0.78, bottom: 0 }, // bottom 22% for volume
    });
    chartRef.current = ch; candleRef.current = cs; volRef.current = vs;
    const onResize = () => ch.timeScale().fitContent();
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); ch.remove(); };
  }, []);

  const plot = (arr) => {
    const candles = arr.map(r => ({ time: r.timeSec, open:r.open, high:r.high, low:r.low, close:r.close }));
    const vols = arr.map(r => ({ time: r.timeSec, value: r.volume }));
    candleRef.current.setData(candles);
    volRef.current.setData(vols);
    chartRef.current.timeScale().fitContent();
  };

  // ---------- Strategy helpers ----------
  function atrWilder(rows, period) {
    const tr = new Array(rows.length).fill(0);
    for (let i=0;i<rows.length;i++){
      const r = rows[i];
      const prev = i>0 ? rows[i-1] : r;
      const hl = r.high - r.low;
      const hc = Math.abs(r.high - prev.close);
      const lc = Math.abs(r.low - prev.close);
      tr[i] = Math.max(hl, hc, lc);
    }
    const out = new Array(rows.length).fill(NaN);
    let prevATR = 0;
    for (let i=0;i<rows.length;i++){
      if (i === period-1){ let s=0; for(let k=0;k<period;k++) s+=tr[k]; prevATR = s/period; out[i]=prevATR; continue; }
      if (i >= period){ prevATR = (prevATR*(period-1) + tr[i]) / period; out[i]=prevATR; }
    }
    return out;
  }
  function parseSessionStr(str){
    if (!str) return [];
    const parts = String(str).split(',').map(s=>s.trim()).filter(Boolean);
    const out=[]; for (const p of parts){ const m=p.match(/^(\d{2}):(\d{2})\-(\d{2}):(\d{2})$/); if(!m) continue; const a=+m[1]*60+ +m[2]; const b=+m[3]*60+ +m[4]; out.push([a,b]); }
    return out;
  }
  function inSessions(tsMs, ranges){ if(!ranges||!ranges.length) return true; const d=new Date(tsMs); const t=d.getUTCHours()*60+d.getUTCMinutes(); return ranges.some(([a,b])=> t>=a && t<=b); }

  function detectStreakPullbackSignals(rows, params, opts={ session:"", max_spread:null }){
    const { min_streak, pullback_max, atr_period, sl_atr_k, tp_rr, entry_type } = params;
    const atr = atrWilder(rows, atr_period);
    const sessions = parseSessionStr(opts.session||"");
    const sigs = [];
    const seenFill = new Set(); // avoid duplicate signals for same fill bar
    let activeUntil = -1;
    for (let i = min_streak + pullback_max + 1; i < rows.length; i++){
      if (i <= activeUntil) continue;
      const streakEnd = i - 1;
      // LONG side
      let pb_len = 0, k = streakEnd;
      while (k >= 0 && (rows[k].close < rows[k].open) && pb_len < pullback_max){ pb_len++; k--; }
      if (pb_len >= 1){
        let ok=true; for (let j=k-min_streak+1;j<=k;j++){ if (j<0 || !(rows[j].close > rows[j].open)){ ok=false; break; } }
        if (ok){
          const streakLow = Math.min(...rows.slice(k-min_streak+1, k+1).map(r=>r.low));
          const streakHigh = Math.max(...rows.slice(k-min_streak+1, k+1).map(r=>r.high));
          const pbLow = Math.min(...rows.slice(k+1, k+1+pb_len).map(r=>r.low));
          const pbHigh = Math.max(...rows.slice(k+1, k+1+pb_len).map(r=>r.high));
          if (!(pbLow < streakLow || pbHigh >= streakHigh)){
            if (opts.max_spread != null && Number.isFinite(rows[i].spread||NaN) && rows[i].spread > opts.max_spread){}
            else if (!inSessions(rows[i].timeSec*1000, sessions)){}
            else {
              const entryLevel = entry_type === 'stop' ? (pbHigh + tickSize) : pbHigh;
              let fillIdx=-1, entryPrice=entryLevel;
              for (let j=i; j<rows.length; j++){
                const r=rows[j];
                if (r.low < streakLow) { fillIdx=-1; break; }
                if (entry_type==='stop'){ if (r.high >= entryLevel){ fillIdx=j; break; } }
                else { if (r.close > pbHigh){ fillIdx=j; entryPrice=r.close; break; } }
              }
              if (fillIdx>=0){
                const a=atr[fillIdx]; const atrSL = entryPrice - a*sl_atr_k; const sl = Math.min(pbLow, atrSL); const tp = entryPrice + (entryPrice - sl)*tp_rr;
                let exitIdx=-1; for (let j=fillIdx; j<rows.length; j++){ const r=rows[j]; if (r.low <= sl){ exitIdx=j; break; } if (r.high >= tp){ exitIdx=j; break; } }
                if (exitIdx<0) exitIdx=rows.length-1;
                if (!seenFill.has(fillIdx)) {
                  sigs.push({ side:'long', startIdx:i, fillIdx, exitIdx, k_end:k, pb_len, streakLow, streakHigh, pbLow, pbHigh, entry:entryPrice, sl, tp });
                  seenFill.add(fillIdx);
                }
                activeUntil = exitIdx;
              }
            }
          }
        }
      }
      // SHORT side
      pb_len = 0; k = streakEnd;
      while (k >= 0 && (rows[k].close > rows[k].open) && pb_len < pullback_max){ pb_len++; k--; }
      if (pb_len >= 1){
        let ok=true; for (let j=k-min_streak+1;j<=k;j++){ if (j<0 || !(rows[j].close < rows[j].open)){ ok=false; break; } }
        if (ok){
          const streakLow = Math.min(...rows.slice(k-min_streak+1, k+1).map(r=>r.low));
          const streakHigh = Math.max(...rows.slice(k-min_streak+1, k+1).map(r=>r.high));
          const pbLow = Math.min(...rows.slice(k+1, k+1+pb_len).map(r=>r.low));
          const pbHigh = Math.max(...rows.slice(k+1, k+1+pb_len).map(r=>r.high));
          if (!(pbHigh > streakHigh || pbLow <= streakLow)){
            if (opts.max_spread != null && Number.isFinite(rows[i].spread||NaN) && rows[i].spread > opts.max_spread){}
            else if (!inSessions(rows[i].timeSec*1000, sessions)){}
            else {
              const entryLevel = entry_type === 'stop' ? (pbLow - tickSize) : pbLow;
              let fillIdx=-1, entryPrice=entryLevel;
              for (let j=i; j<rows.length; j++){
                const r=rows[j];
                if (r.high > streakHigh) { fillIdx=-1; break; }
                if (entry_type==='stop'){ if (r.low <= entryLevel){ fillIdx=j; break; } }
                else { if (r.close < pbLow){ fillIdx=j; entryPrice=r.close; break; } }
              }
              if (fillIdx>=0){
                const a=atr[fillIdx]; const atrSL = entryPrice + a*sl_atr_k; const sl = Math.max(pbHigh, atrSL); const tp = entryPrice - (sl - entryPrice)*tp_rr;
                let exitIdx=-1; for (let j=fillIdx; j<rows.length; j++){ const r=rows[j]; if (r.high >= sl){ exitIdx=j; break; } if (r.low <= tp){ exitIdx=j; break; } }
                if (exitIdx<0) exitIdx=rows.length-1;
                if (!seenFill.has(fillIdx)) {
                  sigs.push({ side:'short', startIdx:i, fillIdx, exitIdx, k_end:k, pb_len, streakLow, streakHigh, pbLow, pbHigh, entry:entryPrice, sl, tp });
                  seenFill.add(fillIdx);
                }
                activeUntil = exitIdx;
              }
            }
          }
        }
      }
    }
    return sigs;
  }

  function rebuildSignalIndexMaps(sigs){
    const keep = new Set(); const byFill = new Map();
    for (const s of sigs){ for (let i=s.fillIdx; i<=s.exitIdx; i++) keep.add(i); byFill.set(s.fillIdx, s); }
    keepIndexSetRef.current = keep; signalByFillIndexRef.current = byFill;
  }
  function drawSignalLines(sig){
    priceLinesRef.current.forEach(l => candleRef.current.removePriceLine(l)); priceLinesRef.current = [];
    if (!showLevels) return;
    const add = (price, color) => { const l = candleRef.current.createPriceLine({ price, color, lineWidth: 2, lineStyle: 2 }); priceLinesRef.current.push(l); };
    add(sig.entry, '#22c55e'); add(sig.sl, '#ef4444'); add(sig.tp, '#60a5fa');
  }

  // Simple, safe markers: draw amber ALERT squares at each fill bar
  function refreshMarkers(){
    if (!candleRef.current) return;
    if (!showMarkers) { candleRef.current.setMarkers([]); return; }
    const ms = (signals || []).map(s => ({
      time: rows[s.fillIdx]?.timeSec,
      position: 'aboveBar',
      color: '#f59e0b',
      shape: 'square',
      text: 'ALERT',
    })).filter(m => m.time);
    candleRef.current.setMarkers(ms);
  }
  function applyStrategyNow(){
    if (!rows.length) return;
    const sigs = detectStreakPullbackSignals(rows, params, { session: '', max_spread: null });
    setSignals(sigs); rebuildSignalIndexMaps(sigs);
    refreshMarkers();
    if (sigs.length){
      drawSignalLines(sigs[0]);
      if (autoZoom){
        const a=Math.max(0,sigs[0].fillIdx-50), b=Math.min(rows.length-1, sigs[0].exitIdx+50);
        chartRef.current.timeScale().setVisibleRange({ from: rows[a].timeSec, to: rows[b].timeSec });
      }
    }
  }

  // Reflect toggles & density changes
  useEffect(() => {
    if (volRef.current) volRef.current.applyOptions({ visible: showVolume });
    if (candleRef.current) {
      candleRef.current.applyOptions({
        scaleMargins: showVolume ? { top: 0.08, bottom: 0.22 } : { top: 0.06, bottom: 0.06 },
      });
    }
  }, [showVolume]);
  useEffect(() => {
    if (chartRef.current) chartRef.current.timeScale().applyOptions({ barSpacing: density });
  }, [density]);

  // Keep markers in sync with toggles/data
  useEffect(() => { refreshMarkers(); }, [showMarkers, rows, signals]);

  const onPlot = async () => {
    if (!file) return;
    const text = await file.text();
    const arr = parseCSV(text);
    setAllRows(arr);
    setRows(arr);
    setSymbol(guessSymbolFromName(file.name));
    // init date range controls using dataset
    if (arr.length) {
      const first = new Date(arr[0].timeSec * 1000);
      const last = new Date(arr[arr.length-1].timeSec * 1000);
      const toLocal = (d) => new Date(d.getTime() - d.getTimezoneOffset()*60000).toISOString().slice(0,16);
      setFrom(toLocal(first)); setTo(toLocal(last)); setGoto("");
    }
    plot(arr);
  };

  const onFilter = () => {
    if (!allRows.length) return;
    const f = from ? Date.parse(from) : -Infinity;
    const t = to ? Date.parse(to) : Infinity;
    const arr = allRows.filter(r => (r.timeSec*1000 >= f) && (r.timeSec*1000 <= t));
    setRows(arr);
    plot(arr);
  };

  const startReplayFromFrom = () => {
    if (!rows.length) return;
    stopReplay();
    setPlaying(true);
    // prime with first bar
    const first = rows[0];
    candleRef.current.setData([{ time:first.timeSec, open:first.open, high:first.high, low:first.low, close:first.close }]);
    volRef.current.setData([{ time:first.timeSec, value:first.volume }]);
    chartRef.current.timeScale().fitContent();
    replayIndexRef.current = 1;
  };

  const stepReplay = () => {
    let i = replayIndexRef.current || 1;
    if (i >= rows.length) { stopReplay(); return; }
    if (useStrategy && signalsOnly && keepIndexSetRef.current.size){
      while (i < rows.length && !keepIndexSetRef.current.has(i)) i++;
      if (i >= rows.length) { stopReplay(); return; }
    }
    const r = rows[i];
    candleRef.current.update({ time:r.timeSec, open:r.open, high:r.high, low:r.low, close:r.close });
    volRef.current.update({ time:r.timeSec, value:r.volume });
    chartRef.current.timeScale().fitContent();
    const prev = rows[i-1];
    const move = prev ? (r.close - prev.close) : 0;
    setBarInfo({ r, move });
    if (signalByFillIndexRef.current.has(i)){
      const s = signalByFillIndexRef.current.get(i); drawSignalLines(s);
      const a = Math.max(0, s.fillIdx - 50), b = Math.min(rows.length-1, s.exitIdx + 50);
      chartRef.current.timeScale().setVisibleRange({ from: rows[a].timeSec, to: rows[b].timeSec });
    }
    replayIndexRef.current = i + 1;
  };

  const stopReplay = () => { clearInterval(timer.current); timer.current = null; setPlaying(false); replayIndexRef.current = 0; };

  const goToDate = () => {
    if (!rows.length || !goto) return;
    const ts = Date.parse(goto)/1000;
    let lo=0, hi=rows.length-1, idx=0;
    while(lo<=hi){ const mid=(lo+hi>>1); if(rows[mid].timeSec>=ts){ idx=mid; hi=mid-1;} else lo=mid+1; }
    const start = Math.max(0, idx-20), end = Math.min(rows.length-1, idx+50);
    const range = { from: rows[start].timeSec, to: rows[end].timeSec };
    chartRef.current.timeScale().setVisibleRange(range);
  };

  const drawHLine = () => {
    if (!rows.length) return;
    const last = rows[rows.length-1];
    const line = candleRef.current.createPriceLine({ price: last.close, color: '#64748b', lineWidth: 1, lineStyle: 2 });
    priceLinesRef.current.push(line);
  };
  const removeLastHLine = () => { const l = priceLinesRef.current.pop(); if (l) candleRef.current.removePriceLine(l); };
  const removeAllHLines = () => { priceLinesRef.current.forEach(l => candleRef.current.removePriceLine(l)); priceLinesRef.current = []; };

  // Drive playback based on `playing` and `speed`
  useEffect(() => {
    if (!playing) { if (timer.current) { clearInterval(timer.current); timer.current = null; } return; }
    if (!rows.length) return;
    if (!timer.current) {
      timer.current = setInterval(() => { stepReplay(); }, speed);
    } else {
      clearInterval(timer.current);
      timer.current = setInterval(() => { stepReplay(); }, speed);
    }
    return () => { if (timer.current) { clearInterval(timer.current); timer.current = null; } };
  }, [playing, speed, rows]);

  return (
    <div className="p-4 flex flex-col gap-4 text-neutral-200">
      <div className="mx-auto text-center">
        <h2 className="text-xl font-semibold">Upload Your TradingView CSV</h2>
      </div>

      <div className="mx-auto w-full max-w-5xl bg-neutral-900 border border-neutral-800 rounded-xl p-4 flex flex-wrap items-center gap-3">
        <label className="text-sm text-neutral-400">Select CSV file:</label>
        <input
          className="text-sm file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:bg-neutral-800 file:text-neutral-200 file:hover:bg-neutral-700"
          type="file" accept=".csv"
          onChange={(e)=> setFile(e.target.files?.[0] || null)}
        />
        <button
          className="ml-auto bg-emerald-600 hover:bg-emerald-500 text-black font-medium px-4 py-2 rounded-lg disabled:opacity-60"
          onClick={onPlot}
          disabled={!file}
        >
          Plot Chart
        </button>
      </div>

      <div className="mx-auto w-full max-w-5xl bg-neutral-900 border border-neutral-800 rounded-xl p-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-neutral-300 border border-rose-800/60 rounded-md px-3 py-1.5">
            <input type="checkbox" className="accent-emerald-500" checked={replay} onChange={(e)=> setReplay(e.target.checked)} />
            <span>Replay Mode Active</span>
          </label>

          <button className="bg-emerald-600 hover:bg-emerald-500 text-black px-3 py-1.5 rounded-md disabled:opacity-50" disabled={!replay || playing} onClick={startReplayFromFrom}>Play</button>
          <button className="bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded-md disabled:opacity-50" disabled={!replay} onClick={()=> {
            if (!rows.length) return;
            if (replayIndexRef.current === 0) {
              const first = rows[0];
              candleRef.current.setData([{ time:first.timeSec, open:first.open, high:first.high, low:first.low, close:first.close }]);
              volRef.current.setData([{ time:first.timeSec, value:first.volume }]);
              chartRef.current.timeScale().fitContent();
              replayIndexRef.current = 1;
            } else {
              stepReplay();
            }
          }}>Next Bar »</button>
          <button className="bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded-md disabled:opacity-50" disabled={!replay} onClick={stopReplay}>Stop Replay</button>

          <div className="flex items-center gap-2 ml-auto">
            <span className="text-sm text-neutral-400">Speed</span>
            <input className="w-40 accent-emerald-500" type="range" min={50} max={1200} step={10} value={speed} onChange={(e)=> setSpeed(Number(e.target.value)||800)} />
            <span className="text-sm tabular-nums">{speed} ms</span>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3">
          {/* Strategy compact controls */}
          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input type="checkbox" className="accent-emerald-500" checked={useStrategy} onChange={(e)=> setUseStrategy(e.target.checked)} />
            Strategy v2
          </label>
          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input type="checkbox" className="accent-emerald-500" checked={signalsOnly} onChange={(e)=> setSignalsOnly(e.target.checked)} />
            Signals only
          </label>
          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input type="checkbox" className="accent-emerald-500" checked={showMarkers} onChange={(e)=> { setShowMarkers(e.target.checked); if (!e.target.checked) candleRef.current?.setMarkers([]); else applyStrategyNow(); }} />
            Show markers
          </label>
          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input type="checkbox" className="accent-emerald-500" checked={autoZoom} onChange={(e)=> setAutoZoom(e.target.checked)} />
            Auto‑zoom
          </label>
          <label className="flex items-center gap-2 text-sm text-neutral-400">
            Tick
            <input className="bg-neutral-950 border border-neutral-800 rounded-md px-2 py-1 text-sm w-24" type="number" step="0.00001" value={tickSize} onChange={(e)=> setTickSize(Number(e.target.value)||0.0001)} />
          </label>
          <button className="bg-emerald-600 hover:bg-emerald-500 text-black px-3 py-1.5 rounded-md" onClick={applyStrategyNow} disabled={!useStrategy || !allRows.length}>Apply Strategy</button>

          <label className="text-sm text-neutral-400">From</label>
          <input className="bg-neutral-950 border border-neutral-800 rounded-md px-2 py-1 text-sm" type="datetime-local" value={from} onChange={(e)=> setFrom(e.target.value)} />
          <label className="text-sm text-neutral-400">To</label>
          <input className="bg-neutral-950 border border-neutral-800 rounded-md px-2 py-1 text-sm" type="datetime-local" value={to} onChange={(e)=> setTo(e.target.value)} />
          <button className="bg-sky-600 hover:bg-sky-500 text-black px-3 py-1.5 rounded-md" onClick={onFilter}>Filter</button>
          <button className="bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded-md" onClick={()=> { setRows(allRows); plot(allRows); stopReplay(); }}>Reset View</button>

          <div className="ml-auto flex items-center gap-2">
            <span className="text-sm text-neutral-400">Go to Date</span>
            <input className="bg-neutral-950 border border-neutral-800 rounded-md px-2 py-1 text-sm" type="datetime-local" value={goto} onChange={(e)=> setGoto(e.target.value)} />
            <button className="bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded-md" onClick={goToDate}>Go</button>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-3 flex-wrap">
          <button className="bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded-md" onClick={drawHLine}>Draw H‑Line</button>
          <button className="bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded-md" onClick={removeLastHLine}>Remove Last</button>
          <button className="bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5 rounded-md" onClick={removeAllHLines}>Remove All</button>
          <span className="mx-2 opacity-40">|</span>
          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input type="checkbox" className="accent-emerald-500" checked={showLevels} onChange={(e)=> { setShowLevels(e.target.checked); priceLinesRef.current.forEach(l => candleRef.current?.removePriceLine(l)); priceLinesRef.current=[]; if (e.target.checked && signals.length){ drawSignalLines(signals[0]); } }} />
            Show levels
          </label>
          <label className="flex items-center gap-2 text-sm text-neutral-300">
            <input type="checkbox" className="accent-emerald-500" checked={showVolume} onChange={(e)=> setShowVolume(e.target.checked)} />
            Show Volume
          </label>
          <div className="flex items-center gap-2">
            <span className="text-sm text-neutral-400">Density</span>
            <input className="w-40 accent-emerald-500" type="range" min={4} max={24} step={1} value={density} onChange={(e)=> setDensity(Number(e.target.value)||10)} />
          </div>
        </div>
      </div>

      <div className="mx-auto w-full max-w-6xl bg-neutral-900 border border-neutral-800 rounded-xl p-2">
        <div ref={canvasRef} className="w-full" style={{ height: '76vh' }} />
      </div>

      <div className="mx-auto w-full max-w-6xl">
        <div className="inline-block bg-neutral-900 border border-neutral-800 rounded-md px-3 py-2 text-sm text-neutral-300">
          <div>Time: {barInfo?.r ? new Date(barInfo.r.timeSec*1000).toLocaleString() : '-'}</div>
          <div>
            O: {barInfo?.r?.open ?? '-'} · H: {barInfo?.r?.high ?? '-'} · L: {barInfo?.r?.low ?? '-'} · C: {barInfo?.r?.close ?? '-'}
            <span className="ml-3">Move: {barInfo?.move?.toFixed?.(5) ?? '-'}</span>
            {symbol ? <span className="ml-3 opacity-70">Symbol: {symbol}</span> : null}
          </div>
        </div>
      </div>
    </div>
  );
}
