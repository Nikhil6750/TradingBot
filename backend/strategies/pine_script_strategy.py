from __future__ import annotations

import ast
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend.backtesting.metrics import compute_metrics


_COMMENT_RE = re.compile(r"//.*$")
_ASSIGNMENT_RE = re.compile(r"^(?:var\s+)?([A-Za-z_]\w*)\s*(?::=|=)\s*(.+)$")
_TYPED_ASSIGNMENT_RE = re.compile(r"^(?:var\s+)?(?:float|int|bool|string)\s+([A-Za-z_]\w*)\s*(?::=|=)\s*(.+)$")
_ENTRY_RE = re.compile(
    r"""strategy\.entry\(\s*["'](?P<entry_id>[^"']+)["']\s*,\s*strategy\.(?P<side>long|short)(?P<rest>.*)\)\s*$""",
    re.IGNORECASE,
)
_CLOSE_RE = re.compile(
    r"""strategy\.close\(\s*["'](?P<entry_id>[^"']+)["'](?P<rest>.*)\)\s*$""",
    re.IGNORECASE,
)
_WHEN_RE = re.compile(r"when\s*=\s*(.+?)(?:,\s*\w+\s*=.*)?$", re.IGNORECASE)


def _get_series_index(env: Dict[str, Any]) -> pd.Index:
    for value in env.values():
        if isinstance(value, pd.Series):
            return value.index
    raise ValueError("Dataset is empty.")


def _to_series(value: Any, index: pd.Index) -> pd.Series:
    if isinstance(value, pd.Series):
        return value.reindex(index)
    return pd.Series([value] * len(index), index=index)


def _to_bool_series(value: Any, index: pd.Index) -> pd.Series:
    if isinstance(value, pd.Series):
        return value.fillna(False).astype(bool)
    return pd.Series([bool(value)] * len(index), index=index)


def _to_length(value: Any) -> int:
    length = int(float(value))
    if length <= 0:
        raise ValueError("Indicator periods must be positive.")
    return length


