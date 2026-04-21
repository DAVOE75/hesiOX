
import os
import requests
import json

api_key = os.environ.get('GEMINI_API_KEY')
if not api_key:
    print("No API Key found")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
try:
    resp = requests.get(url)
    if resp.status_code == 200:
        models = resp.json().get('models', [])
        for m in models:
            print(f"Model: {m.get('name')} - Methods: {m.get('supportedGenerationMethods')}")
    else:
        print(f"Error {resp.status_code}: {resp.text}")
except Exception as e:
    print(f"Exception: {e}")
