import { useEffect, useRef, useMemo } from "react";

/**
 * DataFlowBackground
 * ─────────────────────────────────────────────────────────────────────────
 * SVG network of curved Bézier pipelines with animateMotion particles and
 * glow nodes. Mouse proximity brightens nearby nodes and accelerates
 * nearby particle glows (visual only — no DOM manipulation of animations).
 *
 * All values are expressed as percentages of the SVG viewBox (0 0 1000 600)
 * so the layout is fully responsive.
 */

// ── Network definition ───────────────────────────────────────────────────────

const PATHS = [
    // Horizontal pipelines
    { id: "p1", d: "M -20 120 C 200 100, 350 160, 520 140 S 750 90, 1020 110" },
    { id: "p2", d: "M -20 300 C 150 280, 300 340, 500 300 S 720 240, 1020 260" },
    { id: "p3", d: "M -20 470 C 180 450, 340 510, 510 470 S 760 430, 1020 440" },

    // Cross-pipelines (diagonal data flows)
    { id: "p4", d: "M 80  -20 C 100 120, 160 220, 200 300 S 250 440, 280 620" },
    { id: "p5", d: "M 320 -20 C 350 80,  390 200, 420 300 S 430 430, 460 620" },
    { id: "p6", d: "M 560 -20 C 580 90,  600 200, 630 300 S 650 430, 680 620" },
    { id: "p7", d: "M 800 -20 C 820 100, 840 210, 860 300 S 870 440, 890 620" },

    // Diagonal connectors (signal routing)
    { id: "p8", d: "M -20 120 C 150 200, 280 270, 420 300" },
    { id: "p9", d: "M 420 300 C 560 330, 700 280, 1020 260" },
    { id: "p10", d: "M -20 300 C 120 340, 260 420, 420 470" },
    { id: "p11", d: "M 420 470 C 580 510, 740 460, 1020 440" },
    { id: "p12", d: "M -20 120 C 100 170, 200 250, 320 300" },
    { id: "p13", d: "M 680 300 C 780 240, 880 190, 1020 110" },
];

// Particles: which path, stagger delay, duration, radius, opacity
const PARTICLES = [
    // Horizontal
    { path: "p1", delay: 0, dur: 7, r: 2.5, opacity: 0.9 },
    { path: "p1", delay: 3.5, dur: 7, r: 1.8, opacity: 0.55 },
    { path: "p2", delay: 1, dur: 6, r: 2.2, opacity: 0.85 },
    { path: "p2", delay: 4, dur: 6, r: 1.5, opacity: 0.5 },
    { path: "p3", delay: 2, dur: 8, r: 2, opacity: 0.7 },
    { path: "p3", delay: 5, dur: 8, r: 1.8, opacity: 0.45 },

    // Vertical
    { path: "p4", delay: 0.5, dur: 8, r: 2, opacity: 0.75 },
    { path: "p5", delay: 2, dur: 7, r: 2.2, opacity: 0.8 },
    { path: "p6", delay: 1, dur: 9, r: 1.8, opacity: 0.6 },
    { path: "p7", delay: 3, dur: 7.5, r: 2, opacity: 0.7 },

    // Diagonals
    { path: "p8", delay: 0, dur: 5, r: 1.8, opacity: 0.8 },
    { path: "p9", delay: 1, dur: 5, r: 1.8, opacity: 0.8 },
    { path: "p10", delay: 2, dur: 5.5, r: 1.5, opacity: 0.65 },
    { path: "p11", delay: 3, dur: 5.5, r: 1.5, opacity: 0.65 },
    { path: "p12", delay: 1.5, dur: 4.5, r: 2, opacity: 0.72 },
    { path: "p13", delay: 0.5, dur: 4.5, r: 2, opacity: 0.72 },
];

// Glow nodes at pipeline junctions / indicator decision points
const NODES = [
    { id: "n1", cx: 420, cy: 300, r: 4, label: "Strategy Engine" },
    { id: "n2", cx: 200, cy: 300, r: 3, label: "RSI" },
    { id: "n3", cx: 630, cy: 300, r: 3, label: "MACD" },
    { id: "n4", cx: 320, cy: 140, r: 2.5, label: "EMA Cross" },
    { id: "n5", cx: 750, cy: 90, r: 2.5, label: "Signal Out" },
    { id: "n6", cx: 80, cy: 120, r: 2, label: "Price Feed" },
    { id: "n7", cx: 280, cy: 470, r: 2.5, label: "Bollinger" },
    { id: "n8", cx: 680, cy: 440, r: 2, label: "ATR" },
    { id: "n9", cx: 860, cy: 300, r: 2.5, label: "Risk Filter" },
    { id: "n10", cx: 160, cy: 260, r: 1.8, label: "" },
    { id: "n11", cx: 560, cy: 340, r: 1.8, label: "" },
    { id: "n12", cx: 460, cy: 140, r: 1.5, label: "" },
    { id: "n13", cx: 740, cy: 460, r: 1.5, label: "" },
];

