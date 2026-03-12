"""
AI Trade Scoring System
Evaluates the quality/confidence of each trade signal using an ML model
trained on market features at the time of signal generation.
"""

from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

# ── Risk classification thresholds ──────────────────────────────────────────
RISK_THRESHOLDS = {
    "Low":    0.72,
    "Medium": 0.52,
    # anything below Medium → "High"
}

def _risk_level(score: float) -> str:
    if score >= RISK_THRESHOLDS["Low"]:
        return "Low"
    if score >= RISK_THRESHOLDS["Medium"]:
        return "Medium"
    return "High"

# ── Indicator helpers ────────────────────────────────────────────────────────

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def _macd_line(close: pd.Series) -> pd.Series:
    return _ema(close, 12) - _ema(close, 26)

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift(1)).abs(),
        (df["low"]  - df["close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    atr = _atr(df, period)
    up   = df["high"].diff().clip(lower=0)
    down = (-df["low"].diff()).clip(lower=0)
    plus_dm  = np.where(up > down, up, 0)
    minus_dm = np.where(down > up, down, 0)
    atr_s = atr.replace(0, np.nan)
    plus_di  = 100 * pd.Series(plus_dm,  index=df.index).rolling(period).mean() / atr_s
    minus_di = 100 * pd.Series(minus_dm, index=df.index).rolling(period).mean() / atr_s
    denom = (plus_di + minus_di).replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / denom
    return dx.rolling(period).mean()


# ── Feature engineering ──────────────────────────────────────────────────────

def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a feature matrix aligned to df's index. Rows with NaN are kept
    (filled with 0) to preserve index alignment with the trade timestamps.
    """
    df = df.copy()
    df.columns = df.columns.str.lower()
    for col in ["open","high","low","close"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    feat = pd.DataFrame(index=df.index)
    close = df["close"]

    feat["rsi"]          = _rsi(close, 14)
    feat["macd"]         = _macd_line(close)
    feat["momentum_5"]   = close.pct_change(5)
    feat["momentum_1"]   = close.pct_change(1)
    feat["atr_norm"]     = _atr(df, 14) / close
    feat["adx"]          = _adx(df, 14)
    feat["vol_20"]       = close.pct_change().rolling(20).std()
    feat["dist_ema50"]   = (close - _ema(close, 50)) / close
    feat["dist_ema200"]  = (close - _ema(close, 200)) / close

    if "volume" in df.columns:
        vol = pd.to_numeric(df["volume"], errors="coerce")
        feat["volume_spike"] = vol / vol.rolling(20).mean().replace(0, np.nan)
    else:
        feat["volume_spike"] = 1.0

    feat["vol_ratio"] = (
        close.pct_change().rolling(5).std()
        / close.pct_change().rolling(60).std().replace(0, np.nan)
    )

    return feat.fillna(0)


def _build_labels_from_trades(df: pd.DataFrame, trades: list[dict]) -> tuple[list[int], list[int]]:
    """
    Map each trade to the closest candle bar by entry_time.
    Label = 1 if pnl > 0 (profitable), else 0.
    Returns (bar_indices, labels).
    """
    times  = df["time"].values if "time" in df.columns else np.arange(len(df))
    indices, labels = [], []

    for t in trades:
        entry_t = t.get("entry_time") or t.get("exit_time")
        if entry_t is None:
            continue
        # Find nearest bar
        diffs = np.abs(times - entry_t)
        idx   = int(np.argmin(diffs))
        pnl   = t.get("pnl", 0)
        indices.append(idx)
        labels.append(1 if pnl > 0 else 0)

    return indices, labels


# ── Public scoring API ───────────────────────────────────────────────────────

def score_trades(df: pd.DataFrame, trades: list[dict]) -> list[dict]:
    """
    Score every trade in `trades` using a RandomForest trained on in-sample features.

    Args:
        df:     OHLCV DataFrame.
        trades: List of trade dicts produced by the backtest engine.

    Returns:
        The original trade dicts each augmented with:
          trade_score  (float 0‒1)
          confidence   (float 0‒1, same as trade_score for RF proba)
          risk_level   ("Low" | "Medium" | "High")
    """
    df = df.copy()
    df.columns = df.columns.str.lower()

    if len(trades) < 2:
        # Not enough trades to train — return default scores
        return [
            {**t, "trade_score": 0.5, "confidence": 0.5, "risk_level": "Medium"}
            for t in trades
        ]

    feat_df = extract_features(df)
    X_all   = feat_df.values

    bar_indices, labels = _build_labels_from_trades(df, trades)

    if len(set(labels)) < 2:
        # All winners or all losers — model can't discriminate
        default_score = 0.75 if all(l == 1 for l in labels) else 0.30
        return [
            {**t, "trade_score": default_score, "confidence": default_score,
             "risk_level": _risk_level(default_score)}
            for t in trades
        ]

    X_train = np.array([X_all[i] for i in bar_indices])
    y_train = np.array(labels)

    scaler  = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=3,
        n_jobs=-1,
        random_state=42,
    )
    model.fit(X_train_s, y_train)

    scored = []
    for idx, t in zip(bar_indices, trades):
        x       = scaler.transform(X_all[[idx]])
        proba   = model.predict_proba(x)[0]
        # index of class "1" (profitable)
        classes = list(model.classes_)
        pos_idx = classes.index(1) if 1 in classes else 0
        score   = float(proba[pos_idx])
        
        scored.append({
            **t,
            "trade_score": round(score, 4),
            "confidence":  round(score, 4),
            "risk_level":  _risk_level(score),
        })

    # Sort best-score-first for the "top trades" view
    scored.sort(key=lambda x: x["trade_score"], reverse=True)
    return scored
