import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

print("✅ Fetching models list...")

try:
    # We will just print the "name" of every single model found.
    for model in client.models.list():
        print(f"👉 {model.name}")
        
except Exception as e:
    print(f"❌ Error: {e}")
