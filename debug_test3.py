import os
import requests
import json
from dotenv import load_dotenv

load_dotenv(override=True)
client_id = os.getenv("NAVER_CLIENT_ID", "").strip("'\" ")
client_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip("'\" ")

print(f"Testing Client ID: [{client_id}]")

hosts = [
    "https://naveropenapi.apigw.ntruss.com",
    "https://naveropenapi.apigw-vpc.ntruss.com",
    "https://fin-naveropenapi.apigw.fin-ntruss.com",
    "https://fin-naveropenapi.apigw-vpc.fin-ntruss.com",
    "https://gov-naveropenapi.apigw.gov-ntruss.com"
]

paths = [
    "/datalab/v1/search",
    "/v1/datalab/search",
    "/datalab/search"
]

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

for host in hosts:
    for path in paths:
        url = host + path
        try:
            res = requests.post(url, headers=headers, json=body, timeout=3)
            print(f"URL: {url} -> Status: {res.status_code}, Body: {res.text[:120]}")
        except Exception as e:
            print(f"URL: {url} -> Exception: {e}")
