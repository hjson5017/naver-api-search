# 네이버 API 데이터 수집 가이드 (NAVER API Data Collection Guide)

이 문서는 **네이버 검색 API**, **네이버 데이터랩 검색어 트렌드 API**, **네이버 데이터랩 쇼핑 인사이트 API**를 활용하여 데이터분석 및 종합 EDA 대시보드를 구축하기 위한 수집 가이드입니다.

---

## 1. 사전 준비 및 API 키 발급 (API Authentication Setup)

네이버 오픈 API를 호출하기 위해서는 네이버 개발자 포털(NAVER Developers)에서 애플리케이션을 등록하고 **Client ID** 및 **Client Secret**을 발급받아야 합니다.

### 1.1 애플리케이션 등록 절차
1. **네이버 API Hub 콘솔 접속**: [https://console.ncloud.com/naver-api-hub/application](https://console.ncloud.com/naver-api-hub/application) (또는 [네이버 개발자 센터](https://developers.naver.com))에 접속하여 로그인합니다.
2. **[애플리케이션 등록]** 또는 **[Application 등록]** 버튼을 클릭합니다.
3. 애플리케이션 이름(예: `My EDA Dashboard`)을 입력합니다.
4. 사용 API 선택:
   - **검색 (Search)**
   - **데이터랩 (검색어 트렌드)**
   - **데이터랩 (쇼핑인사이트)**
5. 환경 추가: `WEB` 선택 후 URL 입력 (예: `http://localhost:8501`)
6. 등록 완료 후 발급된 **Client ID**와 **Client Secret**을 확인합니다.

### 1.2 HTTP 요청 인증 헤더 (Request Header)
모든 REST API 요청 시 아래 HTTP 헤더를 포함해야 합니다.

| Header 키 | 설명 |
| :--- | :--- |
| `X-Naver-Client-Id` | 발급받은 Client ID 값 |
| `X-Naver-Client-Secret` | 발급받은 Client Secret 값 |
| `Content-Type` | `application/json` (POST 요청 시) |

---

## 2. 네이버 검색 API (Naver Search API)

키워드 기반의 쇼핑 상품, 뉴스, 블로그 검색 결과를 수집합니다.

### 2.1 주요 엔드포인트 (Endpoints)
- **쇼핑 검색 API**: `GET https://openapi.naver.com/v1/search/shop.json`
- **뉴스 검색 API**: `GET https://openapi.naver.com/v1/search/news.json`
- **블로그 검색 API**: `GET https://openapi.naver.com/v1/search/blog.json`

### 2.2 주요 요청 파라미터 (Query Parameters)
| 파라미터명 | 타입 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- |
| `query` | String | (필수) | 검색어 (UTF-8 URL 인코딩 필요) |
| `display` | Integer | 10 | 한 번에 표시할 검색 결과 수 (1 ~ 100) |
| `start` | Integer | 1 | 검색 시작 위치 (1 ~ 1000) |
| `sort` | String | `sim` | 정렬 옵션 (`sim`: 정확도순, `date`: 날짜순, `asc`/`dsc`: 가격순(쇼핑 전용)) |

### 2.3 Python 수집 코드 예시 (Search API Example)
```python
import requests
import json
import pandas as pd

def search_naver_shop(client_id: str, client_secret: str, query: str, display: int = 50):
    url = "https://openapi.naver.com/v1/search/shop.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret
    }
    params = {
        "query": query,
        "display": display,
        "start": 1,
        "sort": "sim"
    }
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        items = data.get("items", [])
        df = pd.DataFrame(items)
        # HTML 태그 제거 (<b> 등)
        if not df.empty and "title" in df.columns:
            df["title"] = df["title"].str.replace("<b>", "").str.replace("</b>", "")
        return df
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")
```

---

## 3. 네이버 검색어 트렌드 API (DataLab Search Trend API)

지정한 기간 동안 특정 검색어(들)의 네이버 검색량 상대 지수를 수집합니다.

### 3.1 엔드포인트 및 메소드
- **URL**: `POST https://openapi.naver.com/v1/datalab/search`
- **Content-Type**: `application/json`

### 3.2 주요 요청 바디 (Request Body JSON)
```json
{
  "startDate": "2024-01-01",
  "endDate": "2024-06-30",
  "timeUnit": "week",
  "keywordGroups": [
    {
      "groupName": "아이폰",
      "keywords": ["아이폰", "iPhone", "아이폰15"]
    },
    {
      "groupName": "갤럭시",
      "keywords": ["갤럭시", "Galaxy", "S24"]
    }
  ],
  "device": "",
  "gender": "",
  "ages": []
}
```

- `timeUnit`: `date` (일간), `week` (주간), `month` (월간)
- `keywordGroups`: 최대 5개 그룹 지정 가능
- `device`: `pc`, `mobile`, `""` (전체)
- `gender`: `m` (남성), `f` (여성), `""` (전체)
- `ages`: `["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]` (10대 미만 ~ 60대 이상)

### 3.3 응답 데이터 구조 (Response Format)
응답 JSON 내 `results[i].data` 배열의 `ratio`는 조회 기간 중 최대 검색량을 **100**으로 기준잡은 상대적 검색 비율입니다.

### 3.4 Python 수집 코드 예시 (Search Trend Example)
```python
import requests
import json
import pandas as pd

def get_search_trend(client_id, client_secret, keywords_list, start_date, end_date, time_unit="week", device="", gender=""):
    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json"
    }
    
    # 키워드 그룹 작성 (최대 5개)
    keyword_groups = []
    for kw in keywords_list[:5]:
        keyword_groups.append({
            "groupName": kw.strip(),
            "keywords": [kw.strip()]
        })
        
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

    response = requests.post(url, headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
    if response.status_code == 200:
        res_json = response.json()
        results = res_json.get("results", [])
        
        records = []
        for group in results:
            g_name = group["title"]
            for item in group["data"]:
                records.append({
                    "period": item["period"],
                    "group": g_name,
                    "ratio": item["ratio"]
                })
        df = pd.DataFrame(records)
        return df
    else:
        raise Exception(f"DataLab API Error {response.status_code}: {response.text}")
```

---

## 4. 네이버 쇼핑 인사이트 API (DataLab Shopping Insight API)

네이버 쇼핑 분야(카테고리) 및 특정 키워드의 기기별, 성별, 연령별 클릭 추이를 제공합니다.

### 4.1 주요 엔드포인트
1. **분야별 클릭 트렌드**: `POST https://openapi.naver.com/v1/datalab/shopping/categories`
2. **분야 내 기기별 트렌드**: `POST https://openapi.naver.com/v1/datalab/shopping/category/device`
3. **분야 내 성별 트렌드**: `POST https://openapi.naver.com/v1/datalab/shopping/category/gender`
4. **분야 내 연령별 트렌드**: `POST https://openapi.naver.com/v1/datalab/shopping/category/age`

### 4.2 주요 요청 파라미터 (Request Body)
```json
{
  "startDate": "2024-01-01",
  "endDate": "2024-06-30",
  "timeUnit": "month",
  "category": "50000000",
  "device": "",
  "gender": "",
  "ages": []
}
```
*대표 카테고리 ID 예시:*
- 패션의류: `50000000`
- 패션잡화: `50000001`
- 화장품/미용: `50000002`
- 디지털/가전: `50000003`
- 가구/인테리어: `50000004`
- 식품: `50000006`
- 스포츠/레저: `50000007`
- 생활/건강: `50000008`

### 4.3 Python 수집 코드 예시 (Shopping Insight Example)
```python
def get_shopping_category_gender(client_id, client_secret, category_code, start_date, end_date, time_unit="month"):
    url = "https://openapi.naver.com/v1/datalab/shopping/category/gender"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json"
    }
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": time_unit,
        "category": category_code
    }
    response = requests.post(url, headers=headers, data=json.dumps(body, ensure_ascii=False).encode('utf-8'))
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Shopping API Error {response.status_code}: {response.text}")
```

---

## 5. EDA 대시보드 구축 요약 (Dashboard Integration Summary)

본 문서의 수집 코드를 바탕으로 구축된 **Streamlit EDA 대시보드**는 다음과 같은 통합 분석 프로세스를 제공합니다:

1. **다중 검색어 파싱**: 사용자가 입력한 `캠핑, 텐트, 글램핑` 등의 쉼표(`,`) 구분 문자열을 파싱하여 최대 5개 검색어 그룹으로 자동 할당합니다.
2. **트렌드 비교 (Trend Comparison)**: 검색어별 시간 경과에 따른 상대 관심도 추이를 선 그래프(Line Chart)로 연동합니다.
3. **소비자 행동 분석 (Consumer Insight)**: 선택한 상품 분야에 대한 기기/성별/연령대별 클릭 지수를 시각화합니다.
4. **상품 & 콘텐츠 검색 (Search Result Distribution)**: 검색어에 해당하는 쇼핑 상품의 가격 분포(Histogram, Boxplot), 브랜드 비중 및 최신 뉴스/블로그 기사를 통합 대시보드에서 조회할 수 있습니다.
