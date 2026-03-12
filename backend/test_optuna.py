import requests

url = "http://127.0.0.1:8000/optimize_strategy"
# Use a minimal test data file
try:
    files = {'file': open('test_data.csv', 'rb')} 
except FileNotFoundError:
    print("test_data.csv not found, please create or point to a valid csv.")
    exit(1)

payload = {
    'config': '{"mode":"template","strategy":"ma_crossover","parameters":{"stop_loss":0.02,"take_profit":0.04}}',
    'param_ranges': '{"short_ma":[5,10],"long_ma":[20,50]}',
    'trials': 5
}

print("Testing Optuna Optimization Payload")
response = requests.post(url, files=files, data=payload)

if response.status_code == 200:
    import json
    data = response.json()
    print("Optimization returned successfully.")
    print(f"Best parameters: {json.dumps(data.get('best_parameters'))}")
    print(f"Best score: {data.get('best_score')}")
    print(f"Number of history entries: {len(data.get('optimization_history', []))}")
else:
    print(f"Error {response.status_code}: {response.text}")
