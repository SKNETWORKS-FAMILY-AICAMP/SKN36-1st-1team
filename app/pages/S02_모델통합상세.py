
import sys
from pathlib import Path

# ------------------------------------------------------------
# 경로 설정
# ------------------------------------------------------------
# app/pages에서 실행해도 프로젝트 루트의 src와 app/lib를 찾을 수 있게 설정
PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = Path(__file__).resolve().parents[1]

sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(APP_ROOT))

import pandas as pd
import streamlit as st

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


# ============================================================
# 선택 모델 확인
# ============================================================

# S01에서 사용자가 선택한 모델의 model_key
selected_model_key = st.session_state.get("selected_model_key")

st.title("🚘 모델 통합 상세")

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
        "아래 Home으로 이동해서 관심 모델을 먼저 검색해 주세요."
    )
    st.page_link("app.py", label="🏠 Home")
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

header_cols = st.columns([5, 1])

with header_cols[0]:
    st.subheader(
        f"{model_row['manufacturer_std']}  {model_row['model_std']}"
        + (
            f" ({model_row['generation_name']})"
            if model_row["generation_name"]
            and str(model_row["generation_name"]) != "nan"
            else ""
        )
    )

    st.caption(
        "※ 시장 전체 등록현황은 모델 검색 / 등록현황 상세에서 확인하세요."
    )

with header_cols[1]:
    if st.button("🏠 Home"):
        st.switch_page("app.py")


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

st.markdown("**연도별 국내 판매량 추이**")

m05_df = compute_M05(
    sales_df,
    selected_model_key,
)

# 판매량 값이 실제 존재하는 연도만 그래프 표시
m05_present = m05_df[
    m05_df["domestic_sales_count"].notna()
]

if m05_present.empty:
    st.caption(
        "확인된 연도별 판매량이 없습니다."
    )

else:
    chart_series = m05_present.set_index(
        m05_present["sales_year"].astype(str)
    )["domestic_sales_count"]

    # x_label_angle=0 → 연도 숫자를 가로로 표시
    static_bar_chart(
        chart_series,
        height=280,
        sort=False,
        x_label_angle=0,
    )

    # 판매량이 없는 연도는 0이 아니라 미확보로 처리
    missing_years = sorted(
        set(
            range(
                ANALYSIS_YEAR_START,
                ANALYSIS_YEAR_END + 1,
            )
        )
        - set(m05_present["sales_year"])
    )

    if missing_years:
        st.caption(
            f"※ {', '.join(str(y) for y in missing_years)}년은 "
            "확인된 판매량이 없어 그래프에 미표시"
        )

    display_m05 = m05_present.rename(
        columns={
            "sales_year": "연도",
            "domestic_sales_count": "판매량",
            "verification_status": "검증상태",
            "source_url": "출처",
        }
    )

    st.dataframe(
        display_m05[
            ["연도", "판매량", "검증상태", "출처"]
        ],
        hide_index=True,
        width="stretch",
    )


st.divider()


# ============================================================
# 2. 소비자 제작결함 신고
# ============================================================

st.subheader(
    "소비자 제작결함 신고 — 이상 신호 (Signal)"
)

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

def_cols = st.columns(2)


with def_cols[0]:
    st.metric(
        "결함신고 건수",
        f"{m06:,}건",
    )

    st.caption(
        f"분석 원천: {ANALYSIS_YEAR_START}–2022, "
        f"2024–{ANALYSIS_YEAR_END}"
    )

    st.caption(
        "※ 2023은 원천 미확보이며 0건이 아니에요."
    )


# ------------------------------------------------------------
# 접수연도별 신고 추이
# ------------------------------------------------------------

