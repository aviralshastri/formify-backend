import requests

# URL of your FastAPI endpoint
url = "http://192.168.1.8:8000/contact"  # Update this if your server runs on a different host/port

# Sample data to send to the endpoint
payload = {
    "name": "John Doe",
    "phone": "1234567890",
    "message": "Hello, this is a test message.",
    "email": "johndoe@example.com"
}

# Send the POST request
response = requests.post(url, json=payload)

# Print the response
if response.status_code == 200:
    print("Success:", response.json())
else:
    print("Failed:", response.status_code, response.text)
