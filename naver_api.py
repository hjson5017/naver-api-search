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

# NAVER API HUB 공식 베이스 도메인.
# 예전 코드에 있던 "naveropenapi.apigw.ntruss.com"은 오타 수준으로 다른(존재하지 않거나
# 구버전) 도메인입니다. 반드시 "naverapihub"인지 확인하세요.
API_HUB_BASE = "https://naverapihub.apigw.ntruss.com"


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
    """NAVER API HUB(naverapihub.apigw.ntruss.com) 기반 데이터 수집 클래스.

    NOTE: 2026년 네이버 검색/데이터랩 API가 NAVER API HUB로 이관되면서
    - 인증 헤더: X-NCP-APIGW-API-KEY-ID / X-NCP-APIGW-API-KEY (기존 X-Naver-Client-Id 계열 아님)
    - 베이스 도메인: naverapihub.apigw.ntruss.com (기존 openapi.naver.com / naveropenapi.apigw.ntruss.com 아님)
    - 경로: .json 확장자 제거, 대신 format=json 쿼리 파라미터 사용
    로 바뀌었습니다. 상품(쇼핑) 검색 API는 HUB로 이관되지 않고 완전히 종료되었으므로
    fetch_shop_items는 실패 시 명확한 안내와 함께 빈 결과를 돌려줍니다.

    실패 시 가짜 데이터로 조용히 대체하지 않고 NaverApiError를 던집니다 — 원인(상태코드/응답
    본문)을 그대로 화면에서 확인할 수 있어야 디버깅이 가능하기 때문입니다.
    """

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = clean_key_str(client_id)
        self.client_secret = clean_key_str(client_secret)

        self.hub_headers = {
            "X-NCP-APIGW-API-KEY-ID": self.client_id,
            "X-NCP-APIGW-API-KEY": self.client_secret,
        }

    def is_valid_credentials(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _get(self, path: str, params: dict) -> requests.Response:
        params = {**params, "format": "json"}
        url = f"{API_HUB_BASE}{path}"
        res = requests.get(url, headers=self.hub_headers, params=params, timeout=10)
        if res.status_code != 200:
            raise NaverApiError(f"{url} 호출 실패 ({res.status_code}): {res.text[:400]}")
        return res

    def _post(self, path: str, body: dict) -> requests.Response:
        url = f"{API_HUB_BASE}{path}"
        json_data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        res = requests.post(
            url,
            headers={**self.hub_headers, "Content-Type": "application/json"},
            params={"format": "json"},
            data=json_data,
            timeout=10,
        )
        if res.status_code != 200:
            raise NaverApiError(f"{url} 호출 실패 ({res.status_code}): {res.text[:400]}")
        return res

    # ------------------------------------------------------------------
    # 검색어 트렌드 (구 /datalab/v1/search -> HUB /search-trend/v1/search)
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

        res = self._post("/search-trend/v1/search", body)

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
    # 쇼핑인사이트 (구 /datalab/v1/shopping/* -> HUB /shopping/v1/*)
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
        res = self._post("/shopping/v1/categories", body)

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

        # 이 엔드포인트는 category를 문자열로 받습니다 (categories 엔드포인트와 다름 — 400 TypeError로 확인됨)
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": category_code
        }
        res = self._post("/shopping/v1/category/gender", body)

        # 실제 응답 구조 (2026-08 확인): results[].title은 카테고리 코드이고,
        # 성별 구분은 각 data 항목의 "group" 필드("m"/"f")에 들어있습니다.
        # 예: {"results":[{"title":"50000007","data":[{"period":...,"ratio":...,"group":"f"}, ...]}]}
        res_data = res.json()
        results = res_data.get("results", [])
        records = []
        unrecognized = False
        for grp in results:
            for data_item in grp.get("data", []):
                raw_group = data_item.get("group")
                if raw_group == "m":
                    gender_name = "남성"
                elif raw_group == "f":
                    gender_name = "여성"
                else:
                    unrecognized = True
                    gender_name = raw_group
                records.append({
                    "period": data_item.get("period"),
                    "gender": gender_name,
                    "ratio": float(data_item.get("ratio", 0.0))
                })
        if unrecognized or not records:
            raise NaverApiError(
                "쇼핑인사이트(성별) 응답이 예상 형식(group=m/f)이 아닙니다. "
                f"원본 응답: {json.dumps(res_data, ensure_ascii=False)[:600]}"
            )
        # 화면(파이차트)은 성별당 값 1개를 기대하므로, 조회 기간 내 기간별 값을 평균내서
        # 성별당 한 줄로 합칩니다. (합치지 않으면 기간 수만큼 중복 누적되어 왜곡됩니다.)
        df_raw = pd.DataFrame(records)
        return df_raw.groupby("gender", as_index=False)["ratio"].mean()

    def fetch_shopping_age_insight(
        self,
        category_code: str,
        start_date: str,
        end_date: str,
        time_unit: str = "month"
    ) -> pd.DataFrame:
        if not self.is_valid_credentials() or not category_code:
            return pd.DataFrame()

        # 이 엔드포인트는 category를 문자열로 받습니다 (categories 엔드포인트와 다름 — 400 TypeError로 확인됨)
        body = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "category": category_code
        }
        res = self._post("/shopping/v1/category/age", body)

        # 성별 인사이트와 동일하게, 연령대 구분도 각 data 항목의 "group" 필드
        # ("10"/"20"/"30"/"40"/"50"/"60")에 들어있습니다.
        res_data = res.json()
        results = res_data.get("results", [])
        records = []
        unrecognized = False
        for grp in results:
            for data_item in grp.get("data", []):
                raw_group = data_item.get("group", "")
                if raw_group not in AGE_MAP:
                    unrecognized = True
                age_label = AGE_MAP.get(raw_group, f"{raw_group}대")
                records.append({
                    "period": data_item.get("period"),
                    "age_group": age_label,
                    "ratio": float(data_item.get("ratio", 0.0))
                })
        if unrecognized or not records:
            raise NaverApiError(
                "쇼핑인사이트(연령) 응답이 예상 형식(group=연령대 코드)이 아닙니다. "
                f"원본 응답: {json.dumps(res_data, ensure_ascii=False)[:600]}"
            )
        # 화면(막대차트)은 연령대당 값 1개를 기대하므로, 기간별 값을 평균내서
        # 연령대당 한 줄로 합칩니다.
        df_raw = pd.DataFrame(records)
        return df_raw.groupby("age_group", as_index=False)["ratio"].mean()

    # ------------------------------------------------------------------
    # 검색 API (뉴스/블로그/카페/장소) — HUB로 이관된 것들
    # ------------------------------------------------------------------
    def fetch_shop_items(self, query: str, display: int = 50, sort: str = "sim") -> pd.DataFrame:
        """상품(쇼핑) 검색 API는 2026-07-31부로 NAVER API HUB에 이관되지 않고 완전히
        종료되었습니다. 이 함수는 더 이상 실시간 데이터를 가져올 수 없으며, 호출 시
        NaverApiError를 던집니다. app.py에서는 이 실패를 잡아 '종료된 API'임을 안내하고
        네이버쇼핑 검색 링크로 대체하는 것을 권장합니다.
        """
        raise NaverApiError(
            "네이버 상품(쇼핑) 검색 API는 2026-07-31부로 서비스가 완전히 종료되어 "
            "NAVER API HUB에서도 제공되지 않습니다. 이 기능은 더 이상 실시간 데이터를 "
            "가져올 수 없습니다. (네이버쇼핑 통합검색 페이지 링크로 대체하는 것을 권장합니다.)"
        )

    def fetch_news_items(self, query: str, display: int = 30) -> pd.DataFrame:
        if not query.strip():
            return pd.DataFrame()
        params = {"query": query.strip(), "display": min(display, 100), "start": 1, "sort": "date"}
        res = self._get("/search/v1/news", params)

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
        res = self._get("/search/v1/blog", params)

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
        res = self._get("/search/v1/cafearticle", params)

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
        res = self._get("/search/v1/local", params)

        items = res.json().get("items", [])
        df = pd.DataFrame(items)
        if df.empty:
            return df
        df["title"] = df["title"].apply(clean_html_tags)
        df["category"] = df["category"].apply(clean_html_tags)
        df["address"] = df["address"].apply(clean_html_tags)
        df["roadAddress"] = df["roadAddress"].apply(clean_html_tags)
        return df
