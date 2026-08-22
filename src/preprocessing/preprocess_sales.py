"""
preprocess_sales.py
====================
이 파일이 하는 일 (한 줄 요약):
  현대·기아 판매량 검증본 엑셀 파일을 읽어서, 우리 프로젝트가 다루는 6개 모델의
  판매량만 뽑아 서비스에서 쓰기 좋은 모양(long format)의 CSV로 바꿔줍니다.

원본 → 결과물 모양 예시:
  [원본] 모델별로 연도가 옆으로 쭉 나열된 표
      모델    2020   2021   2022  ...
      아반떼  87731  (공란)  58743

  [결과] 한 줄에 "모델 하나 + 연도 하나"만 담기도록 세로로 풀어놓은 표
      sales_year | manufacturer | model_original | model_key
      2020       | 현대자동차   | 아반떼         | HYU_AVANTE
      2021       | 현대자동차   | 아반떼         | HYU_AVANTE

  이렇게 바꾸는 이유: DB나 차트 라이브러리는 "한 줄 = 한 개의 사실"인 표 모양을 훨씬 다루기 쉽습니다.

결과 저장 위치: data/processed/vehicle_sales.csv

지켜야 하는 규칙 (v2.5 문서 기준):
  - 원본 엑셀의 2015~2025년 데이터는 손대지 않고 그대로 둠 (우리는 읽기만 함)
  - 서비스에서 실제로 쓰는 건 2020~2025년뿐
  - 판매량이 비어있는 칸은 절대로 0으로 바꾸지 않음 (안 판 것과 "모르는 것"은 다르므로)
  - model_mapping.csv에서 "검증완료"로 확인된 모델만 사용
  - 여기서 말하는 "판매량"은 자동차 등록대수가 아니라, 제조사가 발표한 국내 판매량(출고 기준)
"""

import argparse                    # 터미널에서 --input 같은 옵션을 받기 위한 도구
from datetime import datetime      # "언제 전처리했는지" 날짜를 기록하기 위한 도구
from pathlib import Path           # 파일/폴더 경로를 다루는 도구

import pandas as pd                # 엑셀 읽기 · 표 정리 · CSV 저장을 담당하는 라이브러리


# ── 1. 프로젝트 폴더 위치 ─────────────────────────────────────────
# 이 파일 기준 2단계 위 폴더가 프로젝트 최상위 폴더입니다.
# 예: SKN36-1st-1team/src/preprocessing/preprocess_sales.py 라면
#     parents[2] 는 SKN36-1st-1team 폴더를 가리킵니다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "sales"          # 판매량 원본 엑셀을 넣어두는 폴더
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"        # 전처리 결과물이 저장될 폴더
MODEL_MAPPING_PATH = PROCESSED_DIR / "model_mapping.csv"   # 이전 단계(D-MAP)에서 만든 파일
OUTPUT_PATH = PROCESSED_DIR / "vehicle_sales.csv"           # 이 스크립트가 최종적으로 만들 파일


# ── 2. 서비스가 다루는 기간 ────────────────────────────────────────
START_YEAR = 2020
END_YEAR = 2025
ANALYSIS_YEARS = list(range(START_YEAR, END_YEAR + 1))  # [2020, 2021, 2022, 2023, 2024, 2025]


# ── 3. 엑셀 안의 시트(탭) 이름들 ───────────────────────────────────
HYUNDAI_SHEET = "현대_판매량"
KIA_SHEET = "기아_판매량"
SOURCE_SHEET = "출처"   # 어느 자료를 근거로 삼았는지 적힌 시트


# ── 4. 우리 서비스가 다루는 6개 모델 ────────────────────────────────
# 판매량 파일에는 다른 모델도 있을 수 있지만, 아래 6개만 골라서 사용합니다.
TARGET_MODELS = {
    "현대자동차": ["아반떼", "쏘나타", "그랜저"],
    "기아": ["K5", "스포티지", "쏘렌토"],
}