def _compute_rsi(series: pd.Series, length: int) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=length).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _get_call_name(node: ast.AST) -> str:
    parts: List[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
        return ".".join(reversed(parts))
    raise ValueError("Unsupported Pine Script function call.")


def _eval_call(node: ast.Call, env: Dict[str, Any], index: pd.Index) -> Any:
    call_name = _get_call_name(node.func)
    args = [_eval_node(arg, env, index) for arg in node.args]

    if call_name in {"input.int", "input.float"}:
        return args[0] if args else 0
    if call_name == "nz":
        value = args[0] if args else 0
        replacement = args[1] if len(args) > 1 else 0
        if isinstance(value, pd.Series):
            return value.fillna(replacement)
        return replacement if pd.isna(value) else value
    if call_name == "math.abs":
        return abs(args[0]) if args else 0
    if call_name == "ta.sma":
        series = _to_series(args[0], index)
        return series.rolling(window=_to_length(args[1])).mean()
    if call_name == "ta.ema":
        series = _to_series(args[0], index)
        return series.ewm(span=_to_length(args[1]), adjust=False).mean()
    if call_name == "ta.rsi":
        series = _to_series(args[0], index)
        return _compute_rsi(series, _to_length(args[1]))
    if call_name == "ta.crossover":
        left = _to_series(args[0], index)
        right = _to_series(args[1], index)
        return (left.shift(1) <= right.shift(1)) & (left > right)
    if call_name == "ta.crossunder":
        left = _to_series(args[0], index)
        right = _to_series(args[1], index)
        return (left.shift(1) >= right.shift(1)) & (left < right)

    raise ValueError(f"Unsupported Pine Script function: {call_name}")


def _apply_binop(left: Any, right: Any, operator: ast.operator, index: pd.Index) -> Any:
    left_value = _to_series(left, index) if isinstance(left, pd.Series) or isinstance(right, pd.Series) else left
    right_value = _to_series(right, index) if isinstance(left, pd.Series) or isinstance(right, pd.Series) else right

    if isinstance(operator, ast.Add):
        return left_value + right_value
    if isinstance(operator, ast.Sub):
        return left_value - right_value
    if isinstance(operator, ast.Mult):
        return left_value * right_value
    if isinstance(operator, ast.Div):
        return left_value / right_value
    if isinstance(operator, ast.Pow):
        return left_value ** right_value
    if isinstance(operator, ast.Mod):
        return left_value % right_value

    raise ValueError("Unsupported Pine Script arithmetic operator.")


def _apply_compare(left: Any, right: Any, operator: ast.cmpop, index: pd.Index) -> pd.Series:
    left_value = _to_series(left, index) if isinstance(left, pd.Series) or isinstance(right, pd.Series) else left
    right_value = _to_series(right, index) if isinstance(left, pd.Series) or isinstance(right, pd.Series) else right

    if isinstance(operator, ast.Gt):
        result = left_value > right_value
    elif isinstance(operator, ast.GtE):
        result = left_value >= right_value
    elif isinstance(operator, ast.Lt):
        result = left_value < right_value
    elif isinstance(operator, ast.LtE):
        result = left_value <= right_value
    elif isinstance(operator, ast.Eq):
        result = left_value == right_value
    elif isinstance(operator, ast.NotEq):
        result = left_value != right_value
    else:
        raise ValueError("Unsupported Pine Script comparison operator.")

    return _to_bool_series(result, index)


def _eval_node(node: ast.AST, env: Dict[str, Any], index: pd.Index) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env, index)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id == "na":
            return np.nan
        if node.id == "true":
            return True
        if node.id == "false":
            return False
        if node.id in env:
            return env[node.id]
        raise ValueError(f"Unknown Pine Script identifier: {node.id}")
    if isinstance(node, ast.UnaryOp):
        value = _eval_node(node.operand, env, index)
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return value
        if isinstance(node.op, ast.Not):
            return ~_to_bool_series(value, index)
        raise ValueError("Unsupported Pine Script unary operator.")
    if isinstance(node, ast.BoolOp):
        values = [_to_bool_series(_eval_node(value, env, index), index) for value in node.values]
        result = values[0]
        for next_value in values[1:]:
            if isinstance(node.op, ast.And):
                result = result & next_value
            elif isinstance(node.op, ast.Or):
                result = result | next_value
            else:
                raise ValueError("Unsupported Pine Script boolean operator.")
        return result
    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, env, index)
        right = _eval_node(node.right, env, index)
        return _apply_binop(left, right, node.op, index)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, env, index)
        result: Optional[pd.Series] = None
        for operator, comparator in zip(node.ops, node.comparators):
            right = _eval_node(comparator, env, index)
            comparison = _apply_compare(left, right, operator, index)
            result = comparison if result is None else result & comparison
            left = right
        return result if result is not None else pd.Series(False, index=index)
    if isinstance(node, ast.Call):
        return _eval_call(node, env, index)
    if isinstance(node, ast.Subscript):
        value = _eval_node(node.value, env, index)
        if not isinstance(value, pd.Series):
            raise ValueError("Historical indexing requires a time series.")
        if isinstance(node.slice, ast.Constant):
            offset = int(node.slice.value)
        elif isinstance(node.slice, ast.Index) and isinstance(node.slice.value, ast.Constant):  # pragma: no cover - py38 compat
            offset = int(node.slice.value.value)
        else:
            raise ValueError("Unsupported Pine Script historical index.")
        return value.shift(offset)

    raise ValueError("Unsupported Pine Script expression.")


def _eval_expression(expression: str, env: Dict[str, Any], index: pd.Index) -> Any:
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid Pine Script expression: {expression}") from exc
    return _eval_node(parsed.body, env, index)


def _normalize_condition(condition: Optional[str], when_expression: Optional[str]) -> str:
    if condition and when_expression:
        return f"({condition}) and ({when_expression})"
    if when_expression:
        return when_expression
    return condition or "true"


def _extract_when_expression(rest: str) -> Optional[str]:
    if not rest:
        return None
    match = _WHEN_RE.search(rest)
    return match.group(1).strip() if match else None


