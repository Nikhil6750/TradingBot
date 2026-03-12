// Lightweight unvectorized TA functions for the frontend Replay Terminal

function SMA(data, period, key = 'close') {
    const res = [];
    let sum = 0;
    for (let i = 0; i < data.length; i++) {
        sum += data[i][key];
        if (i >= period) {
            sum -= data[i - period][key];
            res.push({ time: data[i].time, value: sum / period });
        } else if (i === period - 1) {
            res.push({ time: data[i].time, value: sum / period });
        } else {
            res.push({ time: data[i].time, value: NaN });
        }
    }
    return res;
}

function EMA(data, period, key = 'close') {
    const res = [];
    const multiplier = 2 / (period + 1);
    let ema = 0;

    for (let i = 0; i < data.length; i++) {
        const val = data[i][key];
        if (i === 0) {
            ema = val;
            res.push({ time: data[i].time, value: ema });
        } else {
            ema = (val - ema) * multiplier + ema;
            res.push({ time: data[i].time, value: ema });
        }
    }
    return res;
}

function BollingerBands(data, period, stdDev, key = 'close') {
    const sma = SMA(data, period, key);
    const upper = [];
    const lower = [];

    for (let i = 0; i < data.length; i++) {
        if (i < period - 1) {
            upper.push({ time: data[i].time, value: NaN });
            lower.push({ time: data[i].time, value: NaN });
            continue;
        }

        const slice = data.slice(i - period + 1, i + 1);
        const mean = sma[i].value;
        const variance = slice.reduce((sum, val) => sum + Math.pow(val[key] - mean, 2), 0) / period;
        const std = Math.sqrt(variance);

        upper.push({ time: data[i].time, value: mean + (stdDev * std) });
        lower.push({ time: data[i].time, value: mean - (stdDev * std) });
    }
    return { upper, lower };
}

function RSI(data, period, key = 'close') {
    const res = [];
    if (data.length < period) return res;

    let gains = 0;
    let losses = 0;

    for (let i = 1; i <= period; i++) {
        const diff = data[i][key] - data[i - 1][key];
        if (diff >= 0) gains += diff;
        else losses -= diff;
    }

    let avgGain = gains / period;
    let avgLoss = losses / period;

    let rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    let rsi = 100 - (100 / (1 + rs));
    res.push({ time: data[period].time, value: rsi });

    for (let i = period + 1; i < data.length; i++) {
        const diff = data[i][key] - data[i - 1][key];
        const gain = diff >= 0 ? diff : 0;
        const loss = diff < 0 ? -diff : 0;

        avgGain = (avgGain * (period - 1) + gain) / period;
        avgLoss = (avgLoss * (period - 1) + loss) / period;

        rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
        rsi = 100 - (100 / (1 + rs));

        res.push({ time: data[i].time, value: rsi });
    }

    // Pad start
    const padded = [...Array(period).fill({ value: NaN }), ...res];
    for (let i = 0; i < period; i++) padded[i] = { time: data[i]?.time || 0, value: NaN };
    return padded;
}

function MACD(data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9, key = 'close') {
    const fastEma = EMA(data, fastPeriod, key);
    const slowEma = EMA(data, slowPeriod, key);

    const macdLine = [];
    for (let i = 0; i < data.length; i++) {
        if (i < slowPeriod - 1) {
            macdLine.push({ time: data[i].time, value: NaN });
        } else {
            macdLine.push({ time: data[i].time, value: fastEma[i].value - slowEma[i].value });
        }
    }

    const signalEma = EMA(macdLine.filter(d => !isNaN(d.value)), signalPeriod, 'value');

    const signalLine = [];
    const histogram = [];

    let signalIdx = 0;
    for (let i = 0; i < data.length; i++) {
        if (i < slowPeriod - 1 + signalPeriod - 1) {
            signalLine.push({ time: data[i].time, value: NaN });
            histogram.push({ time: data[i].time, value: NaN, color: 'rgba(0,0,0,0)' });
        } else {
            const mVal = macdLine[i].value;
            const sVal = signalEma[signalIdx++].value;
            const hist = mVal - sVal;

            signalLine.push({ time: data[i].time, value: sVal });
            histogram.push({
                time: data[i].time,
                value: hist,
                color: hist >= 0 ? (hist > (histogram[i - 1]?.value || 0) ? '#26a69a' : '#b2dfdb') : (hist < (histogram[i - 1]?.value || 0) ? '#ef5350' : '#ffcdd2')
            });
        }
    }

    return { macd: macdLine, signal: signalLine, histogram };
}

export { SMA, EMA, BollingerBands, RSI, MACD };
