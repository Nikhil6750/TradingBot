"""
AI Strategy Explainer
Converts trading rules into clear natural language explanations.
Works entirely locally — no external API required.
"""

from __future__ import annotations
from typing import Any

# ---------------------------------------------------------------------------
# Indicator → clause templates
# Each key is (indicator_normalized, operator, value_bucket)
# value_bucket: "low" / "high" / "indicator" / "any"
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    return str(s).strip().upper()

def _value_bucket(value: Any) -> str:
    """Categorise the vale side of a rule."""
    try:
        v = float(value)
        return "low" if v < 50 else "high"
    except (TypeError, ValueError):
        # value is a reference to another indicator
        return _normalize(str(value))

# ---------------------------------------------------------------------------
# Per-indicator clause factories
# ---------------------------------------------------------------------------

def _explain_rsi(operator: str, value: Any) -> str:
    v = _value_bucket(value)
    if operator in ("<", "<="):
        if v == "low":  # RSI < 30-ish
            return "the market is deeply oversold and primed for a potential rebound"
        return "the RSI is below the threshold, suggesting weakening selling pressure"
    elif operator in (">", ">="):
        if v == "high":  # RSI > 70-ish
            return "the market is overbought and a pullback may be imminent"
        return "the RSI is elevated, confirming upward momentum"
    return "the RSI satisfies the defined condition"


def _explain_sma(operator: str, value: Any, period: str = "") -> str:
    label = f"the {period}-period Simple Moving Average" if period else "the Simple Moving Average"
    if operator in (">", ">="):
        return f"price has crossed above {label}, a classical bullish signal"
    return f"price has broken below {label}, a classical bearish signal"


def _explain_ema(operator: str, value: Any, period: str = "") -> str:
    label_map = {"200": "the long-term trend (EMA 200)", "50": "the medium-term trend (EMA 50)", "20": "the short-term EMA"}
    label = label_map.get(period, f"the {period}-period EMA" if period else "the EMA")
    if operator in (">", ">="):
        return f"price trades above {label}, signalling bullish momentum"
    return f"price trades below {label}, signalling bearish momentum"


def _explain_price(operator: str, value: Any) -> str:
    v = _normalize(str(value))
    # value is another indicator reference
    if v.startswith("EMA"):
        period = v.replace("EMA", "").strip()
        return _explain_ema(operator, value, period)
    if v.startswith("SMA"):
        period = v.replace("SMA", "").strip()
        return _explain_sma(operator, value, period)
    if v.startswith("BB_UPPER"):
        return "price breaks above the upper Bollinger Band, indicating a breakout" if operator in (">", ">=") else "price is below the upper Bollinger Band"
    if v.startswith("BB_LOWER"):
        return "price bounces off the lower Bollinger Band, a mean-reversion entry" if operator in ("<", "<=") else "price is above the lower Bollinger Band"
    try:
        float(value)
        if operator in (">", ">="):
            return f"price pushes above {value}, breaking a key level"
        return f"price falls below {value}, a potential support violation"
    except (TypeError, ValueError):
        return f"price satisfies the condition relative to {value}"


def _explain_macd(operator: str, value: Any) -> str:
    v = _normalize(str(value))
    if v == "SIGNAL" or v == "MACD_SIGNAL":
        if operator in (">", ">="):
            return "the MACD line crosses above the signal line, generating a bullish crossover"
        return "the MACD line falls below the signal line, generating a bearish crossover"
    try:
        float(value)
        if operator in (">", ">="):
            return "the MACD is positive, indicating upward price momentum"
        return "the MACD is negative, indicating downward price momentum"
    except (TypeError, ValueError):
        return "the MACD satisfies the specified condition"


def _explain_bb(operator: str, value: Any) -> str:
    v = _normalize(str(value))
    if "UPPER" in v:
        return "price breaks above the upper Bollinger Band, signalling a potential breakout" if operator in (">", ">=") else "price remains below the upper band"
    if "LOWER" in v:
        return "price touches the lower Bollinger Band, indicating an oversold bounce zone" if operator in ("<", "<=") else "price is above the lower band"
    return "the Bollinger Band condition is met"


