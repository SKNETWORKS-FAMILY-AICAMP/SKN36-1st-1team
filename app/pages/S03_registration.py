import sys
from pathlib import Path
import html

# app/pages에서 실행할 때 app/lib 모듈을 찾을 수 있도록 경로를 추가합니다.
sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from lib.ui import apply_ui, navbar, page_intro, site_footer

# 전국 등록현황 화면에서 사용하는 공통 데이터 로딩/집계/표시 함수입니다.
from lib.common import (
    load_national_registration,
    latest_national_snapshot,
    national_total_count,
    region_summary,
    vehicle_type_summary,
    fuel_summary,
    fmt_count,
    source_caption,
    static_bar_chart,
)

# ------------------------------------------------------------
# 페이지 기본 설정
# ------------------------------------------------------------

st.set_page_config(page_title="전국 자동차 등록현황 상세", page_icon="📊", layout="wide")

# 사이드바와 Streamlit 기본 툴바를 숨기는 화면 스타일 설정입니다.
apply_ui()
navbar("등록현황")

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stExpandSidebarButton"] { display: none; }
    [data-testid="stElementToolbar"] { display: none !important; }
    [data-testid="stMain"] { scrollbar-gutter: stable; }

    /* 공통 차트 카드 */
    .reg-chart-card {
        background:#fff;
        border:1px solid #e3e6eb;
        border-radius:14px;
        padding:28px 30px;
        margin-top:12px;
        box-shadow:0 5px 18px rgba(20,20,25,.04);
    }

    /* 지역별 차트와 바로 아래 표 사이 여백 */
    .region-chart-card {
        margin-bottom:32px !important;
    }

    /* -------------------------------------------------
        지역별 : LOLLIPOP CHART
       ------------------------------------------------- */
    .region-lollipop {
        display:flex;
        flex-direction:column;
        gap:15px;
    }

    .region-row {
        display:grid;
        grid-template-columns:78px 1fr 110px;
        align-items:center;
        gap:14px;
    }

    .region-name {
        color:#343a44;
        font-size:15px;
        font-weight:800;
        white-space:nowrap;
    }

    .region-track {
        position:relative;
        height:18px;
    }

    .region-line {
        position:absolute;
        left:0;
        top:8px;
        height:2px;
        border-radius:999px;
        background:linear-gradient(90deg,#d76a70,#ad2630);
    }

    .region-dot {
        position:absolute;
        top:2px;
        width:14px;
        height:14px;
        border-radius:50%;
        background:#b72a34;
        border:3px solid #f8dfe1;
        box-shadow:0 0 0 1px #b72a34;
        transform:translateX(-50%);
    }

    .region-value {
        color:#5f6672;
        font-size:12px;
        font-weight:700;
        text-align:right;
        white-space:nowrap;
    }

    /* -------------------------------------------------
        차종별 : VERTICAL BAR CHART
       ------------------------------------------------- */
    .vehicle-chart {
        display:flex;
        align-items:flex-end;
        gap:26px;
        min-height:330px;
    }

    .vehicle-bar-item {
        flex:1;
        min-width:72px;
        text-align:center;
    }

    .vehicle-bar-value {
        margin-bottom:8px;
        color:#5f6672;
        font-size:12px;
        font-weight:700;
        white-space:nowrap;
    }

    .vehicle-bar-track {
        height:235px;
        display:flex;
        align-items:flex-end;
        justify-content:center;
        border-bottom:1px solid #dfe3e8;
    }

    .vehicle-bar {
        width:min(72px,72%);
        min-height:4px;
        background:linear-gradient(180deg,#d34a51 0%,#ad2630 100%);
        border-radius:8px 8px 2px 2px;
        transition:.2s ease;
    }

    .vehicle-bar-item:hover .vehicle-bar {
        filter:brightness(.92);
        transform:translateY(-2px);
    }

    .vehicle-bar-label {
        margin-top:10px;
        color:#303640;
        font-size:13px;
        font-weight:700;
        word-break:keep-all;
    }

    /* -------------------------------------------------
        연료별 : DONUT + LEGEND
       ------------------------------------------------- */
    /* 연료별 차트와 바로 아래 표 사이 여백 */
    .fuel-chart-card {
        margin-bottom: 28px !important;
    }
    .fuel-chart-wrap {
        display:grid;
        grid-template-columns:minmax(280px,.8fr) minmax(420px,1.2fr);
        gap:44px;
        align-items:center;
    }
    .fuel-donut-wrap {
        display:flex;
        justify-content:center;
        align-items:center;
    }

    .fuel-donut {
        width:250px;
        height:250px;
        border-radius:50%;
        position:relative;
        box-shadow:inset 0 0 0 1px rgba(0,0,0,.03);
    }

    .fuel-donut::after {
        content:"";
        position:absolute;
        inset:60px;
        border-radius:50%;
        background:#fff;
        box-shadow:0 0 0 1px #edf0f3;
    }

    .fuel-donut-center {
        position:absolute;
        inset:0;
        z-index:2;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        pointer-events:none;
    }

    .fuel-donut-center span {
        color:#7a828e;
        font-size:12px;
        font-weight:700;
    }

    .fuel-donut-center b {
        margin-top:4px;
        color:#20242c;
        font-size:20px;
    }

    .fuel-legend {
        display:grid;
        gap:0;
    }

    .fuel-legend-row {
        display:grid;
        grid-template-columns:12px minmax(130px,1fr) auto auto;
        gap:12px;
        align-items:center;
        padding:10px 0;
        border-bottom:1px solid #f0f1f3;
    }

    .fuel-legend-row:last-child {
        border-bottom:none;
    }

    .fuel-dot {
        width:10px;
        height:10px;
        border-radius:50%;
    }

    .fuel-name {
        color:#343a44;
        font-size:13px;
        font-weight:700;
    }

    .fuel-count {
        color:#555d68;
        font-size:13px;
        white-space:nowrap;
    }

    .fuel-pct {
        min-width:58px;
        color:#ad2630;
        font-size:13px;
        font-weight:800;
        text-align:right;
    }

    @media (max-width:900px) {
        .region-row { grid-template-columns:64px 1fr 88px; }
        .vehicle-chart { gap:10px; }
        .fuel-chart-wrap { grid-template-columns:1fr; }
    }

    /* -------------------------------------------------
        기준시점 / Stock 안내
        기존 가로선 대신 한 줄 정보 바 형태로 정리
       ------------------------------------------------- */
    .registration-meta {
        display:flex;
        align-items:center;
        gap:14px;
        flex-wrap:wrap;
        margin:10px 0 24px;
        padding:12px 16px;
        background:#F3F4F6;
        border:1px solid #E1E4E8;
        border-radius:10px;
        color:#6B7280;
        font-size:13px;
        line-height:1.5;
    }

    .registration-meta .meta-label {
        color:#A92530;
        font-weight:900;
        font-size:12px;
        letter-spacing:.02em;
    }

    .registration-meta .meta-value {
        color:#252A31;
        font-weight:800;
    }

    .registration-meta .meta-divider {
        width:1px;
        height:15px;
        background:#D1D5DB;
        flex:none;
    }

    .registration-meta .meta-note {
        color:#717986;
    }

    /* -------------------------------------------------
        지역별 / 차종별 / 연료별 탭
        텍스트형 유지 + 선택 탭에 연한 레드 포인트
       ------------------------------------------------- */
    [data-testid="stTabs"] {
        margin-top:18px !important;
    }

/* =========================================
    지역별 / 차종별 / 연료별 탭
   ========================================= */

    /* 탭 전체 영역 */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 24px !important;
        padding: 0 !important;
        margin: 0 0 22px !important;
        background: transparent !important;
        border: 0 !important;
        border-bottom: 1px solid #D9DDE3 !important;
    }

    /* 각각의 탭 크기 */
    [data-testid="stTabs"] [data-baseweb="tab"],
    [data-testid="stTabs"] [role="tab"] {
        width: 140px !important;
        min-width: 140px !important;
        max-width: 140px !important;
        flex: 0 0 140px !important;

        height: 48px !important;
        min-height: 48px !important;

        padding: 0 0 18px 0 !important;

        display: flex !important;
        align-items: flex-end !important;
        justify-content: center !important;

        background: transparent !important;
        border-radius: 8px 8px 0 0 !important;

        color: #252A31 !important;
    }

    /* 지역별 / 차종별 / 연료별 글씨 */
    [data-testid="stTabs"] [data-baseweb="tab"] *,
    [data-testid="stTabs"] [role="tab"] * {
        font-size: 20px !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;

        transform: none !important;
        margin: 0 !important;
    }

    /* 마우스 올렸을 때 */
    [data-testid="stTabs"] [data-baseweb="tab"]:hover {
        background: #FAF0F1 !important;
        color: #B52D35 !important;
    }

    /* 선택된 탭 */
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        background: #F8E7E9 !important;
        color: #B52D35 !important;
    }

    /* 선택된 탭 글씨 */
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] * {
        color: #B52D35 !important;
        font-weight: 800 !important;
    }

    /* 선택 탭 아래 빨간 선 */
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        display: block !important;
        background-color: #B52D35 !important;
        height: 3px !important;
    }
    [data-testid="stTabs"] [role="tabpanel"] {
        padding-top:4px !important;
    }

    @media (max-width:700px) {
        [data-testid="stTabs"] [data-baseweb="tab"] {
            min-width:0 !important;
            flex:1 !important;
            padding:0 12px !important;
        }

        .registration-meta {
            gap:8px;
        }

        .registration-meta .meta-divider {
            display:none;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 상단 제목
# ------------------------------------------------------------

page_intro("전국 자동차 등록현황", "지역·차종·연료 기준으로 현재 등록된 자동차 시장의 규모를 확인합니다.", "MARKET DATA")
# 제목 아래 회색선 ↔ 기준시점 사이 여백
st.markdown(
    '<div style="height:22px;"></div>',
    unsafe_allow_html=True,
)
# ------------------------------------------------------------
# 전국 등록현황 데이터 로딩
# ------------------------------------------------------------

# D-REG 전국 등록현황 데이터를 불러옵니다.
# 이 데이터는 특정 모델이 아니라 시장 전체 Stock 데이터입니다.
national_df = load_national_registration()

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

# 기준시점과 Stock 안내를 한 줄 정보 바로 정리합니다.
if selected_key is not None:
    meta_html = (
        f'<div class="registration-meta">'
        f'<span class="meta-label">기준시점</span>'
        f'<span class="meta-value">{_label_for(selected_key)}</span>'
        f'<span class="meta-divider"></span>'
        f'<span class="meta-note">현재 등록 상태의 자동차 대수(Stock)이며 신규판매·신규등록 흐름이 아닙니다.</span>'
        f'</div>'
    )
    st.markdown(meta_html, unsafe_allow_html=True)

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
            # 지역별은 막대 대신 롤리팝(lollipop) 차트로 표시합니다.
            region_chart_df = region_df.copy()
            region_chart_df["registration_count"] = pd.to_numeric(
                region_chart_df["registration_count"], errors="coerce"
            ).fillna(0)

            region_max = float(region_chart_df["registration_count"].max()) if not region_chart_df.empty else 0
            region_rows = []

            for _, r in region_chart_df.iterrows():
                name = html.escape(str(r["dimension_value"]))
                count = int(r["registration_count"])
                pct = (count / region_max * 100) if region_max > 0 else 0

                region_rows.append(
                    f'<div class="region-row">'
                    f'<div class="region-name">{name}</div>'
                    f'<div class="region-track">'
                    f'<div class="region-line" style="width:{pct:.2f}%"></div>'
                    f'<div class="region-dot" style="left:{pct:.2f}%"></div>'
                    f'</div>'
                    f'<div class="region-value">{count:,}대</div>'
                    f'</div>'
                )

            region_html = (
                f'<div class="reg-chart-card region-chart-card">'
                f'<div class="region-lollipop">{"".join(region_rows)}</div>'
                f'</div>'
            )
            st.markdown(region_html, unsafe_allow_html=True)

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
            # 차종별은 세로 막대그래프로 표시합니다.
            vt_chart_df = vt_df.copy()
            vt_chart_df["registration_count"] = pd.to_numeric(
                vt_chart_df["registration_count"], errors="coerce"
            ).fillna(0)

            vt_max = float(vt_chart_df["registration_count"].max()) if not vt_chart_df.empty else 0
            vehicle_items = []

            for _, r in vt_chart_df.iterrows():
                name = html.escape(str(r["dimension_value"]))
                count = int(r["registration_count"])
                height_pct = (count / vt_max * 100) if vt_max > 0 else 0

                vehicle_items.append(
                    f'<div class="vehicle-bar-item">'
                    f'<div class="vehicle-bar-value">{count:,}대</div>'
                    f'<div class="vehicle-bar-track">'
                    f'<div class="vehicle-bar" style="height:{height_pct:.2f}%"></div>'
                    f'</div>'
                    f'<div class="vehicle-bar-label">{name}</div>'
                    f'</div>'
                )

            vehicle_html = (
                f'<div class="reg-chart-card">'
                f'<div class="vehicle-chart">{"".join(vehicle_items)}</div>'
                f'</div>'
            )
            st.markdown(vehicle_html, unsafe_allow_html=True)

    # ========================================================
    # 3. 연료별 등록현황
    # ========================================================

    with tab_fuel:
        fuel_df = fuel_summary(selected_df)

        if fuel_df.empty:
            st.info("연료별 데이터가 없습니다. (0대와 데이터 미제공은 구분해요.)")

        else:
            # 연료별은 도넛 차트 + 범례로 표시합니다.
            fuel_chart_df = fuel_df.copy()
            fuel_chart_df["registration_count"] = pd.to_numeric(
                fuel_chart_df["registration_count"], errors="coerce"
            ).fillna(0)
            fuel_chart_df = fuel_chart_df[fuel_chart_df["registration_count"] > 0].copy()

            fuel_total = float(fuel_chart_df["registration_count"].sum())
            fuel_colors = [
                "#a92530", "#c73b43", "#df6268", "#e98b8f",
                "#f0afb2", "#7f242b", "#5d3438", "#9b6a6e",
                "#c89b9e", "#e5c8ca", "#6d737c", "#a7adb5",
            ]

            if fuel_total > 0:
                start_pct = 0.0
                gradient_parts = []
                legend_rows = []

                for idx, (_, r) in enumerate(fuel_chart_df.iterrows()):
                    name = html.escape(str(r["dimension_value"]))
                    count = int(r["registration_count"])
                    pct = count / fuel_total * 100
                    end_pct = start_pct + pct
                    color = fuel_colors[idx % len(fuel_colors)]

                    gradient_parts.append(
                        f"{color} {start_pct:.4f}% {end_pct:.4f}%"
                    )

                    legend_rows.append(
                        f'<div class="fuel-legend-row">'
                        f'<span class="fuel-dot" style="background:{color}"></span>'
                        f'<span class="fuel-name">{name}</span>'
                        f'<span class="fuel-count">{count:,}대</span>'
                        f'<span class="fuel-pct">{pct:.1f}%</span>'
                        f'</div>'
                    )

                    start_pct = end_pct

                donut_gradient = ", ".join(gradient_parts)

                fuel_html = (
                    f'<div class="reg-chart-card fuel-chart-card">'
                    f'<div class="fuel-chart-wrap">'
                    f'<div class="fuel-donut-wrap">'
                    f'<div class="fuel-donut" style="background:conic-gradient({donut_gradient})">'
                    f'<div class="fuel-donut-center">'
                    f'<span>총 등록대수</span>'
                    f'<b>{int(fuel_total):,}대</b>'
                    f'</div></div></div>'
                    f'<div class="fuel-legend">{"".join(legend_rows)}</div>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(fuel_html, unsafe_allow_html=True)

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

st.markdown(
    '<div style="height:32px;"></div>',
    unsafe_allow_html=True,
)
site_footer()