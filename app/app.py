# ============================================================
# app.py
#
# 이 파일은 "웹사이트 화면 하나"를 만드는 코드예요.
# Streamlit이라는 도구를 쓰면, 파이썬 코드만으로
# 버튼/그래프/표가 있는 웹페이지를 만들 수 있어요.
#
# 이 화면(S-01, 첫 화면)에서 보여주는 것:
# 1. 전국에 등록된 자동차 총 대수
# 2. 차종(승용/승합/화물 등)별 등록현황
# 3. 지역별 상위 등록현황
# 4. 연료(휘발유/전기 등)별 상위 등록현황
# 5. 사용자가 원하는 자동차 모델을 검색하는 기능
# ============================================================

from pathlib import Path
# Path: 컴퓨터 안의 "파일이 있는 위치(경로)"를 다루기 쉽게 해주는 도구예요.

import re
# re: 문자열에서 특정 패턴(예: 특수문자)을 찾아 바꾸거나 지울 때 쓰는 도구예요.

import unicodedata
# unicodedata: 같은 글자라도 컴퓨터 내부적으로 다르게 저장될 수 있는데,
# 이를 "같은 모양"으로 통일해주는 도구예요. (검색이 잘 되게 하기 위함)

import pandas as pd
# pandas: 엑셀표 같은 데이터(CSV 파일 등)를 읽고 다루는 도구예요.
# 앞으로 "pd.무언가" 형태로 사용해요.

import altair as alt
# altair: 막대그래프, 선그래프 같은 "그림(차트)"을 그리는 도구예요.

import streamlit as st
# streamlit: 이 코드 전체를 웹페이지로 보여주는 도구예요.
# "st.무언가"라고 쓰면 화면에 글자/버튼/그래프가 나타나요.


# ============================================================
# 1. 웹페이지의 기본 설정 (브라우저 탭 이름, 아이콘 등)
# ============================================================
st.set_page_config(
    page_title="자동차 등록·판매·안전정보",  # 브라우저 탭에 표시될 제목
    page_icon="🚗",                          # 브라우저 탭에 표시될 아이콘(이모지)
    layout="wide",                            # 화면을 좌우로 넓게 사용하겠다는 뜻
)


# ============================================================
# 2. 데이터 파일(CSV)이 어디 있는지 "주소"를 만들어두는 부분
#    (실제로 파일을 읽는 건 아니고, 위치만 계산해두는 것)
# ============================================================

# 지금 이 app.py 파일은 "프로젝트폴더/app/app.py"에 있다고 가정해요.
# .parents[1] 은 "한 단계 위 폴더로 올라가라"는 뜻 → 프로젝트 최상위 폴더가 됨
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 프로젝트 최상위 폴더 안의 data/processed 폴더 (정리된 데이터가 있는 곳)
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# 자동차 등록현황 데이터가 들어있는 CSV 파일 경로
REGISTRATION_PATH = PROCESSED_DIR / "registration_summary.csv"

# 자동차 "모델 이름 검색"에 쓰이는 매핑표 CSV 파일 경로
MODEL_MAPPING_PATH = PROCESSED_DIR / "model_mapping.csv"


# ============================================================
# 3. CSV 파일을 실제로 읽어오는 부분
# ============================================================

# @st.cache_data 는 "한 번 계산한 결과를 기억해두는" 기능이에요.
# Streamlit은 사용자가 버튼을 누르거나 글자를 입력할 때마다
# 이 파일 전체를 처음부터 다시 실행하는데,
# 매번 CSV 파일을 다시 읽으면 느려지니까
# "이미 읽은 적 있으면 다시 읽지 말고 저장해둔 걸 써라"라고 알려주는 거예요.
@st.cache_data
def load_data():
    # 등록현황 CSV 읽기 (encoding="utf-8-sig"는 한글 깨짐 방지용 설정)
    registration = pd.read_csv(REGISTRATION_PATH, encoding="utf-8-sig")

    # 모델 매핑 CSV 읽기
    model_mapping = pd.read_csv(MODEL_MAPPING_PATH, encoding="utf-8-sig")

    # 두 개의 표(데이터)를 동시에 돌려줌
    return registration, model_mapping


# 위에서 만든 함수를 실제로 실행해서, 결과를 두 변수에 담아요.
registration_df, model_mapping_df = load_data()


