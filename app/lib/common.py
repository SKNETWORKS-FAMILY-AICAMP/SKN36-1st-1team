# ============================================================
# app/lib/common.py
#
# S-01~S-04 화면들이 공통으로 쓰는 데이터 로딩·계산 함수 모음이에요.
# 데이터정의서_최종본_v2.6 / 화면설계서_v2.5(2020기준 최종확정) 규칙을
# 한 군데에 모아두면 화면마다 같은 로직을 다시 짜지 않아도 되고,
# 나중에 데이터가 갱신될 때도 이 파일만 손보면 돼요.
#
# v2.6에서 "신규등록 API 폐기"가 확정되면서(11_변경이력 v2.0), 모델별
# 신규등록 흐름을 계산하던 옛 함수들(compute_M00/M01/M12, national_series,
# period_trend, region_breakdown, fuel_breakdown 등)은 이제 어떤 화면도
# 쓰지 않아서 정리했어요. S-01/S-03은 D-REG(전국 Stock), S-02는
# D-SALES(판매)→D-DEF(결함신고)→D-REC(리콜) 순서로 봐요.
#
# ※ 이 프로젝트는 판매량·결함신고·리콜대수를 서로 나눈 결함률/리콜률을
#   계산하지 않습니다. (데이터정의서_v2.6 파생지표_정의 X01/X02, 사용 금지)
# ============================================================

from pathlib import Path
import re
import unicodedata

import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# 0. 경로 설정
#
# D-REG(전국등록)·D-MAP(모델매핑)·D-REC(리콜)·D-SALES(판매량)·D-DEF(결함신고)·
# D-FAQ(자동차리콜센터 공통 FAQ)까지 이제 모두 data/processed/의 실데이터를
# 사용해요. D-FAQ는 feature/faq 브랜치에서 전처리된 faq_master.csv를 반영한
# 거예요(v2.6 데이터정의서 스키마: faq_id/provider/category/question/answer/
# source_url/collected_at). 그 전까지 쓰던 더미(data/dummy/faq_recall_center_
# dummy.csv)는 더 이상 안 써요.
# ------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

MODEL_MAPPING_PATH = PROCESSED_DIR / "model_mapping.csv"              # D-MAP (실데이터)
RECALL_PATH = PROCESSED_DIR / "recall.csv"                             # D-REC (실데이터)
NATIONAL_REGISTRATION_PATH = PROCESSED_DIR / "registration_summary.csv"  # D-REG (실데이터, 전국 Stock)
SALES_PATH = PROCESSED_DIR / "vehicle_sales.csv"                       # D-SALES (실데이터)
DEFECT_PATH = PROCESSED_DIR / "defect_reports.csv"                     # D-DEF (실데이터)
FAQ_PATH = PROCESSED_DIR / "faq_master.csv"                            # D-FAQ (실데이터)

# 서비스 공통 분석기간 (요구사항정의서_v2.6 11_변경이력 v2.3/v2.5) — 판매·결함신고·리콜은
# 2020~2025만 분석하고, 이보다 이전/이후 원본은 있어도 화면 계산에 넣지 않아요.
ANALYSIS_YEAR_START = 2020
ANALYSIS_YEAR_END = 2025
# 결함신고 원천 확보 정책
# 데이터정의서/요구사항 기준으로 2020~2022, 2024~2025는 확보,
# 2023은 원천 미확보입니다. '원천 미확보'와 '확보했지만 0건'을 구분하기 위해
# 파일 내 행 존재 여부로 추론하지 않고 정책값으로 명시합니다.
DEFECT_AVAILABLE_YEARS = frozenset({2020, 2021, 2022, 2024, 2025})
DEFECT_MISSING_YEARS = frozenset({2023})


# ------------------------------------------------------------
# 1. 데이터 로딩 (모두 @st.cache_data로 캐시)
# ------------------------------------------------------------
@st.cache_data
def load_model_mapping() -> pd.DataFrame:
    """D-MAP. model_key 하나가 source_type(SALES/DEFECT/REC)별로 여러 행일 수 있어요."""
    df = pd.read_csv(MODEL_MAPPING_PATH, encoding="utf-8-sig")
    df = df.dropna(subset=["model_key"])
    return df