def _explain_volume(operator: str, value: Any) -> str:
    if operator in (">", ">="):
        return "trading volume is above average, confirming conviction behind the move"
    return "volume is low, suggesting a lack of participation in the current move"


# ---------------------------------------------------------------------------
# Main clause dispatcher
# ---------------------------------------------------------------------------

_INDICATOR_HANDLERS = {
    "RSI": _explain_rsi,
    "MACD": _explain_macd,
    "VOLUME": _explain_volume,
}

def _indicator_clause(indicator: str, operator: str, value: Any) -> str:
    ind = _normalize(indicator)

    if ind == "RSI":
        return _explain_rsi(operator, value)
    if ind.startswith("EMA"):
        period = ind.replace("EMA", "").strip()
        return _explain_ema(operator, value, period)
    if ind.startswith("SMA"):
        period = ind.replace("SMA", "").strip()
        return _explain_sma(operator, value, period)
    if ind in ("PRICE", "CLOSE"):
        return _explain_price(operator, value)
    if ind == "MACD":
        return _explain_macd(operator, value)
    if ind.startswith("BB") or ind.startswith("BOLLINGER"):
        return _explain_bb(operator, value)
    if ind == "VOLUME":
        return _explain_volume(operator, value)
    # Generic fallback
    if operator in (">", ">="):
        return f"{indicator} is above {value}"
    if operator in ("<", "<="):
        return f"{indicator} is below {value}"
    return f"{indicator} {operator} {value}"


# ---------------------------------------------------------------------------
# Strategy fingerprinting → risk analysis
# ---------------------------------------------------------------------------

_MEAN_REVERSION_INDICATORS = {"RSI", "BB", "BOLLINGER"}
_TREND_INDICATORS = {"EMA", "SMA", "MACD"}

def _risk_note(rules: list[dict]) -> str:
    indicators = {_normalize(r.get("indicator", "")).split()[0][:3] for r in rules}
    rev_score = sum(1 for i in indicators if any(i.startswith(k) for k in _MEAN_REVERSION_INDICATORS))
    trend_score = sum(1 for i in indicators if any(i.startswith(k) for k in _TREND_INDICATORS))

    if rev_score > trend_score:
        return (
            "This appears to be a mean-reversion strategy. "
            "It may underperform during strong trending markets where price momentum sustains for extended periods."
        )
    if trend_score > rev_score:
        return (
            "This appears to be a trend-following strategy. "
            "It may generate false signals during sideways or choppy market conditions."
        )
    # mixed
    return (
        "This strategy combines both trend-following and mean-reversion elements. "
        "This diversification can reduce false signals but may limit returns in strongly trending markets."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_explanation(rules: list[dict], side: str = "buy") -> dict[str, str]:
    """
    Generate a natural-language explanation for a list of trading rules.

    Args:
        rules:  List of {"indicator": str, "operator": str, "value": Any}
        side:   "buy" (default) or "sell"

    Returns:
        {"explanation": str, "risk_note": str}
    """
    if not rules:
        return {
            "explanation": "No rules have been defined yet. Add indicator conditions to describe your strategy.",
            "risk_note": "Please add at least one rule to receive a risk assessment.",
        }

    clauses = []
    for r in rules:
        indicator = r.get("indicator", "")
        operator  = r.get("operator", ">")
        value     = r.get("value", 0)
        clause = _indicator_clause(indicator, operator, value)
        if clause:
            clauses.append(clause)

    action = "buys" if side == "buy" else "sells"

    if len(clauses) == 1:
        explanation = f"This strategy {action} when {clauses[0]}."
    elif len(clauses) == 2:
        explanation = f"This strategy {action} when {clauses[0]}, while simultaneously {clauses[1]}."
    else:
        joined = "; ".join(clauses[:-1])
        explanation = f"This strategy {action} when {joined}; and finally {clauses[-1]}."

    return {
        "explanation": explanation,
        "risk_note": _risk_note(rules),
    }