with def_cols[1]:
    st.markdown(
        "**접수연도별 신고 추이**"
    )

    m07_df = compute_M07(
        defect_df,
        selected_model_key,
    )

    m07_present = m07_df[
        m07_df["신고건수"].notna()
    ]

    if m07_present.empty:
        st.caption(
            "확인된 접수연도별 신고 건수가 없습니다."
        )

    else:
        chart_series = m07_present.set_index(
            m07_present["접수연도"].astype(str)
        )["신고건수"]

        # 연도 숫자 가로 표시
        static_bar_chart(
            chart_series,
            height=240,
            sort=False,
            x_label_angle=0,
        )

    # 2023은 0건이 아니라 데이터 미확보
    missing = m07_df[
        m07_df["상태"] == "데이터 미확보"
    ]["접수연도"].tolist()

    if missing:
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
    chart_series = m08_df.set_index(
        "model_year_label"
    )["신고건수"]

    # 모델년도 숫자 가로 표시
    static_bar_chart(
        chart_series,
        height=260,
        sort=False,
        x_label_angle=0,
    )


st.divider()


# ============================================================
# 3. 공식 리콜
# ============================================================

st.subheader(
    "공식 리콜 — 제작사의 안전조치 (Action)"
)

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


recall_kpi_cols = st.columns(2)

with recall_kpi_cols[0]:
    st.metric(
        "리콜 캠페인",
        f"{m09}건",
    )

with recall_kpi_cols[1]:
    st.metric(
        "리콜 대상대수 합계",
        fmt_count(m10),
    )

    st.caption(
        "※ 여러 캠페인에 동일 차량이 "
        "중복 포함될 수 있어요."
    )


# ------------------------------------------------------------
# 리콜 사유 구성
# ------------------------------------------------------------

st.markdown(
    "**리콜 사유 구성** (캠페인 수 기준)"
)

reason_df = compute_M11_M12(
    recall_df,
    selected_model_key,
)

if reason_df.empty:
    st.info(
        "확인된 공식 리콜 캠페인이 없습니다."
    )

else:
    chart_series = reason_df.set_index(
        "recall_category"
    )["비중(%)"]

    static_bar_chart(
        chart_series,
        height=280,
        horizontal=True,
        sort=False,
    )

    st.dataframe(
        reason_df.rename(
            columns={
                "recall_category": "사유유형"
            }
        ),
        hide_index=True,
        width="stretch",
    )


st.divider()


# ============================================================
# 4. 리콜 캠페인 상세 목록
# ============================================================

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
    for _, r in sub_recalls.iterrows():
        with st.expander(
            f"{r['model_original']}  ·  "
            f"{r['recall_category']}  ·  "
            f"{fmt_date(r['recall_start_date'])}"
        ):
            st.write(
                f"제작사  {r['manufacturer']}"
            )

            st.write(
                f"원본 차명  {r['model_original']}"
            )

            st.write(
                f"사유 유형  {r['recall_category']}"
            )

            reason = r.get("recall_reason")

            st.write(
                "공식 리콜사유  "
                + (
                    str(reason)
                    if reason
                    and str(reason) != "nan"
                    else "리콜사유 미제공"
                )
            )

            st.write(
                f"대상 생산기간  "
                f"{fmt_date(r['production_from'])} ~ "
                f"{fmt_date(r['production_to'])}"
            )

            st.write(
                f"리콜개시일  "
                f"{fmt_date(r['recall_start_date'])}"
            )

            st.write(
                f"리콜 대상대수  "
                f"{fmt_count(r['recall_count'])}"
            )

            link_or_gap(
                r.get("official_check_url"),
                "자동차리콜센터에서 공식 확인",
            )


st.divider()


# ============================================================
# 5. 다른 모델과 비교
# ============================================================

st.subheader(
    "다른 모델과 비교"
)

# 현재 보고 있는 모델은 비교 후보에서 제외
other_models = verified_models[
    verified_models["model_key"]
    != selected_model_key
]

compare_labels = {
    model_label(
        row["manufacturer_std"],
        row["model_std"],
        row["generation_name"],
    ): row["model_key"]
    for _, row in other_models.iterrows()
}


