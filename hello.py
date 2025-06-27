import requests

# 1. Create API key
create_key_response = requests.post(
    "http://localhost:8000/v1/api-keys",
    json={"name": "python-test-key", "description": "Test key from Python"},
)
api_key = create_key_response.json()["key"]
print(f"Created API key: {api_key}")

# 2. Use API key for chat
chat_response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello from Python!"}],
        "max_tokens": 100,
        "temperature": 0.7,
        "stream": False,
    },
)

result = chat_response.json()
print(result)