# ── 5. verification_status(검증 상태) 칸에 들어갈 수 있는 값 ─────────
ALLOWED_VERIFICATION_STATUS = {
    "공식자료",   # 제조사/현대차그룹의 공식 연간 자료로 확인됨
    "교차검증",   # 공식자료를 인용한 다른 자료로 한 번 더 확인됨
    "보완필요",   # 아직 이 모델·연도의 값이 확인되지 않음 (=비어있음)
}


# ── 6. 사용할 판매량 엑셀 파일 찾기 ─────────────────────────────────
def find_input_file(input_path):
    """판매량 엑셀 파일이 어디 있는지 찾아줍니다. 방법은 두 가지입니다.
    1) 터미널에서 --input 옵션으로 직접 경로를 알려준 경우 → 그 파일을 사용
    2) --input을 안 준 경우 → data/raw/sales 폴더 안의 xlsx 파일을 자동으로 찾아 사용
       (이때 폴더 안에 파일이 정확히 1개여야만 "이게 맞구나" 하고 자동으로 고를 수 있습니다)"""

    if input_path:
        path = Path(input_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path  # 상대경로면 프로젝트 폴더 기준으로 위치를 계산
        if not path.exists():
            raise FileNotFoundError(f"판매량 Excel 파일을 찾을 수 없습니다:\n{path}")
        return path

    # --input을 안 준 경우: 폴더 안을 자동으로 뒤짐
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"판매량 원본 폴더가 없습니다.\n먼저 폴더를 만들어주세요:\n{RAW_DIR}")

    # "~$파일명.xlsx" 는 엑셀이 파일을 열어둔 동안 자동으로 만드는 임시 파일이라 제외합니다.
    candidates = [f for f in RAW_DIR.glob("*.xlsx") if not f.name.startswith("~$")]

    if len(candidates) == 0:
        raise FileNotFoundError("data/raw/sales 폴더에 판매량 Excel 파일이 없습니다.")

    if len(candidates) > 1:
        # 파일이 여러 개면 어떤 걸 써야 할지 코드가 판단할 수 없으므로, 목록만 보여주고 사람이 고르게 함
        print("\n현재 sales 폴더의 Excel 파일:")
        for f in candidates:
            print(f"- {f.name}")
        raise RuntimeError("판매량 Excel이 여러 개 있습니다. --input 옵션으로 사용할 파일 하나를 지정해주세요.")

    return candidates[0]  # 딱 하나뿐이면 그걸 사용


# ── 7. D-MAP(model_mapping.csv) 불러오기 ───────────────────────────
def load_model_mapping():
    """이전 단계(model_mapping.py)가 만들어둔 매핑표를 읽습니다.
    판매량 전처리에서는 그중에서도 "판매량 데이터용(SALES)이면서 검증완료된" 매핑만 사용합니다."""
    if not MODEL_MAPPING_PATH.exists():
        raise FileNotFoundError("model_mapping.csv가 없습니다.\n먼저 model_mapping.py를 실행해주세요.")

    df = pd.read_csv(MODEL_MAPPING_PATH, encoding="utf-8-sig")
    df = df[(df["source_type"] == "SALES") & (df["match_status"] == "검증완료")].copy()

    if df.empty:
        raise ValueError("D-MAP에 검증완료 SALES 매핑이 없습니다.")
    return df


# ── 8. 판매량 시트(현대/기아) 읽기 ──────────────────────────────────
def read_sales_sheet(input_path, sheet_name):
    """현대_판매량 또는 기아_판매량 시트를 읽습니다.
    이 엑셀은 1행이 제목, 2행부터가 진짜 표 머리글(모델, 2015, 2016, ... , 검증상태)이라서
    header=1로 지정합니다. (pandas는 0번째 줄부터 세므로, header=1은 "엑셀의 2행"을 뜻합니다.)"""
    df = pd.read_excel(input_path, sheet_name=sheet_name, header=1, engine="openpyxl")

    df = df[df["모델"].notna()].copy()          # 모델명이 비어있는 빈 줄은 제거
    df["모델"] = df["모델"].astype(str).str.strip()  # 모델명 앞뒤 공백 정리
    return df


