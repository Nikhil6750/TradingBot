#!/usr/bin/env python3
"""Test Pine Script Converter"""

import sys
sys.path.insert(0, '/Users/prashanthkumar/Projects/TradingBot/backend')

from pine_converter import PineConverter

# The Pine Script from the screenshot
pine_script = """
str.tostring(open[1]) + "," + "O" +
str.tostring(high[1]) + "," + "H" +
str.tostring(low[1]) + "," + "C" +
str.tostring(close[1]) + "," + "L" +
"{O}" +
str.tostring(open) + "," + "H" +
str.tostring(high) + "," + "L" +
str.tostring(low) + "," + "C" +
str.tostring(close) + "}" +
"]"

// Trigger alert only when pattern is matched
if alertTriggered
    alert(json.payload,
    alert.freq_once_per_bar_close)
"""

print("=" * 80)
print("TESTING PINE SCRIPT CONVERSION")
print("=" * 80)

converter = PineConverter()
try:
    python_code = converter.convert(pine_script)
    print("\n✅ CONVERSION SUCCESSFUL!\n")
    print("Generated Python Code:")
    print("-" * 80)
    print(python_code)
    print("-" * 80)
    
    # Try to compile it
    print("\n🔍 VALIDATING PYTHON SYNTAX...")
    try:
        compile(python_code, "<string>", "exec")
        print("✅ Python syntax is VALID!")
    except SyntaxError as e:
        print(f"❌ SYNTAX ERROR: {e.msg} at line {e.lineno}")
        print(f"\nProblematic line:")
        lines = python_code.split('\n')
        if e.lineno and e.lineno <= len(lines):
            start = max(0, e.lineno - 3)
            end = min(len(lines), e.lineno + 2)
            for i in range(start, end):
                marker = ">>> " if i == e.lineno - 1 else "    "
                print(f"{marker}{i+1:3d}: {lines[i]}")
        
except Exception as e:
    print(f"❌ CONVERSION FAILED: {e}")
    import traceback
    traceback.print_exc()
