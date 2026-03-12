import { createContext, useContext, useState } from "react";

const StrategyContext = createContext(null);

export function StrategyProvider({ children }) {
    const [config, setConfig] = useState({
        mode: "template", // template, parameter, rules
        strategyTemplate: "ma_crossover",
        templateParams: {
            short_ma_period: 10, long_ma_period: 50,
            lookback_period: 20, deviation_threshold: 2.0,
            rsi_period: 14, oversold_level: 30, overbought_level: 70,
            breakout_period: 20, volume_confirmation: true,
            stop_loss: 0.02, take_profit: 0.04
        },
        customRules: {
            buy: "rsi < 30 AND close > ma50",
            sell: "rsi > 70"
        },
        jsonRules: JSON.stringify({
            buy_rules: [{ indicator: "rsi", operator: "<", value: 30 }],
            sell_rules: [{ indicator: "rsi", operator: ">", value: 70 }]
        }, null, 2),
        globalStops: {
            stop_loss: 0.02,
            take_profit: 0.04
        }
    });

    const [results, setResults] = useState({
        candles: [],
        buySignals: [],
        sellSignals: [],
        trades: [],
        metrics: null,
    });

    // Store the raw File object so other pages (e.g. Results) can re-use it
    const [uploadedFile, setUploadedFile] = useState(null);

    return (
        <StrategyContext.Provider value={{ config, setConfig, results, setResults, uploadedFile, setUploadedFile }}>
            {children}
        </StrategyContext.Provider>
    );
}

export function useStrategy() {
    return useContext(StrategyContext);
}