# ── 9. 출처(근거자료) 시트 읽기 ─────────────────────────────────────
def read_source_sheet(input_path):
    """'출처' 시트를 읽습니다. (컬럼: 회사, 연도, 출처명, URL, 출처유형, 검증범위)
    이 시트가 "이 판매량 숫자는 어디서 가져온 건지"를 증명하는 근거 자료입니다."""
    df = pd.read_excel(input_path, sheet_name=SOURCE_SHEET, header=0, engine="openpyxl")

    df = df[df["연도"].notna()].copy()   # "공통/월별 보완"처럼 특정 연도가 없는 행은 제외
    df["연도"] = df["연도"].astype(int)
    df = df[df["연도"].between(START_YEAR, END_YEAR)].copy()  # 서비스 기간(2020~2025)만 남김
    return df


# ── 10. 회사명 표기를 통일하는 함수 ──────────────────────────────────
def normalize_source_company(company):
    """출처 시트에는 "현대"라고만 적혀있는데, 우리 D-SALES 표준값은 "현대자동차"이므로 맞춰줍니다."""
    company = str(company).strip()
    if company == "현대":
        return "현대자동차"
    if company == "기아":
        return "기아"
    return company  # 그 외 값은 건드리지 않고 그대로 반환


# ── 11. "출처유형" → verification_status(검증상태) 변환 ─────────────
def normalize_verification_status(source_type, sales_count):
    """엑셀의 '출처유형' 칸(공식 연간/교차검증/2차자료 등)을,
    데이터정의서가 정한 3가지 표준값(공식자료/교차검증/보완필요) 중 하나로 바꿔줍니다."""
    if pd.isna(sales_count):
        # 판매량 숫자 자체가 비어있다면, 출처가 있더라도 "그 모델의 값은 아직 확인 안 됨" 상태입니다.
        return "보완필요"

    source_type = "" if pd.isna(source_type) else str(source_type).strip()

    if source_type == "공식 연간":
        return "공식자료"
    if source_type == "교차검증":
        return "교차검증"
    # 2차자료, 월별보완 등 그 외 경우는 문서 규칙상 "최근 KPI/모델비교에 바로 쓰지 않음" = 보완필요
    return "보완필요"


# ── 12. (제조사, 연도) → 출처 정보를 바로 찾는 사전 만들기 ────────────
def build_source_lookup(source_df):
    """예: lookup[("현대자동차", 2020)] 하면 그 해 그 회사의 출처 URL/유형을 바로 꺼낼 수 있게 만듭니다."""
    lookup = {}
    for _, row in source_df.iterrows():
        manufacturer = normalize_source_company(row["회사"])
        year = int(row["연도"])
        lookup[(manufacturer, year)] = {
            "source_url": row["URL"],
            "source_type": row["출처유형"],
            "source_name": row["출처명"],
            "verification_scope": row["검증범위"],
        }
    return lookup


# ── 13. (제조사, 원본 모델명) → model_key를 바로 찾는 사전 만들기 ─────
def build_model_lookup(mapping_df):
    """예: lookup[("현대자동차", "아반떼")] 하면 "HYU_AVANTE"를 바로 꺼낼 수 있게 만듭니다."""
    lookup = {}
    for _, row in mapping_df.iterrows():
        key = (str(row["manufacturer_std"]).strip(), str(row["alias_name"]).strip())
        lookup[key] = row["model_key"]
    return lookup


# ── 14. 판매량 숫자를 깔끔하게 정리하는 함수 ─────────────────────────
def normalize_sales_count(value):
    """87731.0 처럼 소수점이 붙어 나오는 값은 87731(정수)로 바꾸고,
    빈 칸은 None(=DB/CSV에서 "값 없음")으로 바꿉니다. 절대 0으로 바꾸지 않습니다."""
    if pd.isna(value):
        return None  # 공란은 끝까지 공란(None)으로 유지

    count = int(float(value))
    if count < 0:
        raise ValueError(f"음수 판매량 발견: {value}")
    return count


