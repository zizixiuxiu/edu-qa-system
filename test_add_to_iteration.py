import urllib.request
import json

# Test add-to-iteration API
data = json.dumps({"result_ids": [1]}).encode()

req = urllib.request.Request(
    'http://localhost:8001/api/v1/benchmark/add-to-iteration',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=10) as response:
        print(response.read().decode())
except Exception as e:
    print(f"Error: {e}")
