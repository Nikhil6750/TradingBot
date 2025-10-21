from typing import List, Dict, Any

def mock_llm(messages: List[Dict[str,str]]) -> Dict[str, Any]:
    user = next((m["content"] for m in reversed(messages) if m["role"]=="user"), "")
    if "backtest" in user.lower():
        return {"type":"tool_call","tool":"run_backtest",
                "args":{"symbol":"EURJPY","timeframe":"15m","start":"2024-01-01","end":"2024-12-31","strategy":"streak_pullback_v1","params":{}}}
    return {"type":"final","content":"- Ready to run a backtest.\n- Say: backtest EURJPY 2024 15m."}