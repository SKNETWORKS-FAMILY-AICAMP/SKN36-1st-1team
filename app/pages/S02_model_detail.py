import sys
from pathlib import Path
import html

# ------------------------------------------------------------
# 경로 설정
# ------------------------------------------------------------
# app/pages에서 실행해도 프로젝트 루트의 src와 app/lib를 찾을 수 있게 설정
PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = Path(__file__).resolve().parents[1]

sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(APP_ROOT))

import pandas as pd
import altair as alt
import streamlit as st
from lib.ui import apply_ui, navbar, page_intro, site_footer

# 모델 비교는 MySQL DB 조회 모듈 사용
from src.db.model_compare import compare_models

# 화면 공통 데이터/계산 함수
from lib.common import (
    load_vehicle_sales,
    load_defect_reports,
    load_recall,
    get_verified_models,
    model_label,
    model_sales,
    compute_M04,
    sales_coverage,
    compute_M05,
    model_defects,
    compute_M06,
    compute_M07,
    compute_M08_model_year,
    model_recalls,
    compute_M09,
    compute_M10,
    compute_M11_M12,
    compute_M15,
    has_production_period_gap,
    fmt_count,
    fmt_date,
    source_caption,
    link_or_gap,
    ANALYSIS_YEAR_START,
    ANALYSIS_YEAR_END,
    static_bar_chart,
)


# ============================================================
# 페이지 기본 설정
# ============================================================

st.set_page_config(
    page_title="모델 통합 상세",
    page_icon="🚘",
    layout="wide",
)

