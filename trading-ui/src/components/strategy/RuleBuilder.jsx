import { useCallback, useMemo, useEffect, useRef } from "react";
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    addEdge,
    useNodesState,
    useEdgesState,
    BackgroundVariant,
    MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { useStrategy } from "../../context/StrategyContext";
import { useTheme } from "../../context/ThemeContext";

import IndicatorNode from "./IndicatorNode";
import ConditionNode from "./ConditionNode";
import ActionNode from "./ActionNode";

// ── Register custom node types ──────────────────────────────────────────────

const NODE_TYPES = {
    indicator: IndicatorNode,
    condition: ConditionNode,
    action: ActionNode,
};

// ── Palette items ────────────────────────────────────────────────────────────

const PALETTE = [
    {
        type: "indicator",
        label: "Indicator",
        icon: "📈",
        color: "blue",
        defaults: { indicator: "RSI", period: "14" },
    },
    {
        type: "condition",
        label: "Condition",
        icon: "⚡",
        color: "violet",
        defaults: { operator: "<", value: "30" },
    },
    {
        type: "action",
        label: "Action",
        icon: "🎯",
        color: "emerald",
        defaults: { action: "BUY" },
    },
];

// ── Graph → JSON rules ──────────────────────────────────────────────────────

function graphToRules(nodes, edges) {
    const buyRules = [];
    const sellRules = [];

    // Build adjacency map: nodeId → next nodeId(s)
    const adj = {};
    for (const e of edges) {
        if (!adj[e.source]) adj[e.source] = [];
        adj[e.source].push(e.target);
    }

    const nodeById = Object.fromEntries(nodes.map((n) => [n.id, n]));

    // Walk: indicator → condition → action
    for (const indNode of nodes.filter((n) => n.type === "indicator")) {
        const condIds = adj[indNode.id] ?? [];
        for (const condId of condIds) {
            const condNode = nodeById[condId];
            if (!condNode || condNode.type !== "condition") continue;

            const actionIds = adj[condId] ?? [];
            for (const actionId of actionIds) {
                const actionNode = nodeById[actionId];
                if (!actionNode || actionNode.type !== "action") continue;

                const { indicator, period } = indNode.data;
                const { operator, value } = condNode.data;
                const { action } = actionNode.data;

                const rule = {
                    indicator: period ? `${indicator}${period}` : indicator,
                    operator,
                    value: isNaN(Number(value)) ? value : Number(value),
                };

                if (action === "BUY") buyRules.push(rule);
                if (action === "SELL") sellRules.push(rule);
            }
        }
    }

    return { buy_rules: buyRules, sell_rules: sellRules };
}

// ── Validate: at least one BUY rule ─────────────────────────────────────────

function validate(nodes, edges) {
    const { buy_rules, sell_rules } = graphToRules(nodes, edges);
    if (buy_rules.length === 0 && sell_rules.length === 0) {
        return "Connect at least one Indicator → Condition → Action path.";
    }
    return null;
}

// ── Default initial graph ────────────────────────────────────────────────────

const INITIAL_NODES = [
    {
        id: "n1",
        type: "indicator",
        position: { x: 60, y: 120 },
        data: { indicator: "RSI", period: "14" },
    },
    {
        id: "n2",
        type: "condition",
        position: { x: 300, y: 120 },
        data: { operator: "<", value: "30" },
    },
    {
        id: "n3",
        type: "action",
        position: { x: 540, y: 120 },
        data: { action: "BUY" },
    },
];

const INITIAL_EDGES = [
    { id: "e1-2", source: "n1", target: "n2", animated: true },
    { id: "e2-3", source: "n2", target: "n3", animated: true },
];

// ── Main component ───────────────────────────────────────────────────────────

