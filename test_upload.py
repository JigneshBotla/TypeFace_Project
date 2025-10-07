# test_upload.py
import os
import requests

# Paste your working Bearer token here (from login or register)
TOKEN = "<paste-your-token-here>"

# Update this to the actual file path
file_path = r"C:\Users\botla\Desktop\sample_receipt.jpg"

url = "http://127.0.0.1:8000/api/v1/receipts"

if not os.path.exists(file_path):
    print(f"❌ File not found: {file_path}")
    exit(1)

with open(file_path, "rb") as f:
    files = {"file": (os.path.basename(file_path), f, "image/jpeg")}
    headers = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.post(url, files=files, headers=headers)
    print("Status:", r.status_code)
    print("Response:", r.text)