cmp_cols = st.columns([3, 1])

with cmp_cols[0]:
    compare_label = st.selectbox(
        "비교 모델 선택",
        ["(선택 안 함)"]
        + list(compare_labels.keys()),
    )

with cmp_cols[1]:
    st.write("")
    compare_clicked = st.button(
        "비교하기"
    )


if (
    compare_clicked
    and compare_label != "(선택 안 함)"
):
    compare_key = compare_labels[
        compare_label
    ]

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
            "**판매량 비교** "
            "(두 모델 모두 검증된 동일 연도만)"
        )

        sales_common = compare_result[
            "sales_common"
        ]

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

            static_bar_chart(
                cmp_sales,
                height=260,
                sort=False,
                x_label_angle=0,
            )


        # ----------------------------------------------------
        # 결함신고 비교
        # ----------------------------------------------------

        st.markdown(
            "**결함신고 비교** "
            "(공통 확보 접수연도, 2023 제외)"
        )

        defect_a = compare_result[
            "defect_yearly_a"
        ]

        defect_b = compare_result[
            "defect_yearly_b"
        ]

        # 결함신고 원천 확보 연도
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
                    int(
                        a_counts.get(
                            year,
                            0,
                        )
                    )
                    for year
                    in common_defect_years
                ],
                b_label: [
                    int(
                        b_counts.get(
                            year,
                            0,
                        )
                    )
                    for year
                    in common_defect_years
                ],
            }
        ).set_index("연도")

        static_bar_chart(
            cmp_defect,
            height=260,
            sort=False,
            x_label_angle=0,
        )


        # ----------------------------------------------------
        # 리콜 비교
        # ----------------------------------------------------

        st.markdown(
            "**리콜 비교**"
        )

        recall_a = compare_result[
            "recall_a"
        ]

        recall_b = compare_result[
            "recall_b"
        ]

        compare_table = pd.DataFrame(
            {
                "항목": [
                    "리콜 캠페인 수",
                    "리콜 대상대수 합계",
                    "최근 리콜일",
                ],
                a_label: [
                    f"{int(recall_a['campaign_count'])}건",
                    fmt_count(
                        recall_a[
                            "recall_target_sum"
                        ]
                    ),
                    fmt_date(
                        recall_a[
                            "latest_recall_date"
                        ]
                    ),
                ],
                b_label: [
                    f"{int(recall_b['campaign_count'])}건",
                    fmt_count(
                        recall_b[
                            "recall_target_sum"
                        ]
                    ),
                    fmt_date(
                        recall_b[
                            "latest_recall_date"
                        ]
                    ),
                ],
            }
        )

        st.dataframe(
            compare_table,
            hide_index=True,
            width="stretch",
        )


        # ----------------------------------------------------
        # 리콜 사유 구성 비교
        # ----------------------------------------------------

        reason_cols = st.columns(2)


        with reason_cols[0]:
            st.caption(
                f"{a_label} 리콜 사유 구성"
            )

            a_reason = compare_result[
                "recall_categories_a"
            ]

            if a_reason.empty:
                st.caption(
                    "리콜 캠페인 없음"
                )

            else:
                static_bar_chart(
                    a_reason.set_index(
                        "recall_category"
                    )["campaign_count"],
                    height=200,
                    horizontal=True,
                    sort=False,
                )


        with reason_cols[1]:
            st.caption(
                f"{b_label} 리콜 사유 구성"
            )

            b_reason = compare_result[
                "recall_categories_b"
            ]

            if b_reason.empty:
                st.caption(
                    "리콜 캠페인 없음"
                )

            else:
                static_bar_chart(
                    b_reason.set_index(
                        "recall_category"
                    )["campaign_count"],
                    height=200,
                    horizontal=True,
                    sort=False,
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

st.subheader(
    "FAQ / 출처 / 해석 안내"
)

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