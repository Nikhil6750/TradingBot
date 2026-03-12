import requests

url = "http://127.0.0.1:8000/optimize_strategy"
files = {'file': open('/Users/prashanthkumar/Projects/TradingBot/backend/data/Student_Performance_Dataset.csv', 'rb')} # We just need a valid CSV to test payload drop, this test will purposefully fail strategy physics but should return optimization format
payload = {
    'config': '{"mode":"template","strategy":"ma_crossover","parameters":{"stop_loss":0.02,"take_profit":0.04}}',
    'param_ranges': '{"short_ma":[5,10],"long_ma":[20,50]}'
}

print("Testing Payload structure")
response = requests.post(url, files=files, data=payload)
print(response.json())
