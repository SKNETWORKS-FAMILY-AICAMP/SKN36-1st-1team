import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st

from lib.ui import apply_ui, navbar, page_intro, section_header, site_footer
from lib.common import (
    load_national_registration,
    latest_national_snapshot,
    national_total_count,
    region_summary,
    vehicle_type_summary,
    fuel_summary,
    fmt_count,
    get_verified_models,
    source_caption,
)

st.set_page_config(
    page_title="모델 검색 | MODEL SEARCH",
    page_icon="🚗",
    layout="wide",
)

apply_ui()
navbar("모델 검색")

# 이 페이지에서만 사용하는 카드/차트 스타일
st.markdown(
    """
    <style>
    /* KPI 3개 카드 높이/크기를 왼쪽 카드 기준으로 완전히 통일 */
    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #FAF8F8 100%);
        border: 1px solid #E5E2E2;
        border-radius: 18px;
        padding: 20px 22px !important;
        box-shadow: 0 8px 24px rgba(15, 35, 70, 0.06);
        height: 160px !important;
        min-height: 160px !important;
        box-sizing: border-box;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    div[data-testid="stMetric"] > div {
        width: 100%;
    }

    div[data-testid="stMetric"] label,
    div[data-testid="stMetricLabel"] {
        color: #6B7280 !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        line-height: 1.2 !important;
        margin-bottom: 10px !important;
    }

    div[data-testid="stMetricValue"] {
        color: #1a1a1e !important;
        font-weight: 800 !important;
        font-size: 42px !important;
        line-height: 1.05 !important;
        min-height: 46px !important;
        display: flex !important;
        align-items: center !important;
    }

    div[data-testid="stMetricDelta"] {
        min-height: 24px !important;
        margin-top: 8px !important;
        font-size: 14px !important;
    }

    /* delta가 없는 첫 카드도 같은 높이를 유지하도록 하단 여백 확보 */
    div[data-testid="stMetric"]:has(div[data-testid="stMetricValue"]) {
        overflow: hidden;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 20px !important;
        border: 1px solid #E5E2E2 !important;
        background: #FFFFFF !important;
        box-shadow: 0 10px 28px rgba(20, 15, 15, 0.06);
    }

    .chart-kicker {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: #FDEBEC;
        color: #C8102E;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.02em;
        margin-bottom: 8px;
    }

    .chart-title {
        font-size: 21px;
        line-height: 1.35;
        font-weight: 800;
        color: #1a1a1e;
        margin: 0 0 4px 0;
    }

    .chart-desc {
        font-size: 13px;
        color: #7B8494;
        margin: 0 0 6px 0;
    }

    .chart-summary {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 4px;
    }

    .summary-chip {
        padding: 7px 10px;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        background: #F8FAFC;
        color: #536071;
        font-size: 12px;
        font-weight: 700;
    }


    .ranking-wrap {
        padding: 20px 4px 8px;
        min-height: 315px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 19px;
    }
    .rank-row {
        display: grid;
        grid-template-columns: 30px 68px 1fr 100px;
        align-items: center;
        gap: 10px;
    }
    .rank-number {
        width: 27px; height: 27px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        background: #EEEEF0; color: #667085; font-size: 12px; font-weight: 900;
    }
    .rank-1 { background:#FFF4D6; color:#D99500; }
    .rank-2 { background:#EEEEF0; color:#667085; }
    .rank-3 { background:#FFF0E8; color:#C87542; }
    .rank-name { color:#273247; font-size:14px; font-weight:800; white-space:nowrap; }
    .rank-track { height:11px; border-radius:999px; background:#F2E9E9; overflow:hidden; }
    .rank-bar { height:100%; border-radius:999px; }
    .rank-bar-1 { background:linear-gradient(90deg,#a50e27,#c8102e); }
    .rank-bar-2 { background:linear-gradient(90deg,#c8102e,#de2e3f); }
    .rank-bar-3 { background:linear-gradient(90deg,#de2e3f,#e85a66); }
    .rank-bar-4 { background:linear-gradient(90deg,#e85a66,#f08a92); }
    .rank-bar-5 { background:linear-gradient(90deg,#f08a92,#f7b9be); }
    .rank-value { color:#c8102e; font-size:12px; font-weight:800; text-align:right; white-space:nowrap; }

    .fuel-layout {
        min-height:315px; display:grid;
        grid-template-columns:minmax(190px,.9fr) minmax(230px,1.1fr);
        align-items:center; gap:22px; padding:10px 4px 4px;
    }
    .donut-shell { display:flex; justify-content:center; align-items:center; }
    .css-donut {
        width:210px; height:210px; border-radius:50%; position:relative;
        box-shadow:0 10px 30px rgba(200,16,46,.14);
    }
    .css-donut::after {
        content:""; position:absolute; inset:46px; background:#FFF;
        border-radius:50%; box-shadow:inset 0 0 0 1px #EEEEF0;
    }
    .donut-center {
        position:absolute; inset:0; z-index:2; display:flex; flex-direction:column;
        justify-content:center; align-items:center; pointer-events:none;
    }
    .donut-center span { color:#7B8494; font-size:12px; font-weight:700; margin-bottom:4px; }
    .donut-center strong { color:#1a1a1e; font-size:18px; font-weight:900; letter-spacing:-.04em; }

    .fuel-list {
        display:flex; flex-direction:column; border:1px solid #EEEEF0;
        border-radius:14px; overflow:hidden; background:#FFF;
    }
    .fuel-item {
        display:grid; grid-template-columns:12px minmax(80px,1fr) 92px 48px;
        align-items:center; gap:7px; padding:12px 10px;
        border-bottom:1px solid #EEEEF0; font-size:11px;
    }
    .fuel-item:last-child { border-bottom:0; }
    .fuel-dot { width:9px; height:9px; border-radius:50%; }
    .fuel-name { color:#596579; font-weight:700; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
    .fuel-count { color:#536071; text-align:right; white-space:nowrap; }
    .fuel-pct { color:#7B8494; text-align:right; font-weight:800; }

    @media (max-width:1100px) {
        .fuel-layout { grid-template-columns:1fr; }
        .css-donut { width:180px; height:180px; }
        .css-donut::after { inset:40px; }
        .rank-row { grid-template-columns:28px 55px 1fr 82px; }
        .rank-value { font-size:10px; }
    }

    @media (max-width: 900px) {
        .chart-title { font-size: 18px; }
    }
    

/* 관심 모델 찾기 카드: 위아래 높이 축소 */
.ai-card {
    padding: 14px 24px !important;
    margin-top: 14px !important;
    margin-bottom: 0 !important;
    min-height: auto !important;
}

.ai-card .ai-badge {
    margin-bottom: 3px !important;
}

.ai-card h3 {
    margin-top: 5px !important;
    margin-bottom: 0 !important;
    font-size: 18px !important;
    line-height: 1.2 !important;
}

/* 관심 모델 카드와 검색 영역 사이 간격
   선택박스 + 버튼을 조금 더 아래로 내림 */
.st-key-model_search_controls {
    margin-top: 30px !important;
    margin-bottom: 0 !important;
}

/* columns 세로 정렬 통일 */
.st-key-model_search_controls [data-testid="stHorizontalBlock"] {
    align-items: stretch !important;
}

.st-key-model_search_controls [data-testid="column"] {
    display: flex !important;
    align-items: stretch !important;
}

.st-key-model_search_controls [data-testid="column"] > div {
    width: 100% !important;
}

/* 선택박스: 더 진한 회색 + 40px */
.st-key-model_search_controls div[data-baseweb="select"] {
    height: 40px !important;
    min-height: 40px !important;
}

.st-key-model_search_controls div[data-baseweb="select"] > div {
    height: 40px !important;
    min-height: 40px !important;
    box-sizing: border-box !important;
    background-color: #C7CBD1 !important;
    border: 1px solid #AEB4BC !important;
    border-radius: 8px !important;
    box-shadow: none !important;
    display: flex !important;
    align-items: center !important;
}

.st-key-model_search_controls div[data-baseweb="select"] span {
    color: #3F4650 !important;
}

/* 이 모델 보기 버튼: 선택박스와 정확히 같은 40px */
.st-key-model_search_controls div[data-testid="stButton"] {
    height: 40px !important;
    min-height: 40px !important;
}

.st-key-model_search_controls div[data-testid="stButton"] > button,
.st-key-model_search_controls .stButton > button {
    height: 40px !important;
    min-height: 40px !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    box-sizing: border-box !important;
    border-radius: 8px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 !important;
}

/* Streamlit 기본 wrapper 여백 제거 */
.st-key-model_search_controls [data-testid="stSelectbox"],
.st-key-model_search_controls [data-testid="stButton"] {
    margin: 0 !important;
    padding: 0 !important;
}

/* 버튼/선택박스 높이가 줄어도 검증완료 문구와의 간격은 고정 */
.st-key-model_search_caption {
    margin-top: 5px !important;
    margin-bottom: 0 !important;
}

/* 전국 자동차 등록현황 상세보기 버튼 위/아래 여백 */
.st-key-registration_detail_button {
    margin-top: 24px !important;
    margin-bottom: 20px !important;
}

/* 전국 자동차 등록현황 출처 아래 여백 */
.st-key-registration_source {
    margin-bottom: 30px !important;
}
</style>
    """,
    unsafe_allow_html=True,
)