@st.cache_data
def load_recall() -> pd.DataFrame:
    df = pd.read_csv(RECALL_PATH, encoding="utf-8-sig")
    for col in ("production_from", "production_to", "recall_start_date"):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


@st.cache_data
def load_national_registration() -> pd.DataFrame:
    """D-REG(전국등록_데이터, v2.6). 시장 전체 Stock — 특정 모델 등록대수가 아님."""
    df = pd.read_csv(NATIONAL_REGISTRATION_PATH, encoding="utf-8-sig")
    df["_snapshot_key"] = df["stat_year"].fillna(0).astype(int) * 100 + df["stat_month"].fillna(0).astype(int)
    return df


def latest_national_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """가장 최근 기준시점(stat_year·stat_month)의 행만 반환."""
    if df.empty:
        return df
    latest_key = df["_snapshot_key"].max()
    return df[df["_snapshot_key"] == latest_key].copy()


def national_total_count(latest_df: pd.DataFrame):
    """M00: 전국 총 등록대수 (dimension_type='TOTAL'). TOTAL 행이 없으면 None."""
    total = latest_df[latest_df["dimension_type"] == "TOTAL"]
    if total.empty:
        return None
    return int(total.iloc[0]["registration_count"])


def region_summary(latest_df: pd.DataFrame) -> pd.DataFrame:
    """M01: 지역별 등록대수 (dimension_type='REGION'), 등록대수 내림차순."""
    region = latest_df[latest_df["dimension_type"] == "REGION"].copy()
    return region.sort_values("registration_count", ascending=False)


def vehicle_type_summary(latest_df: pd.DataFrame) -> pd.DataFrame:
    """M02: 차종별 등록대수 (dimension_type='VEHICLE_TYPE')."""
    vt = latest_df[latest_df["dimension_type"] == "VEHICLE_TYPE"].copy()
    return vt.sort_values("registration_count", ascending=False)


def fuel_summary(latest_df: pd.DataFrame) -> pd.DataFrame:
    """M03: 연료별 등록대수 (dimension_type='FUEL')."""
    fuel = latest_df[latest_df["dimension_type"] == "FUEL"].copy()
    return fuel.sort_values("registration_count", ascending=False)


@st.cache_data
def load_vehicle_sales() -> pd.DataFrame:
    """D-SALES(판매량_데이터, v2.6 실데이터). 서비스 분석기간(2020~2025)만 사용해요."""
    df = pd.read_csv(SALES_PATH, encoding="utf-8-sig")
    df = df[(df["sales_year"] >= ANALYSIS_YEAR_START) & (df["sales_year"] <= ANALYSIS_YEAR_END)].copy()
    return df


@st.cache_data
def load_defect_reports() -> pd.DataFrame:
    """D-DEF(결함신고_데이터, v2.6 실데이터). report_date를 날짜형으로 변환해요."""
    df = pd.read_csv(DEFECT_PATH, encoding="utf-8-sig")
    df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
    return df


@st.cache_data
def load_faq() -> pd.DataFrame:
    """D-FAQ(자동차리콜센터 공통 FAQ, v2.6 스키마 더미)."""
    df = pd.read_csv(FAQ_PATH, encoding="utf-8-sig")
    df["question"] = df["question"].fillna("")
    df["answer"] = df["answer"].fillna("")
    df["category"] = df["category"].fillna("")
    return df


