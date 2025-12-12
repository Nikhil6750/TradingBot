
import sys
import os

# Add project root to sys.path
sys.path.insert(0, "/Users/prashanthkumar/Projects/TradingBot/backend")

from pine_converter import PineConverter

pine_code = """
color=color.orange, size=size.small, text="ALERT")

json_payload = '{"ticker":"' + syminfo.ticker + '","time":"' + str.tostring(time, "yyyy-MM-dd HH:mm") + '","ohlc":[' +
    '{"O":' + str.tostring(open[4]) + ',"H":' + str.tostring(high[4]) + ',"L":' +
    str.tostring(low[4]) + ',"C":' + str.tostring(close[4]) + '},' +
    '{"O":' + str.tostring(open[3]) + ',"H":' + str.tostring(high[3]) + ',"L":' +
    str.tostring(low[3]) + ',"C":' + str.tostring(close[3]) + '}' +
    ']}'

// Trigger alert only when pattern is matched
if alertTriggered
    alert(json_payload, alert.freq_once_per_bar_close)
"""

print("--- Original Pine Code ---")
print(pine_code)

converter = PineConverter()
try:
    print("\n--- Converting ---")
    py_code = converter.convert(pine_code)
    print("\n--- Generated Python Code (Snippet) ---")
    print(py_code)
    
    print("\n--- Compiling ---")
    compile(py_code, "<string>", "exec")
    print("SUCCESS: Compilation passed!")
except Exception as e:
    print(f"FAILURE: {e}")
