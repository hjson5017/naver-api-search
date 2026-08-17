import os
import time
import base64
import hmac
import hashlib
import requests
import json
from dotenv import load_dotenv

load_dotenv(override=True)
access_key = os.getenv("NAVER_CLIENT_ID", "").strip("'\" ")
secret_key = os.getenv("NAVER_CLIENT_SECRET", "").strip("'\" ")

print(f"Access Key: [{access_key}]")

timestamp = str(int(time.time() * 1000))

# 1. API GW Simple Key Header
url = "https://naveropenapi.apigw.ntruss.com/datalab/v1/search"

# 2. HMAC Signature
method = "POST"
uri = "/datalab/v1/search"
message = f"{method} {uri}\n{timestamp}\n{access_key}"
signature = base64.b64encode(hmac.new(secret_key.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')

headers_sig = {
    "x-ncp-apigw-timestamp": timestamp,
    "x-ncp-iam-access-key": access_key,
    "x-ncp-apigw-signature-v2": signature,
    "Content-Type": "application/json"
}

body = {
    "startDate": "2024-01-01",
    "endDate": "2024-03-31",
    "timeUnit": "week",
    "keywordGroups": [{"groupName": "아이폰", "keywords": ["아이폰"]}]
}

res = requests.post(url, headers=headers_sig, json=body)
print(f"HMAC Signature Test Status: {res.status_code}")
print(f"HMAC Signature Response: {res.text}")
