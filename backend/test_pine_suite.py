#!/usr/bin/env python3
"""Comprehensive Pine Script Converter Test Suite"""

import sys
sys.path.insert(0, '/Users/prashanthkumar/Projects/TradingBot/backend')

from pine_converter import PineConverter

test_cases = [
    {
        "name": "Alert in If Block",
        "pine": """
if alertTriggered
    alert(json.payload,
    alert.freq_once_per_bar_close)
""",
    },
    {
        "name": "Simple Moving Average",
        "pine": """
sma20 = ta.sma(close, 20)
if close > sma20
    strategy.entry("Long", strategy.long, when=close > sma20)
""",
    },
    {
        "name": "RSI Strategy",
        "pine": """
rsi = ta.rsi(close, 14)
if rsi < 30
    strategy.entry("Long", strategy.long, when=rsi < 30)
if rsi > 70
    strategy.entry("Short", strategy.short, when=rsi > 70)
""",
    },
    {
        "name": "Complex Expression",
        "pine": """
var streak = 0
if close > open
    streak = streak + 1
""",
    },
]

converter = PineConverter()

print("=" * 80)
print("PINE SCRIPT CONVERTER TEST SUITE")
print("=" * 80)

passed = 0
failed = 0

for test in test_cases:
    print(f"\n📝 Test: {test['name']}")
    print("-" * 80)
    
    try:
        python_code = converter.convert(test['pine'])
        
        # Try to compile
        try:
            compile(python_code, "<string>", "exec")
            print("✅ PASSED - Valid Python syntax")
            passed += 1
        except SyntaxError as e:
            print(f"❌ FAILED - Syntax Error: {e.msg} at line {e.lineno}")
            print("\nGenerated code:")
            for i, line in enumerate(python_code.split('\n'), 1):
                marker = ">>> " if i == e.lineno else "    "
                print(f"{marker}{i:3d}: {line}")
            failed += 1
            
    except Exception as e:
        print(f"❌ FAILED - Conversion Error: {e}")
        failed += 1

print("\n" + "=" * 80)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 80)

if failed == 0:
    print("🎉 ALL TESTS PASSED!")
    sys.exit(0)
else:
    print("⚠️  SOME TESTS FAILED")
    sys.exit(1)
