import { useEffect, useRef } from "react";

/**
 * AlgoTradeFlowBackground
 * ─────────────────────────────────────────────────────────────────────────
 * Canvas-based layered animation:
 *   Layer 1 — Faint market-data grid
 *   Layer 2 — Sparse cubic Bézier algorithm paths
 *   Layer 3 — Glowing data-packet particles traveling along paths
 *             (mouse proximity → speed boost)
 *   Layer 4 — Softly pulsing decision nodes at path junctions
 *
 * Color scheme: dark-blue (#0B0F19→#05060A bg), #A7C7FF particles,
 * rgba(255,255,255,0.06) lines, rgba(167,199,255,0.25) nodes.
 */

// ── Cubic Bézier helpers ─────────────────────────────────────────────────────

function bezier(t, p0, p1, p2, p3) {
    const u = 1 - t;
    return u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3;
}

function bezierPoint(t, path) {
    return {
        x: bezier(t, path.x0, path.x1, path.x2, path.x3),
        y: bezier(t, path.y0, path.y1, path.y2, path.y3),
    };
}

// ── Path definitions (normalised 0–1, scaled on draw) ────────────────────────
// Each path: p0→p3 are control points as fractions of width/height

const RAW_PATHS = [
    // Horizontal pipelines
    { x0: -0.02, y0: 0.18, x1: 0.20, y1: 0.15, x2: 0.50, y2: 0.22, x3: 1.02, y3: 0.20 },
    { x0: -0.02, y0: 0.50, x1: 0.25, y1: 0.46, x2: 0.55, y2: 0.54, x3: 1.02, y3: 0.50 },
    { x0: -0.02, y0: 0.80, x1: 0.22, y1: 0.76, x2: 0.52, y2: 0.82, x3: 1.02, y3: 0.78 },

    // Vertical pipelines
    { x0: 0.20, y0: -0.05, x1: 0.22, y1: 0.28, x2: 0.18, y2: 0.52, x3: 0.20, y3: 1.05 },
    { x0: 0.50, y0: -0.05, x1: 0.52, y1: 0.25, x2: 0.48, y2: 0.55, x3: 0.50, y3: 1.05 },
    { x0: 0.80, y0: -0.05, x1: 0.78, y1: 0.30, x2: 0.82, y2: 0.58, x3: 0.80, y3: 1.05 },

    // Diagonal connectors
    { x0: -0.02, y0: 0.18, x1: 0.12, y1: 0.32, x2: 0.18, y2: 0.44, x3: 0.20, y3: 0.50 },
    { x0: 0.20, y0: 0.50, x1: 0.30, y1: 0.56, x2: 0.40, y2: 0.58, x3: 0.50, y3: 0.50 },
    { x0: 0.50, y0: 0.50, x1: 0.62, y1: 0.44, x2: 0.72, y2: 0.52, x3: 0.80, y3: 0.50 },
    { x0: 0.80, y0: 0.50, x1: 0.88, y1: 0.36, x2: 0.94, y2: 0.28, x3: 1.02, y3: 0.20 },
    { x0: 0.50, y0: 0.50, x1: 0.52, y1: 0.62, x2: 0.50, y2: 0.72, x3: 0.50, y3: 1.05 },
    { x0: 0.20, y0: 0.50, x1: 0.22, y1: 0.62, x2: 0.20, y2: 0.70, x3: 0.20, y3: 1.05 },
];

// Decision nodes (normalised x, y)
const RAW_NODES = [
    { x: 0.20, y: 0.18, r: 4.5, label: "Price Feed" },
    { x: 0.50, y: 0.18, r: 3.5, label: "" },
    { x: 0.20, y: 0.50, r: 5.5, label: "RSI Engine" },
    { x: 0.50, y: 0.50, r: 7, label: "Strategy Core" },
    { x: 0.80, y: 0.50, r: 5, label: "Risk Filter" },
    { x: 0.20, y: 0.80, r: 3.5, label: "" },
    { x: 0.50, y: 0.80, r: 4, label: "Signal Out" },
    { x: 0.80, y: 0.80, r: 3, label: "" },
    { x: 0.80, y: 0.20, r: 3.5, label: "MACD" },
];