# ============================================================
# 4. 사용자가 입력한 검색어를 "깔끔하게 정리"하는 함수
# ============================================================
def normalize_search_text(value):
    """
    사람마다 자동차 모델명을 다르게 입력할 수 있어요.
    예: "K5(DL3)" / "k5 dl3" / "K5-DL3"
    이런 걸 전부 "k5 dl3" 처럼 같은 모양으로 맞춰줘야
    검색이 제대로 돼요. 그 역할을 하는 함수예요.
    """

    # 글자 모양을 통일하고, 대문자를 소문자로 바꾸고, 앞뒤 공백을 제거
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()

    # 괄호 문자들을 공백으로 바꿈 (예: "(dl3)" → " dl3 ")
    text = re.sub(r"[()\[\]{}]", " ", text)

    # 하이픈(-), 언더바(_), 슬래시(/)를 공백으로 바꿈
    text = re.sub(r"[-_/]", " ", text)

    # 숫자, 영어 소문자, 한글, 공백을 제외한 나머지 특수문자는 전부 공백으로 바꿈
    text = re.sub(r"[^0-9a-z가-힣\s]", " ", text)

    # 공백이 여러 번 연속되면 하나로 합침 (예: "k5   dl3" → "k5 dl3")
    text = re.sub(r"\s+", " ", text)

    # 맨 앞/맨 뒤 공백을 한번 더 제거해서 최종 결과 반환
    return text.strip()


# ============================================================
# 5. 전체 데이터 중에서 "가장 최근 달"의 데이터만 골라내기
# ============================================================

# CSV에는 여러 연도/월의 데이터가 섞여 있을 수 있어요.
# 그래서 "연도 * 100 + 월" 이라는 숫자를 만들어서 비교하기 쉽게 해요.
# 예: 2026년 7월 → 2026 * 100 + 7 = 202607
# 이렇게 하면 숫자가 클수록 더 최근 데이터라는 뜻이 돼요.
registration_df["_snapshot_key"] = (
    registration_df["stat_year"].fillna(0).astype(int) * 100
    + registration_df["stat_month"].fillna(0).astype(int)
)

# 방금 만든 숫자 중에서 가장 큰 값 = 가장 최근 시점
latest_key = registration_df["_snapshot_key"].max()

# 가장 최근 시점에 해당하는 행(데이터)들만 따로 뽑아냄
latest_df = registration_df[registration_df["_snapshot_key"] == latest_key].copy()

# 화면에 보여줄 "최근 연도"와 "최근 월"을 숫자로 꺼내옴
latest_year = int(latest_df["stat_year"].iloc[0])
latest_month = int(latest_df["stat_month"].iloc[0])

# 화면에 "2026-07" 같은 형태로 보여줄 문자열을 만듦
# :02d 는 "한 자리 숫자면 앞에 0을 붙여라"는 뜻 (7 → 07)
snapshot_label = f"{latest_year}-{latest_month:02d}"


# ============================================================
# 6. 최신 데이터를 "종류별로" 나누기
#    (전체 데이터 안에는 여러 종류가 섞여 있어서 구분이 필요함)
# ============================================================

# dimension_type 컬럼 값이 "TOTAL"인 것 = 전국 총합 데이터
total_df = latest_df[latest_df["dimension_type"] == "TOTAL"].copy()

# "REGION"인 것 = 지역별(서울/경기 등) 데이터
region_df = latest_df[latest_df["dimension_type"] == "REGION"].copy()

# "VEHICLE_TYPE"인 것 = 차종별(승용/화물 등) 데이터
vehicle_df = latest_df[latest_df["dimension_type"] == "VEHICLE_TYPE"].copy()

# "FUEL"인 것 = 연료별(휘발유/전기 등) 데이터
fuel_df = latest_df[latest_df["dimension_type"] == "FUEL"].copy()


# ============================================================
# 7. 화면 맨 위에 보여줄 제목과 설명 글
# ============================================================
st.title("🚗 자동차 등록·판매·안전정보 통합 조회")  # 큰 제목

st.write(  # 일반 문단 텍스트
    "국내 자동차 시장의 등록현황과 "
    "주요 현대·기아 모델의 판매·결함신고·리콜 정보를 "
    "한곳에서 확인합니다."
)

st.divider()  # 화면에 구분선(가로줄) 하나 그어주는 것


# ============================================================
# 8. "전국 자동차 등록대수" 보여주기
# ============================================================
st.subheader("전국 자동차 등록현황")  # 작은 소제목

# 이 데이터가 몇 년 몇 월 기준인지 작은 글씨로 안내
st.caption(f"최신 등록현황 기준: {snapshot_label}")

