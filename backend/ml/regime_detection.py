"""
Market Regime Detection Module
Classifies market conditions into: Trending, Sideways, High Volatility, Low Volatility
Uses a RandomForestClassifier trained on engineered features derived from OHLCV data.
No external APIs required — fully self-contained.
"""

from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── Regime label constants ───────────────────────────────────────────────────
REGIME_LABELS = {
    0: "Sideways",
    1: "Trending",
    2: "High Volatility",
    3: "Low Volatility",
}

# ── Contextual strategy advice ───────────────────────────────────────────────
REGIME_ADVICE = {
    "Trending": "Trend-following strategies (Moving Average Crossover, Breakout) may perform well in this environment.",
    "Sideways": "Mean-reversion strategies (RSI Reversal, Bollinger Band Bounce) tend to outperform in sideways conditions.",
    "High Volatility": "Strategy risk is elevated. Consider reducing position size or widening stop-losses to avoid premature exits.",
    "Low Volatility": "Low-volatility periods often precede larger moves. Breakout setups may offer attractive risk/reward.",
}

# ── Feature engineering ──────────────────────────────────────────────────────

def _calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high = df["high"]
    low  = df["low"]
    close = df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Approximate ADX using directional movement."""
    high  = df["high"]
    low   = df["low"]
    close = df["close"]

    atr = _calculate_atr(df, period)

    up_move   = high.diff()
    down_move = -low.diff()

    plus_dm  = np.where((up_move > down_move) & (up_move > 0), up_move,   0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    plus_dm_s  = pd.Series(plus_dm,  index=df.index).rolling(period).mean()
    minus_dm_s = pd.Series(minus_dm, index=df.index).rolling(period).mean()

    atr_safe = atr.replace(0, np.nan)
    plus_di  = 100 * plus_dm_s  / atr_safe
    minus_di = 100 * minus_dm_s / atr_safe

    dx_denom = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / dx_denom

    return dx.rolling(period).mean()


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build the feature matrix from raw OHLCV data.
    Returns a DataFrame aligned to the original index, NaN rows dropped.
    """
    df = df.copy()

    # Normalise column names
    df.columns = df.columns.str.lower()
    
    # Ensure numeric
    for col in ["open", "high", "low", "close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    feat = pd.DataFrame(index=df.index)

    # 1. Log returns
    feat["returns"]      = np.log(df["close"] / df["close"].shift(1))

    # 2. Rolling volatility (20-bar)
    feat["volatility_20"] = feat["returns"].rolling(20).std()

    # 3. Normalised ATR
    atr = _calculate_atr(df, 14)
    feat["atr_norm"] = atr / df["close"]

    # 4. ADX
    feat["adx"] = _calculate_adx(df, 14)

    # 5. MA slope (50-bar SMA)
    ma50 = df["close"].rolling(50).mean()
    feat["ma_slope"] = ma50.diff(5) / df["close"]

    # 6. Volume change (if available, else zero)
    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce")
        feat["volume_change"] = vol.pct_change().clip(-5, 5)
    else:
        feat["volume_change"] = 0.0

    # 7. Price distance from 20-bar MA (mean-reversion signal)
    ma20 = df["close"].rolling(20).mean()
    feat["dist_ma20"] = (df["close"] - ma20) / df["close"]

    # 8. Volatility regime ratio: recent vs long-term vol
    feat["vol_ratio"] = (
        feat["returns"].rolling(5).std()
        / feat["returns"].rolling(60).std().replace(0, np.nan)
    )

    return feat.dropna()


# ── Rule-based label generation ──────────────────────────────────────────────

def generate_labels(feat: pd.DataFrame) -> pd.Series:
    """
    Assign regime labels using domain-driven heuristics:
      1  Trending      — ADX > 25 AND |ma_slope| high
      2  High Volatility — atr_norm > 80th percentile
      3  Low Volatility  — atr_norm < 20th percentile AND volatility_20 low
      0  Sideways       — everything else
    """
    labels = pd.Series(0, index=feat.index, dtype=int)  # default: Sideways

    atr_80 = feat["atr_norm"].quantile(0.80)
    atr_20 = feat["atr_norm"].quantile(0.20)
    vol_20 = feat["volatility_20"].quantile(0.20)

    trending_mask = (feat["adx"] > 25) & (feat["ma_slope"].abs() > feat["ma_slope"].abs().quantile(0.60))
    high_vol_mask = feat["atr_norm"] > atr_80
    low_vol_mask  = (feat["atr_norm"] < atr_20) & (feat["volatility_20"] < vol_20)

    # Priority order: Trending > High Vol > Low Vol > Sideways
    labels[low_vol_mask]  = 3
    labels[high_vol_mask] = 2
    labels[trending_mask] = 1

    return labels


# ── Model training + prediction ──────────────────────────────────────────────

def _build_model() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=5,
        n_jobs=-1,
        random_state=42,
    )


def detect_market_regime(df: pd.DataFrame) -> dict:
    """
    Full pipeline: engineer features → label → train → predict on last row.

    Args:
        df: OHLCV DataFrame (must have 'close', 'high', 'low'; 'volume' optional).

    Returns:
        {
          "regime":          str,   # "Trending" | "Sideways" | "High Volatility" | "Low Volatility"
          "confidence":      float, # 0‒1 probability from the forest
          "advice":          str,   # contextual strategy hint
          "regime_history":  list,  # last 60 bars regime per-bar for sparkline
        }
    """
    if len(df) < 80:
        return {
            "regime": "Insufficient Data",
            "confidence": 0.0,
            "advice": "At least 80 bars of data are required for regime detection.",
            "regime_history": [],
        }

    feat   = engineer_features(df)
    labels = generate_labels(feat)

    X = feat.values
    y = labels.values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = _build_model()
    model.fit(X_scaled, y)

    # Predict on the most recent bar
    last_X  = X_scaled[[-1]]
    pred_label   = int(model.predict(last_X)[0])
    probabilities = model.predict_proba(last_X)[0]
    confidence   = float(probabilities[pred_label])
    regime_name  = REGIME_LABELS[pred_label]

    # Build per-bar history for sparkline (last 60 bars)
    all_preds = model.predict(X_scaled)
    regime_history = [REGIME_LABELS[int(p)] for p in all_preds[-60:]]

    return {
        "regime":         regime_name,
        "confidence":     round(confidence, 4),
        "advice":         REGIME_ADVICE.get(regime_name, ""),
        "regime_history": regime_history,
    }
