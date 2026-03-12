from __future__ import annotations

import re
from typing import Final, Optional
from pathlib import Path
import numpy as np

_INVALID_FILENAME_MSG: Final[str] = "Invalid CSV filename format"
_PAIR_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9]+$")

def clean_data(obj):
    if isinstance(obj, np.integer): return int(obj)
    elif isinstance(obj, np.floating): return float(obj)
    elif isinstance(obj, np.ndarray): return obj.tolist()
    elif isinstance(obj, list): return [clean_data(i) for i in obj]
    elif isinstance(obj, dict): return {k: clean_data(v) for k, v in obj.items()}
    return obj

def _infer_market_pair_from_filename(filename: Optional[str]) -> tuple[str, str]:
    name = Path(str(filename or "")).name
    if not name:
        raise ValueError(_INVALID_FILENAME_MSG)

    if Path(name).suffix.lower() != ".csv":
        raise ValueError(_INVALID_FILENAME_MSG)

    stem = name[: -len(".csv")]

    if stem.startswith("FX_"):
        market = "forex"
        rest = stem[len("FX_") :]
    elif stem.startswith("BINANCE_"):
        market = "crypto"
        rest = stem[len("BINANCE_") :]
    else:
        raise ValueError(_INVALID_FILENAME_MSG)

    pair = rest.split("_", 1)[0]
    if not pair:
        raise ValueError(_INVALID_FILENAME_MSG)
    if not _PAIR_RE.match(pair):
        raise ValueError(_INVALID_FILENAME_MSG)
    return market, pair
