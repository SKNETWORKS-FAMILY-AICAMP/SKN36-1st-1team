import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = Path(__file__).resolve().parents[1]

sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(APP_ROOT))

import pandas as pd
import streamlit as st

from lib.common import (
    national_total_count,
    region_summary,
    vehicle_type_summary,
    fuel_summary,
    fmt_count,
    source_caption,
    static_bar_chart,
)

from src.db.query_service import (
    get_models,
    get_latest_registration_snapshot,
)

# 이 페이지가 브라우저 탭에 어떻게 보일지 설정합니다 (제목, 아이콘, 화면 넓게 쓰기)
st.set_page_config(
    page_title="전국 자동차 등록현황 · 모델 검색",
    page_icon="🚗",
    layout="wide",
)

# 화면 디자인(CSS)을 직접 넣는 부분입니다. 기능과는 상관없이 "보이는 모양"만 조정합니다.
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stExpandSidebarButton"] { display: none; }
    [data-testid="stElementToolbar"] { display: none !important; }
    [data-testid="stMain"] { scrollbar-gutter: stable; }

    .block-container, [data-testid="stAppViewBlockContainer"] {
      padding-top: 4.5rem !important;
      padding-bottom: 2rem !important;
    }
    [data-testid="stVerticalBlock"] { gap: 0.6rem; }

    h1, h2, h3 { line-height: 1.35 !important; padding-top: 2px; }
    .s01-search-title { text-align: center; }
    .s01-note { color: #8B93A1; font-size: 13px; margin-top: 2px; }
    [data-testid="stMetricValue"] { font-size: 1.5rem; }
    .s01-candidate {
      border: 1px solid #E7E9EE; border-radius: 12px; padding: 10px 16px; margin-bottom: 8px;
      transition: box-shadow 0.2s ease, transform 0.2s ease;
    }
    .s01-candidate:hover { box-shadow: 0 8px 18px rgba(17,24,39,0.07); transform: translateY(-2px); }
    div[data-testid="stForm"] { border: none; padding: 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# DB(또는 데이터 소스)에서 "검색 가능한 차종 목록"을 미리 가져옵니다.
verified_models = get_models()
supported_models_label = " · ".join(verified_models["model_std"].tolist())

# ── 상단 제목 + 홈 버튼 ──────────────────────────────
header_cols = st.columns([5, 1])
with header_cols[0]:
    st.title("🚗 전국 자동차 등록현황 · 모델 검색")
    st.caption("관심 모델을 먼저 검색하거나, 아래에서 국내 자동차 시장 전체 규모를 확인하세요.")
with header_cols[1]:
    st.write("")
    if st.button("🏠 Home"):
        st.switch_page("app.py")

# ── 모델 검색(드롭다운) 영역 ─────────────────────────
st.markdown('<h3 class="s01-search-title">🔎 관심 모델 안전정보 찾기</h3>', unsafe_allow_html=True)

# 화면에 보여줄 이름("현대 | 아반떼")과 실제 DB 키("HYU_AVANTE")를 짝지어 둡니다.
# 사람은 예쁜 이름을 보고 고르고, 코드는 뒤에서 짝지어진 키를 씁니다.
search_options = {
    f"{row['manufacturer_std']} | {row['model_std']}": row["model_key"]
    for _, row in verified_models.iterrows()
}

search_form_cols = st.columns([1, 2, 1])
with search_form_cols[1]:
    # selectbox = 클릭하면 아래로 전체 목록이 펼쳐지는 검색창(드롭다운)
    selected_label = st.selectbox(
        "모델 검색",
        options=list(search_options.keys()),
        index=None,
        placeholder="아반떼 / K5 / 쏘렌토 ...",
        label_visibility="collapsed",
    )

if selected_label:
    # 사용자가 고른 예쁜 이름으로, 그 모델의 실제 정보(한 줄)를 찾아옵니다.
    selected_key = search_options[selected_label]
    selected_row = verified_models[verified_models["model_key"] == selected_key].iloc[0]

    st.markdown("**검색 후보**")
    with st.container(border=False):
        st.markdown('<div class="s01-candidate">', unsafe_allow_html=True)
        cand_cols = st.columns([4, 1])

        with cand_cols[0]:
            st.markdown(
                f"**{selected_row['manufacturer_std']} | {selected_row['model_std']}**"
            )

        with cand_cols[1]:
            # 버튼을 누르면 고른 모델의 키를 기억해 두고(session_state), 상세 페이지로 이동합니다.
            if st.button("이 모델 보기", key=f"select_{selected_key}", use_container_width=True):
                st.session_state["selected_model_key"] = selected_key
                st.switch_page("pages/S02_모델통합상세.py")

        st.markdown("</div>", unsafe_allow_html=True)
else:
    st.caption("검색창을 클릭하면 현재 지원하는 차종을 확인할 수 있어요.")

st.divider()

# ── 전국 자동차 등록현황(시장 전체 통계) 영역 ──────────
latest_df = get_latest_registration_snapshot()

if latest_df.empty:
    st.error("전국 자동차 등록현황 데이터를 불러오지 못했습니다. 잠시 후 다시 확인해 주세요.")
else:
    # 데이터가 몇 년 몇 월 기준인지 표시용 문구를 만듭니다. (예: "2025.06")
    latest_year = int(latest_df.iloc[0]["stat_year"])
    _raw_month = latest_df.iloc[0]["stat_month"]
    latest_month = int(_raw_month) if pd.notna(_raw_month) else None
    stat_label = f"{latest_year}.{latest_month:02d}" if latest_month else f"{latest_year}"

    st.subheader("전국 자동차 등록현황")
    st.markdown(f'<p class="s01-note">기준 {stat_label}</p>', unsafe_allow_html=True)

    total_count = national_total_count(latest_df)

    # 왼쪽엔 총 등록대수, 오른쪽엔 차종별(승용/화물 등) 요약을 나란히 보여줍니다.
    row1 = st.columns([1, 1.6])
    with row1[0]:
        with st.container(border=True):
            if total_count is None:
                st.info("등록현황 데이터가 없습니다.")
            else:
                st.metric("전국 등록대수", f"{total_count:,}대")
    with row1[1]:
        with st.container(border=True):
            st.caption("차종별 요약")
            vt_df = vehicle_type_summary(latest_df)
            if vt_df.empty:
                st.caption("차종별 데이터가 없습니다.")
            else:
                # 항목이 여러 개라 한 줄에 2개씩 짝지어 보여줍니다.
                vt_rows = [vt_df.iloc[i : i + 2] for i in range(0, len(vt_df), 2)]
                for chunk in vt_rows:
                    vt_cols = st.columns(2)
                    for col, (_, r) in zip(vt_cols, chunk.iterrows()):
                        with col:
                            st.metric(r["dimension_value"], fmt_count(r["registration_count"]))

    # 지역별 등록 상위 5곳, 연료별 등록 요약을 그래프 두 개로 나란히 보여줍니다.
    row2 = st.columns(2)
    with row2[0]:
        st.markdown("**지역별 등록 상위**")
        region_df = region_summary(latest_df)
        if region_df.empty:
            st.caption("지역별 데이터가 없습니다.")
        else:
            top_region = region_df.head(5).set_index("dimension_value")["registration_count"]
            static_bar_chart(top_region, height=200, horizontal=True, sort=False)
    with row2[1]:
        st.markdown("**연료별 등록 요약**")
        fuel_df = fuel_summary(latest_df)
        if fuel_df.empty:
            st.caption("연료별 데이터가 없습니다.")
        else:
            fuel_series = fuel_df.set_index("dimension_value")["registration_count"]
            static_bar_chart(fuel_series, height=200, horizontal=True, sort=False)

    if st.button("전국 자동차 등록현황 상세보기 →"):
        st.switch_page("pages/S03_등록현황상세.py")
    st.caption("※ 등록현황은 시장 전체 통계이며 위 모델의 개별 등록대수가 아닙니다.")

    _source_url = latest_df.iloc[0].get("source_url")
    _loaded_at = latest_df.iloc[0].get("loaded_at")

st.divider()

st.caption(f"검색 가능 차종: {supported_models_label}")

if not latest_df.empty:
    source_caption(_source_url, _loaded_at, label="출처 · 기준시점")
