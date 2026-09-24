from dotenv import load_dotenv
import os
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env")

print("API key loaded successfully.")

client = genai.Client(api_key=api_key)

print("Sending request to Gemini...")

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents="Tell me a very short joke."
)

print("\nGemini response:")
print(response.text)