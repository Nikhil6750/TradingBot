from typing import Dict, Any, List, Callable
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .policy import SYSTEM_POLICY
from .llm_provider import mock_llm
from . import tools as tools_router

router = APIRouter(prefix="/chat", tags=["agent"])

# Map tool names to the HTTP handlers we exposed in tools.py
TOOLS = {
    "run_backtest": tools_router.tool_run_backtest,
    "get_prices": tools_router.tool_get_prices,
    "place_order": tools_router.tool_place_order,
    "fetch_calendar": tools_router.tool_fetch_calendar,
}

def run_agent(user_msg: str,
              llm_fn: Callable[[List[Dict[str,str]]], Dict[str,Any]],
              max_steps: int = 6) -> Dict[str, Any]:
    steps: List[Dict[str,Any]] = []
    messages = [{"role":"system","content":SYSTEM_POLICY},
                {"role":"user","content": user_msg}]

    for _ in range(max_steps):
        reply = llm_fn(messages)
        if not isinstance(reply, dict) or "type" not in reply:
            return {"final":"Model returned invalid structure.", "steps":steps}

        if reply["type"] == "final":
            return {"final": reply.get("content",""), "steps": steps}

        if reply["type"] == "tool_call":
            tool = reply.get("tool"); args = reply.get("args", {})
            if tool not in TOOLS:
                return {"final": f"Unknown tool `{tool}`.", "steps": steps}
            try:
                result = TOOLS[tool](args)  # FastAPI will coerce dict→model
            except TypeError:
                # If handler expects a Pydantic model instance, rebuild it:
                from .tools import RunBacktestArgs, GetPricesArgs, PlaceOrderArgs, FetchCalendarArgs
                model = {"run_backtest":RunBacktestArgs,"get_prices":GetPricesArgs,
                         "place_order":PlaceOrderArgs,"fetch_calendar":FetchCalendarArgs}[tool](**args)
                result = TOOLS[tool](model)
            steps.append({"tool": tool, "args": args, "result": result})
            # Feed a compact observation back:
            messages.append({"role":"assistant","content":f"[{tool} OK]"})
            messages.append({"role":"user","content": f"{tool}→ {str(result)[:800]}"})
            continue

        return {"final":"Unrecognized LLM reply type.", "steps": steps}

    return {"final":"Action budget reached. Ask me for a focused backtest (symbol, timeframe, dates).", "steps": steps}

class ChatIn(BaseModel):
    message: str

@router.post("/agent")
def chat_agent(payload: ChatIn):
    msg = (payload.message or "").strip()
    if not msg:
        raise HTTPException(400, "Empty message")
    return run_agent(msg, llm_fn=mock_llm, max_steps=6)
