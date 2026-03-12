import { useEffect, useMemo, useRef } from "react";
import { createChart, CrosshairMode } from "lightweight-charts";
import { useTheme } from "../../context/ThemeContext";

const DEFAULT_PALETTE = {
  backgroundDark: "#0b0f14",
  backgroundLight: "#f4f6f8",
  textDark: "#9aa4af",
  textLight: "#6b7280",
  gridDark: "rgba(255,255,255,0.04)",
  gridLight: "rgba(0,0,0,0.05)",
  positiveLine: "#E5E5E5",
  positiveTop: "rgba(229,229,229,0.18)",
  negativeLine: "#888888",
  negativeTop: "rgba(136,136,136,0.12)",
  bottom: "rgba(0,0,0,0)",
  drawdownLine: "rgba(239,68,68,0)",
  drawdownTop: "rgba(239,68,68,0.22)",
  drawdownBottom: "rgba(239,68,68,0.04)",
};

export default function EquityChart({ trades, initialBalance = 10000, palette = null }) {
  const containerRef = useRef(null);
  const chartRef = useRef(null);
  const equityRef = useRef(null);
  const drawdownRef = useRef(null);
  const { theme } = useTheme();
  const colors = { ...DEFAULT_PALETTE, ...(palette || {}) };

  // ── Build equity & drawdown series ─────────────────────────────────────────
  const { equityData, drawdownData, isProfit } = useMemo(() => {
    if (!trades?.length) return { equityData: [], drawdownData: [], isProfit: true };

    let balance = initialBalance;
    const raw = [];

    const sorted = [...trades].sort(
      (a, b) => (a.exit_time || a.entry_time) - (b.exit_time || b.entry_time)
    );

    const firstTime = sorted[0].entry_time || sorted[0].exit_time;
    if (firstTime) raw.push({ time: firstTime - 60, balance });

    for (const t of sorted) {
      const time = t.exit_time || t.entry_time;
      if (!time) continue;
      balance = balance * (1 + t.pnl);
      raw.push({ time, balance });
    }

    // Deduplicate
    const seen = new Set();
    const unique = raw.filter(d => { if (seen.has(d.time)) return false; seen.add(d.time); return true; });

    // Running peak → drawdown value
    let peak = -Infinity;
    const equityData = unique.map(d => ({ time: d.time, value: d.balance }));
    const drawdownData = unique.map(d => {
      peak = Math.max(peak, d.balance);
      // Draw from current balance up to peak as a "loss zone" area value
      return { time: d.time, value: d.balance < peak ? d.balance : null };
    });

    const finalProfit = unique.length >= 2
      ? unique[unique.length - 1].balance >= unique[0].balance
      : true;

    return { equityData, drawdownData, isProfit: finalProfit };
  }, [trades, initialBalance]);

  const lineColor = isProfit ? colors.positiveLine : colors.negativeLine;
  const topColor = isProfit ? colors.positiveTop : colors.negativeTop;
  const bottomColor = colors.bottom;

  // ── Create chart ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const useDarkPalette = palette ? true : document.documentElement.classList.contains("dark");
    const bg = useDarkPalette ? colors.backgroundDark : colors.backgroundLight;
    const text = useDarkPalette ? colors.textDark : colors.textLight;
    const grid = useDarkPalette ? colors.gridDark : colors.gridLight;

    const ch = createChart(containerRef.current, {
      layout: { background: { type: "solid", color: bg }, textColor: text },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true },
      autoSize: true,
    });

    // Equity area
    const equity = ch.addAreaSeries({
      lineColor,
      topColor,
      bottomColor,
      lineWidth: 1.5,
      priceLineVisible: false,
    });

    // Drawdown shading — red area clipped to the drawdown zone
    const dd = ch.addAreaSeries({
      lineColor: colors.drawdownLine,
      topColor: colors.drawdownTop,
      bottomColor: colors.drawdownBottom,
      lineWidth: 0,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    chartRef.current = ch;
    equityRef.current = equity;
    drawdownRef.current = dd;

    const onResize = () => ch.timeScale().fitContent();
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      ch.remove();
      chartRef.current = null;
      equityRef.current = null;
      drawdownRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [colors.backgroundDark, colors.backgroundLight, colors.drawdownBottom, colors.drawdownLine, colors.drawdownTop, colors.gridDark, colors.gridLight, colors.textDark, colors.textLight, palette]);

  // ── Theme updates ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (palette) {
      chartRef.current?.applyOptions({
        layout: {
          background: { type: "solid", color: colors.backgroundDark },
          textColor: colors.textDark,
        },
        grid: {
          vertLines: { color: colors.gridDark },
          horzLines: { color: colors.gridDark },
        },
      });
      return;
    }
    if (!chartRef.current) return;
    const isDark = theme === "dark";
    chartRef.current.applyOptions({
      layout: {
        background: { type: "solid", color: isDark ? colors.backgroundDark : colors.backgroundLight },
        textColor: isDark ? colors.textDark : colors.textLight,
      },
      grid: {
        vertLines: { color: isDark ? colors.gridDark : colors.gridLight },
        horzLines: { color: isDark ? colors.gridDark : colors.gridLight },
      },
    });
  }, [colors.backgroundDark, colors.backgroundLight, colors.gridDark, colors.gridLight, colors.textDark, colors.textLight, palette, theme]);

  // ── Color update ───────────────────────────────────────────────────────────
  useEffect(() => {
    equityRef.current?.applyOptions({ lineColor, topColor, bottomColor });
  }, [lineColor, topColor, bottomColor]);

  // ── Data update ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!equityRef.current) return;
    equityRef.current.setData(equityData);

    // Only set drawdown points where we're actually in a drawdown
    if (drawdownRef.current) {
      const ddFiltered = drawdownData.filter(d => d.value !== null);
      if (ddFiltered.length) {
        drawdownRef.current.setData(ddFiltered);
      }
    }

    chartRef.current?.timeScale()?.fitContent?.();
  }, [equityData, drawdownData]);

  return <div ref={containerRef} className="w-full h-full" />;
}
