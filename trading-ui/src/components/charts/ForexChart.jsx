import { useEffect, useMemo, useRef } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";
import { useTheme } from "../../context/ThemeContext";
import { normalizeCandles, normalizeSignal } from "../../lib/candleData";

export default function ForexChart({
  candles, buySignals, sellSignals, backendIndicators = {}, openPosition,
  showSMA = false, showEMA = false, showBB = false, showRSI = false, showMACD = false
}) {
  const containerRef = useRef(null);
  const rsiContainerRef = useRef(null);
  const macdContainerRef = useRef(null);
  const chartRef = useRef(null);
  const rsiChartRef = useRef(null);
  const macdChartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const { theme } = useTheme();

  // Indicator Series Refs
  const overlays = useRef({ sma: null, ema: null, bbUpper: null, bbLower: null, rsi: null, macdLine: null, macdSignal: null, macdHist: null });
  // Prev Length Tracker for efficient .update()
  const prevLen = useRef(0);

  const candleData = useMemo(() => {
    return normalizeCandles(candles, "ForexChart");
  }, [candles]);

  const markers = useMemo(() => {
    const arr = [];
    if (buySignals) buySignals
      .map((signal) => normalizeSignal(signal))
      .filter(Boolean)
      .forEach((signal) => arr.push({ time: signal.time, position: 'belowBar', color: '#10b981', shape: 'arrowUp', text: 'BUY' }));
    if (sellSignals) sellSignals
      .map((signal) => normalizeSignal(signal))
      .filter(Boolean)
      .forEach((signal) => arr.push({ time: signal.time, position: 'aboveBar', color: '#ef4444', shape: 'arrowDown', text: 'SELL' }));

    // Deduplicate
    const seen = new Set();
    return arr.sort((a, b) => a.time - b.time).filter(m => {
      const key = `${m.time}_${m.text}`;
      if (seen.has(key)) return false;
      seen.add(key); return true;
    });
  }, [buySignals, sellSignals]);

  // Use injected backend indicators
  const computed = backendIndicators;

  // ── Create Chart ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const isDark = document.documentElement.classList.contains("dark") || theme === "dark" || true; // Force dark for terminal
    const bg = isDark ? "#0a0a0a" : "#f4f6f8";
    const text = isDark ? "#888888" : "#6b7280";
    const grid = isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.06)";

    const ch = createChart(containerRef.current, {
      layout: { background: { type: "solid", color: bg }, textColor: text, fontSize: 11 },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderVisible: false, scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, fixLeftEdge: true },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
      autoSize: true,
    });

    const cs = ch.addCandlestickSeries({
      upColor: "#10b981", downColor: "#ef4444", borderVisible: false,
      wickUpColor: "#10b981", wickDownColor: "#ef4444",
    });

    // Create Indicator Series
    overlays.current.sma = ch.addLineSeries({ color: 'rgba(59, 130, 246, 0.8)', lineWidth: 1.5, crosshairMarkerVisible: false, lastValueVisible: showSMA });
    overlays.current.ema = ch.addLineSeries({ color: 'rgba(245, 158, 11, 0.8)', lineWidth: 1.5, crosshairMarkerVisible: false, lastValueVisible: showEMA });
    overlays.current.bbUpper = ch.addLineSeries({ color: 'rgba(168, 85, 247, 0.5)', lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: showBB });
    overlays.current.bbLower = ch.addLineSeries({ color: 'rgba(168, 85, 247, 0.5)', lineWidth: 1, lineStyle: 2, crosshairMarkerVisible: false, lastValueVisible: showBB });

    chartRef.current = ch;
    candleSeriesRef.current = cs;
    prevLen.current = 0;

    let rsiCh = null;
    let rsiSer = null;

    if (showRSI && rsiContainerRef.current) {
      rsiCh = createChart(rsiContainerRef.current, {
        layout: { background: { type: "solid", color: bg }, textColor: text, fontSize: 11 },
        grid: { vertLines: { color: grid }, horzLines: { color: grid } },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, fixLeftEdge: true },
        handleScroll: { mouseWheel: true, pressedMouseMove: true },
        handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
        autoSize: true,
      });
      rsiSer = rsiCh.addLineSeries({ color: '#f43f5e', lineWidth: 1.5, crosshairMarkerVisible: false });

      rsiCh.timeScale().subscribeVisibleTimeRangeChange((range) => { if (range) ch.timeScale().setVisibleRange(range); });
      ch.timeScale().subscribeVisibleTimeRangeChange((range) => { if (range) rsiCh.timeScale().setVisibleRange(range); });

      rsiChartRef.current = rsiCh;
      overlays.current.rsi = rsiSer;
    }

    let macdCh = null;
    if (showMACD && macdContainerRef.current) {
      macdCh = createChart(macdContainerRef.current, {
        layout: { background: { type: "solid", color: bg }, textColor: text, fontSize: 11 },
        grid: { vertLines: { color: grid }, horzLines: { color: grid } },
        crosshair: { mode: CrosshairMode.Normal },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false, fixLeftEdge: true },
        handleScroll: { mouseWheel: true, pressedMouseMove: true },
        handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
        autoSize: true,
      });

      overlays.current.macdHist = macdCh.addHistogramSeries({ priceFormat: { type: 'volume' }, priceScaleId: '' });
      overlays.current.macdLine = macdCh.addLineSeries({ color: '#2962FF', lineWidth: 1.5, crosshairMarkerVisible: false });
      overlays.current.macdSignal = macdCh.addLineSeries({ color: '#FF6D00', lineWidth: 1.5, crosshairMarkerVisible: false });

      macdCh.timeScale().subscribeVisibleTimeRangeChange((range) => { if (range) ch.timeScale().setVisibleRange(range); });
      ch.timeScale().subscribeVisibleTimeRangeChange((range) => { if (range) macdCh.timeScale().setVisibleRange(range); });
      if (rsiCh) {
        macdCh.timeScale().subscribeVisibleTimeRangeChange((range) => { if (range) rsiCh.timeScale().setVisibleRange(range); });
        rsiCh.timeScale().subscribeVisibleTimeRangeChange((range) => { if (range) macdCh.timeScale().setVisibleRange(range); });
      }

      macdChartRef.current = macdCh;
    }

    const onResize = () => {
      ch.timeScale().fitContent();
      if (rsiCh) rsiCh.timeScale().fitContent();
      if (macdCh) macdCh.timeScale().fitContent();
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      ch.remove();
      if (rsiCh) rsiCh.remove();
      if (macdCh) macdCh.remove();
      chartRef.current = null;
      rsiChartRef.current = null;
      macdChartRef.current = null;
    };
  }, [showRSI, showMACD]); // Rebuild charts when adding/removing panes

  // ── Engine Loop (Streaming / SetData) ────────────────────────────────────
  useEffect(() => {
    if (!candleSeriesRef.current) return;

    const len = candleData.length;
    if (len === 0) {
      candleSeriesRef.current.setData([]);
      prevLen.current = 0;
      return;
    }

    const currentTimes = new Set(candleData.map(c => c.time));
    const validMarkers = markers.filter(m => currentTimes.has(m.time));

    // Streaming Logic (Optimized for React Step progression)
    if (len === prevLen.current + 1 && prevLen.current > 0) {
      // Stream just the new candle
      candleSeriesRef.current.update(candleData[len - 1]);

      // Update indicators safely
      if (showSMA && computed.sma?.length) overlays.current.sma.update(computed.sma[len - 1]);
      if (showEMA && computed.ema?.length) overlays.current.ema.update(computed.ema[len - 1]);
      if (showBB && computed.bbands?.length) {
        overlays.current.bbUpper.update({ time: computed.bbands[len - 1].time, value: computed.bbands[len - 1].upper });
        overlays.current.bbLower.update({ time: computed.bbands[len - 1].time, value: computed.bbands[len - 1].lower });
      }
      if (showRSI && computed.rsi?.length && overlays.current.rsi) {
        overlays.current.rsi.update(computed.rsi[len - 1]);
      }
      if (showMACD && computed.macd?.length && overlays.current.macdLine) {
        overlays.current.macdLine.update({ time: computed.macd[len - 1].time, value: computed.macd[len - 1].macd });
        overlays.current.macdSignal.update({ time: computed.macd[len - 1].time, value: computed.macd[len - 1].signal });
        overlays.current.macdHist.update({ time: computed.macd[len - 1].time, value: computed.macd[len - 1].histogram, color: computed.macd[len - 1].histogram > 0 ? '#26a69a' : '#ef5350' });
      }
    } else {
      // Bulk Load
      candleSeriesRef.current.setData(candleData);

      // Strip NaN for bulk indicators
      if (showSMA && computed.sma) overlays.current.sma.setData(computed.sma.filter(d => d && d.value != null && !isNaN(d.value)));
      else overlays.current.sma.setData([]);

      if (showEMA && computed.ema) overlays.current.ema.setData(computed.ema.filter(d => d && d.value != null && !isNaN(d.value)));
      else overlays.current.ema.setData([]);

      if (showBB && computed.bbands) {
        overlays.current.bbUpper.setData(computed.bbands.filter(d => d && d.upper != null && !isNaN(d.upper)).map(d => ({ time: d.time, value: d.upper })));
        overlays.current.bbLower.setData(computed.bbands.filter(d => d && d.lower != null && !isNaN(d.lower)).map(d => ({ time: d.time, value: d.lower })));
      } else {
        overlays.current.bbUpper.setData([]);
        overlays.current.bbLower.setData([]);
      }

      if (showRSI && overlays.current.rsi && computed.rsi) {
        overlays.current.rsi.setData(computed.rsi.filter(d => d && d.value != null && !isNaN(d.value)));
      }

      if (showMACD && overlays.current.macdLine && computed.macd) {
        overlays.current.macdLine.setData(computed.macd.filter(d => d && d.macd != null && !isNaN(d.macd)).map(d => ({ time: d.time, value: d.macd })));
        overlays.current.macdSignal.setData(computed.macd.filter(d => d && d.signal != null && !isNaN(d.signal)).map(d => ({ time: d.time, value: d.signal })));
        overlays.current.macdHist.setData(computed.macd.filter(d => d && d.histogram != null && !isNaN(d.histogram)).map(d => ({ time: d.time, value: d.histogram, color: d.histogram > 0 ? '#26a69a' : '#ef5350' })));
      }

      chartRef.current.timeScale().fitContent();
      if (rsiChartRef.current) rsiChartRef.current.timeScale().fitContent();
      if (macdChartRef.current) macdChartRef.current.timeScale().fitContent();
    }

    candleSeriesRef.current.setMarkers(validMarkers);
    prevLen.current = len;

  }, [candleData, markers, computed, showSMA, showEMA, showBB, showRSI, showMACD]);

  // ── Position Line Overlay ────────────────────────────────────────────────
  // Note: Lightweight Charts V4 handles price lines natively via series.createPriceLine
  useEffect(() => {
    if (!candleSeriesRef.current) return;
    // Clear old lines (we'll just use a ref to track if needed, but for now we won't draw persistent PnL lines to keep it clean)
  }, [openPosition]);

  return (
    <div className="w-full h-full relative group">
      <div className="w-full h-full flex flex-col">
        <div ref={containerRef} className="flex-1 w-full" />
        {showRSI && (
          <div className="w-full h-[120px] shrink-0 border-t border-white/10 relative">
            <div className="absolute top-2 left-4 z-10 text-[10px] font-bold text-rose-400">RSI (14, close)</div>
            <div ref={rsiContainerRef} className="w-full h-full" />
          </div>
        )}
        {showMACD && (
          <div className="w-full h-[120px] shrink-0 border-t border-white/10 relative">
            <div className="absolute top-2 left-4 z-10 text-[10px] font-bold text-blue-400">MACD (12, 26, 9)</div>
            <div ref={macdContainerRef} className="w-full h-full" />
          </div>
        )}
      </div>
    </div>
  );
}
