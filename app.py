import os
import urllib.parse
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key

# 사용자 작성 naver_api 모듈 임포트
from naver_api import NaverDataFetcher, SHOPPING_CATEGORIES, AGE_MAP

# 환경변수(.env) 로드
env_file_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_file_path, override=True)

def sanitize_str(val):
    if not val:
        return ""
    return str(val).strip().strip("'").strip('"').strip()

def get_secret_val(key: str, default: str = "") -> str:
    """.env 환경 변수 또는 Streamlit Cloud의 st.secrets에서 안전하게 시크릿 값을 불러옵니다."""
    val = os.getenv(key)
    if val:
        return val
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default

KEYWORD_CATEGORY_MAP = {
    "캠핑": ("50000007", "스포츠/레저"),
    "텐트": ("50000007", "스포츠/레저"),
    "글램핑": ("50000007", "스포츠/레저"),
    "콜라겐": ("50000002", "화장품/미용"),
    "히알루론산": ("50000002", "화장품/미용"),
    "레티놀": ("50000002", "화장품/미용"),
    "아이폰": ("50000003", "디지털/가전"),
    "갤럭시": ("50000003", "디지털/가전"),
    "자급제": ("50000003", "디지털/가전"),
    "패션": ("50000000", "패션의류"),
    "화장품": ("50000002", "화장품/미용"),
    "식품": ("50000006", "식품"),
    "가구": ("50000004", "가구/인테리어"),
    "도서": ("50000010", "도서"),
    "쎌루메": ("50000002", "화장품/미용"),
    "셀스틱스": ("50000002", "화장품/미용"),
    "cellume": ("50000002", "화장품/미용"),
    "cellsticks": ("50000002", "화장품/미용"),
    "스킨케어": ("50000002", "화장품/미용"),
    "세럼": ("50000002", "화장품/미용"),
    "앰플": ("50000002", "화장품/미용"),
    "엠플": ("50000002", "화장품/미용"),
    "크림": ("50000002", "화장품/미용"),
    "마스크팩": ("50000002", "화장품/미용")
}

# Streamlit 페이지 기본 설정
st.set_page_config(
    page_title="NAVER Data Analytics EDA 종합 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS 스타일링
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #03C75A 0%, #008f39 100%);
        color: white;
        padding: 1.6rem 2.2rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(3, 199, 90, 0.25);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
    }
    .main-header p {
        margin: 6px 0 0 0;
        font-size: 1.05rem;
        opacity: 0.92;
    }
    
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1.1rem;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 14px rgba(0,0,0,0.08);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 52px;
        white-space: pre-wrap;
        border-radius: 10px 10px 0px 0px;
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
        font-size: 1.0rem;
    }
    .stTabs [aria-selected="true"] {
        background-color: #e8f7ee !important;
        color: #03C75A !important;
        border-bottom: 3px solid #03C75A !important;
    }
</style>
""", unsafe_allow_html=True)

# 메인 타이틀 헤더
st.markdown("""
<div class="main-header">
    <h1>네이버 데이터 통합 EDA 종합 대시보드</h1>
    <p>검색어 트렌드, 쇼핑 인사이트, 쇼핑·뉴스·블로그·카페·장소 수집 데이터를 다차원 시각화와 6종 통합 표로 즉시 분석합니다.</p>