# ------------------------------------------------------------
# 2. 검색어 정규화
# ------------------------------------------------------------
def normalize_search_text(value) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    text = re.sub(r"[()\[\]{}]", " ", text)
    text = re.sub(r"[-_/]", " ", text)
    text = re.sub(r"[^0-9a-z가-힣\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def search_faq(faq_df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    """S04-C02: 질문·답변 텍스트 부분검색 (대소문자 무시)."""
    if not keyword:
        return faq_df.iloc[0:0]
    kw = keyword.strip().lower()
    mask = (
        faq_df["question"].str.lower().str.contains(kw, regex=False)
        | faq_df["answer"].str.lower().str.contains(kw, regex=False)
    )
    return faq_df[mask].copy()


# ------------------------------------------------------------
# 3. 모델 검증 상태 (S01-C06 / ST-03 공통 규칙)
# ------------------------------------------------------------
def get_verified_models() -> pd.DataFrame:
    """match_status == '검증완료'인 모델만 서비스 후보로 사용 (RF-7.4).

    model_mapping.csv는 source_type(SALES/DEFECT/REC)별로 같은 model_key가
    여러 행일 수 있어서, model_key 기준으로 하나만 남겨요. manufacturer_support_url은
    제조사별 정적값이라 어느 행에서 가져와도 같아요(S04-C08용).
    """
    mapping = load_model_mapping()
    verified = mapping[mapping["match_status"] == "검증완료"].copy()
    cols = ["model_key", "manufacturer_std", "model_std", "generation_name", "manufacturer_support_url"]
    return verified[cols].drop_duplicates(subset=["model_key"])


def model_label(manufacturer_std, model_std, generation_name=None) -> str:
    gen = f" ({generation_name})" if generation_name and str(generation_name) != "nan" else ""
    return f"{manufacturer_std} | {model_std}{gen}"


def get_model_row(model_key: str):
    """선택된 model_key의 표준 정보 한 줄을 돌려줌. 없으면 None (ST-03 미검증/미존재)."""
    verified = get_verified_models()
    match = verified[verified["model_key"] == model_key]
    if match.empty:
        return None
    return match.iloc[0]


# ------------------------------------------------------------
# 4. 판매(D-SALES) 파생지표 M04 / M05 (S02-C03~C05)
# ------------------------------------------------------------
def model_sales(sales_df: pd.DataFrame, model_key: str) -> pd.DataFrame:
    return sales_df[sales_df["model_key"] == model_key].copy()


def compute_M04(sales_df: pd.DataFrame, model_key: str):
    """M04: 값이 있고 검증상태가 공식자료/교차검증인 가장 최근 연도의 국내 판매량.

    '보완필요' 연도나 공란은 건너뛰어요. 반환값은 (연도, 판매량, verification_status)
    튜플이거나, 조건에 맞는 연도가 하나도 없으면 None이에요.
    """
    sub = model_sales(sales_df, model_key)
    sub = sub[sub["domestic_sales_count"].notna() & sub["verification_status"].isin(["공식자료", "교차검증"])]
    if sub.empty:
        return None
    row = sub.sort_values("sales_year", ascending=False).iloc[0]
    return int(row["sales_year"]), int(row["domestic_sales_count"]), row["verification_status"]


def sales_coverage(sales_df: pd.DataFrame, model_key: str):
    """S02-C04: 2020~2025 중 값이 확인된(non-null) 연도 수 / 전체 연도 수."""
    sub = model_sales(sales_df, model_key)
    total_years = ANALYSIS_YEAR_END - ANALYSIS_YEAR_START + 1
    confirmed = int(sub["domestic_sales_count"].notna().sum())
    return confirmed, total_years


def compute_M05(sales_df: pd.DataFrame, model_key: str) -> pd.DataFrame:
    """M05: 2020~2025 연도별 국내 판매량 추이. 공란은 0/보간하지 않고 그대로 비워둬요."""
    sub = model_sales(sales_df, model_key).sort_values("sales_year")
    return sub[["sales_year", "domestic_sales_count", "verification_status", "source_url", "loaded_at"]]


# ------------------------------------------------------------
# 5. 결함신고(D-DEF) 파생지표 M06 / M07 / M08 (S02-C07~C09)
# ------------------------------------------------------------
def model_defects(defect_df: pd.DataFrame, model_key: str) -> pd.DataFrame:
    return defect_df[defect_df["model_key"] == model_key].copy()


def defect_available_years(defect_df: pd.DataFrame) -> set[int]:
    """D-DEF 원천 확보 연도를 문서 확정 정책에 따라 반환합니다.

    2023은 신고 0건이 아니라 원천 미확보이므로 실제 CSV 행 유무로
    확보 여부를 판정하지 않습니다.
    """
    return set(DEFECT_AVAILABLE_YEARS)


def compute_M06(defect_df: pd.DataFrame, model_key: str) -> int:
    """M06: 원천이 실제 확보된 분석연도의 결함신고 레코드 수."""
    sub = model_defects(defect_df, model_key)
    years = sub["report_date"].dt.year
    available_years = defect_available_years(defect_df)
    mask = years.notna() & years.isin(available_years)
    return int(mask.sum())


def compute_M07(defect_df: pd.DataFrame, model_key: str) -> pd.DataFrame:
    """M07: 접수연도별 신고 건수. 2023 원천 미확보 정책을 명시적으로 반영."""
    sub = model_defects(defect_df, model_key)
    counts = sub["report_date"].dt.year.value_counts()
    available_years = defect_available_years(defect_df)

    rows = []
    for year in range(ANALYSIS_YEAR_START, ANALYSIS_YEAR_END + 1):
        if year not in available_years:
            rows.append({"접수연도": year, "신고건수": None, "상태": "데이터 미확보"})
        else:
            rows.append({"접수연도": year, "신고건수": int(counts.get(year, 0)), "상태": "확보"})
    return pd.DataFrame(rows)


def compute_M08_model_year(defect_df: pd.DataFrame, model_key: str) -> pd.DataFrame:
    """M08: 모델년도별 신고 분포. model_year 결측은 '미상'으로 표시해요."""
    sub = model_defects(defect_df, model_key).copy()
    sub["model_year_label"] = sub["model_year"].apply(
        lambda v: "미상" if pd.isna(v) else str(int(v))
    )
    g = sub.groupby("model_year_label").size().reset_index(name="신고건수")
    # 미상을 맨 뒤로, 나머지는 연도 오름차순으로 정렬
    g["_sort"] = g["model_year_label"].apply(lambda v: (1, 0) if v == "미상" else (0, int(v)))
    return g.sort_values("_sort").drop(columns="_sort")


# ------------------------------------------------------------
# 6. 리콜(D-REC) 파생지표 M09~M12 / M15 (S02-C10~C14)
#    분석기준: recall_start_date 2020~2025 (요구사항정의서_v2.6 11_변경이력)
# ------------------------------------------------------------
def model_recalls(recall_df: pd.DataFrame, model_key: str) -> pd.DataFrame:
    """선택 모델의 리콜 캠페인 중 분석기간(리콜개시일 2020~2025)에 해당하는 행만."""
    sub = recall_df[recall_df["model_key"] == model_key].copy()
    start = pd.Timestamp(f"{ANALYSIS_YEAR_START}-01-01")
    end = pd.Timestamp(f"{ANALYSIS_YEAR_END}-12-31")
    return sub[(sub["recall_start_date"] >= start) & (sub["recall_start_date"] <= end)]


def compute_M09(recall_df: pd.DataFrame, model_key: str) -> int:
    """M09: 전체 리콜 캠페인 수."""
    return int(len(model_recalls(recall_df, model_key)))


def compute_M10(recall_df: pd.DataFrame, model_key: str) -> int:
    """M10: 리콜 대상대수 합계 (동일 차량이 여러 캠페인에 중복 포함될 수 있음)."""
    return int(model_recalls(recall_df, model_key)["recall_count"].sum())


def compute_M11_M12(recall_df: pd.DataFrame, model_key: str) -> pd.DataFrame:
    """M11: 사유별 캠페인 수, M12: 사유별 캠페인 비중(%). 캠페인 수 기준이에요."""
    sub = model_recalls(recall_df, model_key)
    total = len(sub)
    if total == 0:
        return pd.DataFrame(columns=["recall_category", "캠페인수", "비중(%)"])
    g = sub.groupby("recall_category").size().reset_index(name="캠페인수")
    g["비중(%)"] = (g["캠페인수"] / total * 100).round(1)
    return g.sort_values("캠페인수", ascending=False)


def compute_M15(recall_df: pd.DataFrame, model_key: str):
    """M15: 분석기간(2020~2025) 내 가장 최근 리콜개시일."""
    sub = model_recalls(recall_df, model_key)
    if sub.empty or sub["recall_start_date"].isna().all():
        return None
    return sub["recall_start_date"].max()


def has_production_period_gap(recall_df: pd.DataFrame, model_key: str) -> bool:
    """ST-08: 생산기간 일부 누락 여부."""
    sub = model_recalls(recall_df, model_key)
    if sub.empty:
        return False
    return bool(sub["production_from"].isna().any() or sub["production_to"].isna().any())


# ------------------------------------------------------------
# 7. 표시 helper
# ------------------------------------------------------------
def fmt_count(n) -> str:
    try:
        return f"{int(n):,}대"
    except (TypeError, ValueError):
        return "정보 없음"


def fmt_date(d) -> str:
    if d is None or pd.isna(d):
        return "정보 없음"
    return pd.Timestamp(d).strftime("%Y-%m-%d")


def source_caption(source_url: str, loaded_at: str, label: str = "출처") -> None:
    """공통 출처·기준일 표시. source_url 없으면 ST-10."""
    if source_url and str(source_url) != "nan":
        st.caption(f"{label}: {source_url}  |  적재일 {loaded_at}")
    else:
        st.caption(f"{label}: 공식 원문 링크를 확인할 수 없습니다 (기관명만 표시). 적재일 {loaded_at}")


def link_or_gap(source_url: str, button_label: str) -> None:
    """ST-10 외부 링크 없음 공통 처리."""
    if source_url and str(source_url) != "nan":
        st.link_button(button_label, source_url)
    else:
        st.info("공식 원문 링크를 확인할 수 없습니다. 출처기관명만 표시합니다. (ST-10)")


# ------------------------------------------------------------
# 막대그래프 — 마우스 휠로 확대/축소되지 않는 '고정' 버전
#
# st.bar_chart는 내부적으로 Altair의 .interactive()를 항상 붙여요. 이게
# 켜져 있으면 그래프 위에서 마우스 휠을 굴릴 때(페이지를 스크롤하려던
# 것이어도) 페이지 대신 그래프의 축이 확대/축소돼요 — 사용자가 그래프를
# 스쳐 지나가며 스크롤만 해도 축 눈금과 막대 높이가 계속 바뀌어 보이는
# 문제로 이어졌어요(마우스를 올려두면 그래프가 흔들리는 것처럼 보였던
# 원인이 바로 이거였어요).
#
# st.bar_chart는 이 동작을 끄는 옵션을 제공하지 않아서, Streamlit이
# st.bar_chart를 만들 때 쓰는 것과 완전히 같은 내부 함수
# (streamlit.elements.lib.built_in_chart_utils.generate_chart)를 그대로
# 써서 똑같은 모양의 차트를 만든 뒤, 자동으로 붙는 확대/축소·이동
# 바인딩(bind: "scales" 파라미터)만 제거하고 st.altair_chart로 그려요.
# 색상·툴팁·정렬·크기 등 나머지는 st.bar_chart와 동일해요.
#
# generate_chart는 Streamlit의 공식 공개 API가 아니라 내부 구현이라,
# 나중에 Streamlit 버전이 올라가며 구조가 바뀌면 깨질 수 있어요. 그런
# 경우를 대비해 실패하면 예전처럼 st.bar_chart로 자동 대체해요(그래프는
# 계속 나오되, 이 휠-확대/축소 문제만 다시 생길 수 있어요).
# ------------------------------------------------------------
def static_bar_chart(
    data,
    *,
    horizontal: bool = False,
    sort: bool | str = False,
    height="content",
    width="stretch",
    x_label_angle=None,
) -> None:
    try:
        from streamlit.elements.lib.built_in_chart_utils import (
            ChartType,
            generate_chart,
        )

        chart_type = ChartType.HORIZONTAL_BAR if horizontal else ChartType.VERTICAL_BAR
        chart = generate_chart(
            chart_type=chart_type,
            data=data,
            width=width,
            height=height,
            sort_from_user=sort,
        )
        # generate_chart()가 기본으로 붙이는 "스크롤=확대/축소, 드래그=이동"
        # 바인딩만 제거해요. 이게 이번 흔들림 문제의 원인이었어요.
        chart.params = [
            p for p in (chart.params or []) if getattr(p, "bind", None) != "scales"
        ]
        if x_label_angle is not None and not horizontal:
            chart = chart.configure_axisX(labelAngle=x_label_angle)
        st.altair_chart(chart, width=width, height=height, theme="streamlit")
    except Exception:
        st.bar_chart(data, horizontal=horizontal, sort=sort, height=height, width=width)
