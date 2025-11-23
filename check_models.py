import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

print("Đang lấy danh sách models...")
try:
    for m in genai.list_models():
        print(f"Model: {m.name}")
except Exception as e:
    print(f"Lỗi: {e}")