import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, BarChart2, Cpu, TrendingUp, Activity, Brain, LineChart, Target, Layers } from "lucide-react";

// ── Shared design tokens ──────────────────────────────────────────────────────
const C = {
    bg: "#050505",
    bgAlt: "#080808",
    card: "#111111",
    border: "rgba(255,255,255,0.07)",
    text: "#FFFFFF",
    muted: "#A1A1A1",
    dim: "#444444",
};

// ── Fade-in wrapper (scroll-triggered via IntersectionObserver) ───────────────
function FadeIn({ children, delay = 0, className = "" }) {
    const ref = useRef(null);
    const [vis, setVis] = useState(false);
    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVis(true); io.disconnect(); } }, { threshold: 0.15 });
        io.observe(el);
        return () => io.disconnect();
    }, []);
    return (
        <div
            ref={ref}
            className={className}
            style={{
                opacity: vis ? 1 : 0,
                transform: vis ? "translateY(0)" : "translateY(18px)",
                transition: `opacity 0.55s ease ${delay}s, transform 0.55s ease ${delay}s`,
            }}
        >
            {children}
        </div>
    );
}

// ── Count-up ──────────────────────────────────────────────────────────────────
function useCounter(target, duration, start) {
    const [v, setV] = useState(0);
    const raf = useRef(null);
    useEffect(() => {
        if (!start) return;
        const t0 = performance.now();
        const tick = (now) => {
            const p = Math.min((now - t0) / duration, 1);
            setV(Math.round((1 - Math.pow(1 - p, 3)) * target));
            if (p < 1) raf.current = requestAnimationFrame(tick);
        };
        raf.current = requestAnimationFrame(tick);
        return () => raf.current && cancelAnimationFrame(raf.current);
    }, [start, target, duration]);
    return v;
}

// ── Divider ───────────────────────────────────────────────────────────────────
function Divider() {
    return <div className="w-full" style={{ height: "1px", background: C.border }} />;
}

// ── Section wrapper ───────────────────────────────────────────────────────────
function Section({ children, alt = false, className = "" }) {
    return (
        <section
            className={`w-full px-6 md:px-16 lg:px-24 py-24 ${className}`}
            style={{ background: alt ? C.bgAlt : C.bg }}
        >
            <div className="max-w-6xl mx-auto">
                {children}
            </div>
        </section>
    );
}

// ── Label chip ────────────────────────────────────────────────────────────────
function Label({ text }) {
    return (
        <span
            className="inline-block text-[10px] font-semibold uppercase tracking-[0.2em] px-3 py-1 rounded-full mb-6"
            style={{ background: "rgba(255,255,255,0.05)", border: `1px solid ${C.border}`, color: C.muted }}
        >
            {text}
        </span>
    );
}

// ── Feature card ──────────────────────────────────────────────────────────────
function FeatureCard({ icon: Icon, title, desc, delay }) {
    const [hov, setHov] = useState(false);
    return (
        <FadeIn delay={delay}>
            <div
                onMouseEnter={() => setHov(true)}
                onMouseLeave={() => setHov(false)}
                className="flex flex-col gap-4 p-6 rounded-2xl cursor-default"
                style={{
                    background: C.card,
                    border: `1px solid ${hov ? "rgba(255,255,255,0.14)" : C.border}`,
                    transition: "border-color 0.2s ease, box-shadow 0.2s ease",
                    boxShadow: hov ? "0 0 0 1px rgba(255,255,255,0.06) inset" : "none",
                }}
            >
                <div
                    className="w-10 h-10 rounded-xl flex items-center justify-center"
                    style={{ background: "rgba(255,255,255,0.05)" }}
                >
                    <Icon size={18} color={C.muted} strokeWidth={1.5} />
                </div>
                <div>
                    <p className="text-sm font-semibold mb-1" style={{ color: C.text }}>{title}</p>
                    <p className="text-xs leading-relaxed" style={{ color: C.dim }}>{desc}</p>
                </div>
            </div>
        </FadeIn>
    );
}

