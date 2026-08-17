import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(override=True)
client_id = os.getenv("NAVER_CLIENT_ID", "").strip("'\" ")
client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip("'\" ")

print(f"Testing Client ID: [{client_id}]")
print(f"Testing Client Secret: [{client_secret}]")

# 가능한 헤더 및 URL 조합 테스트
combinations = [
    # 1. NCP API GW 공식 헤더 대소문자
    ("https://naveropenapi.apigw.ntruss.com/datalab/v1/search", {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret}),
    # 2. NCP 소문자
    ("https://naveropenapi.apigw.ntruss.com/datalab/v1/search", {"x-ncp-apigw-api-key-id": client_id, "x-ncp-apigw-api-key": client_secret}),
    # 3. Naver Client ID 헤더 on ntruss
    ("https://naveropenapi.apigw.ntruss.com/datalab/v1/search", {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}),
    # 4. openapi.naver.com on Naver headers
    ("https://openapi.naver.com/v1/datalab/search", {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}),
    # 5. openapi.naver.com on NCP headers
    ("https://openapi.naver.com/v1/datalab/search", {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret}),
    # 6. Combined on ntruss
    ("https://naveropenapi.apigw.ntruss.com/datalab/v1/search", {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret, "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}),
    # 7. Combined on openapi
    ("https://openapi.naver.com/v1/datalab/search", {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret, "X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}),
]

body = {
    "startDate": "2024-01-01",
    "endDate": "2024-03-31",
    "timeUnit": "week",
    "keywordGroups": [{"groupName": "아이폰", "keywords": ["아이폰"]}]
}

for idx, (url, headers) in enumerate(combinations, 1):
    h = {**headers, "Content-Type": "application/json"}
    res = requests.post(url, headers=h, data=json.dumps(body))
    print(f"[{idx}] {url}")
    print(f"    Headers: {list(headers.keys())}")
    print(f"    Status: {res.status_code}")
    print(f"    Body: {res.text[:150]}")
