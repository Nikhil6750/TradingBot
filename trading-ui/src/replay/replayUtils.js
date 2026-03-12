const DEFAULT_METRICS = {
    total_trades: 0,
    win_rate: 0,
    total_return: 0,
    avg_trade: 0,
    best_trade: 0,
    worst_trade: 0,
    profit_factor: 0,
    sharpe_ratio: null,
    max_drawdown: 0,
    expectancy: 0,
};

function getRulesFromConfig(config) {
    if (Array.isArray(config.buy_rules) || Array.isArray(config.sell_rules)) {
        return {
            buy_rules: Array.isArray(config.buy_rules) ? config.buy_rules : [],
            sell_rules: Array.isArray(config.sell_rules) ? config.sell_rules : [],
        };
    }

    try {
        const parsed = JSON.parse(config.jsonRules || "{}");
        return {
            buy_rules: Array.isArray(parsed.buy_rules) ? parsed.buy_rules : [],
            sell_rules: Array.isArray(parsed.sell_rules) ? parsed.sell_rules : [],
        };
    } catch {
        return { buy_rules: [], sell_rules: [] };
    }
}

function extractPeriodsFromRule(rule) {
    const values = [rule?.indicator, rule?.value].filter(Boolean);
    return values.flatMap((value) => {
        const match = String(value).match(/(ema|sma|ma|rsi)(\d+)/i);
        return match ? [Number(match[2])] : [];
    });
}

function appendGroupedEvent(map, key, value) {
    const bucket = map.get(key);
    if (bucket) {
        bucket.push(value);
    } else {
        map.set(key, [value]);
    }
}

export function buildReplayStrategyConfig(config, riskSettings) {
    const stopLoss = Number(riskSettings.stopLossPct || 0) / 100;
    const takeProfit = Number(riskSettings.takeProfitPct || 0) / 100;

    if (config.mode === "rules") {
        const rules = getRulesFromConfig(config);
        return {
            mode: "rules",
            ...rules,
            stop_loss: stopLoss,
            take_profit: takeProfit,
        };
    }

    if (config.mode === "code") {
        return {
            mode: "code",
            code_string: config.codeString || "",
            stop_loss: stopLoss,
            take_profit: takeProfit,
        };
    }

    return {
        mode: "template",
        strategy: config.strategyTemplate,
        parameters: {
            ...(config.templateParams || {}),
            stop_loss: stopLoss,
            take_profit: takeProfit,
        },
        stop_loss: stopLoss,
        take_profit: takeProfit,
    };
}

export function inferReplayStart(candles, config) {
    if (!Array.isArray(candles) || candles.length === 0) {
        return 0;
    }

    let warmup = 50;
    const templateName = config.strategyTemplate || config.strategy;
    const templateParams = config.templateParams || config.parameters || {};

    if (config.mode === "template") {
        if (templateName === "ma_crossover") {
            const shortPeriod = Number(templateParams.short_ma_period || 10);
            const longPeriod = Number(templateParams.long_ma_period || 50);
            warmup = Math.max(shortPeriod, longPeriod) + 5;
        } else if (templateName === "rsi_reversal") {
            warmup = Number(templateParams.rsi_period || 14) + 5;
        } else if (templateName === "breakout") {
            warmup = Number(templateParams.breakout_period || 20) + 5;
        }
    } else if (config.mode === "rules") {
        const rules = getRulesFromConfig(config);
        const periods = [...rules.buy_rules, ...rules.sell_rules].flatMap(extractPeriodsFromRule);
        warmup = periods.length ? Math.max(...periods) + 5 : 50;
    } else if (config.mode === "code") {
        warmup = 100;
    }

    const contextualStart = Math.max(30, warmup + 25);
    return Math.min(candles.length - 1, contextualStart);
}

export function buildStrategyPlan(replayResult) {
    if (!replayResult) {
        return null;
    }

    const buySignalsByTime = new Map();
    const sellSignalsByTime = new Map();
    const entriesByTime = new Map();
    const exitsByTime = new Map();

    const buySignals = Array.isArray(replayResult.buy_signals) ? replayResult.buy_signals : [];
    const sellSignals = Array.isArray(replayResult.sell_signals) ? replayResult.sell_signals : [];
    const trades = Array.isArray(replayResult.trades) ? replayResult.trades : [];

    buySignals.forEach((signal, index) => {
        appendGroupedEvent(buySignalsByTime, Number(signal.time), { ...signal, id: `buy-${index}` });
    });

    sellSignals.forEach((signal, index) => {
        appendGroupedEvent(sellSignalsByTime, Number(signal.time), { ...signal, id: `sell-${index}` });
    });

    trades.forEach((trade, index) => {
        const normalizedTrade = {
            ...trade,
            id: `trade-${index}`,
            entry_time: Number(trade.entry_time),
            exit_time: Number(trade.exit_time),
        };

        appendGroupedEvent(entriesByTime, normalizedTrade.entry_time, normalizedTrade);
        appendGroupedEvent(exitsByTime, normalizedTrade.exit_time, normalizedTrade);
    });

    return {
        buySignalsByTime,
        sellSignalsByTime,
        entriesByTime,
        exitsByTime,
    };
}