// ── Workflow step ─────────────────────────────────────────────────────────────
function WorkflowStep({ n, title, desc, last }) {
    return (
        <div className="flex flex-col items-center text-center relative flex-1 min-w-0">
            {/* connector line */}
            {!last && (
                <div
                    className="absolute top-5 left-1/2 w-full"
                    style={{ height: "1px", background: C.border, zIndex: 0 }}
                />
            )}
            <div
                className="relative z-10 w-10 h-10 rounded-full flex items-center justify-center mb-4 flex-shrink-0"
                style={{ background: C.card, border: `1px solid ${C.border}` }}
            >
                <span className="text-xs font-black" style={{ color: C.muted }}>{n}</span>
            </div>
            <p className="text-sm font-semibold mb-1" style={{ color: C.text }}>{title}</p>
            <p className="text-xs leading-relaxed px-2" style={{ color: C.dim }}>{desc}</p>
        </div>
    );
}

// ── AI block ──────────────────────────────────────────────────────────────────
function AIBlock({ icon: Icon, title, desc, delay }) {
    return (
        <FadeIn delay={delay}>
            <div className="flex gap-4 items-start py-6" style={{ borderBottom: `1px solid ${C.border}` }}>
                <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                    style={{ background: "rgba(255,255,255,0.04)", border: `1px solid ${C.border}` }}
                >
                    <Icon size={16} color={C.muted} strokeWidth={1.5} />
                </div>
                <div>
                    <p className="text-sm font-semibold mb-1" style={{ color: C.text }}>{title}</p>
                    <p className="text-xs leading-relaxed" style={{ color: C.dim }}>{desc}</p>
                </div>
            </div>
        </FadeIn>
    );
}

// ── Stat chip (with count-up) ─────────────────────────────────────────────────
function StatChip({ value, suffix, label, start, delay }) {
    const n = useCounter(value, 1600, start);
    return (
        <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            className="flex flex-col items-center gap-0.5"
        >
            <span className="text-xl font-black tabular-nums" style={{ color: C.text }}>
                {n.toLocaleString()}{suffix}
            </span>
            <span className="text-[10px] font-medium tracking-widest uppercase" style={{ color: C.dim }}>
                {label}
            </span>
        </motion.div>
    );
}

// ══════════════════════════════════════════════════════════════════════════════
// Page
// ══════════════════════════════════════════════════════════════════════════════

