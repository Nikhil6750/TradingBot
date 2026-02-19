import { useEffect, useMemo, useRef } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";

export default function ForexChart({ candles, onApi }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);

  const candleData = useMemo(
    () =>
      (Array.isArray(candles) ? candles : []).map((c) => ({
        time: c.time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    [candles]
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
      borderVisible: false,
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    chartRef.current = ch;
    candleSeriesRef.current = cs;

    const handleResize = () => ch.timeScale().fitContent();
    window.addEventListener("resize", handleResize);

    onApi?.({ chart: ch, candleSeries: cs });

    return () => {
      window.removeEventListener("resize", handleResize);
      ch.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
    };
  }, [onApi]);

  useEffect(() => {
    if (!candleSeriesRef.current) return;
    candleSeriesRef.current.setData(candleData);
    chartRef.current?.timeScale()?.fitContent?.();
  }, [candleData]);

  return <div ref={containerRef} className="w-full h-full" />;
}

