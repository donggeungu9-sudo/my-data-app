from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import requests
import streamlit as st

# 스트림릿 페이지 설정 (와이드 모드)
st.set_page_config(
    page_title="영화진흥위원회 일일 박스오피스", page_icon="🎬", layout="wide"
)

st.title("🎬 어제의 영화 박스오피스 순위")


# API 호출 함수 (1시간 동안 결과를 기억하여 중복 요청 방지)
@st.cache_data(ttl=3600)
def get_box_office_data(target_date, api_key):
  url = (
      "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
  )
  params = {"key": api_key, "targetDt": target_date}

  try:
    response = requests.get(url, params=params)
    data = response.json()
    return data
  except Exception as e:
    return {"error": str(e)}


# 1. 비밀 금고(st.secrets)에서 KOBIS_KEY 불러오기
try:
  API_KEY = st.secrets["KOBIS_KEY"]
except Exception:
  st.error(
      "🚨 비밀 금고(Secrets)에 KOBIS_KEY가 설정되어 있지 않습니다. 스트림릿"
      " 설정에서 키를 등록해 주세요."
  )
  st.stop()

# 2. 서버 시계와 상관없이 '한국 시간(KST)' 기준으로 어제 날짜 계산 (YYYYMMDD 형식)
kst = ZoneInfo("Asia/Seoul")
yesterday = datetime.now(kst) - timedelta(days=1)
target_dt = yesterday.strftime("%Y%m%d")

st.write(
    f"📅 **조회 날짜 (한국 시간 기준 어제):** {yesterday.strftime('%Y년 %m월 %d일')}"
)

# 3. 데이터 가져오기
result = get_box_office_data(target_dt, API_KEY)

# 4. 네트워크 오류 처리
if "error" in result:
  st.error(
      "⚠️ API 요청 중 네트워크 오류가 발생했습니다. 인터넷 연결을 확인하거나"
      " 잠시 후 다시 시도해 주세요."
  )
  st.stop()

# 5. API 내부 오류 상자(faultInfo) 확인
if "faultInfo" in result:
  st.error(f"❌ API 오류 발생: {result['faultInfo']}")
  st.info(
      "💡 확인해 주세요: 스트림릿 Secrets에 등록된 KOBIS_KEY가 올바른지"
      " 확인해 주세요."
  )
  st.stop()

box_office_result = result.get("boxOfficeResult", {})
movie_list = box_office_result.get("dailyBoxOfficeList", [])

# 6. 영화 목록이 비어 있는 경우 처리
if not movie_list:
  st.warning(
      "📭 조회된 영화 데이터가 없습니다. 아직 박스오피스 집계가 끝나지 않았거나"
      " 해당 날짜의 데이터가 없을 수 있습니다."
  )
  st.stop()

# 7. 데이터를 데이터프레임으로 변환 및 정제
df = pd.DataFrame(movie_list)

# 필요한 컬럼만 선택 및 한글 이름으로 변경
df = df[
    [
        "rank",
        "movieNm",
        "openDt",
        "audiCnt",
        "audiAcc",
        "scrnCnt",
        "rankInten",
    ]
]
df.columns = [
    "순위",
    "영화명",
    "개봉일",
    "관객수",
    "누적관객",
    "스크린수",
    "전일대비순위증감",
]

# 문자열로 된 숫자를 실제 숫자형(int)으로 변환 (정렬과 그래프를 위해 필수)
df["순위"] = pd.to_numeric(df["순위"])
df["관객수"] = pd.to_numeric(df["관객수"])
df["누적관객"] = pd.to_numeric(df["누적관객"])
df["스크린수"] = pd.to_numeric(df["스크린수"])

# 순위 순서대로 정렬
df = df.sort_values("순위")


# --- UI 구성: 1위 영화 지표 카드 ---
st.markdown("---")
st.subheader("🏆 어제의 박스오피스 1위 영화")
top_movie = df.iloc[0]

col1, col2, col3 = st.columns(3)
col1.metric(
    label="영화명",
    value=top_movie["영화명"],
    delta=f"순위 변동: {top_movie['전일대비순위증감']}",
)
col2.metric(label="어제 관객수", value=f"{top_movie['관객수']:,} 명")
col3.metric(label="누적 관객수", value=f"{top_movie['누적관객']:,} 명")


# --- UI 구성: 관객수 상위 5편 막대그래프 ---
st.markdown("---")
st.subheader("📊 관객수 상위 5편 영화 비교")
top_5 = df.head(5).set_index("영화명")
st.bar_chart(top_5["관객수"])


# --- UI 구성: 전체 순위 표 ---
st.markdown("---")
st.subheader("📋 전체 박스오피스 순위표")
st.dataframe(df, use_container_width=True)
