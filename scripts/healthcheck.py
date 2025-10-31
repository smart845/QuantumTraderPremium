
import requests, os
url = os.environ.get("HEALTH_URL","http://localhost:8000/healthz")
try:
    r = requests.get(url, timeout=2)
    print(r.status_code, r.text)
    exit(0 if r.ok else 1)
except Exception as e:
    print("ERR", e)
    exit(1)
