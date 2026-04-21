#!/usr/bin/env python3
"""Lista los modelos disponibles en Google AI"""

import os
from dotenv import load_dotenv

load_dotenv()

import google.generativeai as genai

api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

print("📋 Modelos disponibles en Google AI:\n")

for model in genai.list_models():
    print(f"Modelo: {model.name}")
    print(f"  Display: {model.display_name}")
    print(f"  Métodos: {model.supported_generation_methods}")
    print()
