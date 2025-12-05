import os
import pandas as pd 

def _project_data_dir():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _resolve_csv_path(path_or_name) -> str:
    return str(path_or_name) if os.path.isabs(path_or_name) else os.path.join(_project_data_dir(), str(path_or_name))

def load_ohlcv(path_or_name, limit=None) -> pd.DataFrame:
    csv_path = _resolve_csv_path(path_or_name)
    df = pd.read_csv(csv_path)

    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            raise ValueError(f"Missing column: {col}")

    for col in ("time", "timestamp", "date", "datetime"):
        if col in df.columns:
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
                df = df.set_index(col, drop=True).sort_index()
                break
            except Exception:
                pass

    if limit is not None:
        df = df.tail(int(limit))
    return df