def _clean_line(raw_line: str) -> str:
    line = _COMMENT_RE.sub("", raw_line.rstrip("\n")).rstrip()
    return line.expandtabs(4)


def _is_ignorable_line(stripped: str) -> bool:
    if not stripped:
        return True
    prefixes = (
        "//@",
        "strategy(",
        "indicator(",
        "plot(",
        "plotshape(",
        "plotchar(",
        "bgcolor(",
        "barcolor(",
        "alertcondition(",
    )
    return stripped.startswith(prefixes)


def _parse_action(line: str, inherited_condition: Optional[str]) -> Optional[Dict[str, Any]]:
    entry_match = _ENTRY_RE.match(line)
    if entry_match:
        side = entry_match.group("side").lower()
        return {
            "kind": "entry",
            "entry_id": entry_match.group("entry_id"),
            "direction": "BUY" if side == "long" else "SELL",
            "condition": _normalize_condition(inherited_condition, _extract_when_expression(entry_match.group("rest"))),
        }

    close_match = _CLOSE_RE.match(line)
    if close_match:
        return {
            "kind": "close",
            "entry_id": close_match.group("entry_id"),
            "condition": _normalize_condition(inherited_condition, _extract_when_expression(close_match.group("rest"))),
        }

    return None


def _parse_script(script: str) -> Tuple[List[Tuple[str, str]], List[Dict[str, Any]]]:
    lines = [_clean_line(line) for line in str(script or "").splitlines()]
    assignments: List[Tuple[str, str]] = []
    actions: List[Dict[str, Any]] = []
    entry_directions: Dict[str, str] = {}

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if _is_ignorable_line(stripped):
            index += 1
            continue

        current_indent = len(line) - len(line.lstrip(" "))

        if stripped.startswith("if "):
            condition = stripped[3:].strip()
            index += 1
            while index < len(lines):
                nested_line = lines[index]
                nested_stripped = nested_line.strip()
                nested_indent = len(nested_line) - len(nested_line.lstrip(" "))
                if not nested_stripped:
                    index += 1
                    continue
                if nested_indent <= current_indent:
                    break

                action = _parse_action(nested_stripped, condition)
                if action:
                    actions.append(action)
                    if action["kind"] == "entry":
                        entry_directions[action["entry_id"]] = action["direction"]
                index += 1
            continue

        action = _parse_action(stripped, None)
        if action:
            actions.append(action)
            if action["kind"] == "entry":
                entry_directions[action["entry_id"]] = action["direction"]
            index += 1
            continue

        typed_assignment = _TYPED_ASSIGNMENT_RE.match(stripped)
        assignment = typed_assignment or _ASSIGNMENT_RE.match(stripped)
        if assignment:
            assignments.append((assignment.group(1), assignment.group(2).strip()))
            index += 1
            continue

        index += 1

    for action in actions:
        if action["kind"] != "close":
            continue
        entry_direction = entry_directions.get(action["entry_id"])
        if entry_direction == "BUY":
            action["direction"] = "SELL"
        elif entry_direction == "SELL":
            action["direction"] = "BUY"
        else:
            action["direction"] = "BUY" if "short" in action["entry_id"].lower() else "SELL"

    if not actions:
        raise ValueError("Pine Script did not define any strategy.entry() or strategy.close() actions.")

    return assignments, actions


def _build_indicators(env: Dict[str, Any], working: pd.DataFrame) -> Dict[str, List[Dict[str, float]]]:
    indicators: Dict[str, List[Dict[str, float]]] = {}
    base_names = {"time", "open", "high", "low", "close", "volume"}

    for name, value in env.items():
        if name in base_names or not isinstance(value, pd.Series):
            continue
        if pd.api.types.is_bool_dtype(value):
            continue

        points = [
            {
                "time": int(working.iloc[idx]["time"]),
                "value": float(series_value),
            }
            for idx, series_value in enumerate(value)
            if pd.notna(series_value)
        ]
        if points:
            indicators[name] = points

    return indicators