// Particles
const PARTICLE_CONFIG = [
    { pathIdx: 0, tStart: 0.0, speed: 0.018 },
    { pathIdx: 0, tStart: 0.5, speed: 0.015 },
    { pathIdx: 1, tStart: 0.1, speed: 0.016 },
    { pathIdx: 1, tStart: 0.65, speed: 0.013 },
    { pathIdx: 2, tStart: 0.2, speed: 0.017 },
    { pathIdx: 3, tStart: 0.0, speed: 0.014 },
    { pathIdx: 3, tStart: 0.55, speed: 0.016 },
    { pathIdx: 4, tStart: 0.15, speed: 0.012 },
    { pathIdx: 5, tStart: 0.3, speed: 0.015 },
    { pathIdx: 6, tStart: 0.0, speed: 0.020 },
    { pathIdx: 7, tStart: 0.0, speed: 0.019 },
    { pathIdx: 8, tStart: 0.0, speed: 0.018 },
    { pathIdx: 9, tStart: 0.0, speed: 0.017 },
    { pathIdx: 10, tStart: 0.0, speed: 0.016 },
    { pathIdx: 11, tStart: 0.2, speed: 0.015 },
];

// ── Component ────────────────────────────────────────────────────────────────

export default function AlgoTradeFlowBackground() {
    const canvasRef = useRef(null);
    const mouseRef = useRef({ x: -9999, y: -9999 });

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");

        // Initialise particle state
        const particles = PARTICLE_CONFIG.map(cfg => ({
            ...cfg,
            t: cfg.tStart,
            baseSpeed: cfg.speed,
        }));

        // Pulse state per node
        const nodePulse = RAW_NODES.map(() => Math.random() * Math.PI * 2);

        let animId;
        let lastTime = 0;

        // ── Size canvas ──────────────────────────────────────────────────
        function resize() {
            canvas.width = canvas.offsetWidth;
            canvas.height = canvas.offsetHeight;
        }
        resize();
        const ro = new ResizeObserver(resize);
        ro.observe(canvas);

        // ── Draw loop ────────────────────────────────────────────────────
        function draw(ts) {
            animId = requestAnimationFrame(draw);

            const dt = Math.min((ts - lastTime) / 1000, 0.05); // seconds, capped
            lastTime = ts;

            const W = canvas.width;
            const H = canvas.height;
            if (W === 0 || H === 0) return;

            ctx.clearRect(0, 0, W, H);

            // Scale helpers
            const sx = p => p * W;
            const sy = p => p * H;

            // Scale a path to pixel coords
            function scalePath(rp) {
                return {
                    x0: sx(rp.x0), y0: sy(rp.y0),
                    x1: sx(rp.x1), y1: sy(rp.y1),
                    x2: sx(rp.x2), y2: sy(rp.y2),
                    x3: sx(rp.x3), y3: sy(rp.y3),
                };
            }
            const paths = RAW_PATHS.map(scalePath);

            // Scale a node
            function scaleNode(rn) {
                return { ...rn, px: sx(rn.x), py: sy(rn.y) };
            }
            const nodes = RAW_NODES.map(scaleNode);

            const mx = mouseRef.current.x;
            const my = mouseRef.current.y;

            // ── Layer 1: Grid ──────────────────────────────────────────
            const GRID = 60;
            ctx.strokeStyle = "rgba(255,255,255,0.035)";
            ctx.lineWidth = 0.5;
            for (let x = 0; x < W; x += GRID) {
                ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
            }
            for (let y = 0; y < H; y += GRID) {
                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
            }

            // ── Layer 2: Bezier paths ──────────────────────────────────
            ctx.strokeStyle = "rgba(167,199,255,0.06)";
            ctx.lineWidth = 1;
            paths.forEach(p => {
                ctx.beginPath();
                ctx.moveTo(p.x0, p.y0);
                ctx.bezierCurveTo(p.x1, p.y1, p.x2, p.y2, p.x3, p.y3);
                ctx.stroke();
            });

            // ── Layer 3: Decision nodes (pulsing) ─────────────────────
            nodes.forEach((node, i) => {
                nodePulse[i] += dt * 0.6;
                const pulse = Math.sin(nodePulse[i]) * 0.5 + 0.5; // 0–1

                // Mouse proximity boost
                const dx = node.px - mx;
                const dy = node.py - my;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const prox = Math.max(0, 1 - dist / (Math.min(W, H) * 0.25));

                const alpha = 0.12 + pulse * 0.12 + prox * 0.35;
                const r = node.r + pulse * 1.5 + prox * 3;

                // Outer glow ring
                const grad = ctx.createRadialGradient(node.px, node.py, 0, node.px, node.py, r * 5);
                grad.addColorStop(0, `rgba(167,199,255,${alpha * 0.9})`);
                grad.addColorStop(0.4, `rgba(167,199,255,${alpha * 0.3})`);
                grad.addColorStop(1, "rgba(167,199,255,0)");
                ctx.beginPath();
                ctx.arc(node.px, node.py, r * 5, 0, Math.PI * 2);
                ctx.fillStyle = grad;
                ctx.fill();

                // Core dot
                ctx.beginPath();
                ctx.arc(node.px, node.py, r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(167,199,255,${0.35 + prox * 0.5})`;
                ctx.fill();

                // Label on hover
                if (prox > 0.25 && node.label) {
                    ctx.fillStyle = `rgba(167,199,255,${prox * 0.7})`;
                    ctx.font = "10px Inter, monospace";
                    ctx.fillText(node.label, node.px + r + 5, node.py + 4);
                }
            });

            // ── Layer 4: Data-packet particles ────────────────────────
            particles.forEach(pt => {
                const path = paths[pt.pathIdx];

                // Mouse proximity → speed boost (up to 3×)
                const pos = bezierPoint(pt.t, path);
                const ddx = pos.x - mx;
                const ddy = pos.y - my;
                const pdist = Math.sqrt(ddx * ddx + ddy * ddy);
                const boost = 1 + Math.max(0, 1 - pdist / (Math.min(W, H) * 0.25)) * 2;

                pt.t += pt.baseSpeed * boost * dt * 60;
                if (pt.t > 1) pt.t = 0;

                const { x, y } = bezierPoint(pt.t, path);

                // Glow
                const glowR = 14;
                const glow = ctx.createRadialGradient(x, y, 0, x, y, glowR);
                glow.addColorStop(0, "rgba(167,199,255,0.55)");
                glow.addColorStop(0.4, "rgba(167,199,255,0.18)");
                glow.addColorStop(1, "rgba(167,199,255,0)");
                ctx.beginPath();
                ctx.arc(x, y, glowR, 0, Math.PI * 2);
                ctx.fillStyle = glow;
                ctx.fill();

                // Core dot
                ctx.beginPath();
                ctx.arc(x, y, 2, 0, Math.PI * 2);
                ctx.fillStyle = "#A7C7FF";
                ctx.fill();
            });
        }

        animId = requestAnimationFrame(draw);

        // Mouse
        const onMove = (e) => {
            const rect = canvas.getBoundingClientRect();
            mouseRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        };
        window.addEventListener("mousemove", onMove, { passive: true });

        return () => {
            cancelAnimationFrame(animId);
            ro.disconnect();
            window.removeEventListener("mousemove", onMove);
        };
    }, []);

    return (
        <canvas
            ref={canvasRef}
            className="absolute inset-0 w-full h-full pointer-events-none"
            aria-hidden="true"
        />
    );
}