export function createEmptyReplayRuntime() {
    return {
        buySignals: [],
        sellSignals: [],
        completedTrades: [],
        openTrades: [],
        lastEvent: null,
    };
}

export function applyReplayEvents(runtime, candle, plan) {
    if (!plan || !candle) {
        return runtime;
    }

    const time = Number(candle.time);
    const buySignals = plan.buySignalsByTime.get(time) || [];
    const sellSignals = plan.sellSignalsByTime.get(time) || [];
    const enteringTrades = plan.entriesByTime.get(time) || [];
    const exitingTrades = plan.exitsByTime.get(time) || [];

    const nextOpenTrades = [...runtime.openTrades];
    enteringTrades.forEach((trade) => {
        nextOpenTrades.push(trade);
    });

    const completedTrades = [...runtime.completedTrades];
    exitingTrades.forEach((trade) => {
        const openTradeIndex = nextOpenTrades.findIndex((candidate) => candidate.id === trade.id);
        if (openTradeIndex >= 0) {
            nextOpenTrades.splice(openTradeIndex, 1);
        }
        completedTrades.push(trade);
    });

    const lastExit = exitingTrades[exitingTrades.length - 1];
    const lastBuy = buySignals[buySignals.length - 1];
    const lastSell = sellSignals[sellSignals.length - 1];

    const lastEvent = lastExit
        ? { type: "exit", trade: lastExit, candle }
        : lastBuy
            ? { type: "buy", signal: lastBuy, candle }
            : lastSell
                ? { type: "sell", signal: lastSell, candle }
                : runtime.lastEvent;

    return {
        buySignals: runtime.buySignals.concat(buySignals),
        sellSignals: runtime.sellSignals.concat(sellSignals),
        completedTrades,
        openTrades: nextOpenTrades,
        lastEvent,
    };
}

export function buildReplayRuntime(candles, cursor, plan) {
    if (!Array.isArray(candles) || !candles.length || !plan) {
        return createEmptyReplayRuntime();
    }

    let runtime = createEmptyReplayRuntime();
    const finalCursor = Math.max(0, Math.min(cursor, candles.length - 1));
    for (let index = 0; index <= finalCursor; index += 1) {
        runtime = applyReplayEvents(runtime, candles[index], plan);
    }
    return runtime;
}

export function computeReplayMetrics(trades) {
    if (!Array.isArray(trades) || trades.length === 0) {
        return DEFAULT_METRICS;
    }

    const pnls = trades.map((trade) => Number(trade.pnl || 0));
    const wins = pnls.filter((pnl) => pnl > 0);
    const losses = pnls.filter((pnl) => pnl <= 0);

    const totalTrades = pnls.length;
    const totalReturn = pnls.reduce((sum, pnl) => sum + pnl, 0);
    const avgTrade = totalReturn / totalTrades;
    const bestTrade = Math.max(...pnls);
    const worstTrade = Math.min(...pnls);
    const grossProfit = wins.reduce((sum, pnl) => sum + pnl, 0);
    const grossLoss = Math.abs(losses.reduce((sum, pnl) => sum + pnl, 0));
    const winRate = wins.length / totalTrades;
    const avgWin = wins.length ? grossProfit / wins.length : 0;
    const avgLoss = losses.length ? losses.reduce((sum, pnl) => sum + pnl, 0) / losses.length : 0;
    const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : (grossProfit > 0 ? Number.POSITIVE_INFINITY : 0);

    const equityCurve = [1];
    pnls.forEach((pnl) => {
        equityCurve.push(equityCurve[equityCurve.length - 1] * (1 + pnl));
    });

    let peak = equityCurve[0];
    let maxDrawdown = 0;
    for (const point of equityCurve) {
        peak = Math.max(peak, point);
        maxDrawdown = Math.min(maxDrawdown, point / peak - 1);
    }

    let sharpeRatio = null;
    if (pnls.length >= 5) {
        const returns = [];
        for (let index = 1; index < equityCurve.length; index += 1) {
            returns.push((equityCurve[index] - equityCurve[index - 1]) / equityCurve[index - 1]);
        }

        const mean = returns.reduce((sum, value) => sum + value, 0) / returns.length;
        const variance = returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / returns.length;
        const stdDev = Math.sqrt(variance);
        if (stdDev > 1e-10) {
            sharpeRatio = mean / stdDev * Math.sqrt(252);
        }
    }

    return {
        total_trades: totalTrades,
        win_rate: winRate,
        total_return: totalReturn,
        avg_trade: avgTrade,
        best_trade: bestTrade,
        worst_trade: worstTrade,
        profit_factor: profitFactor,
        sharpe_ratio: sharpeRatio,
        max_drawdown: maxDrawdown,
        expectancy: winRate * avgWin - (1 - winRate) * Math.abs(avgLoss),
    };
}

export function formatPercent(value) {
    const numeric = Number(value || 0) * 100;
    return `${numeric >= 0 ? "+" : ""}${numeric.toFixed(2)}%`;
}

export function formatPrice(value) {
    return Number(value || 0).toFixed(5);
}

export function formatReplayTime(time) {
    if (!time) {
        return "Waiting for replay";
    }

    return new Date(Number(time) * 1000).toLocaleString();
}
