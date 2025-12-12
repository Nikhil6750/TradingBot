// trading-ui/src/pages/Backtest.jsx
import React, { useEffect, useRef, useState } from "react";
import { BASE_URL } from "../lib/api";
import { createChart, CrosshairMode } from "lightweight-charts";

const card = {
  background: "#0b1220",
  border: "1px solid #1f2937",
  borderRadius: 10,
  padding: 12,
};

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

  const [verifyMap, setVerifyMap] = useState({});
  const [verifying, setVerifying] = useState(false);
  const fileInputRef = useRef(null);

  const fetchSymbols = async (selectSymbol = null) => {
    try {
      const r = await fetch(`${BASE_URL}/symbols`);
      const d = await r.json();
      const list = d.symbols || [];
      setSymbols(list);
      if (selectSymbol && list.includes(selectSymbol)) {
        setSymbol(selectSymbol);
      }
    } catch { }
  };

  useEffect(() => {
    let abort = false;
    (async () => {
      try {
        await fetchSymbols();
      } catch {
        if (!abort) setSymbols([]);
      }
    })();
    return () => { abort = true; };
  }, []);

  useEffect(() => {
    if (!symbol) {
      setCsvRange(null);
      return;
    }
    let abort = false;
    (async () => {
      try {
        const r = await fetch(`${BASE_URL}/csv/debug?symbol=${encodeURIComponent(symbol)}&n=1`);
        const d = await r.json();
        if (!abort) {
          if (d?.ok && d.end_utc) {
            setCsvRange({ start: d.start_utc, end: d.end_utc });
            setDate(d.end_utc.slice(0, 10));
          } else {
            setCsvRange(null);
          }
        }
      } catch {
        if (!abort) setCsvRange(null);
      }
    })();
    return () => { abort = true; };
  }, [symbol]);

  const runBacktest = async (e) => {
    e?.preventDefault?.();
    setErr(""); setLoading(true);
    setAlerts([]); setSummary(null);
    setRunMeta(null);
    setVerifyMap({});

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
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(`${r.status} ${txt}`);
      }
      const data = await r.json();
      setAlerts(Array.isArray(data.alerts) ? data.alerts : []);
      setSummary(data.summary || null);
      setRunMeta(data.run || null);
    } catch (ex) {
      setErr(String(ex?.message || ex));
    } finally {
      setLoading(false);
    }
  };

  const verifyAlerts = async () => {
    if (!symbol || !alerts.length) return;
    setVerifying(true);
    try {
      const body = {
        symbol: (symbol || "").toUpperCase().trim(),
        items: alerts.map((a) => ({ time: a.time, reason: a.reason })),
      };
      const r = await fetch(`${BASE_URL}/backtest/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (d?.ok && Array.isArray(d.results)) {
        const map = {};
        d.results.forEach((x) => {
          map[x.time] = { ok: x.ok, detected: x.detected, match: x.match };
        });
        setVerifyMap(map);
      }
    } catch { }
    finally {
      setVerifying(false);
    }
  }


  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setErr("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("tz", "UTC");

      // Infer symbol from filename (e.g., "MyData.csv" -> "MYDATA")
      const symName = file.name.replace(/\.[^/.]+$/, "").toUpperCase().trim();

      const r = await fetch(`${BASE_URL}/upload-csv?symbol=${encodeURIComponent(symName)}`, {
        method: "POST",
        body: formData,
      });
      if (!r.ok) {
        const txt = await r.text();
        throw new Error(`${r.status} ${txt}`);
      }
      const d = await r.json();
      if (d.status === "ok") {
        // Refresh symbols and select the new one (if returned)
        const loadedSym = d.symbols_loaded?.[0];
        await fetchSymbols(loadedSym);
      }
    } catch (ex) {
      setErr(String(ex.message || ex));
    } finally {
      setLoading(false);
      // Reset input so same file can be selected again if needed
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "320px 1fr",
        gap: 16,
        padding: 16,
      }}
    >
      {/* Left panel */}
      <form onSubmit={runBacktest} style={card}>
        <h3 style={{ color: "#e5e7eb", margin: "4px 0 8px" }}>Parameters</h3>

        {csvRange ? (
          <div style={{ color: "#94a3b8", fontSize: 12, marginBottom: 12 }}>
            Available (UTC): <b>{csvRange.start}</b> → <b>{csvRange.end}</b>
          </div>
        ) : (
          <div style={{ color: "#64748b", fontSize: 12, marginBottom: 12 }}>
            Select a symbol to view date range.
          </div>
        )}

        <label style={{ color: "#9ca3af", fontSize: 12 }}>Symbol</label>
        <div style={{ display: "flex", gap: 10, marginTop: 6, marginBottom: 12 }}>
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            style={{
              padding: "8px 12px",
              background: "#374151",
              color: "#e5e7eb",
              border: "1px solid #4b5563",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 12,
              whiteSpace: "nowrap",
            }}
          >
            Upload CSV
          </button>
          <input
            type="text"
            readOnly
            value={symbol || "No symbol selected"}
            placeholder="No symbol selected"
            style={{
              width: "100%",
              padding: 8,
              background: "#111827",
              color: symbol ? "#e5e7eb" : "#6b7280",
              border: "1px solid #374151",
              borderRadius: 6,
              fontSize: 14,
            }}
          />
          <input
            type="file"
            accept=".csv"
            ref={fileInputRef}
            style={{ display: "none" }}
            onChange={handleUpload}
          />
        </div>

        <label style={{ color: "#9ca3af", fontSize: 12 }}>Date (UTC)</label>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          style={{
            width: "100%",
            margin: "6px 0 12px",
            padding: 8,
            background: "#111827",
            color: "#e5e7eb",
            border: "1px solid #374151",
            borderRadius: 6,
          }}
        />

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <div>
            <label style={{ color: "#9ca3af", fontSize: 12 }}>Hour from (UTC)</label>
            <input
              type="number" min="0" max="23"
              value={hourFrom}
              onChange={(e) => setHourFrom(e.target.value)}
              style={{
                width: "100%", marginTop: 6,
                padding: 8, background: "#111827",
                color: "#e5e7eb", border: "1px solid #374151",
                borderRadius: 6,
              }}
            />
          </div>
          <div>
            <label style={{ color: "#9ca3af", fontSize: 12 }}>Hour to (UTC)</label>
            <input
              type="number" min="1" max="24"
              value={hourTo}
              onChange={(e) => setHourTo(e.target.value)}
              style={{
                width: "100%", marginTop: 6,
                padding: 8, background: "#111827",
                color: "#e5e7eb", border: "1px solid #374151",
                borderRadius: 6,
              }}
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || !symbol}
          style={{
            width: "100%", marginTop: 12,
            padding: "10px 12px",
            background: "#22c55e", color: "black",
            border: "none", borderRadius: 8,
            opacity: loading ? 0.7 : 1,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Running…" : "Run backtest"}
        </button>

        {err && (
          <div style={{ color: "#ef4444", fontSize: 12, marginTop: 10 }}>
            {err}
          </div>
        )}
      </form>

      {/* Right panel */}
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
                  {runMeta?.date_utc && (
                    <>Date (UTC): <b>{runMeta.date_utc}</b>{runMeta?.hour_allow ? " • " : ""}</>
                  )}
                  {runMeta?.hour_allow && <>Hours (UTC): <b>{runMeta.hour_allow}</b></>}
                </div>
              )}
            </>
          )}
        </div>

        {/* Pattern Alerts */}
        <div style={card}>
          <div
            style={{
              display: "flex", alignItems: "center",
              justifyContent: "space-between", marginBottom: 12,
            }}
          >
            <h3 style={{ color: "#e5e7eb", margin: 0 }}>Pattern Alerts</h3>
            <button
              type="button"
              onClick={verifyAlerts}
              disabled={!alerts.length || verifying}
              style={{
                background: "#0ea5e9", color: "white",
                border: "none", borderRadius: 8,
                padding: "8px 12px",
                opacity: !alerts.length || verifying ? 0.6 : 1,
                cursor: !alerts.length || verifying ? "not-allowed" : "pointer",
              }}
            >
              {verifying ? "Verifying…" : "Verify"}
            </button>
          </div>

          {alerts.length === 0 ? (
            <div style={{ color: "#9ca3af", fontSize: 12 }}>No alerts.</div>
          ) : (
            <div style={{ display: "grid", gap: 12 }}>
              {alerts.map((a, i) => {
                const imgSrc = a.plot_data_url || `${BASE_URL}${a.plot_url}`;
                const v = verifyMap[a.time];
                return (
                  <div
                    key={`${a.tidx ?? i}-${i}`}
                    style={{
                      border: "1px solid #1f2937",
                      borderRadius: 10,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        padding: "8px 12px",
                        background: "#0f172a",
                        color: "#e5e7eb",
                        display: "flex",
                        gap: 12,
                        alignItems: "center",
                        flexWrap: "wrap",
                      }}
                    >
                      <span style={{ opacity: 0.8 }}>{a.time}</span>
                      <span>•</span>
                      <span>{a.side}</span>

                      {v && (
                        <span
                          title={v.ok ? "Pattern verified" : `Mismatch: detected ${v.detected || "none"}`}
                          style={{
                            marginLeft: 8, padding: "2px 6px",
                            borderRadius: 6, fontSize: 12,
                            background: v.ok ? "#064e3b" : "#7f1d1d",
                            color: v.ok ? "#22c55e" : "#f87171",
                            border: "1px solid rgba(255,255,255,0.1)",
                          }}
                        >
                          {v.ok ? "✓ verified" : "✗ mismatch"}
                        </span>
                      )}

                      <span
                        style={{
                          marginLeft: "auto",
                          color: a.take ? "#22c55e" : "#f59e0b",
                        }}
                      >
                        {a.take ? "TAKE" : "SKIP"}
                      </span>
                    </div>

                    <div style={{ padding: 12 }}>
                      <img
                        src={imgSrc}
                        alt="candles"
                        style={{
                          width: "100%",
                          height: "auto",
                          display: "block",
                          background: "transparent",
                          borderRadius: 6,
                          border: "1px solid #1f2937",
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
