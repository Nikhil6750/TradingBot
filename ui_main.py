# ui_main.py — Streamlit UI: News (calendar), Chat (hybrid LLM + tools + optional RAG), Strategy (backtester)
# Run: streamlit run ui_main.py

import os
import re
import sys
import time
import random
import subprocess
import datetime as dt
from pathlib import Path
from typing import Optional, Tuple, List

import pandas as pd
import streamlit as st

# ======================
# App config and styles
# ======================
st.set_page_config(page_title="Trading Bot", page_icon="📈", layout="wide")
st.markdown(
    """
    <style>
        .hero h1 { margin: 0 0 0.25rem 0; font-size: 2rem; }
        .hero-sub { color: #6b7280; margin-bottom: 1rem; }
        .small { font-size: 0.9rem; color: #6b7280; }
        .ok { color: #16a34a; }
        .warn { color: #ca8a04; }
        .err { color: #dc2626; }
        .stButton button { border-radius: 10px; }
        .pill { display:inline-block; padding:2px 8px; border-radius:999px; background:#f1f5f9; margin-right:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ======================
# Constants / Paths
# ======================
ROOT = Path.cwd()
CAL_TODAY = ROOT / "calendar_today.csv"
BACKTEST_RESULTS = ROOT / "backtest_results.csv"
AUDIT_BY_SYMBOL = ROOT / "audit_by_symbol.csv"
AUDIT_BY_HOUR = ROOT / "audit_by_hour.csv"

# ======================
# Gemini (Google) — robust init + helpers
# ======================
GEMINI_AVAILABLE = False
genai = None

def _load_env_key() -> Optional[str]:
    # support either env var; both can point to the same key
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or (st.secrets.get("GEMINI_API_KEY") if hasattr(st, "secrets") else None)
        or (st.secrets.get("GOOGLE_API_KEY") if hasattr(st, "secrets") else None)
    )
    return key

try:
    import google.generativeai as genai  # type: ignore
    _gemini_key = _load_env_key()
    if _gemini_key:
        genai.configure(api_key=_gemini_key)
        GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

# Models you actually have (from your check_models output)
GEMINI_MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-latest",
    "gemini-pro-latest",
]

SYSTEM_INSTRUCTION = (
    # 1. CORE IDENTITY AND PERSONA
    "You are a highly capable and friendly AI assistant, built by Google. Your primary function is to provide comprehensive, accurate, and helpful information across all domains."
    "Maintain a professional, knowledgeable, and empathetic persona. Your tone should be encouraging and non-judgmental."
    "You are designed to assist, explain, brainstorm, and generate creative content. Avoid being overly formal or using unnecessary jargon."

    # 2. KEY PRIORITIES (IN ORDER)
    "1) **Safety and Ethics:** Adhere strictly to all content, safety, and ethical policies. Immediately refuse to generate content that is illegal, harmful, hateful, or promotes violence."
    "2) **Accuracy and Grounding:** Provide factual information based on your training data and real-time searches. If you use the search tool, treat the results as ground truth for current, external information."
    "3) **Helpfulness and Completion:** Address all parts of the user's prompt, ensuring the answer is complete, relevant, and well-structured. Anticipate user intent and offer logical next steps."

    # 3. RESPONSE STRUCTURE AND FORMATTING
    "Obey the Reply Rubric:\n"
    "• **Concise Start:** Begin every response with a crisp, direct, and immediate answer to the user's main question, typically in 1-2 sentences."
    "• **Logical Flow:** Structure the body of the response using markdown headings (`##`) and horizontal lines (`---`) when the content covers multiple distinct points or exceeds a few paragraphs."
    "• **Clarity and Emphasis:** Use **bold** text to highlight keywords, concepts, or critical steps. Use relevant emojis sparingly to enhance the tone."
    "• **Mathematical and Scientific Notation:** Always use $\text{LaTeX}$ formatting for all mathematical and scientific expressions, formulas, and symbols (e.g., $\text{E}=\text{mc}^2$ or $\mu$). Enclose them in dollar signs ($\$$)."
    "• **Code and Commands:** Present all code snippets, terminal commands, or configurations in fenced code blocks (` ```python `) for clarity."

    # 4. TOOL USAGE AND DATA INTEGRITY
    "• **Search Tool Use:** Use the Google search tool only when a query explicitly requires current, real-time, or external information (e.g., news, weather, recent events, specific stock prices, video content)."
    "• **Grounding:** When citing information from the search tool, integrate it naturally into the response; do not simply copy/paste raw snippets."
    "• **Internal Knowledge:** For general knowledge queries, rely on your extensive internal training data ('Based on general knowledge...')."

    # 5. CONVERSATIONAL MANAGEMENT
    "• **Context Awareness:** Refer to previous turns in the conversation to maintain context and continuity. Correct any previous factual errors gracefully."
    "• **Proactive Engagement:** End the response with a thought-provoking question or a relevant, optional suggestion to encourage the user to continue the conversation."
)


def make_gemini(model_name: str):
    return genai.GenerativeModel(model_name)

# ======================
# Optional RAG (retrieval-augmented generation)
# ======================
RAG_AVAILABLE = False
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    RAG_AVAILABLE = True
except Exception:
    RAG_AVAILABLE = False

RAG_DB_DIR = "rag_db"
RAG_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_rag_client = None
_rag_coll = None
_rag_embedder = None

# --- model cache to avoid re-instantiation overhead
_GMODELS = {}

def get_gemini(model_name: str):
    if model_name not in _GMODELS:
        _GMODELS[model_name] = make_gemini(model_name)
    return _GMODELS[model_name]


def rag_init():
    if not RAG_AVAILABLE:
        return
    global _rag_client, _rag_coll, _rag_embedder
    if _rag_client:
        return
    if not Path(RAG_DB_DIR).exists():
        return
    _rag_client = chromadb.PersistentClient(path=RAG_DB_DIR)
    __rag_coll = _rag_client.get_or_create_collection("knowledge_base")

    _rag_embedder = SentenceTransformer(RAG_EMBED_MODEL)
# --- RAG helpers ---

def _kb_file_map():
    """Returns {filename: full_text} for knowledge/*.md"""
    kb = {}
    try:
        for p in (ROOT / "knowledge").glob("*.md"):
            kb[p.name] = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    return kb


def rag_search(query: str, k=8):
    # your rag_search code here...
    ...

def rag_search(query: str, k=8):
    """
    Returns list of (snippet, source). First tries Chroma. If empty or weak,
    falls back to keyword search over knowledge/*.md.
    """
    results = []

    # --- Vector search (Chroma)
    try:
        rag_init()
        if _rag_coll and _rag_embedder:
            qvec = _rag_embedder.encode([query], normalize_embeddings=True).tolist()
            res = _rag_coll.query(query_embeddings=qvec, n_results=k)
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            for snip, meta in zip(docs or [], metas or []):
                if snip:
                    results.append((snip, (meta or {}).get("source", "kb")))
    except Exception:
        pass

    # If we got at least 2 good snippets, return them
    if len(results) >= 2:
        return results[:k]

    # --- Keyword fallback over raw files
    kb = _kb_file_map()
    if not kb:
        return results

    query_l = query.lower()
    scored = []
    for fname, text in kb.items():
        # Split by blank lines into paragraphs
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        for p in paras:
            pl = p.lower()
            # simple score: count overlapping keywords
            score = sum(w in pl for w in query_l.split())
            # bonus for exact key phrases commonly used in your KB
            if "backtest" in pl and "workflow" in query_l:
                score += 3
            if "economic" in pl and "calendar" in pl and "filter" in query_l:
                score += 3
            if score > 0:
                scored.append((score, p, fname))
    scored.sort(key=lambda x: x[0], reverse=True)
    for _, p, fname in scored[:k]:
        results.append((p, fname))

    return results[:k]


def build_context_snippet(query: str):
    """
    Retrieve snippets and return (snippet_text, has_kb_bool, known_sources_list).
    Ensures we keep diverse sources and cap to 5 snippets.
    """
    hits = rag_search(query, k=8)
    if not hits:
        # still provide known sources to avoid fabricated names
        return "", False, list(_kb_file_map().keys())

    # Prefer different sources
    seen = set()
    kept = []
    for snip, src in hits:
        src = src or "kb"
        if src not in seen:
            kept.append((snip, src))
            seen.add(src)
        if len(kept) >= 5:
            break

    lines = ["\n[KNOWLEDGE PACK SNIPPETS]\n"]
    for i, (snip, src) in enumerate(kept, 1):
        snip = (snip or "").strip().replace("\n\n", "\n")
        lines.append(f"({i}) Source: {src}\n{snip}\n")
    known_sources = sorted(set(_kb_file_map().keys()))
    return "\n".join(lines), True, known_sources


def detect_intent(q: str) -> str:
    ql = q.lower().strip()
    # Tools first
    if ql.startswith(("events", "next")):
        return "tool:calendar"
    if ql.startswith("test"):
        return "tool:backtest"
    # KB-heavy trading intents
    trading_kw = ("backtest", "workflow", "risk", "calendar", "impact", "session",
                  "profit factor", "drawdown", "win rate", "strategy", "ATR", "RR", "threshold")
    if any(k in ql for k in trading_kw):
        return "kb:trading"
    return "general"


def _compose_messages(prompt: str, kb_text: str, has_kb: bool, convo_summary: str | None):
    rubric = (
        "Reply Rubric: 1) brief answer, 2) 3–8 bullets with numbers/steps, "
        "3) cite only KNOWN_SOURCES if snippets exist, 4) end with an actionable next step."
    )
    context_bits = []
    if convo_summary:
        context_bits.append(f"[CONVERSATION SUMMARY]\n{convo_summary}\n")
    if has_kb and kb_text:
        context_bits.append(kb_text)
    context = "\n".join(context_bits)

    planner = (
        "You are a planner. Write a short outline: user intent, which tools/KB to use, "
        "and the 3–5 key points to cover. Output 5–8 bullets max."
    )
    drafter = (
        "You are a drafter. Using the plan and context, write the full answer following the Reply Rubric."
    )
    critic = (
        "You are a critic. Improve the draft for trading depth, clarity, and actions. "
        "Tighten wording, keep citations correct, ensure it is grounded in snippets if provided."
    )
    sys = SYSTEM_INSTRUCTION + "\n" + rubric
    return sys, context, planner, drafter, critic

def _call_gemini(messages: list, model_name: str, gen_cfg: dict) -> str:
    model = make_gemini(model_name)
    resp = model.generate_content(messages, generation_config=gen_cfg)
    return (getattr(resp, "text", None) or "").strip()



# ======================
# Generation (Gemini + optional fallbacks)
# ======================
def gemini_generate(prompt: str, fast: bool = False) -> str:
    if not GEMINI_AVAILABLE:
        return ("Gemini key not configured. Set GEMINI_API_KEY / GOOGLE_API_KEY.\n\n"
                "Tools: `events USD` (calendar), `test EURJPY 9-12` (backtest).")

    # --- FAST PATH: single-pass, small token budget, flash model
    if fast:
        kb_text, has_kb, known_sources = build_context_snippet(prompt)
        style = (
            "Reply briefly (<=120 words) with 1–2 sentence answer + 3–5 bullets. "
            "If KNOWLEDGE PACK SNIPPETS present, use them and cite filenames exactly; "
            "if not, say 'Based on general knowledge' and do not cite."
        )
        guard_sources = f"\n[KNOWN_SOURCES] {', '.join(known_sources) if known_sources else '(none)'}\n"
        messages = [SYSTEM_INSTRUCTION + " " + style + guard_sources]
        if has_kb and kb_text:
            messages.append(kb_text)
        messages.append(prompt)

        gen_cfg = {"temperature": 0.55 if has_kb else 0.65,
                   "top_p": 0.9, "max_output_tokens": 520}

        # one try on flash, one fallback to pro (no multi-retry)
        for name in ("gemini-2.5-flash", "gemini-2.5-pro"):
            try:
                model = get_gemini(name)
                resp = model.generate_content(messages, generation_config=gen_cfg)
                text = (getattr(resp, "text", None) or "").strip()
                if text:
                    return text
            except Exception:
                continue

        # optional OpenAI fallback (quick)
        if os.getenv("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                oai = OpenAI()
                chat = oai.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role":"system", "content": SYSTEM_INSTRUCTION + " " + style + guard_sources},
                        {"role":"system", "content": kb_text if (has_kb and kb_text) else ""},
                        {"role":"user", "content": prompt},
                    ],
                    temperature=0.55 if has_kb else 0.65,
                    max_tokens=520,
                )
                t = chat.choices[0].message.content.strip()
                if t: return t
            except Exception:
                pass

        return ("⚠️ I couldn’t reach a model quickly. Try again, or switch Fast replies off for a richer answer.")

    # --- DETAILED PATH (your existing pipeline: planner → draft → critic)
    # keep everything you already had below this line (detect_intent, compose, retries, etc.)
    # NOTE: ensure any calls use get_gemini(name) instead of make_gemini(name)
    kb_text, has_kb, known_sources = build_context_snippet(prompt)
    intent = detect_intent(prompt)

    primary = "gemini-2.5-pro" if has_kb or intent.startswith("kb:") else "gemini-2.5-flash"
    gen_cfg_plan = {"temperature": 0.2, "top_p": 0.9, "max_output_tokens": 280}
    gen_cfg_draft = {"temperature": 0.55 if has_kb else 0.7, "top_p": 0.95, "max_output_tokens": 900}
    gen_cfg_crit = {"temperature": 0.3, "top_p": 0.9, "max_output_tokens": 700}

    convo_summary = st.session_state.get("convo_summary")
    sys, context, planner, drafter, critic = _compose_messages(prompt, kb_text, has_kb, convo_summary)
    guard_sources = f"\n[KNOWN_SOURCES] {', '.join(known_sources) if known_sources else '(none)'}\n"

    # 1) plan
    plan_msgs = [sys + guard_sources]
    if context: plan_msgs.append(context)
    plan_msgs += [planner, f"[USER]\n{prompt}"]
    plan = ""
    for m in GEMINI_MODEL_CANDIDATES:
        try:
            plan = _call_gemini(plan_msgs, m if "pro" in m else primary, gen_cfg_plan)
            if plan: break
        except Exception: continue

    # 2) draft
    draft_msgs = [sys + guard_sources]
    if context: draft_msgs.append(context)
    draft_msgs += [f"[PLAN]\n{plan}", drafter, f"[USER]\n{prompt}"]
    draft = ""
    for m in GEMINI_MODEL_CANDIDATES:
        try:
            draft = _call_gemini(draft_msgs, primary, gen_cfg_draft)
            if draft: break
        except Exception: continue

    # 3) critic
    crit_msgs = [sys + guard_sources]
    if context: crit_msgs.append(context)
    crit_msgs += [f"[PLAN]\n{plan}", f"[DRAFT]\n{draft}", critic]
    final = ""
    for m in GEMINI_MODEL_CANDIDATES:
        try:
            final = _call_gemini(crit_msgs, primary, gen_cfg_crit)
            if final: break
        except Exception: continue

    answer = final or draft or "Sorry, I couldn't compose a reply."

    # short rolling summary
    try:
        summ_model = get_gemini("gemini-2.5-flash")
        summ = summ_model.generate_content([
            "Summarize the last user request and assistant answer in <200 chars, trading-focused>.",
            f"USER: {prompt}", f"ASSISTANT: {answer}"
        ], generation_config={"max_output_tokens": 120, "temperature": 0.1})
        st.session_state["convo_summary"] = (getattr(summ, "text", None) or "").strip()
    except Exception:
        pass

    return answer




# ======================
# Helper functions
# ======================
def _load_calendar_csv(p: Path) -> Optional[pd.DataFrame]:
    if not p.exists():
        return None
    df = pd.read_csv(p)

    rename_map = {
        "time": "Time", "Time": "Time",
        "currency": "Cur.", "Currency": "Cur.",
        "impact": "Imp.", "impact_stars": "Imp.", "Impact": "Imp.",
        "event": "Event", "Event": "Event",
        "actual": "Actual", "forecast": "Forecast", "previous": "Previous",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    for col in ["Time", "Cur.", "Imp.", "Event", "Actual", "Forecast", "Previous"]:
        if col not in df.columns:
            df[col] = ""

    for col in ["Actual", "Forecast", "Previous"]:
        df[col] = df[col].fillna("").astype(str).replace({"nan": ""})
    for col in ["Time", "Cur.", "Imp.", "Event"]:
        df[col] = df[col].astype(str)

    try:
        df["_t"] = pd.to_datetime(df["Time"], format="%H:%M", errors="coerce")
        df = df.sort_values(by="_t", na_position="last").drop(columns=["_t"])
    except Exception:
        pass

    return df

def _now_hhmm() -> str:
    return dt.datetime.now().strftime("%H:%M")

def _next_event_index(df: pd.DataFrame) -> Optional[int]:
    if "Time" not in df.columns or df.empty:
        return None
    now = _now_hhmm()
    later = df["Time"] >= now
    if later.any():
        return later.idxmax()
    return None

def _styled_table(df: pd.DataFrame, next_idx: Optional[int] = None):
    if df.empty or next_idx is None:
        return df
    try:
        return df.style.apply(
            lambda s: ["background: #fff3cd" if s.name == next_idx else "" for _ in s],
            axis=1,
        )
    except Exception:
        return df

def _run_backtester(env_overrides: dict) -> Tuple[str, Optional[pd.DataFrame]]:
    env = os.environ.copy()
    env.setdefault("TRUNCATE_RESULTS", "1")
    env.setdefault("SESSION", "ALL")
    for k, v in env_overrides.items():
        if v is not None:
            env[str(k)] = str(v)

    try:
        subprocess.run([sys.executable, "backtest_runner.py"], check=True, env=env, timeout=180)
    except subprocess.CalledProcessError as e:
        return f"Backtest failed (exit {e.returncode}).", None
    except subprocess.TimeoutExpired:
        return "Backtest timed out after 180s.", None

    if not BACKTEST_RESULTS.exists():
        return "Backtest ran but results file wasn't found.", None

    try:
        df = pd.read_csv(BACKTEST_RESULTS)
    except Exception as e:
        return f"Could not read results CSV: {e}", None

    if df.empty:
        return "No trades found for the given filters.", df

    summary_lines: List[str] = ["Backtest summary:"]
    for key in ["trades", "win_rate", "profit_factor", "avg_r", "total_r"]:
        cols = [c for c in df.columns if c.lower() == key]
        if cols:
            val = df.iloc[0][cols[0]]
            summary_lines.append(f"- {cols[0]}: {val}")
    return "\n".join(summary_lines), df

# ======================
# Pages
# ======================
def page_news():
    st.markdown('<div class="hero"><h1>Today’s Economic Calendar</h1>'
                '<div class="hero-sub">Data from your CSV export</div></div>', unsafe_allow_html=True)

    cols = st.columns([1, 1, 1, 2])
    with cols[0]:
        show_upcoming_only = st.toggle("Upcoming only", value=True, help="Hide past times for today")
    with cols[1]:
        cur_filter = st.text_input("Currency (3-letter, optional)", "", placeholder="USD / EUR / INR ...").strip()
    with cols[2]:
        imp_filter = st.text_input("Impact contains (optional)", "", placeholder="e.g., High").strip()
    with cols[3]:
        st.caption(f"CSV Path: `{CAL_TODAY}`")
        st.button("Reload CSV", help="Re-reads CSV from disk (scrape separately).")

    df = _load_calendar_csv(CAL_TODAY)
    if df is None:
        st.warning("Calendar CSV not found. Generate it with your fetcher script first.")
        return

    if cur_filter:
        df = df[df["Cur."].str.upper() == cur_filter.upper()]
    if imp_filter:
        df = df[df["Imp."].str.contains(imp_filter, case=False, na=False)]

    if show_upcoming_only and "Time" in df.columns:
        now = _now_hhmm()
        df = df[df["Time"] >= now]

    next_idx = _next_event_index(df)
    styled = _styled_table(df, next_idx)
    st.dataframe(styled, use_container_width=True)

    if not df.empty:
        first = df.iloc[0]
        st.markdown(
            f"<div class='small'>Showing <b>{len(df)}</b> row(s). "
            f"Next event: <span class='pill'>{first['Time']} {first['Cur.']} [{first['Imp.']}]</span> "
            f"{first['Event']}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown("<div class='small'>No rows matched your filters.</div>", unsafe_allow_html=True)

def page_chat():
    st.markdown('<div class="hero"><h1>Chat</h1>'
                '<div class="hero-sub">Hybrid: tools + knowledge + Gemini</div></div>',
                unsafe_allow_html=True)

    left, right = st.columns([1, 1])
    with left:
        st.caption("Tips: `events USD` • `events` • `test EURJPY 9-12` • `test`")
    with right:
        if st.button("Clear Chat"):
            st.session_state.pop("chat_messages", None)
            st.rerun()
    speed_col, _ = st.columns([1,3])
    with speed_col:
        st.session_state["fast_mode"] = st.toggle("⚡ Fast replies", value=True,
        help="Single-pass answer using gemini-2.5-flash with a small token budget.")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {"role": "assistant", "content": "Hi Nikhil! I’m grounded by your knowledge pack (backtester workflow, calendar tips, risk rules). Ask me anything—try: 'What’s the workflow to run the backtester?'."}


        ]

    for m in st.session_state.chat_messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    prompt = st.chat_input("Type your message…")
    if not prompt:
        return

    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    text = prompt.strip()

    # A) events [CUR]
    m = re.match(r"^\s*(?:events|next)(?:\s+([A-Za-z]{3}))?\s*$", text, re.I)
    if m:
        cur = m.group(1)
        df = _load_calendar_csv(CAL_TODAY)
        if df is None or df.empty:
            reply = "No calendar found for today. Please generate the CSV first."
            with st.chat_message("assistant"): st.markdown(reply)
            st.session_state.chat_messages.append({"role": "assistant", "content": reply})
            return

        if cur:
            df = df[df["Cur."].str.upper() == cur.upper()].reset_index(drop=True)

        if "Time" in df.columns and len(df):
            now = _now_hhmm()
            df = df[df["Time"] >= now].reset_index(drop=True)

        msg = f"Found {len(df)} upcoming event(s)" + (f" for **{cur.upper()}**" if cur else "") + "."
        with st.chat_message("assistant"):
            st.markdown(msg)
            if not df.empty:
                next_idx = _next_event_index(df)
                styled = _styled_table(df, next_idx)
                st.dataframe(styled, use_container_width=True)
        st.session_state.chat_messages.append({"role": "assistant", "content": msg})
        return

    # B) test [SYMBOL] [HOURS]
    m = re.match(r"^\s*test(?:\s+([A-Z0-9/_.-]+))?(?:\s+([\d\-:,]+))?\s*$", text, re.I)
    if m:
        sym = m.group(1)
        hrs = m.group(2)
        env_overrides = {"SYMBOL_ALLOWLIST": sym, "HOUR_ALLOW": hrs}
        summary, df = _run_backtester(env_overrides)
        with st.chat_message("assistant"):
            st.markdown(summary)
            if isinstance(df, pd.DataFrame) and not df.empty:
                st.dataframe(df.head(100), use_container_width=True)
                if AUDIT_BY_SYMBOL.exists():
                    st.subheader("By Symbol"); st.dataframe(pd.read_csv(AUDIT_BY_SYMBOL), use_container_width=True)
                if AUDIT_BY_HOUR.exists():
                    st.subheader("By Hour"); st.dataframe(pd.read_csv(AUDIT_BY_HOUR), use_container_width=True)
        st.session_state.chat_messages.append({"role": "assistant", "content": summary})
        return

    # C) Fallback to Gemini (typing indicator inside the bubble)
    with st.chat_message("assistant"):
        ph = st.empty()
        ph.markdown("💭 ...")
        reply = gemini_generate(prompt, fast=st.session_state.get("fast_mode", True))

        ph.empty()
        st.markdown(reply)
    st.session_state.chat_messages.append({"role": "assistant", "content": reply})

def page_strategy():
    st.markdown('<div class="hero"><h1>Test Strategy</h1>'
                '<div class="hero-sub">Run your backtester with quick controls</div></div>',
                unsafe_allow_html=True)

    with st.form("run_form", clear_on_submit=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            sym = st.text_input("SYMBOL_ALLOWLIST", "", placeholder="e.g., EURJPY, BTCUSD")
        with c2:
            hrs = st.text_input("HOUR_ALLOW", "", placeholder="e.g., 9-12,15-18")
        with c3:
            session = st.text_input("SESSION", "ALL", help="ALL or a session code if supported")

        c4, c5, c6 = st.columns(3)
        with c4:
            rr = st.number_input("RR", value=1.5, min_value=0.5, max_value=5.0, step=0.1)
        with c5:
            atr = st.number_input("ATR_MULTIPLIER", value=1.8, min_value=0.5, max_value=5.0, step=0.1)
        with c6:
            threshold = st.number_input("THRESHOLD", value=65.0, min_value=0.0, max_value=100.0, step=1.0)

        submitted = st.form_submit_button("Run Backtest")

    if submitted:
        env_overrides = {
            "SYMBOL_ALLOWLIST": sym or None,
            "HOUR_ALLOW": hrs or None,
            "SESSION": session or "ALL",
            "RR": rr, "ATR_MULTIPLIER": atr, "THRESHOLD": threshold,
            "TRUNCATE_RESULTS": "1",
        }
        with st.spinner("Running backtest..."):
            summary, df = _run_backtester(env_overrides)

        st.success("Done.")
        st.text(summary)
        if isinstance(df, pd.DataFrame) and not df.empty:
            st.dataframe(df, use_container_width=True)
            if AUDIT_BY_SYMBOL.exists():
                st.subheader("By Symbol"); st.dataframe(pd.read_csv(AUDIT_BY_SYMBOL), use_container_width=True)
            if AUDIT_BY_HOUR.exists():
                st.subheader("By Hour"); st.dataframe(pd.read_csv(AUDIT_BY_HOUR), use_container_width=True)

# ======================
# Router
# ======================
with st.sidebar:
    page = st.radio("Navigate", ["News", "Chat", "Test Strategy"], index=1)
    st.caption("• CSV path: `calendar_today.csv`\n"
               "• Backtester: `backtest_runner.py`\n"
               "• Set GEMINI_API_KEY / GOOGLE_API_KEY (and OPTIONAL OPENAI_API_KEY) for AI replies.")

if page == "News":
    page_news()
elif page == "Chat":
    page_chat()
else:
    page_strategy()