apply_ui()
navbar("모델 검색")

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stExpandSidebarButton"] { display: none; }

    [data-testid="stElementToolbar"] { display: none !important; }

    [data-testid="stMain"] { scrollbar-gutter: stable; }


    /* 판매량 영역 간격 - Streamlit 블록 자체에 적용 */
    .st-key-sales_kpi_wrap {
        margin-top: 18px !important;
        margin-bottom: 30px !important;
    }
    /* 판매량 KPI 박스 아래 회색 안내문 */
    .st-key-sales_kpi_wrap div[data-testid="stCaptionContainer"] {
        margin-top: 6px !important;   /* 박스와 글씨 사이 위쪽 여백 */
        padding-left: 4px !important; /* 글씨 왼쪽 여백 */
    }
    .st-key-sales_chart_title {
        margin-bottom: 16px !important;
    }
    /* 연도별 국내 판매량 추이 제목 */
    .st-key-sales_chart_title p {
        font-size: 20px !important;
        font-weight: 700 !important;
    }

    .st-key-sales_flow_wrap {
        margin-bottom: 20px !important;
    }

    .st-key-sales_missing_note {
        margin-top: 0 !important;
        margin-bottom: 18px !important;
    }

    .st-key-sales_table_wrap {
        margin-top: 0 !important;
        margin-bottom: 30px !important;
    }
    .st-key-compare_title {
    margin-bottom: 16px !important;
    }
    /* FAQ 제목 → 버튼 사이 여백 */
    .st-key-faq_title {
    margin-bottom: 14px !important;
    }
    /* FAQ 버튼 → 아래 출처 문구 사이 여백 */
    .st-key-faq_button {
        margin-bottom: 14px !important;
    }

    /* =========================================================
        소비자 제작결함 신고 — Signal Overview
       ========================================================= */
    /* 결함신고 제목 아래 설명문 간격 */
    .st-key-defect_intro {
        margin-top: 8px !important;
        margin-bottom: 10px !important;
    }

    .st-key-defect_intro div[data-testid="stCaptionContainer"] {
        margin-bottom: 8px !important;
    }

    /* 마지막 설명문은 추가 하단 margin 제거 */
    .st-key-defect_intro div[data-testid="stCaptionContainer"]:last-child {
        margin-bottom: 0 !important;
    }

    .st-key-defect_intro p {
        margin-bottom: 6px !important;
    }

    .st-key-defect_overview {
        margin-top: 4px !important;
        margin-bottom: 22px !important;
    }

    .st-key-defect_overview,
    .st-key-defect_overview [data-testid="stVerticalBlockBorderWrapper"],
    .st-key-defect_overview [data-testid="stVerticalBlock"] {
        background: #ffffff !important;
    }

    /* Signal Overview 좌/우 내부 여백 동일하게 34px */
    .st-key-defect_overview [data-testid="stColumn"]:first-child {
        padding-left: 34px !important;
        padding-right: 34px !important;
        box-sizing: border-box !important;
    }

    .st-key-defect_overview [data-testid="stColumn"]:last-child {
        padding-left: 34px !important;
        padding-right: 34px !important;
        box-sizing: border-box !important;
    }

    .st-key-defect_overview [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #e2e5e9 !important;
        border-radius: 16px !important;
        box-shadow: 0 8px 24px rgba(20, 20, 25, 0.05) !important;
        padding: 4px !important;
    }

    .defect-summary-kicker {
        display: inline-block;
        margin-top: 5px;
        margin-bottom: 5px;
        padding: 5px 9px;
        border-radius: 999px;
        background: #f8e8ea;
        color: #b52d35;
        font-size: 12px;
        font-weight: 900;
        letter-spacing: .03em;
    }

    .defect-summary-title {
        color: #6b7280;
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .defect-summary-value {
        color: #17191d;
        font-size: 40px;
        line-height: 1.02;
        font-weight: 900;
        letter-spacing: -.04em;
        margin-bottom: 18px;
    }

    .defect-info-box {
        display: block;
        width: 100%;
        box-sizing: border-box;
        padding: 12px 16px;
        margin-top: 0;
        margin-bottom: 14px;
        border-radius: 10px;
        background: #f5f6f8;
        color: #6f7783;
        font-size: 13px;
        line-height: 1.55;
    }

    .defect-info-box strong {
        color: #343a43;
        font-weight: 800;
    }

    .defect-missing-badge {
        display: block;
        width: 100%;
        box-sizing: border-box;
        margin-top: 0;
        margin-bottom: 4px;
        padding: 12px 16px;
        border: 1px solid #efcdd0;
        border-radius: 10px;
        background: #fff5f5;
        color: #b52d35;
        font-size: 12px;
        font-weight: 800;
    }

    .st-key-defect_chart_title {
        margin-bottom: 6px !important;
    }

    .st-key-defect_chart_title p {
        font-size: 20px !important;
        font-weight: 800 !important;
        color: #252a31 !important;
    }

    .st-key-defect_chart_note {
        margin-top: 6px !important;
    }


    /* 접수연도별 신고 추이 - 얇은 막대 + 연한 그리드 */
    .defect-thinbar-card {
        position: relative;
        height: 235px;
        box-sizing: border-box;
        padding: 18px 8px 10px;
        background: #ffffff;
        border-top: 1px solid #eceff3;
        overflow: hidden;
    }

    .defect-thinbar-grid-bg {
        position: absolute;
        left: 8px;
        right: 8px;
        top: 44px;
        bottom: 38px;
        background:
            repeating-linear-gradient(
                to bottom,
                transparent 0,
                transparent calc(25% - 1px),
                #eef0f3 calc(25% - 1px),
                #eef0f3 25%
            );
        pointer-events: none;
    }

    .defect-thinbar-grid {
        position: relative;
        z-index: 2;
        height: 100%;
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 22px;
        align-items: end;
    }

    .defect-thinbar-item {
        height: 100%;
        display: grid;
        grid-template-rows: 28px 1fr 30px;
        align-items: end;
        text-align: center;
    }

    .defect-thinbar-value {
        color: #a92d35;
        font-size: 13px;
        font-weight: 800;
        white-space: nowrap;
    }

    .defect-thinbar-plot {
        position: relative;
        height: 145px;
        display: flex;
        align-items: flex-end;
        justify-content: center;
    }

    .defect-thinbar-bar {
        width: 20px;
        min-height: 3px;
        border-radius: 5px 5px 0 0;
        background: linear-gradient(180deg, #b52d35 0%, #d77a80 100%);
        box-shadow: 0 2px 6px rgba(181,45,53,.10);
    }

    .defect-thinbar-year {
        color: #687180;
        font-size: 13px;
        font-weight: 700;
        padding-top: 8px;
    }

    /* 모델년도별 신고 분포 - 랭킹 + 비중 카드 */
    .modelyear-rank-card {
        box-sizing: border-box;
        width: 100%;
        padding: 24px 28px 20px;
        margin-top: 12px;
        background: #ffffff;
        border: 1px solid #e2e5e9;
        border-radius: 16px;
        box-shadow: 0 7px 20px rgba(20, 20, 25, 0.035);
    }

    .modelyear-rank-grid {
        display: grid;
        gap: 10px;
    }

    .modelyear-rank-row {
        display: grid;
        grid-template-columns: 42px 90px minmax(0, 1fr) 76px 72px;
        align-items: center;
        gap: 14px;
        min-height: 46px;
        padding: 7px 10px;
        border-radius: 12px;
        background: #ffffff;
        transition: .15s ease;
    }

    .modelyear-rank-row:hover {
        background: #fafafa;
    }

    .modelyear-rank-badge {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background: #f7eeee;
        color: #75575a;
        font-size: 12px;
        font-weight: 900;
    }

    .modelyear-rank-row:nth-child(1) .modelyear-rank-badge {
        background: #fff0c8;
        color: #9b6a00;
    }

    .modelyear-rank-row:nth-child(2) .modelyear-rank-badge {
        background: #eceef1;
        color: #6e7681;
    }

    .modelyear-rank-row:nth-child(3) .modelyear-rank-badge {
        background: #f8e7d8;
        color: #a1632f;
    }

    .modelyear-rank-label {
        color: #353b45;
        font-size: 14px;
        font-weight: 800;
        white-space: nowrap;
    }

    .modelyear-rank-track {
        position: relative;
        height: 16px;
    }

    .modelyear-rank-track::before {
        content: "";
        position: absolute;
        left: 0;
        right: 0;
        top: 50%;
        height: 2px;
        transform: translateY(-50%);
        background: #eceff2;
        border-radius: 999px;
    }

    .modelyear-rank-line {
        position: absolute;
        left: 0;
        top: 50%;
        height: 3px;
        transform: translateY(-50%);
        border-radius: 999px;
        background: linear-gradient(90deg, #e5a7ab 0%, #b52d35 100%);
    }

    .modelyear-rank-dot {
        position: absolute;
        top: 50%;
        width: 14px;
        height: 14px;
        transform: translate(-50%, -50%);
        border-radius: 50%;
        background: #b52d35;
        border: 3px solid #ffffff;
        box-shadow: 0 0 0 3px #f2d8da;
    }

    .modelyear-rank-count {
        text-align: right;
        color: #a82d34;
        font-size: 14px;
        font-weight: 900;
        white-space: nowrap;
    }

    .modelyear-rank-pct {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        justify-self: end;
        min-width: 60px;
        padding: 6px 9px;
        border-radius: 999px;
        background: #f9eeee;
        color: #a82d34;
        font-size: 12px;
        font-weight: 900;
        white-space: nowrap;
    }

    .modelyear-rank-note {
        margin-top: 16px;
        color: #8a93a0;
        font-size: 12px;
        line-height: 1.5;
    }

    @media (max-width: 900px) {
        .modelyear-rank-row {
            grid-template-columns: 36px 72px minmax(0, 1fr) 64px;
            gap: 10px;
        }

        .modelyear-rank-pct {
            display: none;
        }
    }

    @media (max-width: 900px) {
        .defect-summary-value {
            font-size: 38px;
        }
    }

    /* 리콜 상세 목록: Streamlit expander 대신 native details 사용 */
    /* 판매량 연도별 Flow 타임라인 */
    /* ================================
        판매량 Flow 차트
    ================================ */

    /* 차트 전체 박스 */
    .sales-flow-card {
        position: relative;
        background: #ffffff;
        border: 1px solid #e2e5e9;
        border-radius: 16px;

        /* 기존보다 차트 영역 크게 */
        padding: 38px 42px 32px;
        min-height: 210px;

        box-sizing: border-box;
    }

    /* 가로 연결선 */
    .sales-flow-line {
        position: absolute;
        left: 9%;
        right: 9%;
        top: 98px;

        height: 4px;          /* 선도 조금 굵게 */
        background: #e1e4e8;
        border-radius: 999px;
    }

    /* 연도들을 가로로 배치 */
    .sales-flow-grid {
        position: relative;
        z-index: 2;

        display: grid;
        grid-template-columns: repeat(6, 1fr);
        align-items: start;
        width: 100%;
    }

    /* 연도 하나 */
    .sales-flow-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
    }

    /* 2020, 2021, 2022... */
    .sales-flow-year {
        font-size: 20px;      /* ← 연도 글씨 크기 */
        font-weight: 700;
        color: #596273;

        margin-bottom: 22px;
    }

    /* 동그라미 */
    .sales-flow-dot {
        width: 20px;          /* 기존보다 크게 */
        height: 20px;

        border: 4px solid #d6dae0;
        background: #ffffff;
        border-radius: 50%;

        box-sizing: border-box;
        margin-bottom: 20px;
    }

    /* 실제 데이터가 있는 동그라미 */
    .sales-flow-dot.active {
        width: 22px;
        height: 22px;

        background: #b62e34;
        border: 4px solid #ffffff;

        box-shadow:
            0 0 0 4px #f1d9da,
            0 2px 5px rgba(0, 0, 0, 0.08);
    }

    /* 17,227대 / 미확보 */
    .sales-flow-value {
        font-size: 18px;      /* ← 아래 글씨 크기 */
        font-weight: 600;
        color: #8b929e;
    }

    /* 실제 판매량 */
    .sales-flow-item.has-data .sales-flow-value {
        color: #a82c32;
        background: #f9eaea;

        padding: 9px 14px;
        border-radius: 999px;

        font-size: 18px;
        font-weight: 700;
    }

    /* 미확보 */
    .sales-flow-item.no-data .sales-flow-value {
        font-size: 18px;
        font-weight: 600;
        color: #8b929e;
    }

    @media (max-width: 800px) {
        .sales-flow-card {
            padding-left: 12px;
            padding-right: 12px;
        }
        .sales-flow-year { font-size: 12px; }
        .sales-flow-value { font-size: 11px; }
    }


    /* =========================================================
        공식 리콜 — Action Overview
       ========================================================= */
    .st-key-recall_intro {
        margin-top: 6px !important;
        margin-bottom: 16px !important;
    }

    .st-key-recall_overview {
        margin-bottom: 24px !important;
    }

    .recall-kpi-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 18px;
        margin-bottom: 28px;
    }

    .recall-kpi-card {
        background: #ffffff;
        border: 1px solid #e2e5e9;
        border-radius: 14px;
        padding: 20px 22px;
        box-sizing: border-box;
        box-shadow: 0 6px 18px rgba(20, 20, 25, 0.04);
    }

    .recall-kpi-label {
        color: #737b88;
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .recall-kpi-value {
        color: #17191d;
        font-size: 34px;
        line-height: 1.1;
        font-weight: 900;
        letter-spacing: -.03em;
    }

    .recall-kpi-note {
        margin-top: 10px;
        color: #8a93a0;
        font-size: 12px;
        line-height: 1.5;
    }

    .recall-reason-card {
        background: #ffffff;
        border: 1px solid #e2e5e9;
        border-radius: 14px;
        padding: 22px 24px 20px;
        box-sizing: border-box;
        box-shadow: 0 6px 18px rgba(20, 20, 25, 0.035);
    }

    .recall-reason-head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 18px;
    }

    .recall-reason-title {
        color: #252a31;
        font-size: 20px;
        font-weight: 900;
    }

    .recall-reason-sub {
        color: #8a93a0;
        font-size: 12px;
        font-weight: 600;
    }

    .recall-reason-row {
        display: grid;
        grid-template-columns: 150px 1fr 68px;
        align-items: center;
        gap: 14px;
        margin-bottom: 14px;
    }

    .recall-reason-row:last-child {
        margin-bottom: 0;
    }

    .recall-reason-name {
        color: #3f4652;
        font-size: 13px;
        font-weight: 800;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .recall-reason-track {
        height: 12px;
        border-radius: 999px;
        background: #f1f2f4;
        overflow: hidden;
    }

    .recall-reason-fill {
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, #c73b43 0%, #a92530 100%);
    }

    .recall-reason-pct {
        text-align: right;
        color: #a92530;
        font-size: 13px;
        font-weight: 900;
    }

    @media (max-width: 850px) {
        .recall-kpi-grid {
            grid-template-columns: 1fr;
        }

        .recall-reason-row {
            grid-template-columns: 110px 1fr 56px;
            gap: 10px;
        }
    }

    /* 리콜 캠페인 목록 제목과 첫 번째 목록 사이 여백 */
    .st-key-recall_list_title {
        margin-bottom: 16px !important;
    }

    /* 다른 모델과 비교: 선택창과 버튼 높이/정렬 통일 */
    div[data-testid="stHorizontalBlock"]:has(
        div[data-testid="stSelectbox"] label
    ) div[data-baseweb="select"] > div {
        min-height: 48px !important;
        height: 48px !important;
    }

    div[data-testid="stHorizontalBlock"]:has(
        div[data-testid="stSelectbox"] label
    ) div[data-testid="stButton"] button {
        min-height: 40px !important;
        height: 40px !important;
        width: 100% !important;
        padding: 0 16px !important;
        white-space: nowrap !important;
    }

    .recall-list {
        display: flex;
        flex-direction: column;
    }

    .recall-details {
        display: block;
        width: 100%;
        box-sizing: border-box;
        border: 1px solid #d9dde3;
        border-radius: 10px;
        background: #ffffff;
        margin: 0;
        overflow: hidden;
    }

    .recall-details summary {
        cursor: pointer;
        list-style: none;
        padding: 15px 18px;
        font-size: 15px;
        font-weight: 700;
        color: #20242c;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }

    .recall-details summary::-webkit-details-marker {
        display: none;
    }

    .recall-details summary::after {
        content: "⌄";
        flex: 0 0 auto;
        color: #6b7280;
        font-size: 18px;
        transition: transform .18s ease;
    }

    .recall-details[open] summary::after {
        transform: rotate(180deg);
    }

    .recall-details[open] summary {
        border-bottom: 1px solid #eceff3;
    }

    .recall-detail-body {
        padding: 16px 18px 18px;
        color: #3f4652;
        font-size: 14px;
        line-height: 1.75;
    }

    .recall-detail-row {
        display: grid;
        grid-template-columns: 130px 1fr;
        gap: 12px;
        padding: 4px 0;
    }

    .recall-detail-label {
        color: #6b7280;
        font-weight: 700;
    }

    .recall-detail-link {
        display: inline-block;
        margin-top: 10px;
        color: #c8102e !important;
        font-weight: 800;
        text-decoration: none !important;
    }

    .recall-detail-link:hover {
        text-decoration: underline !important;
    }

    /* =========================================================
        다른 모델과 비교 — Compare Dashboard
       ========================================================= */
    .compare-section-label {
        margin-top: 32px;      /* 이전 차트 ↔ 제목 */
        margin-bottom: 12px;   /* 제목 ↔ 설명 */
        color: #252a31;
        font-size: 18px;
        font-weight: 900;
        letter-spacing: -0.02em;
    }

    .compare-section-note {
        margin-top: 0px;
        margin-bottom: 18px;   /* 설명 ↔ 차트 */
        color: #8a93a0;
        font-size: 12px;
        line-height: 1.5;
    }

    .compare-kpi-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
        margin: 10px 0 20px;
    }

    .compare-kpi-card {
        background: #ffffff;
        border: 1px solid #e3e6ea;
        border-radius: 14px;
        padding: 16px 18px;
        box-sizing: border-box;
        box-shadow: 0 5px 16px rgba(20,20,25,.035);
    }

    .compare-kpi-title {
        color: #777f8b;
        font-size: 12px;
        font-weight: 800;
        margin-bottom: 10px;
    }

    .compare-kpi-model {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 10px;
        align-items: baseline;
        padding: 7px 0;
        border-top: 1px solid #f0f1f3;
    }

    .compare-kpi-model:first-of-type {
        border-top: 0;
    }

    .compare-kpi-name {
        color: #525a66;
        font-size: 12px;
        font-weight: 700;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .compare-kpi-value {
        color: #252a31;
        font-size: 15px;
        font-weight: 900;
        white-space: nowrap;
    }

    @media (max-width: 900px) {
        .compare-kpi-grid {
            grid-template-columns: 1fr;
        }
    }

    /* 비교 차트: 시안과 동일한 흰색 카드 느낌 */
    .st-key-compare_sales_chart,
    .st-key-compare_defect_chart,
    .st-key-compare_reason_chart {
        background: #ffffff !important;
        border: 1px solid #e7e9ed !important;
        border-radius: 14px !important;
        padding: 16px 18px 10px !important;
        box-shadow: 0 6px 18px rgba(20, 20, 25, 0.045) !important;
        box-sizing: border-box !important;
        margin-bottom: 22px !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 선택 모델 확인
# ============================================================

# S01에서 사용자가 선택한 모델의 model_key
selected_model_key = st.session_state.get("selected_model_key")

page_intro("모델 통합 상세", "판매량·제작결함 신고·공식 리콜을 모델 단위로 연결해 확인합니다.", "MODEL INSIGHT")

# 현재 서비스에서 지원하는 검증 완료 모델
verified_models = get_verified_models()

# 모델이 선택되지 않았거나 지원하지 않는 모델이면 중단
if (
    not selected_model_key
    or verified_models[
        verified_models["model_key"] == selected_model_key
    ].empty
):
    st.warning(
        "현재 서비스에서 지원하지 않거나 아직 선택되지 않은 모델입니다. "
        "모델 검색 화면에서 관심 모델을 먼저 선택해 주세요."
    )
    st.stop()


# 선택 모델 정보
model_row = verified_models[
    verified_models["model_key"] == selected_model_key
].iloc[0]

# 단일 모델 상세 화면에서 사용하는 processed 데이터
sales_df = load_vehicle_sales()
defect_df = load_defect_reports()
recall_df = load_recall()


# ============================================================
# 상단 모델 정보
# ============================================================

model_name = f"{model_row['manufacturer_std']}  {model_row['model_std']}" + (
    f" ({model_row['generation_name']})"
    if model_row["generation_name"] and str(model_row["generation_name"]) != "nan"
    else ""
)
st.markdown(
    f'<div class="ai-model-banner"><span class="ai-badge">SELECTED MODEL</span><h2>{model_name}</h2><p>검증완료 모델 · 시장 전체 등록현황은 등록현황 화면에서 별도로 확인합니다.</p></div>',
    unsafe_allow_html=True,
)
st.divider()

# ============================================================
# 1. 판매량
# ============================================================

st.subheader("판매량 — 모델의 시장 흐름 (Flow)")

# M04: 가장 최근 확인 가능한 판매량
m04 = compute_M04(
    sales_df,
    selected_model_key,
)

# 2020~2025 중 판매량 확인 가능 연도 수
confirmed_years, total_years = sales_coverage(
    sales_df,
    selected_model_key,
)

# KPI 카드 + 설명 영역
with st.container(key="sales_kpi_wrap"):
    sales_cols = st.columns(2)

    with sales_cols[0]:
        if m04 is None:
            st.metric(
                "최근 확인 판매량",
                "정보 없음",
            )
            st.caption(
                "검증된 연도별 판매량이 없습니다."
            )
        else:
            m04_year, m04_count, m04_status = m04

            st.metric(
                f"최근 확인 판매량 ({m04_year}년)",
                fmt_count(m04_count),
            )
            st.caption(
                f"검증상태 {m04_status}"
            )

    with sales_cols[1]:
        st.metric(
            "판매 연도",
            (
                f"{ANALYSIS_YEAR_START}–{ANALYSIS_YEAR_END} 중 "
                f"{confirmed_years}개 연도 확인"
            ),
        )
        st.caption(
            "※ 판매량이 확인되지 않은 연도는 "
            "0대로 처리하지 않습니다."
        )


# ------------------------------------------------------------
# 연도별 판매량
# ------------------------------------------------------------

with st.container(key="sales_chart_title"):
    st.markdown("**연도별 국내 판매량 추이**")

m05_df = compute_M05(
    sales_df,
    selected_model_key,
)

m05_present = m05_df[
    m05_df["domestic_sales_count"].notna()
]

if m05_present.empty:
    st.caption(
        "확인된 연도별 판매량이 없습니다."
    )

else:
    sales_by_year = {
        int(row["sales_year"]): int(row["domestic_sales_count"])
        for _, row in m05_present.iterrows()
    }

    timeline_items = []

    for year in range(ANALYSIS_YEAR_START, ANALYSIS_YEAR_END + 1):
        if year in sales_by_year:
            value = f"{sales_by_year[year]:,}대"
            item_class = "sales-flow-item has-data"
            dot_class = "sales-flow-dot active"
        else:
            value = "미확보"
            item_class = "sales-flow-item no-data"
            dot_class = "sales-flow-dot"

        timeline_items.append(
            f'<div class="{item_class}">'
            f'<div class="sales-flow-year">{year}</div>'
            f'<div class="{dot_class}"></div>'
            f'<div class="sales-flow-value">{value}</div>'
            f'</div>'
        )

    sales_flow_html = (
        f'<div class="sales-flow-card">'
        f'<div class="sales-flow-line"></div>'
        f'<div class="sales-flow-grid">{"".join(timeline_items)}</div>'
        f'</div>'
    )

    # 타임라인 카드
    with st.container(key="sales_flow_wrap"):
        st.markdown(
            sales_flow_html,
            unsafe_allow_html=True,
        )

    missing_years = sorted(
        set(
            range(
                ANALYSIS_YEAR_START,
                ANALYSIS_YEAR_END + 1,
            )
        )
        - set(m05_present["sales_year"])
    )

    # 미확보 연도 안내
    # 안내 문구가 없는 경우에도 타임라인과 표 사이 간격을 동일하게 유지합니다.
    with st.container(key="sales_missing_note"):
        if missing_years:
            st.caption(
                f"※ {', '.join(str(y) for y in missing_years)}년은 "
                "확인된 판매량이 없어 그래프에 미표시"
            )
        else:
            st.markdown(
                '<div style="height:18px;"></div>',
                unsafe_allow_html=True,
            )

    display_m05 = m05_present.rename(
        columns={
            "sales_year": "연도",
            "domestic_sales_count": "판매량",
            "verification_status": "검증상태",
            "source_url": "출처",
        }
    )

    # 표
    with st.container(key="sales_table_wrap"):
        st.dataframe(
            display_m05[
                ["연도", "판매량", "검증상태", "출처"]
            ],
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# 2. 소비자 제작결함 신고
# ============================================================

def format_year_ranges(years):
    """[2020, 2021, 2022, 2024, 2025] -> '2020–2022, 2024–2025'"""
    years = sorted({int(y) for y in years if pd.notna(y)})

    if not years:
        return "정보 없음"

    parts = []
    start = prev = years[0]

    for year in years[1:]:
        if year == prev + 1:
            prev = year
            continue

        parts.append(str(start) if start == prev else f"{start}–{prev}")
        start = prev = year

    parts.append(str(start) if start == prev else f"{start}–{prev}")

    return ", ".join(parts)


st.subheader(
    "소비자 제작결함 신고 — 이상 신호 (Signal)"
)

# 제목 아래 설명은 한 덩어리로 묶어 간격을 정리합니다.
with st.container(key="defect_intro"):
    st.caption(
        "소비자 신고 신호이며, 공식 결함판정이 아니에요."
    )
    st.caption(
        "※ 현재 원천 데이터에는 신고 사유·내용이 제공되지 않아 "
        "결함 사유 분석은 제공하지 않습니다."
    )


# M06: 분석기간 내 전체 결함신고 건수
m06 = compute_M06(
    defect_df,
    selected_model_key,
)

# 접수연도별 신고 추이
m07_df = compute_M07(
    defect_df,
    selected_model_key,
)

m07_present = m07_df[
    m07_df["신고건수"].notna()
]

# 데이터의 상태값을 기준으로 확보/미확보 연도를 동적으로 계산합니다.
available_years = (
    m07_df.loc[
        m07_df["상태"] != "데이터 미확보",
        "접수연도",
    ]
    .dropna()
    .astype(int)
    .tolist()
)

missing = (
    m07_df.loc[
        m07_df["상태"] == "데이터 미확보",
        "접수연도",
    ]
    .dropna()
    .astype(int)
    .tolist()
)

available_year_text = format_year_ranges(available_years)
missing_year_text = format_year_ranges(missing)

if missing:
    missing_badge_text = f"{missing_year_text}년 원천 미확보 · 0건 아님"
else:
    missing_badge_text = "전체 분석연도 원천 확보"


# 요약 + 차트를 하나의 Overview 카드 안에 배치
with st.container(border=True, key="defect_overview"):
    overview_cols = st.columns([0.62, 1.55], gap="medium")

    # 왼쪽: 신고 건수 요약
    with overview_cols[0]:
        st.markdown(
            (
                '<span class="defect-summary-kicker">SIGNAL SUMMARY</span>'
                '<div class="defect-summary-title">결함신고 건수</div>'
                f'<div class="defect-summary-value">{m06:,}건</div>'
                '<div class="defect-info-box">'
                '<strong>분석 원천</strong><br>'
                f'{available_year_text}'
                '</div>'
                '<div class="defect-missing-badge">'
                f'{missing_badge_text}'
                '</div>'
            ),
            unsafe_allow_html=True,
        )

    # 오른쪽: 연도별 신고 추이
    with overview_cols[1]:
        with st.container(key="defect_chart_title"):
            st.markdown("**접수연도별 신고 추이**")

        if m07_present.empty:
            st.caption(
                "확인된 접수연도별 신고 건수가 없습니다."
            )
        else:
            # 접수연도별 신고 추이는 얇은 막대 + 연한 그리드로 표시합니다.
            thinbar_items = []
            max_count = int(m07_present["신고건수"].max()) if not m07_present.empty else 1

            for _, row in m07_present.iterrows():
                year = int(row["접수연도"])
                count = int(row["신고건수"])
                height_pct = (count / max_count * 100) if max_count else 0

                thinbar_items.append(
                    f'<div class="defect-thinbar-item">'
                    f'<div class="defect-thinbar-value">{count:,}건</div>'
                    f'<div class="defect-thinbar-plot">'
                    f'<div class="defect-thinbar-bar" style="height:{height_pct:.1f}%"></div>'
                    f'</div>'
                    f'<div class="defect-thinbar-year">{year}</div>'
                    f'</div>'
                )

            defect_thinbar_html = (
                f'<div class="defect-thinbar-card">'
                f'<div class="defect-thinbar-grid-bg"></div>'
                f'<div class="defect-thinbar-grid">{"".join(thinbar_items)}</div>'
                f'</div>'
            )

            st.markdown(
                defect_thinbar_html,
                unsafe_allow_html=True,
            )

        if missing:
            with st.container(key="defect_chart_note"):
                st.caption(
                    f"※ {', '.join(str(y) for y in missing)}년: "
                    "데이터 미확보 (0건 아님)"
                )


# ------------------------------------------------------------
# 모델년도별 신고 분포
# ------------------------------------------------------------

st.write("")
st.markdown(
    "**모델년도별 신고 분포**"
)

m08_df = compute_M08_model_year(
    defect_df,
    selected_model_key,
)

if m08_df.empty:
    st.caption(
        "모델년도별 신고 분포 데이터가 없습니다."
    )

else:
    # 모델년도별 신고 분포는 "랭킹 + 비중" 카드형으로 표시합니다.
    # 기존 데이터 순서를 유지하면서 건수/비중을 함께 보여줍니다.
    m08_show = m08_df.copy()
    m08_show["신고건수"] = pd.to_numeric(
        m08_show["신고건수"],
        errors="coerce",
    ).fillna(0)

    total_modelyear_count = int(m08_show["신고건수"].sum())
    max_modelyear_count = int(m08_show["신고건수"].max()) if not m08_show.empty else 1

    rank_rows = []

    for idx, (_, row) in enumerate(m08_show.iterrows(), start=1):
        label = html.escape(str(row["model_year_label"]))
        count = int(row["신고건수"])

        width_pct = (
            count / max_modelyear_count * 100
            if max_modelyear_count
            else 0
        )

        share_pct = (
            count / total_modelyear_count * 100
            if total_modelyear_count
            else 0
        )

        rank_rows.append(
            f'<div class="modelyear-rank-row">'
            f'<div class="modelyear-rank-badge">{idx}</div>'
            f'<div class="modelyear-rank-label">{label}</div>'
            f'<div class="modelyear-rank-track">'
            f'<div class="modelyear-rank-line" style="width:{width_pct:.1f}%"></div>'
            f'<div class="modelyear-rank-dot" style="left:{width_pct:.1f}%"></div>'
            f'</div>'
            f'<div class="modelyear-rank-count">{count:,}건</div>'
            f'<div class="modelyear-rank-pct">{share_pct:.1f}%</div>'
            f'</div>'
        )

    modelyear_html = (
        f'<div class="modelyear-rank-card">'
        f'<div class="modelyear-rank-grid">{"".join(rank_rows)}</div>'
        f'<div class="modelyear-rank-note">'
        f'※ 모델년도 미입력 또는 확인 불가 건은 ‘미상’으로 분류'
        f'</div>'
        f'</div>'
    )

    st.markdown(
        modelyear_html,
        unsafe_allow_html=True,
    )



st.divider()


# ============================================================
# 3. 공식 리콜
# ============================================================

st.subheader(
    "공식 리콜 — 제작사의 안전조치 (Action)"
)

with st.container(key="recall_intro"):
    st.caption(
        f"분석 기준: 리콜개시일 "
        f"{ANALYSIS_YEAR_START}–{ANALYSIS_YEAR_END}"
    )

# M09: 리콜 캠페인 수
m09 = compute_M09(
    recall_df,
    selected_model_key,
)

# M10: 리콜 대상대수 합계
m10 = compute_M10(
    recall_df,
    selected_model_key,
)

# 리콜 사유 구성
reason_df = compute_M11_M12(
    recall_df,
    selected_model_key,
)

with st.container(key="recall_overview"):

    # 상단 KPI 2개
    recall_kpi_html = (
        f'<div class="recall-kpi-grid">'
        f'<div class="recall-kpi-card">'
        f'<div class="recall-kpi-label">리콜 캠페인</div>'
        f'<div class="recall-kpi-value">{m09:,}건</div>'
        f'</div>'
        f'<div class="recall-kpi-card">'
        f'<div class="recall-kpi-label">리콜 대상대수 합계</div>'
        f'<div class="recall-kpi-value">{fmt_count(m10)}</div>'
        f'<div class="recall-kpi-note">※ 여러 캠페인에 동일 차량이 중복 포함될 수 있습니다.</div>'
        f'</div>'
        f'</div>'
    )

    st.markdown(
        recall_kpi_html,
        unsafe_allow_html=True,
    )

    # 리콜 사유 구성
    if reason_df.empty:
        st.info(
            "확인된 공식 리콜 캠페인이 없습니다."
        )
    else:
        reason_rows = []

        for _, row in reason_df.iterrows():
            name = html.escape(str(row["recall_category"]))
            pct = float(row["비중(%)"])

            reason_rows.append(
                f'<div class="recall-reason-row">'
                f'<div class="recall-reason-name">{name}</div>'
                f'<div class="recall-reason-track">'
                f'<div class="recall-reason-fill" style="width:{max(0, min(pct, 100)):.1f}%"></div>'
                f'</div>'
                f'<div class="recall-reason-pct">{pct:.1f}%</div>'
                f'</div>'
            )

        recall_reason_html = (
            f'<div class="recall-reason-card">'
            f'<div class="recall-reason-head">'
            f'<div class="recall-reason-title">리콜 사유 구성</div>'
            f'<div class="recall-reason-sub">캠페인 수 기준</div>'
            f'</div>'
            f'{"".join(reason_rows)}'
            f'</div>'
        )

        st.markdown(
            recall_reason_html,
            unsafe_allow_html=True,
        )

st.divider()


# ============================================================
# 4. 리콜 캠페인 상세 목록
# ============================================================

with st.container(key="recall_list_title"):
    st.subheader(
        "리콜 캠페인 목록 (최신순) / 상세"
    )

sub_recalls = model_recalls(
    recall_df,
    selected_model_key,
).sort_values(
    "recall_start_date",
    ascending=False,
)


# 일부 캠페인에서 생산기간이 누락된 경우 안내
if has_production_period_gap(
    recall_df,
    selected_model_key,
):
    st.caption(
        "※ 일부 캠페인은 생산기간 정보가 "
        "제공되지 않았습니다. (ST-08)"
    )


if sub_recalls.empty:
    st.caption(
        "표시할 리콜 캠페인이 없습니다."
    )

else:
    recall_detail_blocks = []

    for _, r in sub_recalls.iterrows():
        model_original = html.escape(str(r.get("model_original", "") or ""))
        recall_category = html.escape(str(r.get("recall_category", "") or ""))
        recall_date = html.escape(fmt_date(r.get("recall_start_date")))
        manufacturer = html.escape(str(r.get("manufacturer", "") or ""))

        reason = r.get("recall_reason")
        reason_text = (
            str(reason)
            if reason and str(reason) != "nan"
            else "리콜사유 미제공"
        )
        reason_text = html.escape(reason_text)

        production_from = html.escape(fmt_date(r.get("production_from")))
        production_to = html.escape(fmt_date(r.get("production_to")))
        recall_count = html.escape(fmt_count(r.get("recall_count")))

        official_url = r.get("official_check_url")
        if official_url and str(official_url) != "nan":
            safe_url = html.escape(str(official_url), quote=True)
            link_html = (
                f'<a class="recall-detail-link" href="{safe_url}" '
                f'target="_blank" rel="noopener noreferrer">'
                f'자동차리콜센터에서 공식 확인 →</a>'
            )
        else:
            link_html = '<span style="color:#8a93a0;">공식 확인 URL 미제공</span>'

        details_html = (
            f'<details class="recall-details">'
            f'<summary>'
            f'<span>{model_original} · {recall_category} · {recall_date}</span>'
            f'</summary>'
            f'<div class="recall-detail-body">'
            f'<div class="recall-detail-row"><span class="recall-detail-label">제작사</span><span>{manufacturer}</span></div>'
            f'<div class="recall-detail-row"><span class="recall-detail-label">원본 차명</span><span>{model_original}</span></div>'
            f'<div class="recall-detail-row"><span class="recall-detail-label">사유 유형</span><span>{recall_category}</span></div>'
            f'<div class="recall-detail-row"><span class="recall-detail-label">공식 리콜사유</span><span>{reason_text}</span></div>'
            f'<div class="recall-detail-row"><span class="recall-detail-label">대상 생산기간</span><span>{production_from} ~ {production_to}</span></div>'
            f'<div class="recall-detail-row"><span class="recall-detail-label">리콜개시일</span><span>{recall_date}</span></div>'
            f'<div class="recall-detail-row"><span class="recall-detail-label">리콜 대상대수</span><span>{recall_count}</span></div>'
            f'{link_html}'
            f'</div>'
            f'</details>'
        )

        recall_detail_blocks.append(details_html)

    recall_list_html = (
        f'<div class="recall-list">'
        f'{"".join(recall_detail_blocks)}'
        f'</div>'
    )

    st.markdown(
        recall_list_html,
        unsafe_allow_html=True,
    )


st.divider()


# ============================================================
# 5. 다른 모델과 비교
# ============================================================

with st.container(key="compare_title"):
    st.subheader("다른 모델과 비교")

# 현재 보고 있는 모델은 비교 후보에서 제외
other_models = verified_models[
    verified_models["model_key"] != selected_model_key
]

compare_labels = {
    model_label(
        row["manufacturer_std"],
        row["model_std"],
        row["generation_name"],
    ): row["model_key"]
    for _, row in other_models.iterrows()
}


def _compare_grouped_bar(df, x_col, value_cols, height=260):
    """두 모델 값을 겹치지 않는 그룹형 막대로 비교합니다."""
    chart_df = (
        df.reset_index()
        if df.index.name == x_col
        else df.copy()
    )

    long_df = chart_df.melt(
        id_vars=[x_col],
        value_vars=value_cols,
        var_name="모델",
        value_name="값",
    )

    long_df[x_col] = long_df[x_col].astype(str)

    chart = (
        alt.Chart(long_df)
        .mark_bar(
            size=26,
            cornerRadiusTopLeft=4,
            cornerRadiusTopRight=4,
        )
        .encode(
            x=alt.X(
                f"{x_col}:N",
                title=None,
                axis=alt.Axis(
                    labelAngle=0,
                    labelColor="#737b88",
                    labelFontSize=12,
                    tickSize=0,
                    domain=False,
                ),
            ),
            xOffset=alt.XOffset("모델:N"),
            y=alt.Y(
                "값:Q",
                title=None,
                axis=alt.Axis(
                    grid=True,
                    gridColor="#eef0f3",
                    gridOpacity=1,
                    labelColor="#8a93a0",
                    labelFontSize=11,
                    tickSize=0,
                    domain=False,
                    format=",",
                ),
            ),
            color=alt.Color(
                "모델:N",
                scale=alt.Scale(
                    range=["#b52d35", "#607895"],
                ),
                legend=alt.Legend(
                    title=None,
                    orient="bottom",
                    labelColor="#687180",
                    labelFontSize=12,
                    symbolType="circle",
                ),
            ),
            tooltip=[
                alt.Tooltip(f"{x_col}:N", title=x_col),
                alt.Tooltip("모델:N", title="모델"),
                alt.Tooltip("값:Q", title="값", format=","),
            ],
        )
        .properties(
            height=height,
            padding={"left": 18, "right": 18, "top": 18, "bottom": 18},
        )
        .configure_view(strokeWidth=0)
    )

    st.altair_chart(chart, use_container_width=True)
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)


def _compare_line_chart(df, x_col, value_cols, height=260):
    """연도 흐름 비교는 선 + 포인트로 보여줍니다."""
    chart_df = (
        df.reset_index()
        if df.index.name == x_col
        else df.copy()
    )

    long_df = chart_df.melt(
        id_vars=[x_col],
        value_vars=value_cols,
        var_name="모델",
        value_name="값",
    )

    long_df[x_col] = long_df[x_col].astype(str)

    base = alt.Chart(long_df).encode(
        x=alt.X(
            f"{x_col}:N",
            title=None,
            axis=alt.Axis(
                labelAngle=0,
                labelColor="#737b88",
                labelFontSize=12,
                tickSize=0,
                domain=False,
            ),
        ),
        y=alt.Y(
            "값:Q",
            title=None,
            axis=alt.Axis(
                grid=True,
                gridColor="#eef0f3",
                gridOpacity=1,
                labelColor="#8a93a0",
                labelFontSize=11,
                tickSize=0,
                domain=False,
                format=",",
            ),
        ),
        color=alt.Color(
            "모델:N",
            scale=alt.Scale(
                range=["#b52d35", "#607895"],
            ),
            legend=alt.Legend(
                title=None,
                orient="bottom",
                labelColor="#687180",
                labelFontSize=12,
                symbolType="circle",
            ),
        ),
        tooltip=[
            alt.Tooltip(f"{x_col}:N", title=x_col),
            alt.Tooltip("모델:N", title="모델"),
            alt.Tooltip("값:Q", title="신고건수", format=","),
        ],
    )

    line = base.mark_line(strokeWidth=3)
    points = base.mark_circle(size=85, stroke="white", strokeWidth=2)

    st.altair_chart(
        (line + points)
        .properties(
            height=height,
            padding={"left": 18, "right": 18, "top": 18, "bottom": 18},
        )
        .configure_view(strokeWidth=0),
        use_container_width=True,
    )


def _compare_reason_chart(a_reason, b_reason, a_label, b_label):
    """리콜 사유별 캠페인 수를 한눈에 비교하는 컴팩트한 카드형 막대차트."""
    rows = []

    if not a_reason.empty:
        for _, row in a_reason.iterrows():
            rows.append(
                {
                    "리콜 사유": str(row["recall_category"]),
                    "모델": a_label,
                    "캠페인 수": int(row["campaign_count"]),
                }
            )

    if not b_reason.empty:
        for _, row in b_reason.iterrows():
            rows.append(
                {
                    "리콜 사유": str(row["recall_category"]),
                    "모델": b_label,
                    "캠페인 수": int(row["campaign_count"]),
                }
            )

    if not rows:
        st.caption("두 모델 모두 확인된 리콜 캠페인이 없습니다.")
        return

    reason_df = pd.DataFrame(rows)

    # 모든 사유 × 두 모델 조합을 만들어 0건도 명시적으로 보여줍니다.
    categories = (
        reason_df.groupby("리콜 사유")["캠페인 수"]
        .sum()
        .sort_values(ascending=False)
        .index
        .tolist()
    )

    model_order = [a_label, b_label]

    full_index = pd.MultiIndex.from_product(
        [categories, model_order],
        names=["리콜 사유", "모델"],
    )

    reason_full = (
        reason_df.set_index(["리콜 사유", "모델"])
        .reindex(full_index, fill_value=0)
        .reset_index()
    )

    max_count = max(int(reason_full["캠페인 수"].max()), 1)

    # 배경 트랙
    track = (
        alt.Chart(reason_full)
        .mark_bar(
            size=14,
            cornerRadius=7,
            color="#f1f2f4",
        )
        .encode(
            y=alt.Y(
                "리콜 사유:N",
                sort=categories,
                title=None,
                axis=alt.Axis(
                    labelColor="#525a66",
                    labelFontSize=12,
                    labelLimit=180,
                    tickSize=0,
                    domain=False,
                ),
            ),
            yOffset=alt.YOffset(
                "모델:N",
                sort=model_order,
            ),
            x=alt.X(
                "max_count:Q",
                title=None,
                scale=alt.Scale(domain=[0, max_count]),
                axis=None,
            ),
        )
        .transform_calculate(
            max_count=str(max_count)
        )
    )

    # 실제 값 막대
    bars = (
        alt.Chart(reason_full)
        .mark_bar(
            size=14,
            cornerRadius=7,
        )
        .encode(
            y=alt.Y(
                "리콜 사유:N",
                sort=categories,
                title=None,
                axis=alt.Axis(
                    labelColor="#525a66",
                    labelFontSize=12,
                    labelLimit=180,
                    tickSize=0,
                    domain=False,
                ),
            ),
            yOffset=alt.YOffset(
                "모델:N",
                sort=model_order,
            ),
            x=alt.X(
                "캠페인 수:Q",
                title=None,
                scale=alt.Scale(domain=[0, max_count]),
                axis=None,
            ),
            color=alt.Color(
                "모델:N",
                scale=alt.Scale(
                    domain=model_order,
                    range=["#b52d35", "#607895"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("리콜 사유:N", title="리콜 사유"),
                alt.Tooltip("모델:N", title="모델"),
                alt.Tooltip("캠페인 수:Q", title="캠페인 수"),
            ],
        )
    )

    # 막대 끝 숫자
    labels = (
        alt.Chart(reason_full)
        .mark_text(
            align="left",
            baseline="middle",
            dx=8,
            fontSize=11,
            fontWeight=700,
            color="#5f6672",
        )
        .encode(
            y=alt.Y(
                "리콜 사유:N",
                sort=categories,
            ),
            yOffset=alt.YOffset(
                "모델:N",
                sort=model_order,
            ),
            x=alt.X(
                "캠페인 수:Q",
                scale=alt.Scale(domain=[0, max_count]),
            ),
            text=alt.Text(
                "캠페인 수:Q",
                format="d",
            ),
        )
    )

    chart = (
        (track + bars + labels)
        .properties(
            height=max(170, len(categories) * 54),
            padding={
                "left": 18,
                "right": 36,
                "top": 26,
                "bottom": 24,
            },
        )
        .configure_view(strokeWidth=0)
    )

    legend_html = (
        '<div style="display:flex; gap:18px; align-items:center; '
        'margin:4px 0 22px 8px; color:#687180; font-size:12px;">'
        f'<span><span style="display:inline-block;width:10px;height:10px;'
        f'border-radius:50%;background:#b52d35;margin-right:6px;"></span>{html.escape(a_label)}</span>'
        f'<span><span style="display:inline-block;width:10px;height:10px;'
        f'border-radius:50%;background:#607895;margin-right:6px;"></span>{html.escape(b_label)}</span>'
        '</div>'
    )

    st.markdown(legend_html, unsafe_allow_html=True)
    st.altair_chart(chart, use_container_width=True)

cmp_cols = st.columns(
    [8, 1],
    gap="small",
    vertical_alignment="bottom",
)

with cmp_cols[0]:
    compare_label = st.selectbox(
        "비교 모델 선택",
        ["비교 모델 선택"] + list(compare_labels.keys()),
        label_visibility="collapsed",
    )

with cmp_cols[1]:
    compare_clicked = st.button(
        "비교하기",
        use_container_width=True,
    )


if (
    compare_clicked
    and compare_label != "비교 모델 선택"
):
    compare_key = compare_labels[compare_label]

    try:
        # DB에서 모델 비교에 필요한 데이터를 조회
        compare_result = compare_models(
            selected_model_key,
            compare_key,
        )

        a_label = model_label(
            model_row["manufacturer_std"],
            model_row["model_std"],
            model_row["generation_name"],
        )
        b_label = compare_label

        # ----------------------------------------------------
        # 판매량 비교
        # ----------------------------------------------------
        st.markdown(
            '<div class="compare-section-label">판매량 비교</div>'
            '<div class="compare-section-note">'
            '두 모델 모두 검증된 동일 연도만 비교합니다.'
            '</div>',
            unsafe_allow_html=True,
        )

        sales_common = compare_result["sales_common"]

        if sales_common.empty:
            st.caption(
                "두 모델이 공통으로 검증된 연도가 없어 "
                "판매량은 비교할 수 없습니다."
            )
        else:
            cmp_sales = sales_common.rename(
                columns={
                    "sales_year": "연도",
                    "model_a_sales": a_label,
                    "model_b_sales": b_label,
                }
            ).set_index("연도")

            with st.container(key="compare_sales_chart"):
                _compare_grouped_bar(
                    cmp_sales,
                    "연도",
                    [a_label, b_label],
                    height=250,
                )

        # ----------------------------------------------------
        # 결함신고 비교
        # ----------------------------------------------------
        st.markdown(
            '<div class="compare-section-label">결함신고 비교</div>'
            '<div class="compare-section-note">'
            '공통 확보 접수연도 기준이며 2023년은 제외합니다.'
            '</div>',
            unsafe_allow_html=True,
        )

        defect_a = compare_result["defect_yearly_a"]
        defect_b = compare_result["defect_yearly_b"]

        common_defect_years = [
            2020,
            2021,
            2022,
            2024,
            2025,
        ]

        a_counts = dict(
            zip(
                defect_a["report_year"],
                defect_a["defect_count"],
            )
        )
        b_counts = dict(
            zip(
                defect_b["report_year"],
                defect_b["defect_count"],
            )
        )

        cmp_defect = pd.DataFrame(
            {
                "연도": common_defect_years,
                a_label: [
                    int(a_counts.get(year, 0))
                    for year in common_defect_years
                ],
                b_label: [
                    int(b_counts.get(year, 0))
                    for year in common_defect_years
                ],
            }
        ).set_index("연도")

        with st.container(key="compare_defect_chart"):
            _compare_line_chart(
                cmp_defect,
                "연도",
                [a_label, b_label],
                height=250,
            )

        # ----------------------------------------------------
        # 리콜 비교
        # ----------------------------------------------------
        st.markdown(
            '<div class="compare-section-label">리콜 비교</div>',
            unsafe_allow_html=True,
        )

        recall_a = compare_result["recall_a"]
        recall_b = compare_result["recall_b"]

        # 표 대신 핵심 3개 지표를 카드형으로 비교
        recall_compare_html = (
            '<div class="compare-kpi-grid">'

            '<div class="compare-kpi-card">'
            '<div class="compare-kpi-title">리콜 캠페인 수</div>'
            f'<div class="compare-kpi-model"><span class="compare-kpi-name">{html.escape(a_label)}</span>'
            f'<span class="compare-kpi-value">{int(recall_a["campaign_count"]):,}건</span></div>'
            f'<div class="compare-kpi-model"><span class="compare-kpi-name">{html.escape(b_label)}</span>'
            f'<span class="compare-kpi-value">{int(recall_b["campaign_count"]):,}건</span></div>'
            '</div>'

            '<div class="compare-kpi-card">'
            '<div class="compare-kpi-title">리콜 대상대수 합계</div>'
            f'<div class="compare-kpi-model"><span class="compare-kpi-name">{html.escape(a_label)}</span>'
            f'<span class="compare-kpi-value">{fmt_count(recall_a["recall_target_sum"])}</span></div>'
            f'<div class="compare-kpi-model"><span class="compare-kpi-name">{html.escape(b_label)}</span>'
            f'<span class="compare-kpi-value">{fmt_count(recall_b["recall_target_sum"])}</span></div>'
            '</div>'

            '<div class="compare-kpi-card">'
            '<div class="compare-kpi-title">최근 리콜일</div>'
            f'<div class="compare-kpi-model"><span class="compare-kpi-name">{html.escape(a_label)}</span>'
            f'<span class="compare-kpi-value">{fmt_date(recall_a["latest_recall_date"])}</span></div>'
            f'<div class="compare-kpi-model"><span class="compare-kpi-name">{html.escape(b_label)}</span>'
            f'<span class="compare-kpi-value">{fmt_date(recall_b["latest_recall_date"])}</span></div>'
            '</div>'

            '</div>'
        )

        st.markdown(
            recall_compare_html,
            unsafe_allow_html=True,
        )

        # ----------------------------------------------------
        # 리콜 사유 구성 비교
        # ----------------------------------------------------
        st.markdown(
            '<div class="compare-section-label">리콜 사유 구성</div>'
            '<div class="compare-section-note">'
            '두 모델의 캠페인 수를 동일한 축에서 비교합니다.'
            '</div>',
            unsafe_allow_html=True,
        )

        a_reason = compare_result["recall_categories_a"]
        b_reason = compare_result["recall_categories_b"]

        with st.container(key="compare_reason_chart"):
            _compare_reason_chart(
                a_reason,
                b_reason,
                a_label,
                b_label,
            )

        st.caption(
            "※ 최근 확인 판매량(M04) KPI는 모델마다 "
            "기준연도가 달라질 수 있어 직접 비교하지 않아요. "
            "비교는 안전성 우열·구매추천이 아니에요."
        )

    except Exception as e:
        st.error(
            f"모델 비교 데이터를 불러오지 못했습니다: {e}"
        )

st.divider()

# ============================================================
# 6. FAQ / 출처 / 해석 안내
# ============================================================

with st.container(key="faq_title"):
    st.subheader(
        "FAQ / 출처 / 해석 안내"
    )

with st.container(key="faq_button"):
    if st.button(
        "💬 리콜 FAQ / 공식 안내 보기 →"
    ):
        st.switch_page(
            "pages/S04_FAQ.py"
        )

# ------------------------------------------------------------
# 판매 출처
# ------------------------------------------------------------

sales_source = None
sales_loaded = "정보 없음"

if not m05_df.empty:
    non_null_source = m05_df[
        m05_df["source_url"].notna()
    ]

    if not non_null_source.empty:
        _row = non_null_source.iloc[-1]

        sales_source = _row[
            "source_url"
        ]

        sales_loaded = _row.get(
            "loaded_at",
            "정보 없음",
        )


# ------------------------------------------------------------
# 결함신고 출처
# ------------------------------------------------------------

defect_source = None
defect_loaded = "정보 없음"

_def_rows = model_defects(
    defect_df,
    selected_model_key,
)

if not _def_rows.empty:
    defect_source = _def_rows.iloc[0].get(
        "source_url"
    )

    defect_loaded = _def_rows.iloc[0].get(
        "loaded_at",
        "정보 없음",
    )


# ------------------------------------------------------------
# 리콜 출처
# ------------------------------------------------------------

recall_source = None
recall_loaded = "정보 없음"

if not sub_recalls.empty:
    recall_source = sub_recalls.iloc[0].get(
        "source_url"
    )

    recall_loaded = sub_recalls.iloc[0].get(
        "loaded_at",
        "정보 없음",
    )


# ------------------------------------------------------------
# 출처 표시
# ------------------------------------------------------------

source_caption(
    sales_source,
    sales_loaded,
    label="판매 출처",
)

source_caption(
    defect_source,
    defect_loaded,
    label=(
        "결함신고 출처"
        "(한국교통안전공단 제작결함신고)"
    ),
)

source_caption(
    recall_source,
    recall_loaded,
    label=(
        "리콜 출처"
        "(한국교통안전공단 리콜)"
    ),
)


# 서로 다른 기준의 데이터를 억지로 나누어 비율을 만들지 않음
st.caption(
    "※ 판매량·결함신고·리콜대수·전국 등록대수를 "
    "서로 나눈 결함률/리콜률은 표시하지 않아요."
)

# FAQ / 출처 영역과 푸터 사이 여백
st.markdown(
    '<div style="height:34px;"></div>',
    unsafe_allow_html=True,
)
site_footer()