"""
Lightweight Telegram alert helper (returns booleans).
Respects DRY_RUN / TELEGRAM_DRY_RUN. Supports multiple chat IDs (comma-separated)
and @channelusername or numeric IDs.
"""

from __future__ import annotations
import os
from typing import Iterable, Optional, Tuple, Dict, Any

try:
    import requests
except Exception:
    requests = None

TELEGRAM_API_ROOT = "https://api.telegram.org"

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name, str(int(default)))
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")

def _split_ids(raw: str) -> Iterable[str]:
    for part in (raw or "").split(","):
        p = part.strip()
        if p:
            yield p

def _get_cfg() -> Tuple[str, Tuple[str, ...], bool]:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_ids = tuple(_split_ids(os.getenv("TELEGRAM_CHAT_ID", "")))
    dry = _env_bool("TELEGRAM_DRY_RUN", False) or _env_bool("DRY_RUN", False)
    return token, chat_ids, dry

def _require_requests():
    if requests is None:
        raise RuntimeError("The 'requests' package is not installed. Run: pip install requests")

def _post(token: str, method: str, data: Dict[str, Any], files: Dict[str, Any] | None, dry: bool) -> Dict[str, Any]:
    url = f"{TELEGRAM_API_ROOT}/bot{token}/{method}"
    if dry:
        print(f"[DRY_RUN] POST {url} data_keys={list(data.keys())} files_keys={list(files.keys()) if files else []}")
        return {"ok": True, "dry_run": True}
    _require_requests()
    try:
        resp = requests.post(url, data=data, files=files, timeout=30)
        try:
            return resp.json()
        except Exception:
            return {"ok": False, "status_code": resp.status_code, "text": resp.text}
    except Exception as e:
        return {"ok": False, "error": repr(e)}

def send_telegram(
    text: str,
    parse_mode: Optional[str] = "HTML",
    disable_notification: bool = True,
    disable_web_page_preview: bool = True,
) -> bool:
    if not text:
        return False
    token, chat_ids, dry = _get_cfg()
    if not token or not chat_ids:
        print("[WARN] Telegram config missing: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return False
    ok_any = False
    for cid in chat_ids:
        payload = {
            "chat_id": cid,
            "text": text,
            "disable_notification": disable_notification,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        res = _post(token, "sendMessage", payload, files=None, dry=dry)
        ok = bool(res.get("ok"))
        ok_any = ok_any or ok
        if not ok:
            print(f"[ERR] sendMessage failed for chat_id={cid}: {res}")
    return ok_any

def send_document(
    filepath: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = "HTML",
    disable_notification: bool = True,
) -> bool:
    token, chat_ids, dry = _get_cfg()
    if not token or not chat_ids:
        print("[WARN] Telegram config missing: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return False
    if not os.path.isfile(filepath):
        print(f"[WARN] File not found for Telegram document: {filepath}")
        return False
    ok_any = False
    for cid in chat_ids:
        data = {"chat_id": cid, "disable_notification": disable_notification}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if dry:
            files = {"document": os.path.basename(filepath)}
            res = _post(token, "sendDocument", data, files=files, dry=True)
            ok = bool(res.get("ok"))
            ok_any = ok_any or ok
        else:
            with open(filepath, "rb") as fh:
                files = {"document": fh}
                res = _post(token, "sendDocument", data, files=files, dry=False)
                ok = bool(res.get("ok"))
                ok_any = ok_any or ok
        if not ok:
            print(f"[ERR] sendDocument failed for chat_id={cid}: {res}")
    return ok_any

def send_photo(
    filepath: str,
    caption: Optional[str] = None,
    parse_mode: Optional[str] = "HTML",
    disable_notification: bool = True,
) -> bool:
    token, chat_ids, dry = _get_cfg()
    if not token or not chat_ids:
        print("[WARN] Telegram config missing: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        return False
    if not os.path.isfile(filepath):
        print(f"[WARN] File not found for Telegram photo: {filepath}")
        return False
    ok_any = False
    for cid in chat_ids:
        data = {"chat_id": cid, "disable_notification": disable_notification}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if dry:
            files = {"photo": os.path.basename(filepath)}
            res = _post(token, "sendPhoto", data, files=files, dry=True)
            ok = bool(res.get("ok"))
            ok_any = ok_any or ok
        else:
            with open(filepath, "rb") as fh:
                files = {"photo": fh}
                res = _post(token, "sendPhoto", data, files=files, dry=False)
                ok = bool(res.get("ok"))
                ok_any = ok_any or ok
        if not ok:
            print(f"[ERR] sendPhoto failed for chat_id={cid}: {res}")
    return ok_any

if __name__ == "__main__":
    msg = f"Alert test at {time.strftime('%Y-%m-%d %H:%M:%S')}"
    ok = send_telegram(msg)
    print("sent:", ok)