export default function StrategyNodeEditor() {
    const { setConfig } = useStrategy();
    const { theme } = useTheme();

    const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
    const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);
    const nodeIdRef = useRef(100);

    // Propagate rules to StrategyContext whenever the graph changes
    useEffect(() => {
        const { buy_rules, sell_rules } = graphToRules(nodes, edges);
        setConfig((prev) => ({
            ...prev,
            buy_rules,
            sell_rules,
        }));
    }, [nodes, edges, setConfig]);

    // Update a specific node's data field
    const updateNodeData = useCallback((nodeId, field, value) => {
        setNodes((nds) =>
            nds.map((n) =>
                n.id === nodeId
                    ? { ...n, data: { ...n.data, [field]: value } }
                    : n
            )
        );
    }, [setNodes]);

    // Attach onChange callbacks to nodes
    const nodesWithCallbacks = useMemo(
        () =>
            nodes.map((n) => ({
                ...n,
                data: {
                    ...n.data,
                    onChange: (field, value) => updateNodeData(n.id, field, value),
                },
            })),
        [nodes, updateNodeData]
    );

    const onConnect = useCallback(
        (params) =>
            setEdges((eds) =>
                addEdge(
                    {
                        ...params,
                        animated: true,
                        markerEnd: { type: MarkerType.ArrowClosed, color: "#9aa4af" },
                        style: { stroke: "#9aa4af", strokeWidth: 1.5 },
                    },
                    eds
                )
            ),
        [setEdges]
    );

    // Drop palette item onto canvas
    const onDrop = useCallback(
        (event) => {
            event.preventDefault();
            const type = event.dataTransfer.getData("application/reactflow-type");
            const defaults = JSON.parse(event.dataTransfer.getData("application/reactflow-defaults") || "{}");
            if (!type) return;

            const bounds = event.currentTarget.getBoundingClientRect();
            const position = {
                x: event.clientX - bounds.left - 80,
                y: event.clientY - bounds.top - 30,
            };

            const newId = `n${++nodeIdRef.current}`;
            setNodes((nds) => [
                ...nds,
                { id: newId, type, position, data: { ...defaults } },
            ]);
        },
        [setNodes]
    );

    const onDragOver = useCallback((e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
    }, []);

    const isDark = theme === "dark";
    const bgColor = isDark ? "#0b0f14" : "#f4f6f8";
    const gridColor = isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.06)";
    const minimapMask = isDark ? "#0b0f14" : "#e5e7eb";

    const validationError = validate(nodes, edges);

    return (
        <div className="flex h-full gap-3">
            {/* Left Palette */}
            <div className="flex flex-col gap-2 w-36 shrink-0">
                <p className="text-xs text-textSecondary font-semibold uppercase tracking-widest mb-1">Nodes</p>
                {PALETTE.map(({ type, label, icon, color, defaults }) => (
                    <div
                        key={type}
                        className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border border-border bg-panel/70 cursor-grab text-xs font-medium text-textPrimary hover:border-${color}-400/50 hover:bg-${color}-500/10 transition-all duration-150 select-none`}
                        draggable
                        onDragStart={(e) => {
                            e.dataTransfer.setData("application/reactflow-type", type);
                            e.dataTransfer.setData("application/reactflow-defaults", JSON.stringify(defaults));
                            e.dataTransfer.effectAllowed = "move";
                        }}
                    >
                        <span>{icon}</span>
                        <span>{label}</span>
                    </div>
                ))}

                <div className="mt-auto pt-3 border-t border-border">
                    <p className="text-xs text-textSecondary leading-relaxed">
                        Drag nodes onto the canvas, then connect them.
                    </p>
                </div>
            </div>

            {/* Canvas */}
            <div className="flex-1 min-h-0 rounded-xl overflow-hidden border border-border relative">
                <ReactFlow
                    nodes={nodesWithCallbacks}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    nodeTypes={NODE_TYPES}
                    fitView
                    style={{ background: bgColor }}
                    deleteKeyCode="Delete"
                    multiSelectionKeyCode="Shift"
                >
                    <Background
                        variant={BackgroundVariant.Dots}
                        gap={20}
                        size={1}
                        color={gridColor}
                    />
                    <Controls
                        className="!bg-panel !border-border"
                        showInteractive={false}
                    />
                    <MiniMap
                        maskColor={minimapMask}
                        nodeColor={(n) =>
                            n.type === "indicator" ? "#3b82f6"
                                : n.type === "condition" ? "#8b5cf6"
                                    : n.data?.action === "SELL" ? "#ef4444"
                                        : "#10b981"
                        }
                        style={{ background: isDark ? "#11161c" : "#f5f5f5", border: "1px solid var(--border)" }}
                    />
                </ReactFlow>

                {/* Validation badge */}
                {validationError && (
                    <div className="absolute bottom-3 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg bg-amber-500/20 border border-amber-400/40 text-amber-300 text-xs font-medium">
                        ⚠ {validationError}
                    </div>
                )}
            </div>
        </div>
    );
}
