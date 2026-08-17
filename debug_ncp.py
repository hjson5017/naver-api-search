import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(override=True)
client_id = os.getenv("NAVER_CLIENT_ID", "").strip("'\" ")
client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip("'\" ")

print(f"DEBUG Client ID: [{client_id}]")
print(f"DEBUG Client Secret: [{client_secret}]")

# NCP 공식 API Gateway 단독 호출
url = "https://naveropenapi.apigw.ntruss.com/datalab/v1/search"
headers = {
    "X-NCP-APIGW-API-KEY-ID": client_id,
    "X-NCP-APIGW-API-KEY": client_secret,
    "Content-Type": "application/json"
}

body = {
    "startDate": "2024-01-01",
    "endDate": "2024-03-31",
    "timeUnit": "week",
    "keywordGroups": [{"groupName": "아이폰", "keywords": ["아이폰"]}]
}

res = requests.post(url, headers=headers, json=body)
print(f"NCP API GW Status Code: {res.status_code}")
print(f"NCP API GW Response: {res.text}")

# NCP 검색 API 단독 호출
url_search = "https://naveropenapi.apigw.ntruss.com/search/v1/shop.json?query=아이폰"
res_search = requests.get(url_search, headers={"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret})
print(f"NCP Search Status Code: {res_search.status_code}")
print(f"NCP Search Response: {res_search.text[:300]}")
