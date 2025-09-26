import requests

url = "http://127.0.0.1:5000/api/hr/auth/login"
data = {"email": "officer@example.com", "password": "officer123"}

r = requests.post(url, json=data)
print(r.status_code, r.json())
