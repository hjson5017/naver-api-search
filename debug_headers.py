import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(override=True)
client_id = os.getenv("NAVER_CLIENT_ID", "").strip("'\" ")
client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip("'\" ")

url = "https://naveropenapi.apigw.ntruss.com/datalab/v1/search"
body = {
    "startDate": "2024-01-01",
    "endDate": "2024-03-31",
    "timeUnit": "week",
    "keywordGroups": [{"groupName": "아이폰", "keywords": ["아이폰"]}]
}

test_headers_list = [
    {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret},
    {"X-NCP-API-KEY-ID": client_id, "X-NCP-API-KEY": client_secret},
    {"x-ncp-apigw-api-key-id": client_id, "x-ncp-apigw-api-key": client_secret},
    {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret},
    {"Client-Id": client_id, "Client-Secret": client_secret},
    {"x-ncp-iam-access-key": client_id, "x-ncp-iam-secret-key": client_secret},
    {"Authorization": f"Bearer {client_secret}", "X-NCP-APIGW-API-KEY-ID": client_id}
]

for idx, h in enumerate(test_headers_list, 1):
    req_h = {**h, "Content-Type": "application/json"}
    res = requests.post(url, headers=req_h, json=body)
    print(f"[{idx}] Headers: {list(h.keys())} -> Status: {res.status_code}, Body: {res.text[:120]}")
