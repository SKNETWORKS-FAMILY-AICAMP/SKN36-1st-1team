# ============================================================
# 1_등록현황_상세.py
#
# 이 파일은 S-03 화면(전국 자동차 등록현황 "상세" 페이지)을 만들어요.
# 첫 화면(app.py)에서 요약만 보여줬다면,
# 여기서는 지역별 / 차종별 / 연료별로 더 자세히 볼 수 있어요.
# ============================================================

from pathlib import Path
# Path: 파일이 컴퓨터 어디에 있는지 "주소(경로)"를 다루는 도구예요.

import pandas as pd
# pandas: 엑셀표 같은 데이터(CSV)를 읽고 정리하는 도구예요.

import streamlit as st
# streamlit: 이 코드를 버튼/그래프가 있는 웹페이지로 보여주는 도구예요.


# ============================================================
# 1. 페이지 기본 설정 (브라우저 탭 제목, 아이콘, 화면 폭)
# ============================================================
st.set_page_config(
    page_title="전국 자동차 등록현황 상세",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# 2. 데이터 파일(CSV)이 있는 위치 계산하기
# ============================================================

# 이 파일은 "프로젝트폴더/app/pages/1_등록현황_상세.py"에 있다고 가정해요.
# .parents[2] 는 "두 단계 위 폴더로 올라가라"는 뜻 → 프로젝트 최상위 폴더
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 등록현황 CSV 파일의 전체 경로
REGISTRATION_PATH = PROJECT_ROOT / "data" / "processed" / "registration_summary.csv"


# ============================================================
# 3. CSV 파일 읽기
# ============================================================

# @st.cache_data → "한 번 읽은 결과는 기억해두고, 다음부터는 다시 읽지 마라"는 뜻이에요.
# (화면을 조작할 때마다 CSV를 매번 새로 읽으면 느려지기 때문)
@st.cache_data
def load_registration():
    return pd.read_csv(REGISTRATION_PATH, encoding="utf-8-sig")


registration_df = load_registration()


# ============================================================
# 4. "기준시점"을 비교하기 쉬운 숫자로 만들기
# ============================================================

# 연도 * 100 + 월 → 예: 2026년 7월 = 2026*100+7 = 202607
# 이렇게 숫자 하나로 만들면 "어느 시점이 더 최근인지" 쉽게 비교할 수 있어요.
registration_df["_snapshot_key"] = (
    registration_df["stat_year"].fillna(0).astype(int) * 100
    + registration_df["stat_month"].fillna(0).astype(int)
)

# 존재하는 기준시점들만 중복 없이 뽑아서, 최신 순서로 정렬한 목록
snapshot_table = (
    registration_df[["_snapshot_key", "stat_year", "stat_month"]]
    .drop_duplicates()
    .sort_values("_snapshot_key", ascending=False)
)


# ============================================================
# 5. 화면에 보여줄 "2026-07" 같은 글자를 만드는 함수
# ============================================================
def make_snapshot_label(year, month):
    """
    year, month 숫자를 받아서 화면에 보여줄 문자열로 바꿔줘요.
    월 정보가 없으면 연도만 보여줘요.
    """
    if pd.isna(month):
        return str(int(year))
    return f"{int(year)}-{int(month):02d}"  # 예: 2026-07


# 사용자가 고를 수 있는 기준시점 목록을 딕셔너리로 만듦
# 예: {"2026-07": 202607}  →  화면에는 "2026-07"을 보여주고, 실제로는 202607이라는 값을 씀
snapshot_options = {
    make_snapshot_label(row["stat_year"], row["stat_month"]): int(row["_snapshot_key"])
    for _, row in snapshot_table.iterrows()
}


# ============================================================
# 6. 페이지 제목과 안내 문구
# ============================================================
st.title("📊 전국 자동차 등록현황 상세")

# 데이터 해석에 오해가 없도록 주의 문구를 파란 박스로 보여줌
st.info(
    "등록현황은 시장 전체 규모를 보여주는 Stock 데이터입니다. "
    "특정 모델의 등록대수가 아닙니다."
)


# ============================================================
# 7. 기준시점(몇 년 몇 월 데이터인지) 선택하기
# ============================================================

# 나중에 여러 달의 데이터가 쌓이면, 드롭다운으로 원하는 시점을 고를 수 있게 함
if len(snapshot_options) > 1:
    selected_label = st.selectbox("기준시점 선택", list(snapshot_options.keys()))

# 지금처럼 데이터가 한 시점(한 달)밖에 없다면
else:
    # 자동으로 그 하나뿐인 시점을 선택해줌
    selected_label = next(iter(snapshot_options))
    st.caption(f"현재 확보된 기준시점: {selected_label}")

# 선택한 글자(예: "2026-07")에 해당하는 실제 숫자키(예: 202607)를 꺼냄
selected_key = snapshot_options[selected_label]

# 선택된 시점에 해당하는 데이터만 따로 뽑아냄
selected_df = registration_df[registration_df["_snapshot_key"] == selected_key].copy()


# ============================================================
# 8. 전국 총 등록대수 보여주기
# ============================================================

# dimension_type이 "TOTAL"인 행 = 전국 전체 합계 데이터
total_df = selected_df[selected_df["dimension_type"] == "TOTAL"]

if total_df.empty:
    st.error("전국 등록대수 데이터가 없습니다.")
else:
    total_count = int(total_df.iloc[0]["registration_count"])
    # st.metric = 숫자를 큰 카드 형태로 보여주는 위젯
    # {:,} 는 "천 단위마다 콤마 찍기" (예: 1234567 → 1,234,567)
    st.metric("전국 자동차 등록대수", f"{total_count:,}대")


# ============================================================
# 9. "지역별 / 차종별 / 연료별" 탭(화면 안의 페이지 전환 버튼) 만들기
# ============================================================
tab_region, tab_vehicle, tab_fuel = st.tabs(["지역별", "차종별", "연료별"])


# ============================================================
# 10. [지역별] 탭 내용
# ============================================================
with tab_region:
    st.subheader("시도별 등록현황")

    # dimension_type이 "REGION"인 데이터만 골라냄 (서울/경기/부산 등)
    region_df = selected_df[selected_df["dimension_type"] == "REGION"].copy()

    # 등록대수가 많은 지역부터 순서대로 정렬
    region_df = region_df.sort_values("registration_count", ascending=False)

    # 그래프를 그리려면 "지역 이름"을 표의 맨 왼쪽(인덱스)으로 옮겨야 해요.
    # 이렇게 하면 st.bar_chart가 자동으로 X축에 지역 이름을 넣어줘요.
    region_chart = region_df.set_index("dimension_value")[["registration_count"]]
    st.bar_chart(region_chart, height=420)

    # 그래프 아래에 보여줄 표: 컬럼 이름을 한글로 바꿔서 보기 좋게 만듦
    display_region = region_df[["dimension_value", "registration_count"]].rename(
        columns={"dimension_value": "지역", "registration_count": "등록대수"}
    )
    st.dataframe(display_region, hide_index=True, width="stretch")


# ============================================================
# 11. [차종별] 탭 내용
# ============================================================
with tab_vehicle:
    st.subheader("차종별 등록현황")

    # dimension_type이 "VEHICLE_TYPE"인 데이터만 골라냄 (승용/승합/화물/특수 등)
    vehicle_df = selected_df[selected_df["dimension_type"] == "VEHICLE_TYPE"].copy()

    # 차종 개수만큼 화면을 가로로 나눠서, 각 칸에 숫자 카드를 하나씩 넣음
    columns = st.columns(len(vehicle_df))

    for column, (_, row) in zip(columns, vehicle_df.iterrows()):
        with column:
            st.metric(row["dimension_value"], f"{int(row['registration_count']):,}대")

    # 막대그래프도 함께 보여줌
    vehicle_chart = vehicle_df.set_index("dimension_value")[["registration_count"]]
    st.bar_chart(vehicle_chart, height=350)


# ============================================================
# 12. [연료별] 탭 내용
# ============================================================
with tab_fuel:
    st.subheader("연료별 등록현황")

    # dimension_type이 "FUEL"인 데이터만 골라냄 (휘발유/경유/전기 등)
    fuel_df = selected_df[selected_df["dimension_type"] == "FUEL"].copy()

    # 등록대수 많은 순서로 정렬
    fuel_df = fuel_df.sort_values("registration_count", ascending=False)

    fuel_chart = fuel_df.set_index("dimension_value")[["registration_count"]]
    st.bar_chart(fuel_chart, height=450)

    display_fuel = fuel_df[["dimension_value", "registration_count"]].rename(
        columns={"dimension_value": "연료", "registration_count": "등록대수"}
    )
    st.dataframe(display_fuel, hide_index=True, width="stretch")


# ============================================================
# 13. 기준시점이 "여러 개"일 때만 나타나는 시간 흐름(추이) 그래프
# ============================================================

# 지금은 2026-07 딱 한 시점만 있어서 이 부분은 화면에 안 나타나요.
# 나중에 8월, 9월... 데이터가 쌓이면 자동으로 이 그래프가 나타나게 만든 부분이에요.
if len(snapshot_options) > 1:
    st.divider()
    st.subheader("전국 등록대수 시계열")

    # 모든 기간의 TOTAL(전국 합계) 데이터만 가져옴
    total_history = registration_df[registration_df["dimension_type"] == "TOTAL"].copy()

    # 각 행마다 "2026-07" 같은 화면용 글자를 새로 만들어 컬럼으로 추가
    total_history["기준시점"] = total_history.apply(
        lambda row: make_snapshot_label(row["stat_year"], row["stat_month"]),
        axis=1,
    )

    # 시간 순서(오래된 것 → 최신)로 정렬 후, 그래프용으로 인덱스 설정
    history_chart = (
        total_history.sort_values("_snapshot_key")
        .set_index("기준시점")[["registration_count"]]
    )

    # 시간 흐름을 보여줄 땐 막대그래프보다 선그래프가 더 어울려요.
    st.line_chart(history_chart, height=320)


# ============================================================
# 14. 맨 아래 출처 및 주의사항
# ============================================================
st.divider()

# 공식 출처 링크와 데이터가 저장된 날짜를 꺼내옴
source_url = selected_df["source_url"].iloc[0]
loaded_at = selected_df["loaded_at"].iloc[0]

# 작은 글씨로 출처/기준시점/적재일 안내
st.caption(f"출처: 국토교통부 통계누리 | 기준시점: {selected_label} | 적재일: {loaded_at}")

# 클릭하면 국토교통부 공식 사이트로 이동하는 버튼
st.link_button("국토교통부 공식 출처", source_url)

# 지역/차종/연료는 서로 다른 기준으로 나눈 데이터라서
# 이 값들을 서로 더하면 안 된다는 걸 노란색 경고 박스로 알려줌
st.warning(
    "지역·차종·연료는 서로 다른 집계 기준입니다. "
    "REGION + VEHICLE_TYPE + FUEL 값을 서로 더하면 안 됩니다."
)
