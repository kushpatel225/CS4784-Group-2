import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("❌ GEMINI_API_KEY not found in .env file")
    exit(1)

print(f"✓ API key found: {api_key[:8]}...")

genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content("Say 'works' and nothing else.")
    print(f"✅ gemini-2.5-flash works! Response: {response.text.strip()}")
    print("\n✅ Everything is working. You're good to go!")
except Exception as e:
    print(f"❌ Failed: {e}")