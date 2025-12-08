import sys
import httpx

try:
    r = httpx.get('http://127.0.0.1:8000/items', timeout=5.0)
    print('STATUS', r.status_code)
    print(r.text)
except Exception as e:
    print('HTTP check failed:', e)
    sys.exit(0)