# ── 15. 제조사 한 곳의 판매량 표를, 세로로 긴 모양(long format)으로 변환 ─
def preprocess_company_sales(sales_df, manufacturer, target_models, model_lookup, source_lookup, loaded_at):
    """현대 또는 기아의 "모델 × 연도" 가로 표를, "모델 하나 + 연도 하나"가 한 줄인 세로 표로 바꿉니다."""
    rows = []

    for model_original in target_models:
        # 이 모델에 해당하는 엑셀 행을 찾음
        model_rows = sales_df[sales_df["모델"] == model_original]

        if model_rows.empty:
            raise ValueError(f"{manufacturer} 판매량 시트에서 '{model_original}' 모델을 찾지 못했습니다.")
        if len(model_rows) > 1:
            raise ValueError(f"{manufacturer} / {model_original}가 판매량 시트에 중복되어 있습니다.")

        model_row = model_rows.iloc[0]

        # D-MAP에서 이 모델의 표준 model_key를 확인
        model_key = model_lookup.get((manufacturer, model_original))
        if model_key is None:
            raise ValueError(f"D-MAP SALES 매핑 없음: {manufacturer} / {model_original}")

        # 2020~2025년, 한 해씩 처리
        for year in ANALYSIS_YEARS:
            # 엑셀을 읽는 방식에 따라 연도 컬럼명이 숫자(2020)일 수도, 문자("2020")일 수도 있어 둘 다 대응
            if year in sales_df.columns:
                raw_value = model_row[year]
            elif str(year) in sales_df.columns:
                raw_value = model_row[str(year)]
            else:
                raise ValueError(f"판매량 시트에 {year} 컬럼이 없습니다.")

            sales_count = normalize_sales_count(raw_value)

            # 이 제조사·연도의 출처(근거자료) 찾기 — v2.5 규칙상 출처 URL은 반드시 있어야 함
            source_info = source_lookup.get((manufacturer, year))
            if source_info is None:
                raise ValueError(f"출처 시트에서 {manufacturer} {year} 자료를 찾지 못했습니다.")

            verification_status = normalize_verification_status(
                source_type=source_info["source_type"], sales_count=sales_count,
            )

            rows.append({
                "sales_year": year,
                "manufacturer": manufacturer,
                "model_original": model_original,       # 원본 엑셀에 적힌 모델명 그대로 보존
                "model_key": model_key,                  # 우리 프로젝트 표준 이름표
                "domestic_sales_count": sales_count,      # 미확보 연도는 None(빈칸)
                "verification_status": verification_status,
                "source_url": source_info["source_url"],
                "loaded_at": loaded_at,
            })

    return rows


