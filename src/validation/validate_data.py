"""
데이터 검증 스크립트 (최종본)

이 코드가 하는 일:
data/processed 폴더의 csv 파일들을 하나씩 열어서
파일마다 정해둔 규칙(FILES 딕셔너리)대로 검사한다.
검사 종류가 여러 가지라도, 파일마다 함수를 새로 만들지 않고
"어떤 검사를 할지"를 규칙으로만 적어두면
check_one_file() 함수 하나가 알아서 다 처리한다.
"""

import sys
from pathlib import Path
import pandas as pd
from src.preprocessing.model_mapping import MODEL_MASTER

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"

SUPPORTED_MODELS = set(MODEL_MASTER)

FILES = {
    "model_mapping.csv": {
        "columns": ["model_key", "manufacturer_std", "model_std", "generation_name",
                    "source_type", "alias_name", "alias_normalized", "match_status",
                    "review_note", "manufacturer_support_url"],
        "required": ["model_key", "manufacturer_std", "model_std", "source_type",
                     "alias_name", "alias_normalized", "match_status", "manufacturer_support_url"],
        "count": None,
        "check_model_key": True,
        "allowed_values": {"match_status": {"검증완료"}},
        "unique": [["source_type", "alias_name"]],
        "exclude_contains": {"alias_name": "순찰차"},
    },
    "vehicle_sales.csv": {
        "columns": ["sales_year", "manufacturer", "model_original", "model_key",
                    "domestic_sales_count", "verification_status", "source_url", "loaded_at"],
        # domestic_sales_count는 데이터정의서상 NULL 허용이라 required에서 뺌
        "required": ["sales_year", "manufacturer", "model_original", "model_key",
                     "verification_status", "source_url", "loaded_at"],
        "count": None,
        "check_model_key": True,
        "year_col": "sales_year",
        "year_type": "numeric",
        "allowed_years": [2020, 2021, 2022, 2023, 2024, 2025],
        "numeric_cols": ["sales_year"],
        # 보완필요도 데이터정의서상 정상 상태값
        "allowed_values": {"verification_status": {"공식자료", "교차검증", "보완필요"}},
        "unique": [["model_key", "sales_year"]],
        "non_negative": ["domestic_sales_count"],
    },
    "defect_reports.csv": {
        "columns": ["report_date", "manufacturer", "model_original", "model_year",
                    "model_key", "source_url", "loaded_at"],
        # manufacturer는 데이터정의서상 NULL 허용이라 required에서 뺌
        "required": ["report_date", "model_original", "model_key", "source_url", "loaded_at"],
        "count": None,
        "check_model_key": True,
        "year_col": "report_date",
        "year_type": "date",
        "excluded_years": [2023],  # 2023년 데이터는 정책상 제외 대상
        "allowed_years": [2020, 2021, 2022, 2024, 2025],
        "date_cols": ["report_date"],
    },
    "recall.csv": {
        "columns": ["recall_id", "manufacturer", "model_original", "model_key",
                    "production_from", "production_to", "recall_start_date", "recall_count",
                    "recall_reason", "recall_category", "source_url", "official_check_url", "loaded_at"],
        "required": ["recall_id", "manufacturer", "model_original", "model_key",
                     "recall_start_date", "recall_count", "source_url",
                     "official_check_url", "loaded_at"],
        "count": None,
        "check_model_key": True,
        "year_col": "recall_start_date",
        "year_type": "date",
        "allowed_years": [2020, 2021, 2022, 2023, 2024, 2025],
        "date_cols": ["recall_start_date"],
        "unique": [["recall_id"]],
        "non_negative": ["recall_count"],
    },
    "faq_master.csv": {
        "columns": ["faq_id", "provider", "category", "question", "answer",
                    "source_url", "collected_at"],
        "required": "all",
        "count": 12,
        "check_model_key": False,
        "unique": [["faq_id"]],
        "allowed_values": {"provider": {"자동차리콜센터"}, "category": {"리콜/제작결함"}},
        "date_cols": ["collected_at"],
    },
    "registration_summary.csv": {
        "columns": ["stat_year", "stat_month", "dimension_type", "dimension_value",
                    "registration_count", "source_url", "loaded_at"],
        "required": "all",
        "count": None,
        "check_model_key": False,
        "non_negative": ["registration_count"],
        "range": {"stat_month": (1, 12)},
        "unique": [["stat_year", "stat_month", "dimension_type", "dimension_value"]],
    },
}


def is_blank(series):
    """칸이 비어있는지(NaN이거나 공백문자인지) 확인"""
    return series.isna() | series.astype(str).str.strip().eq("")


def get_years(df, rule):
    """year_col을 숫자 연도 집합으로 바꿔줌 (날짜 컬럼이면 날짜→연도로 변환)"""
    col = rule["year_col"]
    if rule["year_type"] == "date":
        parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
        return parsed.dropna().dt.year.astype(int)
    return pd.to_numeric(df[col], errors="coerce").dropna().astype(int)


