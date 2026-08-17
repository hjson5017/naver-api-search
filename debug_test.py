import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(override=True)
client_id = os.getenv("NAVER_CLIENT_ID", "").strip("'\" ")
client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip("'\" ")

print(f"Testing Client ID: [{client_id}]")
print(f"Testing Client Secret Length: {len(client_secret)}")

test_targets = [
    ("https://openapi.naver.com/v1/datalab/search", {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret, "Content-Type": "application/json"}),
    ("https://naveropenapi.apigw.ntruss.com/datalab/v1/search", {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret, "Content-Type": "application/json"}),
    ("https://naveropenapi.apigw.ntruss.com/v1/datalab/search", {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret, "Content-Type": "application/json"}),
    ("https://openapi.naver.com/v1/search/shop.json?query=아이폰", {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}),
    ("https://naveropenapi.apigw.ntruss.com/map-place/v1/search?query=아이폰", {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret})
]

body = {
    "startDate": "2024-01-01",
    "endDate": "2024-03-31",
    "timeUnit": "week",
    "keywordGroups": [{"groupName": "아이폰", "keywords": ["아이폰"]}]
}

for url, headers in test_targets:
    print(f"\n--- Testing URL: {url} ---")
    if "datalab" in url:
        res = requests.post(url, headers=headers, json=body)
    else:
        res = requests.get(url, headers=headers)
    print(f"Status Code: {res.status_code}")
    print(f"Response Body: {res.text[:300]}")
