import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export default function News() {
  const [currency, setCurrency] = useState("USD");
  const [impact, setImpact] = useState("medium"); // low | medium | high
  const [hrs, setHrs] = useState(12);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    setLoading(true); setErr("");
    try {
      const qs = new URLSearchParams({
        currencies: currency,
        min_impact: impact,
        lookahead_hrs: String(hrs),
        tz: "Asia/Kolkata",
      }).toString();

      const r = await fetch(`${API_BASE}/calendar/today?${qs}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      setItems(Array.isArray(data?.events) ? data.events : []);
    } catch (e) {
      setErr(e.message || "Failed to load");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); /* initial */ }, []);

  return (
    <div className="flex-1 flex flex-col">
      <Topbar title="News / Economic Calendar" />
      <div className="p-4 max-w-5xl">
        <div className="flex flex-wrap gap-2 mb-3 items-center">
          <label className="text-sm text-neutral-400">Currency</label>
          <select
            className="bg-neutral-900 border border-neutral-800 rounded-md px-3 py-2"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
          >
            {["USD","EUR","GBP","JPY","AUD","CAD","CHF","NZD","CNY","INR"].map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>

          <label className="text-sm text-neutral-400 ml-3">Impact</label>
          <select
            className="bg-neutral-900 border border-neutral-800 rounded-md px-3 py-2"
            value={impact}
            onChange={(e) => setImpact(e.target.value)}
          >
            {["low","medium","high"].map(v => <option key={v} value={v}>{v}</option>)}
          </select>

          <label className="text-sm text-neutral-400 ml-3">Next (hrs)</label>
          <input
            type="number"
            min={1}
            max={48}
            value={hrs}
            onChange={(e) => setHrs(Number(e.target.value))}
            className="w-20 bg-neutral-900 border border-neutral-800 rounded-md px-3 py-2"
          />

          <button
            onClick={load}
            disabled={loading}
            className="ml-2 px-4 rounded-md bg-emerald-600 hover:bg-emerald-700 text-black disabled:opacity-50"
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>

        {err && <div className="bg-red-900/40 border border-red-800 rounded-xl p-3 mb-3">⚠️ {err}</div>}

        <div className="space-y-2">
          {items?.length ? items.map((e, i) => (
            <div key={i} className="bg-neutral-900 border border-neutral-800 rounded-xl p-3">
              <div className="text-sm text-neutral-400">
                {e.time_utc ? new Date(e.time_utc).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'}) : (e.time_local || "—")}
                {" • "} {e.currency || "—"} {" • "} {(e.impact || "").toUpperCase()}
              </div>
              <div className="font-medium">{e.event}</div>
              <div className="text-sm text-neutral-400">
                Actual: {e.actual || "—"} · Forecast: {e.forecast || "—"} · Previous: {e.previous || "—"}
              </div>
            </div>
          )) : <div className="text-neutral-400">No upcoming items for the current filters.</div>}
        </div>
      </div>
    </div>
  );
}

function Topbar({ title }) {
  return (
    <div className="h-12 flex items-center px-3 border-b border-neutral-800 bg-neutral-900">
      <div className="text-[14px]">
        {title}
        <span className="text-[10px] ml-2 border border-neutral-800 px-2 py-[2px] rounded-full bg-[#151515]">MVP</span>
      </div>
    </div>
  );
}