export default function Intro() {
    const navigate = useNavigate();
    const [statsOn, setStatsOn] = useState(false);

    useEffect(() => {
        const t = setTimeout(() => setStatsOn(true), 800);
        return () => clearTimeout(t);
    }, []);

    return (
        <motion.div
            className="w-full overflow-y-auto overflow-x-hidden"
            style={{ background: C.bg, color: C.text, minHeight: "100vh" }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
        >
            {/* ══════════════════════════════════════════════════════════
                SECTION 1 — HERO
            ══════════════════════════════════════════════════════════ */}
            <section
                className="relative w-full min-h-screen flex flex-col items-center justify-center text-center px-6"
                style={{ background: C.bg }}
            >
                {/* Subtle grid */}
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{
                        backgroundImage: `
                            linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                            linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
                        `,
                        backgroundSize: "80px 80px",
                    }}
                />
                {/* Center spotlight */}
                <div
                    className="absolute inset-0 pointer-events-none"
                    style={{ background: "radial-gradient(circle at 50% 45%, rgba(255,255,255,0.04), transparent 55%)" }}
                />

                <div className="relative z-10 flex flex-col items-center gap-7 max-w-3xl">
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.7, ease: "easeOut" }}
                        className="flex flex-col items-center gap-3"
                    >
                        <span
                            className="text-[10px] font-semibold tracking-[0.28em] uppercase"
                            style={{ color: C.dim }}
                        >
                            AI Strategy Research Platform
                        </span>

                        <h1
                            className="text-6xl md:text-8xl font-black tracking-tighter leading-none"
                            style={{ color: C.text }}
                        >
                            AlgoTradeX
                        </h1>
                        <p className="text-base font-medium max-w-md" style={{ color: C.muted }}>
                            Research, build, and backtest algorithmic trading strategies powered by machine learning.
                        </p>
                    </motion.div>

                    {/* Feature pills */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.25, duration: 0.5 }}
                        className="flex flex-wrap items-center justify-center gap-2"
                    >
                        {["Generate Strategies", "Build Strategies", "Backtest Strategies"].map(f => (
                            <span
                                key={f}
                                className="px-3 py-1 rounded-full text-[11px] font-medium"
                                style={{ background: "rgba(255,255,255,0.04)", border: `1px solid ${C.border}`, color: C.dim }}
                            >
                                {f}
                            </span>
                        ))}
                    </motion.div>

                    {/* CTA */}
                    <motion.button
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        whileHover={{ y: -2, boxShadow: "0 8px 24px rgba(255,255,255,0.10)" }}
                        whileTap={{ scale: 0.97 }}
                        transition={{ duration: 0.4, delay: 0.3 }}
                        onClick={() => navigate("/setup")}
                        className="group flex items-center gap-2.5 px-8 py-3.5 rounded-xl text-sm font-semibold cursor-pointer"
                        style={{ background: C.text, color: C.bg }}
                        onMouseEnter={e => e.currentTarget.style.background = "#ECECEC"}
                        onMouseLeave={e => e.currentTarget.style.background = C.text}
                    >
                        Get Started
                        <ArrowRight size={16} strokeWidth={2.5}
                            className="group-hover:translate-x-0.5 transition-transform duration-200" />
                    </motion.button>

                    {/* Stats */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: statsOn ? 1 : 0 }}
                        transition={{ duration: 0.5 }}
                        className="flex items-center gap-10 md:gap-14"
                    >
                        {[
                            { value: 500, suffix: "+", label: "Strategies Tested", delay: 0 },
                            { value: 10000, suffix: "+", label: "Backtests Run", delay: 0.1 },
                            { value: 99, suffix: "%", label: "AI-Powered Insights", delay: 0.2 },
                        ].map(s => <StatChip key={s.label} {...s} start={statsOn} />)}
                    </motion.div>
                </div>

                {/* Scroll hint */}
                <div className="absolute bottom-10 flex flex-col items-center gap-2">
                    <div className="w-px h-10" style={{ background: `linear-gradient(to bottom, transparent, ${C.border})` }} />
                </div>
            </section>

            <Divider />

            {/* ══════════════════════════════════════════════════════════
                SECTION 2 — CAPABILITIES
            ══════════════════════════════════════════════════════════ */}
            <Section alt>
                <FadeIn className="mb-14 flex flex-col items-center text-center">
                    <Label text="Platform" />
                    <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-3" style={{ color: C.text }}>
                        Research-grade capabilities
                    </h2>
                    <p className="text-sm max-w-lg" style={{ color: C.muted }}>
                        Everything you need to go from strategy idea to validated performance.
                    </p>
                </FadeIn>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {[
                        { icon: Layers, title: "Build Strategies", desc: "Define entry and exit logic using templates, indicator rules, or a visual node builder.", delay: 0 },
                        { icon: BarChart2, title: "Backtest Engine", desc: "Simulate strategies against historical OHLCV data with accurate trade execution modeling.", delay: 0.08 },
                        { icon: Target, title: "AI Trade Scoring", desc: "Every signal is scored for confidence and risk using ML-based market feature analysis.", delay: 0.16 },
                        { icon: Activity, title: "Market Regime Detection", desc: "Classify market conditions in real time — trending, sideways, or high/low volatility.", delay: 0.24 },
                    ].map(c => <FeatureCard key={c.title} {...c} />)}
                </div>
            </Section>

            <Divider />

            {/* ══════════════════════════════════════════════════════════
                SECTION 3 — STRATEGY WORKFLOW
            ══════════════════════════════════════════════════════════ */}
            <Section>
                <FadeIn className="mb-16 flex flex-col items-center text-center">
                    <Label text="Workflow" />
                    <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-3" style={{ color: C.text }}>
                        From idea to insight in four steps
                    </h2>
                    <p className="text-sm max-w-lg" style={{ color: C.muted }}>
                        A structured pipeline that mirrors how professional quant researchers work.
                    </p>
                </FadeIn>

                <FadeIn delay={0.1}>
                    <div className="flex flex-col md:flex-row items-start gap-8 md:gap-0">
                        {[
                            { n: "01", title: "Build Strategy", desc: "Use templates, indicator rules, or the visual logic builder to define your trading system." },
                            { n: "02", title: "Upload Data", desc: "Upload historical OHLCV CSV files for any ticker, timeframe, or market." },
                            { n: "03", title: "Run Backtest", desc: "Execute the strategy against your data and get detailed performance metrics instantly." },
                            { n: "04", title: "Optimize Strategy", desc: "Use Bayesian optimization to find the best parameter combinations automatically." },
                        ].map((s, i, arr) => (
                            <WorkflowStep key={s.n} {...s} last={i === arr.length - 1} />
                        ))}
                    </div>
                </FadeIn>
            </Section>

            <Divider />

            {/* ══════════════════════════════════════════════════════════
                SECTION 4 — AI INTELLIGENCE
            ══════════════════════════════════════════════════════════ */}
            <Section alt>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-start">
                    {/* Left: heading */}
                    <FadeIn className="flex flex-col gap-4 lg:sticky lg:top-24">
                        <Label text="AI Intelligence" />
                        <h2 className="text-3xl md:text-4xl font-black tracking-tight" style={{ color: C.text }}>
                            Machine learning at every layer
                        </h2>
                        <p className="text-sm leading-relaxed max-w-sm" style={{ color: C.muted }}>
                            AlgoTradeX embeds ML models directly into the research pipeline — not as an afterthought, but as a core analytical layer.
                        </p>
                    </FadeIn>

                    {/* Right: AI blocks */}
                    <div className="flex flex-col">
                        {[
                            { icon: Activity, title: "AI Market Regime Detection", desc: "Classifies every candle into Trending, Sideways, High Volatility, or Low Volatility using a trained ensemble model — aligning your strategy to current conditions.", delay: 0 },
                            { icon: Brain, title: "Sentiment Analysis", desc: "Integrates macro and market sentiment signals as additional features to improve signal quality before entry.", delay: 0.06 },
                            { icon: Cpu, title: "Strategy Optimization", desc: "Bayesian optimization (Optuna) explores parameter spaces intelligently, replacing brute-force grid search with efficient guided search.", delay: 0.12 },
                            { icon: Target, title: "Trade Confidence Scoring", desc: "Scores each trade signal 0–1 based on surrounding market conditions. High-confidence trades are flagged for sizing and execution priority.", delay: 0.18 },
                        ].map(b => <AIBlock key={b.title} {...b} />)}
                    </div>
                </div>
            </Section>

            <Divider />

            {/* ══════════════════════════════════════════════════════════
                SECTION 5 — FINAL CTA
            ══════════════════════════════════════════════════════════ */}
            <Section className="text-center">
                <FadeIn className="flex flex-col items-center gap-6 max-w-xl mx-auto">
                    <h2 className="text-3xl md:text-4xl font-black tracking-tight" style={{ color: C.text }}>
                        Start building smarter<br />trading strategies.
                    </h2>
                    <p className="text-sm" style={{ color: C.muted }}>
                        No code required. Professional-grade research tools, accessible from day one.
                    </p>
                    <button
                        onClick={() => navigate("/login")}
                        className="group flex items-center gap-2.5 px-8 py-3.5 rounded-xl text-sm font-semibold cursor-pointer"
                        style={{
                            background: C.text,
                            color: C.bg,
                            transition: "background 0.2s ease, transform 0.15s ease",
                        }}
                        onMouseEnter={e => { e.currentTarget.style.background = "#ECECEC"; e.currentTarget.style.transform = "translateY(-2px)"; }}
                        onMouseLeave={e => { e.currentTarget.style.background = C.text; e.currentTarget.style.transform = "translateY(0)"; }}
                    >
                        Launch AlgoTradeX
                        <ArrowRight size={16} strokeWidth={2.5}
                            className="group-hover:translate-x-0.5 transition-transform duration-200" />
                    </button>
                </FadeIn>
            </Section>

            {/* Footer */}
            <div
                className="w-full flex items-center justify-center py-6"
                style={{ borderTop: `1px solid ${C.border}`, background: C.bg }}
            >
                <p className="text-[11px]" style={{ color: C.dim }}>
                    © 2026 AlgoTradeX · AI-Powered Strategy Research
                </p>
            </div>
        </motion.div>
    );
}
