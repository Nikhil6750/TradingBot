import { useEffect, useState } from "react";
import { api } from "../lib/api";  // ✅ fixed import path

export default function News() {
  const [currency, setCurrency] = useState("USD");
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function load() {
    setLoading(true); setErr("");
    try {
      const r = await api.news(currency);
      // expect list like [{time, currency, event, impact, actual, forecast, previous}]
      setItems(Array.isArray(r?.events) ? r.events : r);
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []); // first load

  return (
    <div className="flex-1 flex flex-col">
      <Topbar title="News" />
      <div className="p-4 max-w-5xl">
        <div className="flex gap-2 mb-3">
          <select
            className="bg-neutral-900 border border-neutral-800 rounded-md px-3 py-2"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
          >
            {["USD","EUR","GBP","JPY","AUD","CAD","CHF","NZD","CNY","INR"].map(c => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <button
            onClick={load}
            disabled={loading}
            className="px-4 rounded-md bg-emerald-600 hover:bg-emerald-700 text-black disabled:opacity-50"
          >
            {loading ? "Loading…" : "Refresh"}
          </button>
        </div>

        {err && <div className="bg-red-900/40 border border-red-800 rounded-xl p-3 mb-3">⚠️ {err}</div>}

        <div className="space-y-2">
          {items?.length ? items.map((e, i) => (
            <div key={i} className="bg-neutral-900 border border-neutral-800 rounded-xl p-3">
              <div className="text-sm text-neutral-400">{e.time} • {e.currency} • {e.impact}</div>
              <div className="font-medium">{e.event}</div>
              <div className="text-sm text-neutral-400">
                Actual: {e.actual ?? "—"} · Forecast: {e.forecast ?? "—"} · Previous: {e.previous ?? "—"}
              </div>
            </div>
          )) : <div className="text-neutral-400">No upcoming items.</div>}
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