# 혹시 TOTAL 데이터가 하나도 없다면(=파일 문제 등) 에러 메시지를 보여줌
if total_df.empty:
    st.error("전국 등록대수를 불러오지 못했습니다.")

else:
    # 전국 등록대수 숫자를 하나 꺼내옴
    national_total = int(total_df.iloc[0]["registration_count"])

    # st.metric = 큰 숫자 카드 형태로 보여주는 위젯
    # ":," 는 "1000 단위마다 콤마(,) 찍어라"는 뜻 → 1234567 → 1,234,567
    st.metric(label="전국 자동차 등록대수", value=f"{national_total:,}대")


# ============================================================
# 9. "차종별 등록현황" 카드들 보여주기 (승용/승합/화물/특수 등)
# ============================================================
st.subheader("차종별 등록현황")

# 등록대수가 많은 순서(내림차순)로 정렬
vehicle_df = vehicle_df.sort_values("registration_count", ascending=False)

# 차종 개수만큼 화면을 가로로 나눔 (차종이 4개면 칸도 4개)
columns = st.columns(len(vehicle_df))

# 나눠진 칸(column)과 차종 데이터(row)를 하나씩 짝지어서 반복
for column, (_, row) in zip(columns, vehicle_df.iterrows()):
    with column:  # 이 칸 안에다가
        st.metric(
            label=row["dimension_value"],  # 차종 이름 (예: 승용)
            value=f"{int(row['registration_count']):,}대",  # 등록대수
        )


# ============================================================
# 10. "지역별 상위 5개" + "연료별 상위 5개" 막대그래프
# ============================================================

def make_bar_chart(df, tooltip_label):
    """
    지역별 그래프와 연료별 그래프는 생김새가 완전히 똑같아서,
    코드를 두 번 반복해서 쓰지 않고 이 함수 하나로 재사용해요.

    df: 그래프로 그릴 데이터(표)
    tooltip_label: 마우스를 올렸을 때 보여줄 이름표(예: "지역" 또는 "연료")
    """

    # 막대를 왼쪽부터 순서대로 그리기 위한 순서 목록
    order = df["dimension_value"].tolist()

    return (
        alt.Chart(df)      # 이 데이터로 그래프를 그리겠다
        .mark_bar()        # 막대그래프로 그리겠다
        .encode(           # 어떤 값을 X축/Y축/툴팁에 쓸지 정하는 부분
            x=alt.X(
                "dimension_value:N",  # X축 = 지역/연료 이름 (:N은 "이름/글자"라는 뜻)
                sort=order,           # 위에서 정한 순서대로 정렬
                title=None,           # X축 제목은 따로 안 씀
                axis=alt.Axis(
                    labelAngle=0,      # 글자를 눕히지 않고 똑바로(가로) 표시
                    labelPadding=10,   # 글자와 축 사이 여백
                    labelFontSize=12,  # 글자 크기
                    labelLimit=180,    # 글자가 너무 길면 최대 180px까지만 표시
                ),
            ),
            y=alt.Y(
                "registration_count:Q",  # Y축 = 등록대수 (:Q는 "숫자"라는 뜻)
                title=None,
                axis=alt.Axis(format=",d"),  # 숫자에 1000단위 콤마 표시
            ),
            tooltip=[  # 마우스를 올렸을 때 나오는 설명 상자
                alt.Tooltip("dimension_value:N", title=tooltip_label),
                alt.Tooltip("registration_count:Q", title="등록대수", format=","),
            ],
        )
        .properties(height=320)  # 그래프의 세로 높이(픽셀)
    )


# 화면을 왼쪽/오른쪽 두 칸으로 나눔
left, right = st.columns(2)

# 왼쪽 칸 = 지역별 그래프
with left:
    st.subheader("지역별 등록 상위 5개")

    # 등록대수 많은 순으로 정렬한 뒤, 위에서부터 5개만 뽑음
    region_top5 = region_df.sort_values("registration_count", ascending=False).head(5).copy()

    # 위에서 만든 함수로 그래프를 그리고, 화면 너비에 맞게 표시
    st.altair_chart(make_bar_chart(region_top5, "지역"), use_container_width=True)

# 오른쪽 칸 = 연료별 그래프
with right:
    st.subheader("연료별 등록 상위 5개")

    fuel_top5 = fuel_df.sort_values("registration_count", ascending=False).head(5).copy()

    st.altair_chart(make_bar_chart(fuel_top5, "연료"), use_container_width=True)


