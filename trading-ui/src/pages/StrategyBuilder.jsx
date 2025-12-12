import React, { useEffect, useRef, useState } from "react";
import { BASE_URL } from "../lib/api";

const card = {
    background: "#0b1220",
    border: "1px solid #1f2937",
    borderRadius: 10,
    padding: 12,
    height: "100%",
    display: "flex",
    flexDirection: "column",
};

const inputStyle = {
    width: "100%",
    padding: 8,
    background: "#111827",
    color: "#e5e7eb",
    border: "1px solid #374151",
    borderRadius: 6,
    fontFamily: "monospace",
    fontSize: 12,
};

export default function StrategyBuilder() {
    // Pine / Python
    const [pineCode, setPineCode] = useState("");
    // const [pythonCode, setPythonCode] = useState("# Python code will appear here..."); // Hidden
    const [strategyKey, setStrategyKey] = useState(null);
    const [compileSuccess, setCompileSuccess] = useState(false);

    // Data / Execution
    const [symbol, setSymbol] = useState("");
    const [symbols, setSymbols] = useState([]);
    const [date, setDate] = useState("");
    const [hourFrom, setHourFrom] = useState("6");
    const [hourTo, setHourTo] = useState("10");

    const [loading, setLoading] = useState(false);
    const [converting, setConverting] = useState(false);
    const [err, setErr] = useState("");

    const [alerts, setAlerts] = useState([]);
    const [summary, setSummary] = useState(null);
    const [runMeta, setRunMeta] = useState(null);

    const fileInputRef = useRef(null);

    // Load symbols on mount
    useEffect(() => {
        fetchSymbols();
    }, []);

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

    const handleUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setLoading(true); setErr("");
        try {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("tz", "UTC");
            const symName = file.name.replace(/\.[^/.]+$/, "").toUpperCase().trim();

            const r = await fetch(`${BASE_URL}/upload-csv?symbol=${encodeURIComponent(symName)}`, { method: "POST", body: formData });
            if (!r.ok) throw new Error(await r.text());
            const d = await r.json();
            if (d.status === "ok") await fetchSymbols(symName || d.symbols_loaded?.[0]);
        } catch (ex) { setErr(String(ex.message || ex)); }
        finally { setLoading(false); if (fileInputRef.current) fileInputRef.current.value = ""; }
    };

    const convertStrategy = async () => {
        setConverting(true); setErr(""); setCompileSuccess(false);
        try {
            const r = await fetch(`${BASE_URL}/convert_pine`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: pineCode }),
            });
            const d = await r.json();
            if (!d.ok) throw new Error(d.error);
            // setPythonCode(d.python_code); // Internal only
            setStrategyKey(d.key);
            setCompileSuccess(true);
        } catch (ex) {
            setErr("Compilation Error: " + (ex.message || ex));
        } finally {
            setConverting(false);
        }
    };

    const runStrategy = async (e) => {
        e?.preventDefault?.();
        if (!strategyKey) { setErr("Please compile your strategy first."); return; }
        if (!symbol) { setErr("Please upload/select a CSV."); return; }

        setLoading(true); setErr(""); setAlerts([]); setSummary(null);
        try {
            const body = {
                key: strategyKey,
                symbol: symbol,
                hour_allow: `${hourFrom}-${hourTo}`,
                ...(date ? { date } : {}),
            };
            const r = await fetch(`${BASE_URL}/run_strategy`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            const d = await r.json();
            if (!d.ok) throw new Error(d.error);

            setAlerts(d.alerts || []);
            setSummary(d.summary || null);
            setRunMeta(d.run || null);
        } catch (ex) {
            setErr("Runtime Error: " + (ex.message || ex));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ padding: 16, height: "100vh", overflowY: "auto", display: "flex", flexDirection: "column", gap: 16 }}>
            <h2 style={{ color: "#e5e7eb", margin: 0 }}>Strategy Builder (Pine Script)</h2>

            {/* Editor & Config Area */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: 16, height: "500px" }}>

                {/* Pine Editor */}
                <div style={card}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                        <h3 style={{ color: "#9ca3af", fontSize: 14, margin: 0 }}>Pine Script</h3>
                        <button onClick={convertStrategy} disabled={converting || !pineCode.trim()} style={{ background: "#f59e0b", border: "none", borderRadius: 4, padding: "6px 16px", cursor: "pointer", fontSize: 12, opacity: (converting || !pineCode.trim()) ? 0.7 : 1, fontWeight: "600", color: "#111827" }}>
                            {converting ? "Compiling..." : "Compile"}
                        </button>
                    </div>
                    <textarea
                        value={pineCode}
                        onChange={(e) => { setPineCode(e.target.value); setCompileSuccess(false); }}
                        placeholder="Paste your Pinescript"
                        style={{ flex: 1, ...inputStyle, resize: "none", fontSize: 14, lineHeight: "1.5" }}
                        spellCheck={false}
                    />
                    {compileSuccess && (
                        <div style={{ marginTop: 8, color: "#4ade80", fontSize: 13, background: "rgba(74, 222, 128, 0.1)", padding: "6px 10px", borderRadius: 4, display: "flex", alignItems: "center", gap: 6 }}>
                            <span>✓</span> Pinescript successfully compiled
                        </div>
                    )}
                </div>

                {/* Removed Python Preview */}

                {/* Config & Run */}
                <div style={card}>
                    <h3 style={{ color: "#e5e7eb", margin: "0 0 12px", fontSize: 16 }}>Run Settings</h3>

                    <label style={{ color: "#9ca3af", fontSize: 12 }}>Symbol</label>
                    <div style={{ display: "flex", gap: 8, marginTop: 4, marginBottom: 12 }}>
                        <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            style={{ padding: "6px 10px", background: "#374151", color: "#e5e7eb", border: "1px solid #4b5563", borderRadius: 4, cursor: "pointer", fontSize: 11, whiteSpace: "nowrap" }}
                        >
                            Upload CSV
                        </button>
                        <input type="text" readOnly value={symbol || ""} placeholder="Select symbol" style={{ ...inputStyle, width: "100%" }} />
                        <input type="file" accept=".csv" ref={fileInputRef} style={{ display: "none" }} onChange={handleUpload} />
                    </div>

                    <label style={{ color: "#9ca3af", fontSize: 12 }}>Date (UTC)</label>
                    <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={{ ...inputStyle, marginTop: 4, marginBottom: 12 }} />

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
                        <div>
                            <label style={{ color: "#9ca3af", fontSize: 12 }}>Hour From</label>
                            <input type="number" value={hourFrom} onChange={e => setHourFrom(e.target.value)} style={{ ...inputStyle, marginTop: 4 }} />
                        </div>
                        <div>
                            <label style={{ color: "#9ca3af", fontSize: 12 }}>Hour To</label>
                            <input type="number" value={hourTo} onChange={e => setHourTo(e.target.value)} style={{ ...inputStyle, marginTop: 4 }} />
                        </div>
                    </div>

                    <button
                        onClick={runStrategy}
                        disabled={loading || !strategyKey}
                        style={{
                            width: "100%", marginTop: "auto", padding: "12px",
                            background: "#22c55e", color: "black", border: "none", borderRadius: 8,
                            opacity: (loading || !strategyKey) ? 0.6 : 1,
                            cursor: (loading || !strategyKey) ? "not-allowed" : "pointer",
                            fontWeight: "bold"
                        }}
                    >
                        {loading ? "Running..." : "Run Strategy"}
                    </button>

                    {err && <div style={{ color: "#ef4444", fontSize: 12, marginTop: 8 }}>{err}</div>}
                </div>
            </div>

            {/* Results Section (Reusing style) */}
            <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: 16 }}>
                {/* Summary */}
                <div style={{ ...card, height: "auto" }}>
                    <h3 style={{ color: "#e5e7eb", margin: "4px 0 6px" }}>Summary</h3>
                    {!summary ? (
                        <div style={{ color: "#9ca3af", fontSize: 12 }}>No run results yet.</div>
                    ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: 8, color: "#e5e7eb" }}>
                            <div>Trades: <b style={{ float: "right" }}>{summary.trades}</b></div>
                            <div>Wins: <b style={{ float: "right" }}>{summary.wins}</b></div>
                            <div>Losses: <b style={{ float: "right" }}>{summary.losses ?? 0}</b></div>
                            <div>Win%: <b style={{ float: "right" }}>{summary.win_rate}</b></div>
                        </div>
                    )}
                </div>

                {/* Alerts / Table */}
                <div style={{ ...card, height: "auto" }}>
                    <h3 style={{ color: "#e5e7eb", margin: "0 0 12px" }}>Trade Log</h3>
                    {alerts.length === 0 ? (
                        <div style={{ color: "#9ca3af", fontSize: 12 }}>No trades generated.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 12 }}>
                            {alerts.map((a, i) => (
                                <div key={i} style={{ border: "1px solid #1f2937", borderRadius: 8, overflow: "hidden" }}>
                                    <div style={{ padding: "8px 12px", background: "#0f172a", display: "flex", gap: 12, alignItems: "center", fontSize: 13 }}>
                                        <span style={{ color: "#9ca3af" }}>{a.time}</span>
                                        <span style={{ fontWeight: "bold", color: a.side === "LONG" ? "#22c55e" : "#f59e0b" }}>{a.side}</span>
                                        <span style={{ marginLeft: "auto", color: a.take ? "#22c55e" : "#ef4444" }}>
                                            {a.outcome?.toUpperCase()} ({a.r_multiple}R)
                                        </span>
                                    </div>
                                    {a.plot_data_url && (
                                        <div style={{ padding: 8 }}>
                                            <img src={a.plot_data_url} alt="Chart" style={{ width: "100%", borderRadius: 4 }} />
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
