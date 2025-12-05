import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";

export default function Chat() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

  async function onSubmit(e) {
    e.preventDefault();
    if (!text.trim() || busy) return;
    setBusy(true);
    try {
      // keep your existing call or stub
      await api.ping?.(); // harmless if not present
    } finally {
      setBusy(false);
    }
  }

  return (
    /**
     * This outer wrapper lets the page use all remaining height
     * next to the sidebar/topbar, so vertical centering works.
     */
    <div className="flex-1 overflow-auto">
      {/**
       * The magic line: height = full viewport minus the top header (if any).
       * Adjust 80px to your header height if different.
       */}
      <div className="h-[calc(100vh-80px)] w-full flex items-center justify-center">
        {/* Center column */}
        <div className="w-full max-w-3xl px-4">
          {/* Title */}
          <h1 className="text-center text-3xl sm:text-4xl font-semibold tracking-tight text-neutral-200 mb-6">
            What can I help with?
          </h1>

          {/* Input row */}
          <form
            onSubmit={onSubmit}
            className="flex items-center gap-2 rounded-2xl bg-neutral-900 border border-neutral-800 px-4 py-3"
          >
            <input
              ref={inputRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Ask anything"
              className="flex-1 bg-transparent outline-none text-neutral-200 placeholder:text-neutral-500"
            />
            <button
              type="submit"
              disabled={busy || !text.trim()}
              className="select-none rounded-xl bg-emerald-600 disabled:bg-neutral-700 disabled:text-neutral-400 px-4 py-2 text-sm font-medium text-white"
            >
              {busy ? "Sending…" : "Send"}
            </button>
          </form>

          {/* Tiny hint under input */}
          <p className="mt-2 text-center text-xs text-neutral-500">
            Enter to send · Shift+Enter for newline
          </p>
        </div>
      </div>
    </div>
  );
}