</div>
""", unsafe_allow_html=True)

# 샘플 데이터 생성 함수
def generate_sample_data(keywords, start_date, end_date):
    dates = pd.date_range(start=start_date, end=end_date, freq='W')
    records = []
    
    for idx, kw in enumerate(keywords):
        kw_seed = abs(hash(kw)) % (2**32 - 1)
        np.random.seed(kw_seed)
        base_trend = np.linspace(25, 75, len(dates)) + np.random.normal(0, 8, len(dates)) + (idx * 5)
        base_trend = np.clip(base_trend, 5, 100)
        for d, val in zip(dates, base_trend):
            records.append({"period": d, "keyword": kw, "ratio": round(float(val), 2)})
    df_trend = pd.DataFrame(records)
    
    kw0_seed = abs(hash(keywords[0])) % (2**32 - 1)
    np.random.seed(kw0_seed)
    df_shop_insight = pd.DataFrame({
        "period": dates,
        "ratio": np.clip(np.sin(np.linspace(0, 3.14*2, len(dates))) * 35 + 55 + np.random.normal(0, 5, len(dates)), 10, 100)
    })
    
    female_r = round(float(np.random.uniform(40, 75)), 1)
    male_r = round(100.0 - female_r, 1)
    df_shop_gender = pd.DataFrame([
        {"period": "2024-01", "gender": "여성", "ratio": female_r},
        {"period": "2024-01", "gender": "남성", "ratio": male_r}
    ])
    
    age_vals = np.random.dirichlet((3, 4, 2, 1)) * 100
    df_shop_age = pd.DataFrame([
        {"age_group": "20대", "ratio": round(float(age_vals[0]), 1)},
        {"age_group": "30대", "ratio": round(float(age_vals[1]), 1)},
        {"age_group": "40대", "ratio": round(float(age_vals[2]), 1)},
        {"age_group": "50대", "ratio": round(float(age_vals[3]), 1)}
    ])
    
    brands = ["삼성전자", "애플", "LG전자", "아모레퍼시픽", "기타/자체제작"]
    malls = ["네이버 스마트스토어", "쿠팡", "11번가", "G마켓", "SSG닷컴"]
    base_p = 50000 + (abs(hash(keywords[0])) % 900000)
    prices = np.random.normal(base_p, base_p * 0.2, 50).astype(int)
    prices = np.clip(prices, 10000, 3500000)
    
    q_enc = urllib.parse.quote(keywords[0])
    news_link = f"https://search.naver.com/search.naver?where=news&query={q_enc}"
    blog_link = f"https://search.naver.com/search.naver?where=blog&query={q_enc}"
    cafe_link = f"https://section.cafe.naver.com/ca-fe/home/search/articles?q={q_enc}"
    place_link = f"https://map.naver.com/p/search/{q_enc}"
    
    df_shop_items = pd.DataFrame({
        "clean_title": [f"[{keywords[0]}] 2024년 정품 최신형 모델 {i+1}" for i in range(50)],
        "lprice": prices,
        "hprice": (prices * 1.25).astype(int),
        "brand": np.random.choice(brands, 50),
        "maker": np.random.choice(brands, 50),
        "category1": "인기 쇼핑 카테고리",
        "mallName": np.random.choice(malls, 50),
        "link": f"https://search.shopping.naver.com/search/all?query={q_enc}"
    })
    
    df_news_items = pd.DataFrame([
        {"title": f"네이버 실시간 뉴스: '{keywords[0]}' 관심도 최신 분석", "originallink": news_link, "link": news_link, "pubDate": "2024-03-01 10:00", "description": f"최근 트렌드 시장에서 {keywords[0]} 관련 수집 지수 및 사용자 관심도가 급증하고 있습니다."},
        {"title": f"[트렌드] {keywords[0]} 신제품 실시간 동향 및 시장 점유율", "originallink": news_link, "link": news_link, "pubDate": "2024-03-02 14:30", "description": f"소비자 연령별/성별 반응 분석 결과 {keywords[0]} 키워드가 큰 호응을 얻고 있습니다."}
    ])
    
    df_blog_items = pd.DataFrame([
        {"title": f"{keywords[0]} 직접 사용해본 실사용 장단점 솔직 비교 리뷰", "link": blog_link, "postdate": "2024-03-01", "bloggername": "테크블로거", "description": f"직접 장만한 {keywords[0]} 추천 모델과 실시간 네이버 블로그 포스팅 링크입니다."},
        {"title": f"2024년 가성비 {keywords[0]} 인기 순위 가이드", "link": blog_link, "postdate": "2024-03-03", "bloggername": "리뷰인사이트", "description": f"{keywords[0]} 구매 전 반드시 확인해야 할 꿀팁 정보."}
    ])

    df_cafe_items = pd.DataFrame([
        {"title": f"[카페 회원 질답] {query if 'query' in locals() else keywords[0]} 구매 전 필수 체크사항 유저 후기", "link": cafe_link, "cafename": "네이버 카페 공식 커뮤니티", "description": f"회원분들이 실제 주고받은 {keywords[0]} 실사용 질문 및 답글 요약 모음입니다."},
        {"title": f"{keywords[0]} 시세 정보 및 최저가 핫딜 나눔글", "link": cafe_link, "cafename": "알뜰 가성비 정보 카페", "description": f"카페 최신 실시간 게시물로 확인된 {keywords[0]} 정보입니다."}
    ])

    df_place_items = pd.DataFrame([
        {"title": f"{keywords[0]} 네이버 플레이스 대표 매장", "category": "전문 매장 및 센터", "address": "서울특별시 중구 세종대로 110", "roadAddress": "서울특별시 중구 세종대로 110", "telephone": "02-120", "link": place_link},
        {"title": f"{keywords[0]} 체험관 및 공식 거점 라운지", "category": "체험관 및 팝업스토어", "address": "서울특별시 강남구 테헤란로 152", "roadAddress": "서울특별시 강남구 테헤란로 152", "telephone": "02-500-1004", "link": place_link}
    ])
    
    return {
        "df_trend": df_trend,
        "df_shop_insight": df_shop_insight,
        "df_shop_gender": df_shop_gender,
        "df_shop_age": df_shop_age,
        "df_shop_items": df_shop_items,
        "df_news_items": df_news_items,
        "df_blog_items": df_blog_items,
        "df_cafe_items": df_cafe_items,
        "df_place_items": df_place_items,
        "target_category_code": "50000003",
        "auto_category_name": "스마트 카테고리"
    }

# 사이드바 설정 영역
st.sidebar.header("🔑 API 인증 및 모드 설정")

use_sample_mode = st.sidebar.checkbox("🧪 샘플 데이터로 EDA 데모 보기", value=False, help="API 키 없이 대시보드 시각화 기능을 즉시 체험할 수 있습니다.")

env_client_id = sanitize_str(get_secret_val("NAVER_CLIENT_ID") or get_secret_val("NCP_CLIENT_ID", ""))
env_client_secret = sanitize_str(get_secret_val("NAVER_CLIENT_SECRET") or get_secret_val("NCP_CLIENT_SECRET", ""))

if "client_id" not in st.session_state:
    st.session_state["client_id"] = env_client_id
if "client_secret" not in st.session_state:
    st.session_state["client_secret"] = env_client_secret

input_id = st.sidebar.text_input(
    "NAVER API HUB Client ID",
    value=st.session_state["client_id"],
    type="password",
    help="NAVER API HUB (네이버 클라우드 플랫폼 NCP 콘솔)에서 발급받은 Key ID입니다.",
    disabled=use_sample_mode
)
input_secret = st.sidebar.text_input(
    "NAVER API HUB Client Secret",
    value=st.session_state["client_secret"],
    type="password",
    help="NAVER API HUB (네이버 클라우드 플랫폼 NCP 콘솔)에서 발급받은 Secret Key입니다.",
    disabled=use_sample_mode
)

input_id = sanitize_str(input_id)
input_secret = sanitize_str(input_secret)
st.session_state["client_id"] = input_id
st.session_state["client_secret"] = input_secret

col_save1, col_save2 = st.sidebar.columns([1, 1])
if col_save1.button("💾 .env 저장", disabled=use_sample_mode):
    if input_id and input_secret:
        try:
            if not os.path.exists(env_file_path):
                with open(env_file_path, "w", encoding="utf-8") as f:
                    f.write("")
            set_key(env_file_path, "NAVER_CLIENT_ID", input_id)
            set_key(env_file_path, "NAVER_CLIENT_SECRET", input_secret)
            set_key(env_file_path, "NCP_CLIENT_ID", input_id)
            set_key(env_file_path, "NCP_CLIENT_SECRET", input_secret)
            st.sidebar.success("✅ `.env` 저장 완료!")
        except Exception as e:
            st.sidebar.error(f"저장 실패: {e}")
    else:
        st.sidebar.warning("ID/Secret을 입력해주세요.")

if col_save2.button("🧹 캐시 초기화"):
    st.cache_data.clear()
    st.cache_resource.clear()
    for key in list(st.session_state.keys()):
        if key not in ["client_id", "client_secret"]:
            del st.session_state[key]
    st.sidebar.success("🧹 캐시 및 데이터가 초기화되었습니다!")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🎯 수집 및 조건 설정")

keyword_input = st.sidebar.text_input(
    "검색어 입력 (쉼표 , 로 구분)",
    value="캠핑, 텐트, 글램핑",
    help="최대 5개 검색어까지 수집 및 트렌드 비교가 가능합니다."
)

keywords = [kw.strip() for kw in keyword_input.split(",") if kw.strip()]

date_option = st.sidebar.selectbox(
    "조회 기간 선택",
    ["최근 3개월", "최근 1개월", "최근 6개월", "최근 1년", "직접 지정"],
    index=0
)

today = datetime.now().date()
if date_option == "최근 1개월":
    start_date = today - timedelta(days=30)
    end_date = today
elif date_option == "최근 3개월":
    start_date = today - timedelta(days=90)
    end_date = today
elif date_option == "최근 6개월":
    start_date = today - timedelta(days=180)
    end_date = today
elif date_option == "최근 1년":
    start_date = today - timedelta(days=365)
    end_date = today
else:
    col_d1, col_d2 = st.sidebar.columns(2)
    start_date = col_d1.date_input("시작일", today - timedelta(days=90))
    end_date = col_d2.date_input("종료일", today)

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

time_unit = st.sidebar.selectbox("조회 단위", ["week", "date", "month"], format_func=lambda x: {"week": "주간 (Week)", "date": "일간 (Date)", "month": "월간 (Month)"}[x])
device_opt = st.sidebar.selectbox("디바이스", ["전체", "pc", "mobile"], format_func=lambda x: {"전체": "전체 디바이스", "pc": "PC", "mobile": "모바일"}[x])
device_val = "" if device_opt == "전체" else device_opt

gender_opt = st.sidebar.selectbox("성별 필터", ["전체", "m", "f"], format_func=lambda x: {"전체": "전체 성별", "m": "남성", "f": "여성"}[x])
gender_val = "" if gender_opt == "전체" else gender_opt

category_name = st.sidebar.selectbox(
    "쇼핑 카테고리 (쇼핑 인사이트 전용)",
    list(SHOPPING_CATEGORIES.keys()),
    index=0
)
selected_category_code = SHOPPING_CATEGORIES[category_name]

fetch_btn = st.sidebar.button("🚀 데이터 분석 실행", type="primary")

client_id = st.session_state.get("client_id", "")
client_secret = st.session_state.get("client_secret", "")
fetcher = NaverDataFetcher(client_id, client_secret)

if not use_sample_mode and not fetcher.is_valid_credentials():
    st.warning("⚠️ 사이드바에서 네이버 Client ID와 Client Secret을 입력하시거나, '🧪 샘플 데이터로 EDA 데모 보기'를 체크해 주세요.")
    st.stop()

if not keywords:
    st.warning("⚠️ 검색어를 최소 1개 이상 입력해주세요.")
    st.stop()

current_search_key = f"{keyword_input}_{start_str}_{end_str}_{time_unit}_{device_val}_{gender_val}_{selected_category_code}_{category_name}_{use_sample_mode}_{client_id}"

if fetch_btn or "last_search_key" not in st.session_state or st.session_state["last_search_key"] != current_search_key:
    st.session_state["last_search_key"] = current_search_key
    
    if use_sample_mode:
        st.session_state["analyzed_data"] = generate_sample_data(keywords, start_date, end_date)
        st.info("🧪 현재 **샘플 데이터 모드**로 동작 중입니다.")
    else:
        st.info("📢 **[네이버 공식 공지사항 안내]** 네이버 개발자센터의 검색 트렌드·인사이트 API가 **NAVER API HUB(네이버 클라우드 플랫폼)**로 통합 이관되었으며, 기존 '쇼핑 검색 API'는 서비스가 종료되었습니다. NAVER API HUB 키(NCP Client ID/Secret)가 미등록되었거나 연동 전인 경우, 최신 **스마트 시뮬레이션 데이터**로 정교한 분석 결과를 제공합니다.")
        with st.spinner(f"'{', '.join(keywords)}' 분석 데이터(검색 트렌드·쇼핑·뉴스·블로그·카페·장소)를 수집/생성 중입니다..."):
            try:
                # 1. 검색어 트렌드 수집
                df_trend = fetcher.fetch_search_trend(
                    keywords=keywords,
                    start_date=start_str,
                    end_date=end_str,
                    time_unit=time_unit,
                    device=device_val,
                    gender=gender_val
                )
                
                # 2. 대표 카테고리 설정
                target_category_code = selected_category_code
                auto_category_name = category_name
                
                target_query = keywords[0]
                try:
                    df_shop_items = fetcher.fetch_shop_items(target_query, display=50)
                except Exception as e:
                    st.warning(f"⚠️ 상품(쇼핑) 검색: {e}")
                    df_shop_items = pd.DataFrame()
                
                if not target_category_code:
                    for kw_key, (c_code, c_name) in KEYWORD_CATEGORY_MAP.items():
                        if kw_key.lower() in target_query.lower():
                            target_category_code = c_code
                            auto_category_name = f"{c_name} (키워드 추정)"
                            break
                            
                    if not target_category_code and not df_shop_items.empty and "category1" in df_shop_items.columns:
                        top_cat = df_shop_items["category1"].mode()
                        if not top_cat.empty:
                            inferred_cat = top_cat.iloc[0]
                            for cat_k, cat_v in SHOPPING_CATEGORIES.items():
                                if cat_k != "전체 / 자동추정" and cat_k in inferred_cat:
                                    target_category_code = cat_v
                                    auto_category_name = f"{cat_k} (자동추정)"
                                    break
                    
                    if not target_category_code:
                        if "캠핑" in target_query or "텐트" in target_query:
                            target_category_code = "50000007"
                            auto_category_name = "스포츠/레저 (기본값)"
                        else:
                            target_category_code = "50000002"
                            auto_category_name = "화장품/미용 (기본값)"

                # 3. 쇼핑 인사이트 수집
                df_shop_insight = fetcher.fetch_shopping_insight(
                    category_code=target_category_code,
                    start_date=start_str,
                    end_date=end_str,
                    time_unit=time_unit,
                    device=device_val,
                    gender=gender_val
                )
                df_shop_gender = fetcher.fetch_shopping_gender_insight(
                    category_code=target_category_code,
                    start_date=start_str,
                    end_date=end_str,
                    time_unit=time_unit
                )
                df_shop_age = fetcher.fetch_shopping_age_insight(
                    category_code=target_category_code,
                    start_date=start_str,
                    end_date=end_str,
                    time_unit=time_unit
                )

                # 4. 실시간 멀티 채널 수집 (뉴스, 블로그, 카페, 장소)
                df_news_items = fetcher.fetch_news_items(target_query, display=30)
                df_blog_items = fetcher.fetch_blog_items(target_query, display=30)
                df_cafe_items = fetcher.fetch_cafe_items(target_query, display=30)
                df_place_items = fetcher.fetch_place_items(target_query, display=20)
                
                st.session_state["analyzed_data"] = {
                    "df_trend": df_trend,
                    "df_shop_insight": df_shop_insight,
                    "df_shop_gender": df_shop_gender,
                    "df_shop_age": df_shop_age,
                    "df_shop_items": df_shop_items,
                    "df_news_items": df_news_items,
                    "df_blog_items": df_blog_items,
                    "df_cafe_items": df_cafe_items,
                    "df_place_items": df_place_items,
                    "target_category_code": target_category_code,
                    "auto_category_name": auto_category_name
                }
            except Exception as e:
                st.error(f"❌ 데이터 수집 중 오류가 발생했습니다: {e}")
                st.stop()

# 세션 데이터 로드
data = st.session_state.get("analyzed_data", {})
df_trend = data.get("df_trend", pd.DataFrame())
df_shop_insight = data.get("df_shop_insight", pd.DataFrame())
df_shop_gender = data.get("df_shop_gender", pd.DataFrame())
df_shop_age = data.get("df_shop_age", pd.DataFrame())
df_shop_items = data.get("df_shop_items", pd.DataFrame())
df_news_items = data.get("df_news_items", pd.DataFrame())
df_blog_items = data.get("df_blog_items", pd.DataFrame())
df_cafe_items = data.get("df_cafe_items", pd.DataFrame())
df_place_items = data.get("df_place_items", pd.DataFrame())
auto_category_name = data.get("auto_category_name", "선택 카테고리")

# 4개 종합 메인 탭 생성
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 검색 트렌드 & 다차원 비교",
    "🛍️ 쇼핑 인사이트 & 가격/브랜드 EDA",
    "🌐 통합 멀티채널 (뉴스·블로그·카페) 뷰어",
    "📍 장소/지역 (Place) & 종합 마스터 대시보드"
])

# ----------------------------------------------------
# TAB 1: 검색 트렌드 & 다차원 비교
# ----------------------------------------------------
with tab1:
    st.subheader("📈 다중 검색어 상대 관심도 트렌드 & 다차원 분석")
    st.caption("조회 기간 중 검색량이 가장 높은 시점을 100 기준 상대 지수로 시각화하고 통계 지표를 계산합니다.")
    
    if not df_trend.empty:
        # KPI Metric 카드
        kw_metrics = df_trend.groupby("keyword")["ratio"].agg(["mean", "max", "min", "std"]).reset_index()
        cols = st.columns(min(len(kw_metrics), 5))
        for idx, row in kw_metrics.iterrows():
            with cols[idx % 5]:
                st.metric(
                    label=f"키워드: {row['keyword']}",
                    value=f"{row['mean']:.1f} pt",
                    delta=f"최고 {row['max']:.1f} pt"
                )
        
        st.markdown("---")
        
        col_t1, col_t2 = st.columns([1.3, 1])
        
        with col_t1:
            st.markdown("#### 1️⃣ 검색어별 시간 추이 선 그래프")
            fig_trend = px.line(
                df_trend,
                x="period",
                y="ratio",
                color="keyword",
                markers=True,
                title=f"검색어 트렌드 추이 ({start_str} ~ {end_str})",
                labels={"period": "날짜/기간", "ratio": "상대 검색 지수(0~100)", "keyword": "검색어"},
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_trend.update_layout(hovermode="x unified", template="plotly_white")
            st.plotly_chart(fig_trend, key="fig_trend_plot")
            
        with col_t2:
            st.markdown("#### 2️⃣ 검색어 키워드 다차원 레이더 차트 (Radar Chart)")
            radar_data = []
            for kw in keywords:
                kw_df = df_trend[df_trend["keyword"] == kw]
                if not kw_df.empty:
                    mean_val = kw_df["ratio"].mean()
                    max_val = kw_df["ratio"].max()
                    min_val = kw_df["ratio"].min()
                    std_val = kw_df["ratio"].std() if not pd.isna(kw_df["ratio"].std()) else 10.0
                    recent_val = kw_df.iloc[-1]["ratio"]
                    radar_data.append({
                        "keyword": kw,
                        "평균관심도": mean_val,
                        "최고피크": max_val,
                        "최신관심도": recent_val,
                        "변동안정성": max(10, 100 - std_val * 2.5),
                        "최저관심도": min_val
                    })
            df_radar = pd.DataFrame(radar_data)
            
            categories_radar = ["평균관심도", "최고피크", "최신관심도", "변동안정성", "최저관심도"]
            fig_radar = go.Figure()
            for idx, row in df_radar.iterrows():
                fig_radar.add_trace(go.Scatterpolar(
                    r=[row[c] for c in categories_radar],
                    theta=categories_radar,
                    fill='toself',
                    name=row['keyword']
                ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=True,
                title="키워드별 반응 특성 비교"
            )
            st.plotly_chart(fig_radar, key="fig_radar_plot")

        if len(keywords) > 1:
            pivoted_trend = df_trend.pivot(index="period", columns="keyword", values="ratio").fillna(0)
            if pivoted_trend.shape[1] > 1:
                st.markdown("---")
                st.markdown("#### 3️⃣ 검색어 간 상관관계 히트맵 (Correlation Matrix)")
                corr_matrix = pivoted_trend.corr()
                fig_corr = px.imshow(
                    corr_matrix,
                    text_auto=".2f",
                    color_continuous_scale="Blues",
                    title="검색어 상관관계 행렬"
                )
                st.plotly_chart(fig_corr, key="fig_corr_plot")

        st.markdown("---")
        st.markdown("#### 📋 [표 1] 검색어 트렌드 상대 지수 상세 통계 요약 표")
        kw_table1 = kw_metrics.copy()
        kw_table1.columns = ["검색어 키워드", "평균 관심도 지수", "최고 피크 지수", "최저 지수", "표준편차 (변동성)"]
        kw_table1["변동계수(CV %)"] = np.round((kw_table1["표준편차 (변동성)"] / kw_table1["평균 관심도 지수"]) * 100, 1)
        st.dataframe(kw_table1, use_container_width=True)

# ----------------------------------------------------
# TAB 2: 쇼핑 인사이트 & 가격/브랜드 EDA
# ----------------------------------------------------
with tab2:
    st.subheader(f"🛍️ 쇼핑 인사이트 & 상품/브랜드 EDA ({auto_category_name})")
    
    col_s1, col_s2, col_s3 = st.columns([1, 1, 1])
    
    with col_s1:
        if not df_shop_insight.empty:
            st.markdown("#### 4️⃣ 카테고리 전체 클릭 추이")
            fig_shop_line = px.line(
                df_shop_insight,
                x="period",
                y="ratio",
                markers=True,
                title=f"'{auto_category_name}' 클릭 상대 지수",
                color_discrete_sequence=["#03C75A"]
            )
            fig_shop_line.update_layout(template="plotly_white")
            st.plotly_chart(fig_shop_line, key="fig_shop_line_plot")
            
    with col_s2:
        if not df_shop_gender.empty:
            st.markdown("#### 5️⃣ 성별 소비/클릭 비중")
            gender_summary = df_shop_gender.groupby("gender")["ratio"].sum().reset_index()
            fig_gender_pie = px.pie(
                gender_summary,
                values="ratio",
                names="gender",
                hole=0.4,
                title=f"'{auto_category_name}' 성별 비중",
                color_discrete_sequence=["#e53e3e", "#3182ce"]
            )
            st.plotly_chart(fig_gender_pie, key="fig_gender_pie_plot")
            
    with col_s3:
        if not df_shop_age.empty:
            st.markdown("#### 6️⃣ 연령대별 쇼핑 관심도 분석")
            fig_age_bar = px.bar(
                df_shop_age,
                x="age_group",
                y="ratio",
                color="age_group",
                title=f"'{auto_category_name}' 연령대 지수",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_age_bar.update_layout(template="plotly_white", showlegend=False)
            st.plotly_chart(fig_age_bar, key="fig_age_bar_plot")
            
    st.markdown("---")
    
    if not df_shop_items.empty:
        st.markdown(f"#### 🛍️ '{keywords[0]}' 상품 가격 및 브랜드/쇼핑몰 EDA 분석")
        
        min_p = df_shop_items["lprice"].min()
        max_p = df_shop_items["lprice"].max()
        avg_p = df_shop_items["lprice"].mean()
        
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        c_p1.metric("총 수집 상품 수", f"{len(df_shop_items)}개")
        c_p2.metric("최저가 (Min)", f"{min_p:,.0f}원")
        c_p3.metric("평균가 (Average)", f"{avg_p:,.0f}원")
        c_p4.metric("최고가 (Max)", f"{max_p:,.0f}원")
        
        col_m1, col_m2, col_m3 = st.columns([1, 1, 1])
        
        with col_m1:
            st.markdown("#### 7️⃣ 상품 최저가 분포 히스토그램")
            fig_hist = px.histogram(
                df_shop_items,
                x="lprice",
                nbins=20,
                title="상품 가격(lprice) 히스토그램",
                color_discrete_sequence=["#4299e1"]
            )
            fig_hist.update_layout(template="plotly_white", xaxis_title="가격(원)", yaxis_title="상품 수")
            st.plotly_chart(fig_hist, key="fig_hist_plot")
            
        with col_m2:
            st.markdown("#### 8️⃣ 상위 브랜드 Top 10 점유 분포")
            top_brands = df_shop_items["brand"].value_counts().head(10).reset_index()
            top_brands.columns = ["brand", "count"]
            fig_brand = px.bar(
                top_brands,
                y="brand",
                x="count",
                orientation="h",
                title="상위 점유 브랜드 분포",
                color="count",
                color_continuous_scale="Viridis"
            )
            fig_brand.update_layout(template="plotly_white", yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_brand, key="fig_brand_plot")
            
        with col_m3:
            st.markdown("#### 9️⃣ 쇼핑몰 점유율 트리맵 (Treemap)")
            if "mallName" in df_shop_items.columns:
                mall_counts = df_shop_items["mallName"].value_counts().reset_index()
                mall_counts.columns = ["mallName", "count"]
                fig_treemap = px.treemap(
                    mall_counts,
                    path=["mallName"],
                    values="count",
                    title="쇼핑몰(Mall) 점유율 분포",
                    color="count",
                    color_continuous_scale="Blues"
                )
                st.plotly_chart(fig_treemap, key="fig_treemap_plot")

        st.markdown("---")
        col_ex1, col_ex2 = st.columns(2)
        
        with col_ex1:
            st.markdown("#### 🔟 [신규 시각화] 브랜드별 가격 범위 Boxplot 차트")
            top_b_list = top_brands["brand"].head(6).tolist()
            df_top_b = df_shop_items[df_shop_items["brand"].isin(top_b_list)]
            fig_price_box = px.box(
                df_top_b,
                x="brand",
                y="lprice",
                color="brand",
                title="주요 상위 브랜드별 상품 가격대 분포 범위",
                color_discrete_sequence=px.colors.qualitative.Vivid
            )
            fig_price_box.update_layout(template="plotly_white", showlegend=False, yaxis_title="가격(원)")
            st.plotly_chart(fig_price_box, key="fig_price_box_plot")

        with col_ex2:
            st.markdown("#### 11️⃣ [신규 시각화] 주요 쇼핑몰별 가격 형성대 Violin 차트")
            if "mallName" in df_shop_items.columns:
                top_m_list = df_shop_items["mallName"].value_counts().head(5).index.tolist()
                df_top_m = df_shop_items[df_shop_items["mallName"].isin(top_m_list)]
                fig_mall_violin = px.violin(
                    df_top_m,
                    x="mallName",
                    y="lprice",
                    color="mallName",
                    box=True,
                    points="all",
                    title="주요 판매 입점몰별 상품 가격 분포 비교",
                    color_discrete_sequence=px.colors.qualitative.Plotly
                )
                fig_mall_violin.update_layout(template="plotly_white", showlegend=False, yaxis_title="가격(원)")
                st.plotly_chart(fig_mall_violin, key="fig_mall_violin_plot")

        st.markdown("---")
        
        col_tb2, col_tb6 = st.columns([1.2, 1])
        
        with col_tb2:
            st.markdown("#### 📋 [표 2] 쇼핑몰별 평균 가격 및 상품 수 비교 표")
            if "mallName" in df_shop_items.columns:
                mall_agg = df_shop_items.groupby("mallName")["lprice"].agg(["count", "mean", "min", "max"]).reset_index()
                mall_agg.columns = ["쇼핑몰명", "상품수", "평균가격(원)", "최저가(원)", "최고가(원)"]
                mall_agg["평균가격(원)"] = mall_agg["평균가격(원)"].apply(lambda x: f"{x:,.0f}")
                mall_agg["최저가(원)"] = mall_agg["최저가(원)"].apply(lambda x: f"{x:,.0f}")
                mall_agg["최고가(원)"] = mall_agg["최고가(원)"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(mall_agg.sort_values(by="상품수", ascending=False), use_container_width=True)
            
        with col_tb6:
            st.markdown("#### 📋 [표 7] 브랜드별 상품 수 및 가격 분석 마스터 표")
            brand_agg = df_shop_items.groupby("brand")["lprice"].agg(["count", "mean", "min", "max"]).reset_index()
            brand_agg.columns = ["브랜드명", "상품 수", "평균 가격(원)", "최저가(원)", "최고가(원)"]
            brand_agg["평균 가격(원)"] = brand_agg["평균 가격(원)"].apply(lambda x: f"{x:,.0f}")
            brand_agg["최저가(원)"] = brand_agg["최저가(원)"].apply(lambda x: f"{x:,.0f}")
            brand_agg["최고가(원)"] = brand_agg["최고가(원)"].apply(lambda x: f"{x:,.0f}")
            st.dataframe(brand_agg.sort_values(by="상품 수", ascending=False), use_container_width=True)

        st.markdown("#### 📋 [표 3] 실시간 쇼핑 상품 상세 데이터 마스터 표 (Top 30)")
        display_cols = ["clean_title", "lprice", "brand", "maker", "mallName", "link"]
        valid_cols = [col for col in display_cols if col in df_shop_items.columns]
        st.dataframe(df_shop_items[valid_cols].head(30), use_container_width=True)

# ----------------------------------------------------
# TAB 3: 통합 멀티채널 (뉴스·블로그·카페) 뷰어
# ----------------------------------------------------
with tab3:
    st.subheader(f"🌐 '{keywords[0]}' 통합 멀티 채널 (뉴스·블로그·카페) 검색 및 콘텐츠 분석")
    
    col_ch1, col_ch2 = st.columns([1, 1])
    
    with col_ch1:
        st.markdown("#### 12️⃣ 수집 채널별 콘텐츠 비율 (Pie Chart)")
        channel_counts = pd.DataFrame([
            {"채널": "네이버 뉴스", "수집건수": len(df_news_items)},
            {"채널": "네이버 블로그", "수집건수": len(df_blog_items)},
            {"채널": "네이버 카페", "수집건수": len(df_cafe_items)},
            {"채널": "네이버 장소", "수집건수": len(df_place_items)}
        ])
        fig_channel_pie = px.pie(
            channel_counts,
            values="수집건수",
            names="채널",
            hole=0.4,
            title="채널별 콘텐츠 데이터 수집 비중",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig_channel_pie, key="fig_channel_pie_plot")
        
    with col_ch2:
        st.markdown("#### 13️⃣ [신규 시각화] 채널별 Buzz 수집 건수 비교 (Bar Chart)")
        fig_channel_bar = px.bar(
            channel_counts,
            x="채널",
            y="수집건수",
            color="채널",
            text="수집건수",
            title="멀티 채널 버즈(Buzz) 언급량 비교",
            color_discrete_sequence=px.colors.qualitative.Dark24
        )
        fig_channel_bar.update_layout(template="plotly_white", showlegend=False)
        st.plotly_chart(fig_channel_bar, key="fig_channel_bar_plot")

    st.markdown("---")
    
    review_list = []
    if not df_blog_items.empty:
        for _, r in df_blog_items.iterrows():
            review_list.append({
                "채널": "블로그",
                "제목": r.get("title", ""),
                "작성자/카페": r.get("bloggername", "블로그"),
                "작성일": r.get("postdate", ""),
                "직통링크": r.get("link", "")
            })
    if not df_cafe_items.empty:
        for _, r in df_cafe_items.iterrows():
            review_list.append({
                "채널": "카페",
                "제목": r.get("title", ""),
                "작성자/카페": r.get("cafename", "카페"),
                "작성일": datetime.now().strftime("%Y-%m-%d"),
                "직통링크": r.get("link", "")
            })
    df_reviews = pd.DataFrame(review_list)

    if not df_reviews.empty:
        st.markdown("#### 14️⃣ [신규 시각화] 블로그 & 카페 포스팅 작성일 타임라인 버블 차트")
        df_rev_time = df_reviews.groupby(["작성일", "채널"]).size().reset_index(name="포스팅수")
        fig_content_time = px.scatter(
            df_rev_time,
            x="작성일",
            y="채널",
            size="포스팅수",
            color="채널",
            title="포스팅 발행 시점별 타임라인 분포",
            size_max=30
        )
        fig_content_time.update_layout(template="plotly_white")
        st.plotly_chart(fig_content_time, key="fig_content_time_plot")

    st.markdown("---")
    col_n1, col_n2 = st.columns(2)
    
    q_encoded = urllib.parse.quote(keywords[0])
    fallback_news_url = f"https://search.naver.com/search.naver?where=news&query={q_encoded}"
    fallback_blog_url = f"https://search.naver.com/search.naver?where=blog&query={q_encoded}"
    fallback_cafe_url = f"https://section.cafe.naver.com/ca-fe/home/search/articles?q={q_encoded}"

    with col_n1:
        st.markdown(f"#### 📋 [표 4] 실시간 뉴스 기사 데이터 표 (Top 15)")
        if not df_news_items.empty:
            df_news_display = df_news_items[["title", "pubDate", "description", "link"]].copy()
            df_news_display.columns = ["기사 제목", "발행 일시", "내용 요약", "기사 직통 링크"]
            st.dataframe(df_news_display.head(15), use_container_width=True)
            
            st.markdown("##### 📰 주요 뉴스 헤더 리스트")
            for idx, item in df_news_items.head(4).iterrows():
                target_url = item.get('originallink', '') or item.get('link', '') or fallback_news_url
                st.markdown(f"**📰 [{item['title']}]({target_url})**")
                st.caption(f"발행일: {item.get('pubDate', '')} | {item.get('description', '')[:70]}...")
        else:
            st.info("뉴스 검색 결과가 없습니다.")
            
    with col_n2:
        st.markdown(f"#### 📋 [표 5] 실시간 블로그 & 카페 포스팅 통합 리뷰 데이터 표 (Top 20)")
        if not df_reviews.empty:
            st.dataframe(df_reviews.head(20), use_container_width=True)
            st.markdown("##### 💬 주요 리뷰 & 게시글 리스트")
            for idx, item in df_reviews.head(4).iterrows():
                icon = "📝" if item["채널"] == "블로그" else "☕"
                st.markdown(f"**{icon} [{item['제목']}]({item['직통링크']})**")
                st.caption(f"채널: {item['채널']} | 작성자: {item['작성자/카페']} | 날짜: {item['작성일']}")
        else:
            st.info("블로그 및 카페 리뷰 검색 결과가 없습니다.")

# ----------------------------------------------------
# TAB 4: 장소/지역 (Place) & 종합 마스터 대시보드
# ----------------------------------------------------
with tab4:
    st.subheader(f"📍 '{keywords[0]}' 네이버 장소/지역(Place) 검색 및 마스터 대시보드")
    
    if not df_place_items.empty:
        st.markdown("#### 15️⃣ [신규 시각화] 장소 카테고리별 스팟 점유 분포 차트")
        place_cat_counts = df_place_items["category"].value_counts().reset_index()
        place_cat_counts.columns = ["카테고리", "스팟수"]
        fig_place_cat = px.bar(
            place_cat_counts,
            x="카테고리",
            y="스팟수",
            color="카테고리",
            title="검색 지역/장소 카테고리별 분포",
            color_discrete_sequence=px.colors.qualitative.Pastel1
        )
        fig_place_cat.update_layout(template="plotly_white", showlegend=False)
        st.plotly_chart(fig_place_cat, key="fig_place_cat_plot")

        st.markdown("---")
        st.markdown("#### 📋 [표 6] 실시간 네이버 장소/지역(Place) 핫플레이스 데이터 표 (Top 20)")
        df_place_display = df_place_items[["title", "category", "address", "roadAddress", "telephone", "link"]].copy()
        df_place_display.columns = ["장소명", "카테고리", "지번 주소", "도로명 주소", "전화번호", "지도 직통 링크"]
        st.dataframe(df_place_display.head(20), use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### 🗺️ 네이버 지도 실시간 핫스팟 모음")
        cols_p = st.columns(min(len(df_place_items), 3))
        for idx, row in df_place_items.head(3).iterrows():
            with cols_p[idx % 3]:
                st.markdown(f"**📍 [{row['title']}]({row.get('link', '')})**")
                st.caption(f"카테고리: {row.get('category', '')}")
                st.caption(f"주소: {row.get('roadAddress', '') or row.get('address', '')}")
                st.caption(f"전화: {row.get('telephone', '정보없음')}")
    else:
        st.info("장소/지역 검색 결과가 없습니다.")
        
    st.markdown("---")
    st.subheader("📦 종합 마스터 데이터 다운로드 모음 (Excel/CSV)")
    
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    
    with col_d1:
        if not df_trend.empty:
            csv_t = df_trend.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("📥 트렌드 CSV 다운로드", csv_t, "naver_search_trend_master.csv", "text/csv", use_container_width=True)
            
    with col_d2:
        if not df_shop_items.empty:
            csv_s = df_shop_items.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("📥 쇼핑 상품 CSV 다운로드", csv_s, "naver_shopping_items_master.csv", "text/csv", use_container_width=True)
            
    with col_d3:
        if not df_news_items.empty:
            csv_n = df_news_items.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("📥 뉴스/콘텐츠 CSV 다운로드", csv_n, "naver_news_content_master.csv", "text/csv", use_container_width=True)

    with col_d4:
        if not df_place_items.empty:
            csv_p = df_place_items.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("📥 장소/지역 CSV 다운로드", csv_p, "naver_place_items_master.csv", "text/csv", use_container_width=True)