page_intro(
    "모델 검색",
    "지원 모델을 선택하고 판매·결함신고·리콜 정보를 확인하세요.",
)

verified_models = get_verified_models()
options = {
    f"{r['manufacturer_std']}  |  {r['model_std']}": r["model_key"]
    for _, r in verified_models.iterrows()
}

st.markdown(
    '<div class="ai-card"><span class="ai-badge">STEP 1</span><h3>관심 모델 찾기</h3></div>',
    unsafe_allow_html=True,
)

with st.container(key="model_search_controls"):
    search_cols = st.columns([4, 1.3])

    with search_cols[0]:
        selected_label = st.selectbox(
            "모델 검색",
            list(options.keys()),
            index=None,
            placeholder="제조사 또는 모델명을 선택하세요",
            label_visibility="collapsed",
        )

    with search_cols[1]:
        go_detail = st.button(
            "이 모델 보기  →",
            type="primary",
            use_container_width=True,
        )

with st.container(key="model_search_caption"):
    st.caption(
        f"검증완료 {len(verified_models)}개 지원 모델만 노출 · "
        "원천 별칭은 내부 매핑으로 처리"
    )

if selected_label:
    key = options[selected_label]
    row = verified_models[verified_models.model_key == key].iloc[0]
    generation = row.get("generation_name")
    generation_note = (
        f'<span style="color:#6B7280">참고: {generation}</span><br>'
        if pd.notna(generation) and str(generation).strip()
        else ""
    )

    candidate_html = (
        '<div class="ai-notice" style="background:#FDEEEE;border-color:#F0C4C4">'
        '<span class="ai-badge">선택 후보</span>'
        '<div style="margin-top:14px;">'
        f'<div style="font-size:17px;font-weight:800;color:#3F3F46;">'
        f'{row["manufacturer_std"]}  |  {row["model_std"]}'
        '</div>'
        f'{generation_note}'
        '<div style="margin-top:8px;color:#374151;font-size:14px;">'
        'model_key 기반 통합 조회'
        '</div>'
        '</div>'
        '</div>'
    )

    st.markdown(candidate_html, unsafe_allow_html=True)

    if go_detail:
        st.session_state["selected_model_key"] = key
        st.switch_page("pages/S02_model_detail.py")