# ============================================================
# 11. 다른 화면(상세 페이지)으로 이동하는 버튼
# ============================================================
st.page_link(
    "pages/1_등록현황_상세.py",   # 이동할 파일 (다른 화면 코드)
    label="📊 등록현황 상세 보기",  # 화면에 보이는 버튼 글자
)


# ============================================================
# 12. 사용자가 원하는 자동차 모델을 검색하는 기능
# ============================================================
st.divider()
st.subheader("지원 모델 검색")

# 사용자가 글자를 입력할 수 있는 입력창을 만듦
keyword = st.text_input(
    label="모델명 입력",
    placeholder="예: 아반떼, K5, 쏘렌토",  # 입력창 안에 흐리게 보이는 예시 글자
)

# 사용자가 뭔가 입력했을 때만(빈 칸이 아닐 때만) 아래 코드를 실행
if keyword:

    # 4번에서 만든 함수로 검색어를 깔끔하게 정리
    normalized_keyword = normalize_search_text(keyword)

    # match_status가 "검증완료"인 데이터만 사용 (신뢰할 수 있는 매핑만 쓰기 위함)
    verified = model_mapping_df[model_mapping_df["match_status"] == "검증완료"].copy()

    # alias_normalized 컬럼(별명 목록) 안에 검색어가 들어있는 행만 골라냄
    # fillna("")는 빈칸(결측치)을 빈 문자열로 바꿔서 에러 방지
    # regex=False는 "특수기호를 정규표현식으로 해석하지 말고 그냥 글자 그대로 찾아라"는 뜻
    matched = verified[
        verified["alias_normalized"].fillna("").str.contains(normalized_keyword, regex=False)
    ]

    # 같은 자동차 모델이라도 별명이 여러 개일 수 있어서
    # model_key(모델 고유번호) 기준으로 중복된 행을 하나만 남김
    candidates = matched[
        ["model_key", "manufacturer_std", "model_std"]
    ].drop_duplicates(subset=["model_key"])

    # 검색 결과가 하나도 없을 때
    if candidates.empty:
        st.info("지원되는 모델을 찾지 못했습니다.")

    # 검색 결과가 있을 때
    else:
        # 화면에 "제조사 | 모델명" 형태로 보여줄 글자와,
        # 그 글자에 연결된 model_key를 짝지어 저장하는 사전(딕셔너리)을 만듦
        labels = {
            f"{row['manufacturer_std']} | {row['model_std']}": row["model_key"]
            for _, row in candidates.iterrows()
        }

        # 드롭다운(선택 상자)으로 후보들을 보여주고, 사용자가 하나를 고르게 함
        selected_label = st.selectbox("모델 후보", list(labels.keys()))

        # "이 모델 선택" 버튼을 눌렀을 때만 아래 코드 실행
        if st.button("이 모델 선택"):

            # 선택한 모델의 model_key를 st.session_state에 저장
            # session_state는 "이 브라우저 탭이 열려있는 동안 기억해두는 저장소"예요.
            st.session_state["selected_model_key"] = labels[selected_label]

            st.success(f"선택 완료: {selected_label}")

            # 아직 다음 화면(S-02) 데이터 준비가 안 됐다는 안내 문구
            st.caption("S-02 모델 상세 화면은 판매·결함·리콜 전처리 후 연결합니다.")


# ============================================================
# 13. 맨 아래 출처 안내
# ============================================================
st.divider()

# 데이터의 공식 출처 링크(URL)를 데이터에서 꺼내옴
source_url = latest_df["source_url"].iloc[0]

# 이 데이터를 언제 우리 시스템에 저장했는지(적재일) 꺼내옴
loaded_at = latest_df["loaded_at"].iloc[0]

# 출처/기준시점/적재일을 작은 글씨로 안내
st.caption(f"출처: 국토교통부 통계누리 | 기준시점: {snapshot_label} | 적재일: {loaded_at}")

# 클릭하면 공식 출처 웹사이트로 이동하는 버튼
st.link_button("공식 등록현황 출처", source_url)

# 데이터를 오해하지 않도록 주의사항 안내
# (등록현황은 "시장 전체 누적 등록대수"이지, 특정 모델 하나의 등록대수가 아니라는 점)
st.info(
    "등록현황은 시장 전체의 누적 등록대수(Stock)입니다. "
    "아반떼·K5 같은 개별 모델 등록대수가 아닙니다."
)
