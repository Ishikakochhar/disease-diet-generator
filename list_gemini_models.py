import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv("disease_diet_adk/.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
for m in genai.list_models():
    print(f"Model: {m.name}, Methods: {m.supported_generation_methods}")
