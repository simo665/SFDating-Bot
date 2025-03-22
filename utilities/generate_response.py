from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GEMINI_API")
client = genai.Client(api_key=api_key)

def get_response(self, message, instructions):
    response = client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=instructions,
            max_output_tokens=1200,
            temperature=0.9
        )
    )
    return response.text