def check_one_file(filename, rule):
    """파일 하나 + 규칙을 받아서 문제 목록을 돌려줌 (문제 없으면 빈 리스트)"""
    errors = []
    path = DATA_DIR / filename
    if not path.exists():
        return [f"파일이 없음: {path}"]

    df = pd.read_csv(path, encoding="utf-8-sig")

    if list(df.columns) != rule["columns"]:
        errors.append(f"컬럼이 다름 (예상 {rule['columns']} / 실제 {list(df.columns)})")
        return errors

    # 필수값 (여기 리스트에 없는 컬럼은 빈 값이어도 정상 — NULL 허용 컬럼)
    required_cols = rule["columns"] if rule["required"] == "all" else rule["required"]
    for col in required_cols:
        blank = int(is_blank(df[col]).sum())
        if blank > 0:
            errors.append(f"{col}: 빈 값 {blank}건")

    if rule.get("count") is not None and len(df) != rule["count"]:
        errors.append(f"행 개수: 예상 {rule['count']}건 / 실제 {len(df)}건")

    if rule.get("check_model_key") and "model_key" in df.columns:
        actual = set(df["model_key"].dropna().astype(str).str.strip())
        wrong = actual - SUPPORTED_MODELS
        if wrong:
            errors.append(f"지원 안 하는 model_key: {sorted(wrong)}")

    if "year_col" in rule:
        years = get_years(df, rule)
        if "excluded_years" in rule:
            bad = set(years) & set(rule["excluded_years"])
            if bad:
                errors.append(f"제외 대상인 연도 데이터 존재: {sorted(bad)}")
        if "allowed_years" in rule:
            bad = set(years) - set(rule["allowed_years"])
            if bad:
                errors.append(f"허용 범위 밖 연도: {sorted(bad)}")

    for col, allowed in rule.get("allowed_values", {}).items():
        actual = set(df[col].dropna())
        bad = actual - allowed
        if bad:
            errors.append(f"{col}에 허용 안 된 값: {sorted(bad)}")

    for col, expected in rule.get("value_counts", {}).items():
        actual = df[col].value_counts().to_dict()
        if actual != expected:
            errors.append(f"{col} 값별 개수 불일치: 예상 {expected} / 실제 {actual}")

    for cols in rule.get("unique", []):
        dup = int(df.duplicated(subset=cols).sum())
        if dup:
            errors.append(f"{cols} 조합 중복 {dup}건")

    for col, word in rule.get("exclude_contains", {}).items():
        cnt = int(df[col].fillna("").str.contains(word).sum())
        if cnt:
            errors.append(f"{col}에 '{word}' 포함된 행 {cnt}건 (들어오면 안 됨)")

    # 숫자 컬럼 검사
    # 빈 값 허용 컬럼은 NaN이어도 오류가 아니고,
    # 값이 들어있는데 숫자로 바뀌지 않는 경우만 오류로 잡음
    for col in rule.get("non_negative", []):
        raw = df[col]
        nums = pd.to_numeric(raw, errors="coerce")

        invalid = (~is_blank(raw)) & nums.isna()
        if invalid.any():
            errors.append(f"{col} 숫자 변환 실패 {int(invalid.sum())}건")

        # NULL은 제외하고 실제 숫자 중 음수만 검사
        if nums.dropna().lt(0).any():
            errors.append(f"{col}에 음수 존재")

    for col, (lo, hi) in rule.get("range", {}).items():
        nums = pd.to_numeric(df[col], errors="coerce")
        if (~nums.between(lo, hi)).any():
            errors.append(f"{col}이 {lo}~{hi} 범위를 벗어남")

    for col in rule.get("date_cols", []):
        parsed = pd.to_datetime(df[col], errors="coerce", format="mixed")
        if parsed.isna().any():
            errors.append(f"{col} 날짜 변환 실패 {int(parsed.isna().sum())}건")

    for col in rule.get("numeric_cols", []):
        nums = pd.to_numeric(df[col], errors="coerce")
        if nums.isna().any():
            errors.append(f"{col} 숫자 변환 실패 {int(nums.isna().sum())}건")

    return errors


def main():
    print("=== 데이터 검증 시작 ===")
    total_errors = 0

    for filename, rule in FILES.items():
        errors = check_one_file(filename, rule)
        if errors:
            total_errors += len(errors)
            print(f"\n[FAIL] {filename}")
            for e in errors:
                print(f"  - {e}")
        else:
            print(f"\n[PASS] {filename}")

    print("\n" + "=" * 40)
    if total_errors == 0:
        print("전체 통과!")
        sys.exit(0)
    else:
        print(f"문제 {total_errors}개 발견")
        sys.exit(1)


if __name__ == "__main__":
    main()