elif go_detail:
    st.warning("먼저 모델을 선택해 주세요.")


section_header(
    "전국 자동차 등록현황",
    "시장 전체 Stock · 개별 모델 등록대수가 아닙니다.",
    "MARKET SNAPSHOT",
)

# 설명 문구와 아래 KPI 카드 사이 여백
st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)

national_df = load_national_registration()
latest_df = latest_national_snapshot(national_df)

if latest_df.empty:
    st.error("전국 자동차 등록현황 데이터를 불러오지 못했습니다.")

else:
    y = int(latest_df.iloc[0].stat_year)
    m = latest_df.iloc[0].stat_month
    label = f"{y}.{int(m):02d}" if pd.notna(m) else str(y)

    total = national_total_count(latest_df)
    vt = vehicle_type_summary(latest_df)
    region = region_summary(latest_df)
    fuel = fuel_summary(latest_df)

    # KPI 카드
    k = st.columns([1, 1, 1], gap="medium")

    with k[0]:
        st.metric(
            "전국 등록대수",
            f"{total:,}대" if total is not None else "정보 없음",
            help=f"기준 {label}",
        )

    with k[1]:
        if not vt.empty:
            st.metric(
                "차종 최다",
                vt.iloc[0].dimension_value,
                fmt_count(vt.iloc[0].registration_count),
            )
        else:
            st.metric("차종 최다", "정보 없음")

    with k[2]:
        if not fuel.empty:
            st.metric(
                "연료 최다",
                fuel.iloc[0].dimension_value,
                fmt_count(fuel.iloc[0].registration_count),
            )
        else:
            st.metric("연료 최다", "정보 없음")

    st.markdown(
    "<div style='height: 40px;'></div>",
    unsafe_allow_html=True
    ) 

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # 외부 차트 라이브러리 없이 HTML/CSS로 만든 카드형 차트
    charts = st.columns(2, gap="medium")

    with charts[0]:
        with st.container(border=True):
            st.markdown(
                '<span class="chart-kicker">REGION RANKING</span>'
                '<div class="chart-title">지역별 등록 TOP 5</div>'
                '<div class="chart-desc">선택한 기준시점에서 등록대수가 많은 지역입니다.</div>',
                unsafe_allow_html=True,
            )

            if not region.empty:
                region_top5 = region.sort_values("registration_count", ascending=False).head(5).reset_index(drop=True)
                max_region = float(region_top5["registration_count"].max())
                rows = []

                for i, r in region_top5.iterrows():
                    value = int(r["registration_count"])
                    width = max(6, value / max_region * 100)
                    rank = ["1", "2", "3", "4", "5"][i]
                    rows.append(
                        f'<div class="rank-row">'
                        f'<div class="rank-number rank-{i+1}">{rank}</div>'
                        f'<div class="rank-name">{r["dimension_value"]}</div>'
                        f'<div class="rank-track">'
                        f'<div class="rank-bar rank-bar-{i+1}" style="width:{width:.1f}%"></div>'
                        f'</div>'
                        f'<div class="rank-value">{value:,}대</div>'
                        f'</div>'
                    )

                ranking_html = f'<div class="ranking-wrap">{"".join(rows)}</div>'
                st.markdown(ranking_html, unsafe_allow_html=True)
            else:
                st.info("지역별 등록 데이터가 없습니다.")

    with charts[1]:
        with st.container(border=True):
            st.markdown(
                '<span class="chart-kicker">FUEL MIX</span>'
                '<div class="chart-title">연료별 등록 비중</div>'
                '<div class="chart-desc">전체 등록차량의 주요 연료 구성을 비중으로 보여줍니다.</div>',
                unsafe_allow_html=True,
            )

            if not fuel.empty:
                fuel_sorted = fuel.sort_values("registration_count", ascending=False).reset_index(drop=True)
                fuel_top = fuel_sorted.head(4).copy()
                other_count = int(fuel_sorted.iloc[4:]["registration_count"].sum())

                if other_count > 0:
                    fuel_top = pd.concat([
                        fuel_top,
                        pd.DataFrame({
                            "dimension_value": ["기타"],
                            "registration_count": [other_count],
                        })
                    ], ignore_index=True)

                fuel_total = int(fuel_top["registration_count"].sum())
                colors = ["#A50E27", "#C8102E", "#E2545F", "#EF9AA0", "#FBDADC"]

                items = []
                conic_parts = []
                current = 0.0

                for i, r in fuel_top.iterrows():
                    value = int(r["registration_count"])
                    pct = (value / fuel_total * 100) if fuel_total else 0
                    end_pct = current + pct
                    color = colors[i % len(colors)]
                    conic_parts.append(f"{color} {current:.2f}% {end_pct:.2f}%")
                    items.append(
                        f'<div class="fuel-item">'
                        f'<span class="fuel-dot" style="background:{color}"></span>'
                        f'<span class="fuel-name">{r["dimension_value"]}</span>'
                        f'<span class="fuel-count">{value:,}대</span>'
                        f'<span class="fuel-pct">{pct:.1f}%</span>'
                        f'</div>'
                    )
                    current = end_pct

                gradient = ", ".join(conic_parts)

                fuel_html = (
                    f'<div class="fuel-layout">'
                    f'<div class="donut-shell">'
                    f'<div class="css-donut" style="background:conic-gradient({gradient});">'
                    f'<div class="donut-center">'
                    f'<span>총 등록대수</span>'
                    f'<strong>{fuel_total:,}대</strong>'
                    f'</div></div></div>'
                    f'<div class="fuel-list">{"".join(items)}</div>'
                    f'</div>'
                )
                st.markdown(fuel_html, unsafe_allow_html=True)
            else:
                st.info("연료별 등록 데이터가 없습니다.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    with st.container(key="registration_detail_button"):
        if st.button(
            "전국 자동차 등록현황 상세보기  →",
            use_container_width=False,
        ):
            st.switch_page("pages/S03_registration.py")

    with st.container(key="registration_source"):
        source_caption(
            latest_df.iloc[0].get("source_url"),
            latest_df.iloc[0].get("loaded_at"),
            label="출처 · 기준시점",
        )

site_footer()