# ── 16. 완성된 D-SALES 표가 규칙을 잘 지켰는지 최종 점검 ──────────────
def validate_vehicle_sales(df):
    """만들어진 vehicle_sales.csv가 데이터정의서 조건에 맞는지 하나씩 검사합니다."""
    print("\n" + "=" * 70 + "\nD-SALES 정합성 검사\n" + "=" * 70)

    # 1) 전체 행 수: 6개 모델 × 6개 연도 = 36행이어야 함
    expected_rows = 6 * len(ANALYSIS_YEARS)
    print(f"예상 행 수 : {expected_rows}")
    print(f"실제 행 수 : {len(df)}")
    if len(df) != expected_rows:
        raise ValueError("D-SALES 행 수가 예상과 다릅니다.")

    # 2) 연도 범위가 정확히 2020~2025인지
    years = sorted(df["sales_year"].unique().tolist())
    if years != ANALYSIS_YEARS:
        raise ValueError(f"sales_year 범위 오류: {years}")

    # 3) (연도, 모델) 조합이 중복되지 않았는지
    duplicate_mask = df.duplicated(subset=["sales_year", "model_key"], keep=False)
    if duplicate_mask.any():
        print(df[duplicate_mask])
        raise ValueError("sales_year + model_key 중복이 있습니다.")

    # 4) model_key가 빠진 행이 없는지
    if df["model_key"].isna().any():
        raise ValueError("model_key 결측이 있습니다.")

    # 5) source_url이 빠진 행이 없는지
    if df["source_url"].isna().any():
        raise ValueError("source_url 결측이 있습니다.")

    # 6) verification_status에 허용되지 않은 값이 섞여있지 않은지
    actual_status = set(df["verification_status"].unique().tolist())
    invalid_status = actual_status - ALLOWED_VERIFICATION_STATUS
    if invalid_status:
        raise ValueError(f"허용되지 않은 verification_status: {invalid_status}")

    # 7) 판매량에 음수가 없는지
    if df["domestic_sales_count"].dropna().lt(0).any():
        raise ValueError("음수 판매량이 존재합니다.")

    # 8) 판매량이 비어있는데 상태가 "보완필요"가 아닌 모순된 행이 없는지
    bad_null_status = df[df["domestic_sales_count"].isna() & (df["verification_status"] != "보완필요")]
    if not bad_null_status.empty:
        raise ValueError("판매량 공란인데 verification_status가 보완필요가 아닌 행이 있습니다.")

    # 참고용: 모델별로 6개 연도 중 몇 개나 실제 판매량이 확보됐는지 보여줌 (에러는 아님)
    print("\n모델별 2020~2025 판매량 확보 현황\n" + "-" * 70)
    for model_key, group in df.groupby("model_key"):
        confirmed_count = int(group["domestic_sales_count"].notna().sum())
        model_name = group["model_original"].iloc[0]
        missing_years = group[group["domestic_sales_count"].isna()]["sales_year"].tolist()
        print(f"{model_name:<6} | {confirmed_count}/6 | 미확보: {missing_years if missing_years else '없음'}")

    print("\n[OK] D-SALES 정합성 검사 통과")


# ── 17. 전체 흐름 실행 ─────────────────────────────────────────────
def run(input_path):
    print("\n" + "=" * 70 + "\nD-SALES 판매량 전처리 시작\n" + "=" * 70)
    print(f"원본 파일: {input_path}")

    loaded_at = datetime.now().astimezone().date().isoformat()  # 오늘 날짜 (전처리 실행일 기록용)

    mapping_df = load_model_mapping()
    model_lookup = build_model_lookup(mapping_df)

    source_df = read_source_sheet(input_path)
    source_lookup = build_source_lookup(source_df)

    hyundai_df = read_sales_sheet(input_path, HYUNDAI_SHEET)
    kia_df = read_sales_sheet(input_path, KIA_SHEET)

    hyundai_rows = preprocess_company_sales(
        hyundai_df, "현대자동차", TARGET_MODELS["현대자동차"], model_lookup, source_lookup, loaded_at,
    )
    kia_rows = preprocess_company_sales(
        kia_df, "기아", TARGET_MODELS["기아"], model_lookup, source_lookup, loaded_at,
    )

    result = pd.DataFrame(hyundai_rows + kia_rows)

    # 데이터정의서에 정의된 컬럼 순서로 맞춤
    result = result[[
        "sales_year", "manufacturer", "model_original", "model_key",
        "domestic_sales_count", "verification_status", "source_url", "loaded_at",
    ]]

    # 보기 좋게 정렬 (제조사 → 모델 → 연도 순)
    result = result.sort_values(["manufacturer", "model_original", "sales_year"]).reset_index(drop=True)

    validate_vehicle_sales(result)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)   # data/processed 폴더가 없으면 만들어줌
    result.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 70 + "\nD-SALES 판매량 전처리 완료\n" + "=" * 70)
    print(f"저장 위치: {OUTPUT_PATH}")
    print(f"총 행 수: {len(result)}")


# ── 18. 터미널에서 실행했을 때의 시작점 ──────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="현대·기아 판매량 검증본을 D-SALES long format으로 전처리합니다."
    )
    parser.add_argument(
        "--input",
        help="판매량 Excel 파일 경로. 생략하면 data/raw/sales 폴더의 유일한 xlsx를 사용합니다.",
    )
    args = parser.parse_args()

    input_path = find_input_file(args.input)
    run(input_path)


if __name__ == "__main__":
    main()