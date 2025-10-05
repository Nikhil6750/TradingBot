// src/pages/Backtest.jsx
import React, { useEffect, useState } from "react";
import { BASE_URL } from "../lib/api";

const card = { background: "#0b1220", border: "1px solid #1f2937", borderRadius: 10, padding: 12 };

export default function Backtest() {
  const [symbols, setSymbols] = useState([]);
  const [symbol, setSymbol] = useState("");
  const [date, setDate] = useState("");
  const [hourFrom, setHourFrom] = useState("6");
  const [hourTo, setHourTo] = useState("10");
  const [alerts, setAlerts] = useState([]);
  const [summary, setSummary] = useState(null);
  const [runMeta, setRunMeta] = useState(null);
  const [csvRange, setCsvRange] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    fetch(`${BASE_URL}/symbols`).then(r => r.json()).then(d => setSymbols(d.symbols || [])).catch(() => setSymbols([]));
  }, []);

  useEffect(() => {
    if (!symbol) { setCsvRange(null); return; }
    fetch(`${BASE_URL}/csv/debug?symbol=${encodeURIComponent(symbol)}&n=1`)
      .then(r => r.json())
      .then(d => {
        if (d?.ok && d.end_utc) { setCsvRange({ start: d.start_utc, end: d.end_utc }); setDate(d.end_utc.slice(0,10)); }
        else setCsvRange(null);
      })
      .catch(() => setCsvRange(null));
  }, [symbol]);

  const runBacktest = async (e) => {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      const body = {
        symbol: (symbol || "").toUpperCase().trim(),
        hour_allow: `${hourFrom}-${hourTo}`,
        ...(date ? { date } : {}),
        bars_plot: 40,
      };
      const r = await fetch(`${BASE_URL}/backtest/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
      const data = await r.json();
      setAlerts(Array.isArray(data.alerts) ? data.alerts : []);
      setSummary(data.summary || null);
      setRunMeta(data.run || null);
    } catch (ex) {
      setErr(String(ex?.message || ex));
      setAlerts([]); setSummary(null); setRunMeta(null);
    } finally {
      setLoading(false);
    }
  };

  const withBuster = (url) => url + (url.includes("?") ? "&" : "?") + `_=${Date.now()}`;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 16, padding: 16 }}>
      <form onSubmit={runBacktest} style={card}>
        <h3 style={{ color: "#e5e7eb", margin: "4px 0 8px" }}>Parameters</h3>
        {csvRange ? (
          <div style={{ color: "#94a3b8", fontSize: 12, marginBottom: 12 }}>
            Available (UTC): <b>{csvRange.start}</b> → <b>{csvRange.end}</b>
          </div>
        ) : (
          <div style={{ color: "#64748b", fontSize: 12, marginBottom: 12 }}>Select a symbol to view date range.</div>
        )}

        <label style={{ color: "#9ca3af", fontSize: 12 }}>Symbol</label>
        <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
          style={{ width: "100%", margin: "6px 0 12px", padding: 8, background: "#111827", color: "#e5e7eb", border: "1px solid #374151", borderRadius: 6 }}>
          <option value="">-- Select Symbol --</option>
          {symbols.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <label style={{ color: "#9ca3af", fontSize: 12 }}>Date (UTC)</label>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
          style={{ width: "100%", margin: "6px 0 12px", padding: 8, background: "#111827", color: "#e5e7eb", border: "1px solid #374151", borderRadius: 6 }} />

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <label style={{ color: "#9ca3af", fontSize: 12 }}>Hour from (UTC)</label>
            <input type="number" min="0" max="23" value={hourFrom} onChange={(e) => setHourFrom(e.target.value)}
              style={{ width: "100%", marginTop: 6, padding: 8, background: "#111827", color: "#e5e7eb", border: "1px solid #374151", borderRadius: 6 }} />
          </div>
          <div>
            <label style={{ color: "#9ca3af", fontSize: 12 }}>Hour to (UTC)</label>
            <input type="number" min="1" max="24" value={hourTo} onChange={(e) => setHourTo(e.target.value)}
              style={{ width: "100%", marginTop: 6, padding: 8, background: "#111827", color: "#e5e7eb", border: "1px solid #374151", borderRadius: 6 }} />
          </div>
        </div>

        <button type="submit" disabled={loading || !symbol}
          style={{ width: "100%", marginTop: 12, padding: "10px 12px", background: "#22c55e", color: "black", border: "none", borderRadius: 8, opacity: loading ? 0.7 : 1 }}>
          {loading ? "Running…" : "Run backtest"}
        </button>

        {err && <div style={{ color: "#ef4444", fontSize: 12, marginTop: 10 }}>{err}</div>}
      </form>

      <div style={{ display: "grid", gap: 16 }}>
        <div style={card}>
          <h3 style={{ color: "#e5e7eb", margin: "4px 0 6px" }}>Summary</h3>
          {!summary ? (
            <div style={{ color: "#9ca3af", fontSize: 12 }}>No results yet.</div>
          ) : (
            <>
              <div style={{ display: "flex", gap: 16, color: "#e5e7eb" }}>
                <div>Trades: <b>{summary.trades}</b></div>
                <div>Wins: <b>{summary.wins}</b></div>
                <div>Losses: <b>{summary.losses ?? 0}</b></div>
                <div>Win%: <b>{summary.win_rate}</b></div>
              </div>
              {(runMeta?.date_utc || runMeta?.hour_allow) && (
                <div style={{ color: "#94a3b8", fontSize: 12, marginTop: 6 }}>
                  {runMeta?.date_utc && <>Date (UTC): <b>{runMeta.date_utc}</b>{runMeta?.hour_allow ? " • " : ""}</>}
                  {runMeta?.hour_allow && <>Hours (UTC): <b>{runMeta.hour_allow}</b></>}
                </div>
              )}
            </>
          )}
        </div>

        <div style={card}>
          <h3 style={{ color: "#e5e7eb", margin: "4px 0 12px" }}>Pattern Alerts</h3>
          {alerts.length === 0 ? (
            <div style={{ color: "#9ca3af", fontSize: 12 }}>No alerts.</div>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {alerts.map((a, i) => {
                const imgSrc = withBuster(`${BASE_URL}${a.plot_url}`); // carries abs_index + time
                return (
                  <div key={`${a.abs_index}-${i}`} style={{ border: "1px solid #1f2937", borderRadius: 10, overflow: "hidden" }}>
                    <div style={{ padding: "8px 12px", background: "#0f172a", color: "#e5e7eb", display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
                      <span style={{ opacity: 0.8 }}>{a.time}</span>
                      <span>•</span>
                      <span>{a.side}</span>
                      <span>•</span>
                      <span style={{ opacity: 0.8 }}>{a.reason}</span>
                      <span style={{ marginLeft: "auto", color: a.take ? "#22c55e" : "#f59e0b" }}>
                        {a.take ? "TAKE" : "SKIP"}
                      </span>
                    </div>
                    <div style={{ padding: 12 }}>
                      <img
                        src={imgSrc}
                        alt="candles"
                        style={{ width: "100%", height: "auto", display: "block", background: "transparent", borderRadius: 6, border: "1px solid #1f2937" }}
                        onError={(e) => {
                          e.currentTarget.alt = "Chart failed to load";
                          e.currentTarget.style.minHeight = "140px";
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