def run_pine_script_strategy(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
    pine_script = str(config.get("pine_script") or config.get("code_string") or "").strip()
    if not pine_script:
        return {
            "buy_signals": [],
            "sell_signals": [],
            "trades": [],
            "metrics": compute_metrics([]),
            "indicators": {},
        }

    working = df.copy()
    if "time" not in working.columns and "timestamp" in working.columns:
        working["time"] = working["timestamp"]

    for column in ("open", "high", "low", "close", "volume", "time"):
        if column not in working.columns:
            if column == "volume":
                working[column] = 0.0
            else:
                raise ValueError(f"Dataset is missing required column: {column}")

    working = working.reset_index(drop=True)
    env: Dict[str, Any] = {
        "open": working["open"].astype(float),
        "high": working["high"].astype(float),
        "low": working["low"].astype(float),
        "close": working["close"].astype(float),
        "volume": working["volume"].astype(float),
        "time": working["time"].astype(int),
    }
    index = _get_series_index(env)

    assignments, actions = _parse_script(pine_script)
    for name, expression in assignments:
        env[name] = _eval_expression(expression, env, index)

    buy_entries = pd.Series(False, index=index)
    sell_entries = pd.Series(False, index=index)
    buy_exits = pd.Series(False, index=index)
    sell_exits = pd.Series(False, index=index)

    for action in actions:
        condition = _to_bool_series(_eval_expression(action["condition"], env, index), index)
        if action["kind"] == "entry" and action["direction"] == "BUY":
            buy_entries = buy_entries | condition
        elif action["kind"] == "entry" and action["direction"] == "SELL":
            sell_entries = sell_entries | condition
        elif action["kind"] == "close" and action["direction"] == "BUY":
            buy_exits = buy_exits | condition
        elif action["kind"] == "close" and action["direction"] == "SELL":
            sell_exits = sell_exits | condition

    buy_signals: List[Dict[str, Any]] = []
    sell_signals: List[Dict[str, Any]] = []
    trades: List[Dict[str, Any]] = []

    position: Optional[str] = None
    entry_price: Optional[float] = None
    entry_time: Optional[int] = None

    for row_index in range(1, len(working)):
        row = working.iloc[row_index]
        price = float(row["close"])
        timestamp = int(row["time"])

        open_long = bool(buy_entries.iloc[row_index])
        open_short = bool(sell_entries.iloc[row_index])
        close_long = bool(sell_exits.iloc[row_index])
        close_short = bool(buy_exits.iloc[row_index])

        if position == "BUY":
            if close_long or open_short:
                pnl = (price - float(entry_price)) / float(entry_price)
                trades.append({
                    "entry_time": int(entry_time),
                    "exit_time": timestamp,
                    "entry_price": float(entry_price),
                    "exit_price": price,
                    "type": "BUY",
                    "pnl": float(pnl),
                })
                sell_signals.append({"time": timestamp, "price": price, "type": "SELL"})
                position = None
                entry_price = None
                entry_time = None

                if open_short and not open_long:
                    position = "SELL"
                    entry_price = price
                    entry_time = timestamp
            elif open_long:
                continue

        elif position == "SELL":
            if close_short or open_long:
                pnl = (float(entry_price) - price) / float(entry_price)
                trades.append({
                    "entry_time": int(entry_time),
                    "exit_time": timestamp,
                    "entry_price": float(entry_price),
                    "exit_price": price,
                    "type": "SELL",
                    "pnl": float(pnl),
                })
                buy_signals.append({"time": timestamp, "price": price, "type": "BUY"})
                position = None
                entry_price = None
                entry_time = None

                if open_long and not open_short:
                    position = "BUY"
                    entry_price = price
                    entry_time = timestamp
            elif open_short:
                continue

        else:
            if open_long and not open_short:
                buy_signals.append({"time": timestamp, "price": price, "type": "BUY"})
                position = "BUY"
                entry_price = price
                entry_time = timestamp
            elif open_short and not open_long:
                sell_signals.append({"time": timestamp, "price": price, "type": "SELL"})
                position = "SELL"
                entry_price = price
                entry_time = timestamp

    return {
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "trades": trades,
        "metrics": compute_metrics(trades),
        "indicators": _build_indicators(env, working),
    }
