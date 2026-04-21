from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv("GEMINI_API_KEY")
print(f"GEMINI_API_KEY present: {bool(key)}")
if key:
    print(f"Key length: {len(key)}")
    print(f"Key starts with: {key[:4]}...")
