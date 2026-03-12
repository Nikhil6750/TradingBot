import { useRef, useState } from "react";

export default function CSVUploader({ file, setFile }) {
    const inputRef = useRef(null);
    const [dragging, setDragging] = useState(false);

    const handleDrop = (e) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f?.name.endsWith(".csv")) setFile(f);
    };

    const handleChange = (e) => {
        const f = e.target.files?.[0];
        if (f) setFile(f);
    };

    /* ── Success state ──────────────────────────────────────────────────── */
    if (file) {
        return (
            <div
                className="w-full rounded-xl px-5 py-4 flex items-center gap-4 transition-all duration-300"
                style={{
                    background: "rgba(30,30,30,0.8)",
                    border: "1px solid rgba(34,197,94,0.35)",
                    boxShadow: "0 0 20px rgba(34,197,94,0.12)",
                }}
            >
                {/* Icon */}
                <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: "rgba(34,197,94,0.12)" }}
                >
                    <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                </div>

                {/* File info */}
                <div className="flex flex-col min-w-0">
                    <span className="text-sm font-medium text-emerald-400 truncate">{file.name}</span>
                    <span className="text-xs text-textSecondary mt-0.5">
                        {(file.size / 1024 / 1024).toFixed(2)} MB · CSV
                    </span>
                </div>

                {/* Replace button */}
                <button
                    onClick={() => setFile(null)}
                    className="ml-auto text-[11px] text-textSecondary hover:text-textPrimary transition-colors cursor-pointer px-2 py-1 rounded"
                    style={{ background: "rgba(255,255,255,0.04)" }}
                >
                    Replace
                </button>
            </div>
        );
    }

    /* ── Drop zone ──────────────────────────────────────────────────────── */
    return (
        <div
            className="w-full rounded-xl cursor-pointer transition-all duration-200 flex flex-col items-center justify-center gap-3 py-10"
            style={{
                background: dragging ? "rgba(20,20,20,0.9)" : "rgba(15,15,15,0.8)",
                border: dragging ? "1px dashed rgba(255,255,255,0.22)" : "1px dashed rgba(255,255,255,0.08)",
                transform: dragging ? "translateY(-2px)" : "none",
            }}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current.click()}
        >
            <input
                ref={inputRef}
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={handleChange}
            />

            {/* Upload icon */}
            <div
                className="w-12 h-12 rounded-xl flex items-center justify-center"
                style={{ background: "rgba(255,255,255,0.05)" }}
            >
                <svg className="w-5 h-5 text-textSecondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
            </div>

            <div className="flex flex-col items-center gap-1 text-center">
                <span className="text-sm font-medium text-textPrimary">
                    Drop your CSV file here
                </span>
                <span className="text-xs text-textSecondary">
                    or click to browse · OHLCV format
                </span>
            </div>
        </div>
    );
}
