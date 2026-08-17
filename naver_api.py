import requests
import json
import re
import urllib.parse
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional

# 쇼핑 대분류 카테고리 정보
SHOPPING_CATEGORIES = {
    "전체 / 자동추정": "",
    "패션의류": "50000000",
    "패션잡화": "50000001",
    "화장품/미용": "50000002",
    "디지털/가전": "50000003",
    "가구/인테리어": "50000004",
    "출산/육아": "50000005",
    "식품": "50000006",
    "스포츠/레저": "50000007",
    "생활/건강": "50000008",
    "여가/생활편의": "50000009",
    "도서": "50000010"
}

AGE_MAP = {
    "10": "10대 (13-18세)",
    "20": "20대 (19-24세)",
    "30": "30대 (25-29세)",
    "40": "30대 후반~40대",
    "50": "40대 후반~50대",
    "60": "50대 후반~60대 이상"
}


class NaverApiError(Exception):
    """네이버 API 호출이 실패했을 때 실제 원인을 그대로 담아 올리는 예외.
    app.py의 try/except가 이 메시지를 st.error로 그대로 보여줍니다.
    """
    pass


def clean_html_tags(text: str) -> str:
    """문자열 내 HTML 태그 및 특수 엔티티 제거"""
    if not isinstance(text, str):
        return str(text)
    clean_text = re.sub(r'<[^>]+>', '', text)
    clean_text = clean_text.replace("&quot;", '"').replace("&amp;", '&').replace("&lt;", '<').replace("&gt;", '>')
    return clean_text


def clean_key_str(val: str) -> str:
    """따옴표(' 및 ") 및 공백 완벽 제거"""
    if not val:
        return ""
    return str(val).strip().strip("'").strip('"').strip()


