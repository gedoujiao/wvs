import requests

url = "http://localhost:8000/register"
data = {
    "email": "admin@example.com",
    "password": "adminpassword"
}
params = {
    "is_admin": True
}

response = requests.post(url, json=data, params=params)
print(response.json())