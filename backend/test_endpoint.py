#!/usr/bin/env python3
"""Test the /convert_pine endpoint directly"""

import requests
import json

# The Pine Script from the user's screenshot
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
print("TESTING /convert_pine ENDPOINT")
print("=" * 80)

url = "http://localhost:8000/convert_pine"
payload = {"code": pine_script}

try:
    response = requests.post(url, json=payload)
    result = response.json()
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response OK: {result.get('ok', False)}")
    
    if result.get('ok'):
        print("\n✅ CONVERSION SUCCESSFUL!")
        print("\nGenerated Python Code:")
        print("-" * 80)
        print(result.get('python_code', ''))
        print("-" * 80)
    else:
        print(f"\n❌ CONVERSION FAILED!")
        print(f"Error: {result.get('error', 'Unknown error')}")
        
except Exception as e:
    print(f"\n❌ REQUEST FAILED: {e}")