class NaverDataFetcher:
    """NAVER 실시간 다중 채널(검색어 트렌드, 쇼핑, 뉴스, 블로그, 카페, 장소) 데이터 수집 클래스.

    주의: 이 버전은 API 호출이 실패하면 가짜 데이터로 조용히 대체하지 않고
    NaverApiError를 발생시킵니다. 원인(상태코드/응답 본문)을 그대로 확인할 수 있습니다.
    """

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = clean_key_str(client_id)
        self.client_secret = clean_key_str(client_secret)

        # 일반 개발자센터(openapi.naver.com) 키 — 검색 API, 데이터랩 API 모두 이 헤더를 씁니다.
        self.naver_headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        # NCP API Gateway 키(다른 발급 체계). 발급받은 적이 없다면 계속 실패하는 게 정상입니다.
        self.ncp_headers = {
            "X-NCP-APIGW-API-KEY-ID": self.client_id,
            "X-NCP-APIGW-API-KEY": self.client_secret,
        }

    def is_valid_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _post_with_fallback(self, ncp_url: str, naver_url: str, body: dict) -> requests.Response:
        """NCP 엔드포인트를 먼저 시도하고, 실패하면 openapi.naver.com으로 재시도합니다.
        둘 다 실패하면 마지막 응답 정보를 담아 NaverApiError를 던집니다.
        """
        json_data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        res = requests.post(
            ncp_url,
            headers={**self.ncp_headers, "Content-Type": "application/json"},
            data=json_data,
            timeout=10,
        )
        if res.status_code == 200:
            return res

        res_naver = requests.post(
            naver_url,
            headers={**self.naver_headers, "Content-Type": "application/json"},
            data=json_data,
            timeout=10,
        )
        if res_naver.status_code == 200:
            return res_naver

        raise NaverApiError(
            f"네이버 API 호출 실패. NCP({res.status_code}): {res.text[:300]} "
            f"/ openapi.naver.com({res_naver.status_code}): {res_naver.text[:300]}"
        )

    def _get_with_check(self, url: str, params: dict) -> requests.Response:
        res = requests.get(url, headers=self.naver_headers, params=params, timeout=10)
        if res.status_code != 200:
            raise NaverApiError(f"{url} 호출 실패 ({res.status_code}): {res.text[:300]}")
        return res

    # ------------------------------------------------------------------
    # 검색어 트렌드 (Datalab Search)
    # ------------------------------------------------------------------
    def fetch_search_trend(
        self,
        keywords: List[str],
        start_date: str,
        end_date: str,
        time_unit: str = "week",
        device: str = "",
        gender: str = ""
    ) -> pd.DataFrame:
        if not self.is_valid_credentials():
            raise ValueError("Client ID와 Client Secret이 필요합니다.")
        valid_keywords = [kw.strip() for kw in keywords if kw.strip()][:5]
        if not valid_keywords:
            return pd.DataFrame()

        keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in valid_keywords]
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": keyword_groups
        }
        if device:
            body["device"] = device
        if gender:
            body["gender"] = gender

        res = self._post_with_fallback(
            "https://naveropenapi.apigw.ntruss.com/datalab/v1/search",
            "https://openapi.naver.com/v1/datalab/search",
            body,
        )

        res_data = res.json()
        results = res_data.get("results", [])
        records = []
        for grp in results:
            title = grp.get("title")
            for data_item in grp.get("data", []):
                records.append({
                    "period": data_item.get("period"),
                    "keyword": title,
                    "ratio": float(data_item.get("ratio", 0.0))
                })
        df = pd.DataFrame(records)
        if not df.empty:
            df["period"] = pd.to_datetime(df["period"])
        return df

    # ------------------------------------------------------------------
    # 쇼핑인사이트 (Datalab Shopping) — 개발자센터에서 별도 API 사용 승인 필요
    # ------------------------------------------------------------------
    def fetch_shopping_insight(
        self,
        category_code: str,
        start_date: str,
        end_date: str,
        time_unit: str = "month",
        device: str = "",
        gender: str = ""
    ) -> pd.DataFrame:
        if not self.is_valid_credentials() or not category_code:
            return pd.DataFrame()

        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": [{"name": "선택 카테고리", "param": [category_code]}]
        }
        res = self._post_with_fallback(
            "https://naveropenapi.apigw.ntruss.com/datalab/v1/shopping/categories",
            "https://openapi.naver.com/v1/datalab/shopping/categories",
            body,
        )

        res_data = res.json()
        results = res_data.get("results", [])
        records = []
        for grp in results:
            for data_item in grp.get("data", []):
                records.append({
                    "period": data_item.get("period"),
                    "ratio": float(data_item.get("ratio", 0.0))
                })
        df = pd.DataFrame(records)
        if not df.empty:
            df["period"] = pd.to_datetime(df["period"])
        return df

    def fetch_shopping_gender_insight(
        self,
        category_code: str,
        start_date: str,
        end_date: str,
        time_unit: str = "month"
    ) -> pd.DataFrame:
        if not self.is_valid_credentials() or not category_code:
            return pd.DataFrame()

        body = {"startDate": start_date, "endDate": end_date, "timeUnit": time_unit, "category": category_code}
        # 기존 코드는 여기서 NCP 엔드포인트만 호출하고 openapi.naver.com 폴백이 없었습니다.
        # 그래서 일반 Client ID/Secret 사용 시 항상 실패 -> 항상 가짜 데이터였습니다.
        res = self._post_with_fallback(
            "https://naveropenapi.apigw.ntruss.com/datalab/v1/shopping/category/gender",
            "https://openapi.naver.com/v1/datalab/shopping/category/gender",
            body,
        )

        res_data = res.json()
        results = res_data.get("results", [])
        records = []
        for grp in results:
            gender_name = "남성" if grp.get("title") == "m" else ("여성" if grp.get("title") == "f" else grp.get("title"))
            for data_item in grp.get("data", []):
                records.append({
                    "period": data_item.get("period"),
                    "gender": gender_name,
                    "ratio": float(data_item.get("ratio", 0.0))
                })
        return pd.DataFrame(records)

    def fetch_shopping_age_insight(
        self,
        category_code: str,
        start_date: str,
        end_date: str,
        time_unit: str = "month"
    ) -> pd.DataFrame:
        if not self.is_valid_credentials() or not category_code:
            return pd.DataFrame()

        body = {"startDate": start_date, "endDate": end_date, "timeUnit": time_unit, "category": category_code}
        # 마찬가지로 openapi.naver.com 폴백 추가
        res = self._post_with_fallback(
            "https://naveropenapi.apigw.ntruss.com/datalab/v1/shopping/category/age",
            "https://openapi.naver.com/v1/datalab/shopping/category/age",
            body,
        )

        res_data = res.json()
        results = res_data.get("results", [])
        records = []
        for grp in results:
            raw_age = grp.get("title", "")
            age_label = AGE_MAP.get(raw_age, f"{raw_age}대")
            for data_item in grp.get("data", []):
                records.append({
                    "period": data_item.get("period"),
                    "age_group": age_label,
                    "ratio": float(data_item.get("ratio", 0.0))
                })
        return pd.DataFrame(records)

    # ------------------------------------------------------------------
    # 검색 API (뉴스/블로그/카페/장소/쇼핑) — openapi.naver.com, 일반 Client ID/Secret으로 동작
    # ------------------------------------------------------------------
    def fetch_shop_items(self, query: str, display: int = 50, sort: str = "sim") -> pd.DataFrame:
        if not query.strip():
            return pd.DataFrame()
        params = {"query": query.strip(), "display": min(display, 100), "start": 1, "sort": sort}
        res = self._get_with_check("https://openapi.naver.com/v1/search/shop.json", params)

        items = res.json().get("items", [])
        df = pd.DataFrame(items)
        if df.empty:
            return df
        df["clean_title"] = df["title"].apply(clean_html_tags)
        df["lprice"] = pd.to_numeric(df["lprice"], errors="coerce").fillna(0).astype(int)
        df["hprice"] = pd.to_numeric(df["hprice"], errors="coerce").fillna(0).astype(int)
        df["brand"] = df["brand"].replace("", "기타/자체제작")
        df["maker"] = df["maker"].replace("", "기타")
        df["category1"] = df["category1"].apply(clean_html_tags)
        if "mallName" not in df.columns or df["mallName"].isnull().all():
            df["mallName"] = "네이버 스마트스토어"
        return df

    def fetch_news_items(self, query: str, display: int = 30) -> pd.DataFrame:
        if not query.strip():
            return pd.DataFrame()
        params = {"query": query.strip(), "display": min(display, 100), "start": 1, "sort": "date"}
        res = self._get_with_check("https://openapi.naver.com/v1/search/news.json", params)

        items = res.json().get("items", [])
        df = pd.DataFrame(items)
        if df.empty:
            return df
        df["title"] = df["title"].apply(clean_html_tags)
        df["description"] = df["description"].apply(clean_html_tags)
        df["pubDate"] = pd.to_datetime(df["pubDate"], errors="coerce").dt.strftime('%Y-%m-%d %H:%M')
        return df

    def fetch_blog_items(self, query: str, display: int = 30) -> pd.DataFrame:
        if not query.strip():
            return pd.DataFrame()
        params = {"query": query.strip(), "display": min(display, 100), "start": 1, "sort": "date"}
        res = self._get_with_check("https://openapi.naver.com/v1/search/blog.json", params)

        items = res.json().get("items", [])
        df = pd.DataFrame(items)
        if df.empty:
            return df
        df["title"] = df["title"].apply(clean_html_tags)
        df["description"] = df["description"].apply(clean_html_tags)
        df["postdate"] = pd.to_datetime(df["postdate"], format='%Y%m%d', errors='coerce').dt.strftime('%Y-%m-%d')
        return df

    def fetch_cafe_items(self, query: str, display: int = 30) -> pd.DataFrame:
        if not query.strip():
            return pd.DataFrame()
        params = {"query": query.strip(), "display": min(display, 100), "start": 1, "sort": "date"}
        res = self._get_with_check("https://openapi.naver.com/v1/search/cafearticle.json", params)

        items = res.json().get("items", [])
        df = pd.DataFrame(items)
        if df.empty:
            return df
        df["title"] = df["title"].apply(clean_html_tags)
        df["description"] = df["description"].apply(clean_html_tags)
        df["cafename"] = df["cafename"].apply(clean_html_tags)
        return df

    def fetch_place_items(self, query: str, display: int = 20) -> pd.DataFrame:
        if not query.strip():
            return pd.DataFrame()
        params = {"query": query.strip(), "display": min(display, 50), "start": 1, "sort": "random"}
        res = self._get_with_check("https://openapi.naver.com/v1/search/local.json", params)

        items = res.json().get("items", [])
        df = pd.DataFrame(items)
        if df.empty:
            return df
        df["title"] = df["title"].apply(clean_html_tags)
        df["category"] = df["category"].apply(clean_html_tags)
        df["address"] = df["address"].apply(clean_html_tags)
        df["roadAddress"] = df["roadAddress"].apply(clean_html_tags)
        return df
