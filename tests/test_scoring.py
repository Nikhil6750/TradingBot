# tests/test_scoring.py
from bot.scoring import score_factors

def test_scoring_bounds():
    f = {"trend_ok": True, "momentum_ok": True, "vol_ok": True, "sr_ok": True}
    s = score_factors(f)
    assert 0 <= s["score"] <= 100
    assert s["label"] in ("LOW","MEDIUM","HIGH")

def test_scoring_weight_effects():
    f = {"trend_ok": True, "momentum_ok": False, "vol_ok": False, "sr_ok": False}
    s1 = score_factors(f)
    s2 = score_factors(f, {"trend_ok": 0.6})
    assert s2["score"] >= s1["score"]
