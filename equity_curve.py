# equity_curve.py
# Robust equity-curve generator that never crashes and always tries to produce a PNG.
import os
from pathlib import Path
import pandas as pd

# ensure headless plotting backend
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent
PNG_PATH = PROJECT_ROOT / "equity_curve.png"

# Potential inputs (adjust names if yours differ)
TRADES_DETAILED = PROJECT_ROOT / "backtest_results_trades.csv"  # per-trade rows (preferred)
SUMMARY_PATH    = PROJECT_ROOT / "backtest_results.csv"         # run summary (fallback)

def _load_csv(path: Path) -> pd.DataFrame | None:
    try:
        if path.exists():
            df = pd.read_csv(path)
            if isinstance(df, pd.DataFrame) and not df.empty:
                return df
    except Exception:
        pass
    return None

def _pick_return_series(df: pd.DataFrame) -> pd.Series | None:
    """
    Try to find a per-trade return column in 'df' using common names.
    Returns a float series if found, else None.
    """
    candidates = [
        "r", "R", "pnl_r", "pnlR", "ret_r", "ret", "return_r", "reward_r",
        "rr", "risk_reward", "pnlR_multiple"
    ]
    for c in candidates:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce").dropna()
            if not s.empty:
                return s.astype(float).reset_index(drop=True)

    # Sometimes win/loss encoded as 'outcome' and a fixed RR column exists
    if "outcome" in df.columns:
        # try to build +/- series from outcome + a magnitude column if present
        mag_candidates = ["rr", "R", "r", "pnl_r", "ret", "avg_r"]
        mag = None
        for m in mag_candidates:
            if m in df.columns:
                mag = pd.to_numeric(df[m], errors="coerce")
                break
        if mag is not None:
            sign = df["outcome"].astype(str).str.lower().map(
                lambda x: 1.0 if "win" in x else (-1.0 if "loss" in x else 0.0)
            )
            s = (mag.fillna(0).astype(float) * sign.fillna(0).astype(float)).dropna()
            if not s.empty:
                return s.reset_index(drop=True)

    return None

def _synthetic_from_summary(df_sum: pd.DataFrame) -> pd.Series | None:
    """
    Build a synthetic equity curve when only a 1-row summary exists.
    Uses total trades + net_r to create a flat-per-trade series.
    """
    # Accept likely column names
    cols = {c.lower(): c for c in df_sum.columns}
    trades_col = cols.get("trades")
    netr_col   = cols.get("net_r") or cols.get("netr") or cols.get("net_r_sum")

    if trades_col is None or netr_col is None:
        return None

    try:
        trades = int(pd.to_numeric(df_sum.loc[0, trades_col], errors="coerce"))
        net_r  = float(pd.to_numeric(df_sum.loc[0, netr_col], errors="coerce"))
    except Exception:
        return None

    if trades <= 0:
        return None

    # Distribute net_r equally as a simple, monotonic synthetic path
    per_trade = net_r / trades
    return pd.Series([per_trade] * trades, dtype=float)

def main() -> None:
    # 1) Prefer detailed trades file
    df_trades = _load_csv(TRADES_DETAILED)

    r_series = None
    if df_trades is not None:
        # sort by any obvious time column so the curve is chronological
        for tcol in ["timestamp", "time", "date", "datetime", "open_time", "close_time"]:
            if tcol in df_trades.columns:
                try:
                    df_trades = df_trades.sort_values(tcol)
                    break
                except Exception:
                    pass

        r_series = _pick_return_series(df_trades)

    # 2) Fallback to summary file
    if r_series is None:
        df_sum = _load_csv(SUMMARY_PATH)
        if df_sum is not None and not df_sum.empty:
            r_series = _synthetic_from_summary(df_sum)

    # 3) If still nothing, produce a blank informative image and return
    if r_series is None or r_series.empty:
        fig, ax = plt.subplots(figsize=(8, 3.5), dpi=150)
        ax.text(
            0.5, 0.5,
            "No per-trade returns found.\n"
            "Provide 'backtest_results_trades.csv' with a column like 'r' or 'pnl_r'.",
            ha="center", va="center", fontsize=10, transform=ax.transAxes
        )
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(PNG_PATH)
        plt.close(fig)
        return

    # 4) Build cumulative R equity and plot
    eq = r_series.cumsum()

    fig, ax = plt.subplots(figsize=(10, 4), dpi=150)
    ax.plot(eq.index.values, eq.values)
    ax.set_title("Equity Curve (cumulative R)")
    ax.set_xlabel("Trade #")
    ax.set_ylabel("Cumulative R")
    ax.grid(True, alpha=0.25)

    # optional: mark zero line
    ax.axhline(0.0, linewidth=1, linestyle="--", alpha=0.5)

    fig.tight_layout()
    fig.savefig(PNG_PATH)
    plt.close(fig)

if __name__ == "__main__":
    main()
