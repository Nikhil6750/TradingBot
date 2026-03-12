import { useEffect, useMemo, useRef } from "react";
import { createChart, CrosshairMode, LineStyle } from "lightweight-charts";

const DEFAULT_PAD_BEFORE = 10;
const DEFAULT_PAD_AFTER = 10;

function _toFixedMaybe(v, digits = 5) {
  const n = Number(v);
  if (!Number.isFinite(n)) return String(v ?? "");
  return n.toFixed(digits);
}

function _findIndexByTime(sortedCandles, time) {
  const t = Number(time);
  if (!Number.isFinite(t)) return -1;
  let lo = 0;
  let hi = sortedCandles.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const mt = Number(sortedCandles[mid]?.time);
    if (mt === t) return mid;
    if (mt < t) lo = mid + 1;
    else hi = mid - 1;
  }
  return -1;
}

function _buildView(candles, setup, trade, { padBefore, padAfter }) {
  const list = Array.isArray(candles) ? candles : [];
  if (!setup || !list.length) return null;

  const setupTime = Number(setup?.time);
  const setupIdx = _findIndexByTime(list, setupTime);
  if (setupIdx < 0) return null;

  const streakLength = Number(setup?.streak_length);
  const pullbackLength = Number(setup?.pullback_length);
  if (!Number.isFinite(streakLength) || !Number.isFinite(pullbackLength)) return null;

  const streakStartIdx = setupIdx - (streakLength + pullbackLength);
  const streakEndIdx = setupIdx - (pullbackLength + 1);
  const pullbackStartIdx = setupIdx - pullbackLength;
  const pullbackEndIdx = setupIdx - 1;

  const tradeEntryTime = trade?.entry?.time;
  const tradeExitTime = trade?.exit?.time;
  const entryIdx = _findIndexByTime(list, tradeEntryTime);
  const exitIdx = _findIndexByTime(list, tradeExitTime);

  let windowStartIdx = Math.max(0, streakStartIdx - padBefore);
  let windowEndIdx = Math.min(list.length - 1, setupIdx + padAfter);

  if (entryIdx >= 0) windowEndIdx = Math.max(windowEndIdx, Math.min(list.length - 1, entryIdx + padAfter));
  if (exitIdx >= 0) windowEndIdx = Math.max(windowEndIdx, Math.min(list.length - 1, exitIdx + padAfter));

  const windowCandles = list.slice(windowStartIdx, windowEndIdx + 1);
  const firstTime = windowCandles[0]?.time;
  const lastTime = windowCandles[windowCandles.length - 1]?.time;

  const streakColor = "#60a5fa";
  const pullbackColor = "#a78bfa";
  const setupColor = "#fde047";

  const candleData = windowCandles.map((c, relIdx) => {
    const absIdx = windowStartIdx + relIdx;

    let borderColor;
    let wickColor;

    if (absIdx >= streakStartIdx && absIdx <= streakEndIdx) {
      borderColor = streakColor;
      wickColor = streakColor;
    }
    if (absIdx >= pullbackStartIdx && absIdx <= pullbackEndIdx) {
      borderColor = pullbackColor;
      wickColor = pullbackColor;
    }
    if (absIdx === setupIdx) {
      borderColor = setupColor;
      wickColor = setupColor;
    }

    return {
      time: c.time,
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
      ...(borderColor ? { borderColor } : {}),
      ...(wickColor ? { wickColor } : {}),
    };
  });

  const direction = setup?.direction === "SELL" ? "SELL" : "BUY";
  const target = Number(setup?.target);

  const markers = [
    {
      time: setupTime,
      position: "inBar",
      color: setupColor,
      shape: "circle",
      text: `Strategy Setup\nDirection: ${direction}\nStreak: ${streakLength}\nPullback: ${pullbackLength}\nTarget: ${_toFixedMaybe(
        target
      )}`,
    },
  ];

  if (trade?.entry?.time && trade?.exit?.time) {
    markers.push(
      {
        time: trade.entry.time,
        position: "belowBar",
        color: "#22c55e",
        shape: "arrowUp",
        text: "ENTRY",
      },
      {
        time: trade.exit.time,
        position: "aboveBar",
        color: "#ef4444",
        shape: "arrowDown",
        text: "EXIT",
      }
    );
  }

  const targetLine =
    Number.isFinite(target) && firstTime != null && lastTime != null
      ? [
          { time: firstTime, value: target },
          { time: lastTime, value: target },
        ]
      : [];

  return { candleData, markers, targetLine };
}

export default function SetupDetailChart({
  candles,
  setup,
  trade,
  padBefore = DEFAULT_PAD_BEFORE,
  padAfter = DEFAULT_PAD_AFTER,
  onApi,
}) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const targetSeriesRef = useRef(null);

  const view = useMemo(
    () => _buildView(candles, setup, trade, { padBefore, padAfter }),
    [candles, setup, trade, padBefore, padAfter]
  );

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const ch = createChart(containerRef.current, {
      layout: { background: { color: "#0b1220" }, textColor: "#cbd5e1" },
      grid: { vertLines: { color: "#172036" }, horzLines: { color: "#172036" } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
      autoSize: true,
    });

    const cs = ch.addCandlestickSeries({
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderVisible: true,
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    const ts = ch.addLineSeries({
      color: "#eab308",
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    chartRef.current = ch;
    candleSeriesRef.current = cs;
    targetSeriesRef.current = ts;

    const handleResize = () => ch.timeScale().fitContent();
    window.addEventListener("resize", handleResize);

    onApi?.({ chart: ch, candleSeries: cs, targetSeries: ts });

    return () => {
      window.removeEventListener("resize", handleResize);
      ch.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      targetSeriesRef.current = null;
    };
  }, [onApi]);

  useEffect(() => {
    if (!candleSeriesRef.current || !targetSeriesRef.current) return;

    candleSeriesRef.current.setData(view?.candleData || []);
    candleSeriesRef.current.setMarkers(view?.markers || []);
    targetSeriesRef.current.setData(view?.targetLine || []);

    chartRef.current?.timeScale()?.fitContent?.();
  }, [view]);

  return <div ref={containerRef} className="w-full h-full" />;
}

