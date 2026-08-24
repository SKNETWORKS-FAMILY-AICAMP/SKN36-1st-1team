import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = Path(__file__).resolve().parents[1]

sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(APP_ROOT))

import pandas as pd
import streamlit as st

# 전국 등록현황 화면에서 사용하는 공통 데이터 로딩/집계/표시 함수입니다.
from lib.common import (
    national_total_count,
    region_summary,
    vehicle_type_summary,
    fuel_summary,
    fmt_count,
    source_caption,
    static_bar_chart,
)

from src.db.query_service import get_all_registration

# ------------------------------------------------------------
# 페이지 기본 설정
# ------------------------------------------------------------

st.set_page_config(page_title="전국 자동차 등록현황 상세", page_icon="📊", layout="wide")

# 사이드바와 Streamlit 기본 툴바를 숨기는 화면 스타일 설정입니다.
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stExpandSidebarButton"] { display: none; }

    [data-testid="stElementToolbar"] { display: none !important; }

    [data-testid="stMain"] { scrollbar-gutter: stable; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 상단 제목 / Home 버튼
# ------------------------------------------------------------

header_cols = st.columns([5, 1])
with header_cols[0]:
    st.title("📊 전국 자동차 등록현황 상세")
with header_cols[1]:
    st.write("")
    if st.button("🏠 Home"):
        st.switch_page("app.py")

# ------------------------------------------------------------
# 전국 등록현황 데이터 로딩
# ------------------------------------------------------------

# D-REG 전국 등록현황 데이터를 불러옵니다.
# 이 데이터는 특정 모델이 아니라 시장 전체 Stock 데이터입니다.
national_df = get_all_registration()

# 데이터 자체를 불러오지 못한 경우 화면 실행을 중단합니다.
if national_df.empty:
    st.error("전국 자동차 등록현황 데이터를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.")
    st.stop()

# stat_year + stat_month로 만든 기준시점 키를 최신순으로 정렬합니다.
snapshot_keys = sorted(national_df["_snapshot_key"].unique(), reverse=True)


# ------------------------------------------------------------
# 기준시점 표시용 함수
# ------------------------------------------------------------

# _snapshot_key에 해당하는 기준시점을 YYYY.MM 형태로 표시합니다.
# 월 정보가 없으면 연도만 표시합니다.
def _label_for(key: int) -> str:
    row = national_df[national_df["_snapshot_key"] == key].iloc[0]
    y = int(row["stat_year"])
    m = row["stat_month"]
    return f"{y}.{int(m):02d}" if pd.notna(m) else f"{y}"


# ------------------------------------------------------------
# 조회 기준시점 선택
# ------------------------------------------------------------

# 여러 기준시점 데이터가 있으면 사용자가 선택할 수 있도록 합니다.
if len(snapshot_keys) > 1:
    labels = {_label_for(k): k for k in snapshot_keys}
    picked_label = st.selectbox("기준시점", list(labels.keys()))
    selected_key = labels[picked_label]

# 기준시점이 하나뿐이면 선택 UI 없이 최신 기준시점을 표시합니다.
else:
    selected_key = snapshot_keys[0] if snapshot_keys else None
    st.caption(f"기준시점: 최신 기준 ({_label_for(selected_key)})")

# 선택된 기준시점에 해당하는 데이터만 사용합니다.
selected_df = national_df[national_df["_snapshot_key"] == selected_key] if selected_key is not None else national_df.iloc[0:0]

# ------------------------------------------------------------
# 전국 자동차 등록현황 요약
# ------------------------------------------------------------

st.markdown("### 전국 자동차 등록현황")
if selected_key is not None:
    st.caption(f"기준 {_label_for(selected_key)}")

# 전국 등록현황은 판매량이나 신규등록 흐름이 아니라 현재 등록된 차량 Stock임을 안내합니다.
st.caption("※ 현재 등록 상태의 자동차 대수(Stock)이며 신규판매/신규등록 흐름이 아닙니다.")

st.divider()

# 선택 기준시점에 데이터가 없으면 0대로 오해하지 않도록 별도로 안내합니다.
if selected_df.empty:
    st.warning("선택 기준시점 또는 집계축에 제공되는 데이터가 없습니다. (0대와 데이터 미제공은 구분해요.)")

else:
    # M00: 선택 기준시점의 전국 총 등록대수
    total_count = national_total_count(selected_df)

    if total_count is None:
        st.info("등록현황 데이터가 없습니다.")
    else:
        st.metric("전국 등록대수", f"{total_count:,}대")

    st.write("")

    # 전국 등록현황을 지역별 / 차종별 / 연료별로 분리해서 보여줍니다.
    tab_region, tab_vehicle, tab_fuel = st.tabs(["지역별", "차종별", "연료별"])

    # ========================================================
    # 1. 지역별 등록현황
    # ========================================================

    with tab_region:
        region_df = region_summary(selected_df)

        if region_df.empty:
            st.info("지역별 데이터가 없습니다. (0대와 데이터 미제공은 구분해요.)")

        else:
            # 지역별 등록대수를 막대그래프로 표시합니다.
            series = region_df.set_index("dimension_value")["registration_count"]
            static_bar_chart(series, height=max(320, 24 * len(series)), horizontal=True, sort=False)

            # 표에 표시할 지역명 / 등록대수 컬럼만 선택합니다.
            display_region_df = region_df[
                ["dimension_value", "registration_count"]
            ].rename(
                columns={
                    "dimension_value": "지역",
                    "registration_count": "등록대수",
                }
            )

            # 등록대수를 6,777,673처럼 천 단위 쉼표가 포함된 문자열로 표시합니다.
            display_region_df["등록대수"] = display_region_df["등록대수"].apply(
                lambda x: f"{int(x):,}"
            )

            st.dataframe(
            display_region_df,
            hide_index=True,
            width="stretch",
            )

    # ========================================================
    # 2. 차종별 등록현황
    # ========================================================

    with tab_vehicle:
        vt_df = vehicle_type_summary(selected_df)

        if vt_df.empty:
            st.info("차종별 데이터가 없습니다. (0대와 데이터 미제공은 구분해요.)")

        else:
            # 차종별 등록대수를 KPI 형태로 나란히 표시합니다.
            vt_cols = st.columns(len(vt_df))
            for col, (_, r) in zip(vt_cols, vt_df.iterrows()):
                with col:
                    st.metric(r["dimension_value"], fmt_count(r["registration_count"]))

            st.write("")

            # 차종별 등록대수를 막대그래프로 표시합니다.
            series = vt_df.set_index("dimension_value")["registration_count"]
            static_bar_chart(series, height=280, horizontal=True, sort=False)

    # ========================================================
    # 3. 연료별 등록현황
    # ========================================================

    with tab_fuel:
        fuel_df = fuel_summary(selected_df)

        if fuel_df.empty:
            st.info("연료별 데이터가 없습니다. (0대와 데이터 미제공은 구분해요.)")

        else:
            # 연료별 등록대수를 막대그래프로 표시합니다.
            series = fuel_df.set_index("dimension_value")["registration_count"]
            static_bar_chart(series, height=max(320, 24 * len(series)), horizontal=True, sort=False)

            # 연료별 등록대수를 표로도 제공합니다.
            display_fuel_df = fuel_df[
                ["dimension_value", "registration_count"]
            ].rename(
                columns={
                    "dimension_value": "연료",
                    "registration_count": "등록대수",
                }
            )

            display_fuel_df["등록대수"] = display_fuel_df["등록대수"].apply(
                lambda x: f"{int(x):,}"
            )

            st.dataframe(
                display_fuel_df,
                hide_index=True,
                width="stretch",
            )

# ------------------------------------------------------------
# 전국 총 등록대수 시계열
# ------------------------------------------------------------

# 기준시점이 여러 개 있을 때만 전국 총 등록대수 변화 추이를 표시합니다.
if len(snapshot_keys) > 1:
    st.divider()
    st.subheader("전국 등록대수 시계열")

    # TOTAL 행만 사용해서 기준시점별 전국 등록대수 추이를 만듭니다.
    total_history = national_df[national_df["dimension_type"] == "TOTAL"].copy()

    # 그래프에 표시할 기준시점 라벨을 생성합니다.
    total_history["기준시점"] = total_history.apply(
        lambda row: _label_for(int(row["_snapshot_key"])), axis=1
    )

    # 오래된 기준시점부터 정렬해서 시계열 그래프로 표시합니다.
    history_chart = (
        total_history.sort_values("_snapshot_key").set_index("기준시점")[["registration_count"]]
    )

    st.line_chart(history_chart, height=320)

st.divider()

# ------------------------------------------------------------
# 출처 / 해석 안내
# ------------------------------------------------------------

# 선택 기준시점 데이터가 있으면 공식 데이터 출처와 적재 시점을 표시합니다.
if not selected_df.empty:
    sample = selected_df.iloc[0]

    source_caption(
        sample.get("source_url"),
        sample.get("loaded_at"),
        label=f"출처: 국토교통부 통계누리 · 기준시점 {_label_for(selected_key)}",
    )

    _src = sample.get("source_url")

    # 공식 출처 URL이 있으면 바로 이동할 수 있는 버튼을 제공합니다.
    if _src and str(_src) != "nan":
        st.link_button("국토교통부 공식 출처", _src)

# 이 화면의 전국 등록현황 데이터는 개별 모델 등록대수와 연결하지 않습니다.
st.caption("※ 아반떼 · K5 등 개별 모델 등록대수는 이 데이터로 제공하지 않습니다.")

# 지역 / 차종 / 연료는 서로 다른 집계축이므로 서로 합치거나 직접 비교하는 값이 아닙니다.
st.caption("※ 지역·차종·연료는 서로 다른 집계 기준입니다.")