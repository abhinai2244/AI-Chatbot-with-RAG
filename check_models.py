import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

candidates = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-001",
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-1.0-pro"
]

print("Checking Model Availability...")
for model_name in candidates:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hi")
        print(f"✅ {model_name}: WORKS")
    except Exception as e:
        if "404" in str(e):
            print(f"❌ {model_name}: Not Found (404)")
        elif "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            if "limit: 0" in str(e):
                print(f"⚠️ {model_name}: Available but No Quota (Limit 0)")
            else:
                print(f"✅ {model_name}: WORKS (Hit Rate Limit)")
        else:
            print(f"❌ {model_name}: Error {str(e)[:100]}")