// ── Component ────────────────────────────────────────────────────────────────

export default function DataFlowBackground() {
    const svgRef = useRef(null);
    const mouseRef = useRef({ x: -9999, y: -9999 });
    const nodesRef = useRef([]);
    const rafRef = useRef(null);

    // Animate node glow on mousemove
    useEffect(() => {
        const onMove = (e) => {
            if (!svgRef.current) return;
            const rect = svgRef.current.getBoundingClientRect();
            // Map mouse → SVG viewBox coords
            const vx = ((e.clientX - rect.left) / rect.width) * 1000;
            const vy = ((e.clientY - rect.top) / rect.height) * 600;
            mouseRef.current = { x: vx, y: vy };
        };
        window.addEventListener("mousemove", onMove, { passive: true });
        return () => window.removeEventListener("mousemove", onMove);
    }, []);

    useEffect(() => {
        const tick = () => {
            const { x, y } = mouseRef.current;
            nodesRef.current.forEach((el, i) => {
                if (!el) return;
                const node = NODES[i];
                const dx = node.cx - x;
                const dy = node.cy - y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                // Brighten within 180 viewBox units of cursor
                const proximity = Math.max(0, 1 - dist / 180);
                const baseAlpha = 0.25 + proximity * 0.6;
                const scale = 1 + proximity * 0.8;
                el.style.opacity = baseAlpha;
                el.style.transform = `scale(${scale})`;
            });
            rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);
        return () => rafRef.current && cancelAnimationFrame(rafRef.current);
    }, []);

    return (
        <svg
            ref={svgRef}
            viewBox="0 0 1000 600"
            preserveAspectRatio="xMidYMid slice"
            className="absolute inset-0 w-full h-full pointer-events-none select-none"
            aria-hidden="true"
        >
            <defs>
                {/* Glow filter for particles */}
                <filter id="glow-particle" x="-100%" y="-100%" width="300%" height="300%">
                    <feGaussianBlur stdDeviation="2.5" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>

                {/* Glow filter for nodes */}
                <filter id="glow-node" x="-200%" y="-200%" width="500%" height="500%">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                    </feMerge>
                </filter>

                {/* Hidden paths used by animateMotion */}
                {PATHS.map(p => (
                    <path key={p.id} id={p.id} d={p.d} />
                ))}
            </defs>

            {/* ── Pipeline lines ──────────────────────────────────────── */}
            {PATHS.map(p => (
                <use
                    key={p.id}
                    href={`#${p.id}`}
                    stroke="rgba(255,255,255,0.07)"
                    strokeWidth="0.8"
                    fill="none"
                    strokeLinecap="round"
                />
            ))}

            {/* ── Moving particles ────────────────────────────────────── */}
            {PARTICLES.map((pt, i) => (
                <circle
                    key={i}
                    r={pt.r}
                    fill="white"
                    opacity={pt.opacity}
                    filter="url(#glow-particle)"
                >
                    <animateMotion
                        dur={`${pt.dur}s`}
                        begin={`${pt.delay}s`}
                        repeatCount="indefinite"
                        rotate="auto"
                    >
                        <mpath href={`#${pt.path}`} />
                    </animateMotion>
                </circle>
            ))}

            {/* ── Glow nodes (decision points) ────────────────────────── */}
            {NODES.map((node, i) => (
                <g
                    key={node.id}
                    filter="url(#glow-node)"
                    style={{
                        opacity: 0.25,
                        transformOrigin: `${node.cx}px ${node.cy}px`,
                        transition: "opacity 0.25s ease, transform 0.25s ease",
                    }}
                    ref={el => { nodesRef.current[i] = el; }}
                >
                    {/* Outer halo */}
                    <circle
                        cx={node.cx} cy={node.cy}
                        r={node.r * 3.5}
                        fill="rgba(255,255,255,0.04)"
                    />
                    {/* Inner dot */}
                    <circle
                        cx={node.cx} cy={node.cy}
                        r={node.r}
                        fill="rgba(255,255,255,0.7)"
                    />
                    {/* Label (only for named nodes) */}
                    {node.label && (
                        <text
                            x={node.cx + node.r + 4}
                            y={node.cy + 4}
                            fontSize="8"
                            fill="rgba(255,255,255,0.3)"
                            fontFamily="Inter, monospace"
                            letterSpacing="0.04em"
                        >
                            {node.label}
                        </text>
                    )}
                </g>
            ))}
        </svg>
    );
}
