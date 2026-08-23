"""
preprocess_defect.py
=====================
이 파일이 하는 일 (한 줄 요약):
  한국교통안전공단 "자동차제작결함신고" 연도별 CSV 5개(2020·2021·2022·2024·2025)를
  하나로 합쳐서, 우리 6개 모델의 결함신고 데이터(D-DEF)로 만들어줍니다.

결과 저장 위치: data/processed/defect_reports.csv

★ 가장 중요한 규칙: 2023년은 원천 파일을 아예 구하지 못했습니다.
  - 2023년 신고 0건이라고 만들지 않습니다.
  - 2023년치를 가짜로 채우지도 않습니다.
  - 그냥 "2023년 자료는 우리한테 없다"는 사실을 있는 그대로 두고,
    나중에 화면에서는 "데이터 미확보"라고 보여줍니다.
    (0건과 "모른다"는 완전히 다른 의미이기 때문입니다.)

데이터정의서 v2.6 기준 D-DEF 컬럼: report_date, manufacturer, model_original, model_year, model_key, source_url, loaded_at
  (manufacturer / model_year는 "선택" 항목이라 비어있어도 됨, 나머지는 전부 "필수")
"""

from datetime import datetime   # 전처리한 날짜를 loaded_at에 기록하기 위한 도구
from pathlib import Path        # 파일/폴더 경로를 다루는 도구
import re                       # 문자열에서 괄호·공백 등을 규칙적으로 지우거나 바꾸는 도구
import unicodedata              # 겉보기엔 같은 글자인데 컴퓨터 내부 저장 방식이 다른 경우를 통일하는 도구

import pandas as pd             # CSV 읽기·필터링·정렬·저장을 담당하는 라이브러리


# ── 1. 프로젝트 폴더 위치 ─────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "defect"           # 결함신고 원본 CSV들을 넣는 폴더
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_MAPPING_PATH = PROCESSED_DIR / "model_mapping.csv"      # 이전 단계(D-MAP)가 만든 파일
OUTPUT_PATH = PROCESSED_DIR / "defect_reports.csv"             # 이 스크립트가 최종적으로 만들 파일


# ── 2. 서비스가 다루는 기간과, 실제로 확보한/못 한 연도 ─────────────
START_YEAR = 2020
END_YEAR = 2025
AVAILABLE_SOURCE_YEARS = {2020, 2021, 2022, 2024, 2025}   # 원천 파일을 실제로 구한 연도
MISSING_SOURCE_YEARS = {2023}                              # ★ 원천 파일 자체가 없는 연도 (0건 아님!)


# ── 3. 원본 CSV에 꼭 있어야 하는 컬럼 (실제로 이 4개뿐임) ────────────
# 신고사유·신고내용·결함유형 같은 건 원본에 없으므로, 우리가 임의로 만들어 넣지 않습니다.
REQUIRED_COLUMNS = {"접수일자", "제작사", "차명", "모델년도"}


# ── 4. 이 데이터의 공식 출처 주소 ───────────────────────────────────
SOURCE_URL = "https://www.data.go.kr/data/15016450/fileData.do"


# ── 5. 차명을 "비교하기 좋은 모양"으로 다듬는 함수 ──────────────────
def normalize_alias(value):
    """D-MAP의 alias_normalized와 비교할 수 있게 원본 차명을 정리합니다.
    예) "아반떼(AVANTE)" → "아반떼 avante"
    ★ 주의: 이 함수 결과만 보고 모델을 자동으로 확정하지 않습니다.
    실제 model_key는 D-MAP의 검증완료 alias와 정확히 일치할 때만 부여됩니다."""
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.strip().lower()
    text = re.sub(r"[()\[\]{}]", " ", text)   # 괄호류 → 공백 (괄호 안 AVANTE 같은 정보는 지우지 않음)
    text = re.sub(r"[-_/]", " ", text)
    text = re.sub(r"[^0-9a-z가-힣\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── 6. 제작사명을 "비교용"으로만 통일하는 함수 ──────────────────────
def normalize_manufacturer_for_check(value):
    """제작사명을 "현대자동차"/"기아"로 통일합니다.
    ★ 매우 중요: 이 결과는 D-DEF의 manufacturer 컬럼에 절대 저장하지 않습니다.
    D-DEF의 manufacturer는 원문을 그대로 보존해야 하므로, 이 함수는 오직
    "원문 제작사가 D-MAP이 기대하는 제조사와 다른지"를 검사할 때만 사용합니다."""
    if pd.isna(value):
        return None  # 원천 제작사는 비어있을 수 있음

    text = unicodedata.normalize("NFKC", str(value)).strip().lower()
    compact = re.sub(r"[\s().]", "", text)

    if "현대자동차" in text or compact in {"현대", "hyundai", "hyundaimotor"}:
        return "현대자동차"
    if "기아자동차" in text or "기아주식회사" in compact or compact in {"기아", "kia", "kiamotors", "kiacorporation"}:
        return "기아"
    return None


# ── 7. "우리 6개 모델처럼 보이는지" 1차로 걸러내는 함수 ───────────────
def looks_like_target_model(model_name):
    """이 함수는 model_key를 정하지 않습니다. 그냥 "D-MAP에 새로 등록해야 할지도 모르는
    우리 대상 모델 후보"를 놓치지 않고 찾아내기 위한 1차 필터일 뿐입니다."""
    name = normalize_alias(model_name)

    if any(keyword in name for keyword in ["아반떼", "쏘나타", "그랜저", "스포티지", "쏘렌토"]):
        return True

    # K5는 단순히 "k5 in name"으로 검사하면 SLK55, AK550 같은 전혀 다른 차량도 걸릴 수 있어서,
    # 문자열이 정확히 "k5"로 시작할 때만("k5" 뒤에 공백이 오거나 문자열이 끝날 때만) 인정합니다.
    return re.match(r"^k5(?:\s|$)", name) is not None


# ── 8. D-MAP(model_mapping.csv)에서 결함신고용 별칭만 불러오기 ───────
def load_defect_mapping():
    """model_mapping.csv에서 source_type='DEFECT'인 별칭만 가져옵니다."""
    if not MODEL_MAPPING_PATH.exists():
        raise FileNotFoundError(
            "model_mapping.csv가 없습니다.\n먼저 아래 명령을 실행해주세요.\n\n"
            "uv run python src/preprocessing/model_mapping.py"
        )

    df = pd.read_csv(MODEL_MAPPING_PATH, encoding="utf-8-sig")

    required = {"model_key", "manufacturer_std", "source_type", "alias_name", "alias_normalized", "match_status"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"model_mapping.csv 필수 컬럼이 없습니다: {sorted(missing)}")

    df = df[df["source_type"] == "DEFECT"].copy()
    if df.empty:
        raise ValueError("model_mapping.csv에 source_type='DEFECT' 매핑이 없습니다.")

    # model_mapping.py가 만든 alias_normalized 값과, 지금 이 파일의 normalize_alias() 결과가
    # 서로 다르면 두 스크립트의 정규화 규칙이 어긋난 것이므로 미리 잡아냅니다.
    df["_check"] = df["alias_name"].apply(normalize_alias)
    mismatch = df[df["alias_normalized"].fillna("") != df["_check"]]
    if not mismatch.empty:
        raise ValueError(
            "model_mapping.csv의 alias_normalized와 현재 정규화 규칙이 다릅니다.\nmodel_mapping.py를 다시 실행해주세요."
        )
    return df


# ── 9. (정규화된 차명) → D-MAP 행을 바로 찾는 사전 만들기 ─────────────
def build_mapping_lookup(mapping_df):
    """예: lookup["아반떼 avante"] 하면 그 차명의 D-MAP 정보(model_key 등)를 바로 꺼낼 수 있게 만듭니다."""
    lookup = {}
    for _, row in mapping_df.iterrows():
        alias = row["alias_normalized"]

        if alias in lookup:
            previous = lookup[alias]
            # 같은 차명(alias)인데 이전에 저장된 model_key/match_status와 다르면 모순이므로 에러
            if str(previous["model_key"]) != str(row["model_key"]) or \
               str(previous["match_status"]) != str(row["match_status"]):
                raise ValueError(f"D-MAP DEFECT alias 충돌: {row['alias_name']}")

        lookup[alias] = row.to_dict()
    return lookup


# ── 10. data/raw/defect 폴더 안의 CSV 파일 목록 찾기 ─────────────────
def find_source_files():
    """폴더 안의 모든 CSV를 찾습니다. 파일 이름만 믿지 않고,
    실제 접수일자 안의 연도를 나중에 한 번 더 직접 확인합니다."""
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"결함신고 원본 폴더가 없습니다:\n{RAW_DIR}")

    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError("data/raw/defect 폴더에 결함신고 CSV가 없습니다.")
    return files


# ── 11. CSV 파일 하나 읽기 ──────────────────────────────────────────
def read_source_file(path):
    """실제 업로드한 5개 파일은 모두 cp949(한글 윈도우) 인코딩으로 읽힙니다."""
    df = pd.read_csv(path, encoding="cp949")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}\n필수 컬럼이 없습니다: {sorted(missing)}")

    # 문서에 정의된 원천 4개 컬럼만 사용 (나중에 공공데이터에 컬럼이 추가돼도 우리가 임의로 서비스에 넣지 않도록 고정)
    return df[["접수일자", "제작사", "차명", "모델년도"]].copy()


# ── 12. 접수일자를 실제 날짜형으로 변환 ──────────────────────────────
def clean_report_date(series, file_name):
    """"2025-07-15" 같은 문자열을 진짜 날짜 데이터로 바꿉니다. (report_date는 필수값입니다.)"""
    parsed = pd.to_datetime(series, errors="coerce")

    bad_mask = series.notna() & parsed.isna()
    if bad_mask.any():
        bad_values = series[bad_mask].astype(str).drop_duplicates().tolist()
        raise ValueError(f"{file_name} 접수일자 변환 실패: {bad_values[:10]}")

    if parsed.isna().any():
        raise ValueError(f"{file_name}에 접수일자 결측이 있습니다.")
    return parsed


# ── 13. 모델년도를 깔끔한 숫자로 변환 ─────────────────────────────────
def clean_model_year(series, file_name):
    """2021.0 같은 값을 2021(정수)로 바꾸고, 빈 칸은 그대로 빈 값(<NA>)으로 둡니다.
    ★ model_year 결측은 정상적으로 허용되는 상태입니다. 화면에서는 "미상"으로 표시됩니다."""
    numeric = pd.to_numeric(series, errors="coerce")

    bad_mask = series.notna() & numeric.isna()
    if bad_mask.any():
        bad_values = series[bad_mask].astype(str).drop_duplicates().tolist()
        raise ValueError(f"{file_name} 모델년도 숫자 변환 실패: {bad_values[:10]}")

    # 2021.5 같은 이상한(정수가 아닌) 모델년도가 있는지 확인
    non_integer = numeric.notna() & (numeric != numeric.round())
    if non_integer.any():
        raise ValueError(f"{file_name}에 정수가 아닌 모델년도가 있습니다.")

    # 보통의 정수(int)는 빈 값을 담을 수 없지만, pandas의 "Int64"는 2021이나 <NA>를 함께 담을 수 있습니다.
    return numeric.astype("Int64")


# ── 14. CSV 파일 한 개를 전처리 ──────────────────────────────────────
def preprocess_one_file(path, mapping_lookup, loaded_at):
    """원본 CSV 한 개 → 날짜/모델년도 정리 → D-MAP 대조 → 검증완료만 → D-DEF 한 조각 완성, 순서로 처리합니다."""

    df = read_source_file(path)
    df["report_date"] = clean_report_date(df["접수일자"], path.name)

    # 이 파일이 실제로 몇 년도 자료인지 확인 (연도별 파일 하나에 여러 해가 섞여 있으면 이상한 상태)
    source_years = set(df["report_date"].dt.year.unique().tolist())
    if len(source_years) != 1:
        raise ValueError(f"{path.name}에 여러 접수연도가 섞여 있습니다: {sorted(source_years)}")
    source_year = int(next(iter(source_years)))

    df["model_year"] = clean_model_year(df["모델년도"], path.name)

    # 원본 차명은 앞뒤 공백만 정리하고, 표준 모델명으로 바꾸지 않고 그대로 보존
    df["model_original"] = df["차명"].astype("string").str.strip()
    df["_alias_normalized"] = df["model_original"].apply(normalize_alias)

    # 우리 6개 모델 후보로 보이는데 D-MAP에 등록 안 된 새 차명이 있으면, 조용히 버리지 않고 바로 알림
    candidate_df = df[df["model_original"].apply(looks_like_target_model)].copy()
    candidate_df["_has_mapping"] = candidate_df["_alias_normalized"].isin(mapping_lookup.keys())
    unmapped = (
        candidate_df[~candidate_df["_has_mapping"]]["model_original"].dropna().drop_duplicates().tolist()
    )
    if unmapped:
        raise ValueError(
            f"{path.name}\n우리 6개 모델처럼 보이지만 D-MAP에 등록되지 않은 DEFECT alias가 있습니다:\n"
            + "\n".join(f"- {name}" for name in unmapped)
        )

    # D-MAP에 실제로 등록된 alias만 남기고, model_key/match_status/기대 제조사를 붙임
    mapped_df = df[df["_alias_normalized"].isin(mapping_lookup.keys())].copy()

    def get_mapping_value(alias, column):
        return mapping_lookup[alias].get(column)

    mapped_df["_match_status"] = mapped_df["_alias_normalized"].apply(lambda a: get_mapping_value(a, "match_status"))
    mapped_df["model_key"] = mapped_df["_alias_normalized"].apply(lambda a: get_mapping_value(a, "model_key"))
    mapped_df["_expected_manufacturer"] = mapped_df["_alias_normalized"].apply(
        lambda a: get_mapping_value(a, "manufacturer_std")
    )

    excluded_count = int((mapped_df["_match_status"] == "제외").sum())  # 예: "아반떼(AVANTE) 순찰차" 같은 제외 차량 수

    # 검증완료인 매핑만 실제 서비스에 사용
    verified_df = mapped_df[mapped_df["_match_status"] == "검증완료"].copy()

    # 제작사는 원문 그대로 보존 (빈 칸은 빈 칸으로 둠 — 임의로 "현대자동차"/"기아"를 채워 넣지 않음. v2.6 규칙)
    verified_df["manufacturer"] = verified_df["제작사"].astype("string").str.strip().replace("", pd.NA)

    # 원문에 적힌 제작사가 있는 경우에만, D-MAP이 기대하는 제조사와 같은지 검사
    verified_df["_manufacturer_for_check"] = verified_df["manufacturer"].apply(normalize_manufacturer_for_check)
    mismatch = verified_df[
        verified_df["manufacturer"].notna()
        & (verified_df["_manufacturer_for_check"] != verified_df["_expected_manufacturer"])
    ]
    if not mismatch.empty:
        examples = mismatch[["제작사", "model_original", "_expected_manufacturer"]].drop_duplicates().head(10)
        raise ValueError(f"{path.name}\n원천 제작사와 D-MAP 표준 제작사가 충돌합니다:\n{examples.to_string(index=False)}")

    result = pd.DataFrame({
        "report_date": verified_df["report_date"].dt.strftime("%Y-%m-%d"),
        "manufacturer": verified_df["manufacturer"],           # 결측 허용, 원문 그대로
        "model_original": verified_df["model_original"],
        "model_year": verified_df["model_year"],                 # 결측 허용
        "model_key": verified_df["model_key"],                    # 검증완료 매핑만 여기까지 남음
        "source_url": SOURCE_URL,
        "loaded_at": loaded_at,
    })

    info = {
        "source_year": source_year,
        "raw_rows": len(df),
        "target_rows": len(result),
        "excluded_rows": excluded_count,
    }
    return result, info


# ── 15. 완성된 D-DEF 표가 규칙을 잘 지켰는지 최종 점검 ────────────────
def validate_final_result(result, source_infos):
    """만들어진 defect_reports.csv가 v2.6 문서 조건과 일치하는지 확인합니다."""
    print("\n" + "=" * 70 + "\nD-DEF 정합성 검사\n" + "=" * 70)

    actual_source_years = {info["source_year"] for info in source_infos}
    print(f"확보 원천 연도 : {sorted(actual_source_years)}")
    print(f"미확보 원천 연도: {sorted(MISSING_SOURCE_YEARS)}")

    # 5개 필수 연도가 전부 모여있는지
    missing_files = AVAILABLE_SOURCE_YEARS - actual_source_years
    if missing_files:
        raise ValueError(f"필수 결함신고 원천 연도가 없습니다: {sorted(missing_files)}")

    # 2023 파일이 실수로라도 들어와 있으면, 지금 문서 정의(2023=미확보)와 충돌하므로 막음
    if actual_source_years & MISSING_SOURCE_YEARS:
        raise ValueError("현재 v2.6에서는 2023을 원천 미확보로 정의했습니다.\n2023 파일을 사용하려면 먼저 문서를 수정해야 합니다.")

    # 결과의 접수연도가 전부 허용된 연도인지
    report_years = pd.to_datetime(result["report_date"]).dt.year
    if not result[~report_years.isin(AVAILABLE_SOURCE_YEARS)].empty:
        raise ValueError("D-DEF에 허용되지 않은 접수연도가 포함되어 있습니다.")

    # manufacturer/model_year는 선택 항목이라 결측 검사 대상에서 제외, 나머지 5개는 필수
    for column in ["report_date", "model_original", "model_key", "source_url", "loaded_at"]:
        if result[column].isna().any():
            raise ValueError(f"필수 컬럼 '{column}'에 결측이 있습니다.")

    expected_model_keys = {"HYU_AVANTE", "HYU_SONATA", "HYU_GRANDEUR", "KIA_K5", "KIA_SPORTAGE", "KIA_SORENTO"}
    actual_model_keys = set(result["model_key"].unique())

    unexpected = actual_model_keys - expected_model_keys
    if unexpected:
        raise ValueError(f"예상하지 않은 model_key가 있습니다: {sorted(unexpected)}")

    missing_models = expected_model_keys - actual_model_keys
    if missing_models:
        raise ValueError(f"D-DEF에 데이터가 전혀 없는 대상 모델이 있습니다: {sorted(missing_models)}")

    # 참고용 요약표: 모델별 × 접수연도별 신고 건수 (2023은 아예 열에서 빠짐 — 있지도 않은 0을 보여주지 않기 위해)
    summary = (
        result.assign(report_year=pd.to_datetime(result["report_date"]).dt.year)
        .groupby(["model_key", "report_year"]).size()
        .unstack(fill_value=0)
        .reindex(columns=[2020, 2021, 2022, 2024, 2025], fill_value=0)
    )
    print("\n모델별 접수연도 신고 레코드 수")
    print(summary.to_string())

    manufacturer_nulls = int(result["manufacturer"].isna().sum())
    model_year_nulls = int(result["model_year"].isna().sum())

    print(f"\n전체 D-DEF 행 수    : {len(result):,}")
    print(f"manufacturer 결측 : {manufacturer_nulls:,}")
    print(f"model_year 결측    : {model_year_nulls:,}")

    print(
        "\n※ manufacturer 결측은 원문 그대로 보존합니다."
        "\n※ model_year 결측은 삭제하지 않고 화면에서 '미상'으로 표시합니다."
        "\n※ 2023은 0건이 아니라 '데이터 미확보'입니다."
        "\n※ 신고 사유/내용/결함유형은 원천에 없으므로 분석하지 않습니다."
    )
    print("\n[OK] D-DEF 정합성 검사 통과")


# ── 16. 전체 흐름 실행 ─────────────────────────────────────────────
def run():
    print("\n" + "=" * 70 + "\nD-DEF 결함신고 전처리 시작\n" + "=" * 70)

    loaded_at = datetime.now().astimezone().date().isoformat()

    mapping_df = load_defect_mapping()
    mapping_lookup = build_mapping_lookup(mapping_df)

    source_files = find_source_files()
    print(f"\nraw/defect에서 찾은 CSV: {len(source_files)}개")

    results = []
    source_infos = []
    seen_source_years = set()   # 같은 연도 파일이 두 번 들어오는 사고를 막기 위한 기록

    for path in source_files:
        file_result, info = preprocess_one_file(path, mapping_lookup, loaded_at)
        source_year = info["source_year"]

        # 2020~2025 분석기간 밖의 파일은 그냥 건너뜀 (에러는 아님, 안내만)
        if not (START_YEAR <= source_year <= END_YEAR):
            print(f"[제외] {path.name} → 접수연도 {source_year}: 분석기간 밖")
            continue

        # 2023년 파일이 섞여 들어오면, "2023=미확보"라는 문서 정의와 정면으로 충돌하므로 즉시 중단
        if source_year in MISSING_SOURCE_YEARS:
            raise ValueError(f"{path.name}\n현재 v2.6에서는 2023 원천 미확보로 정의되어 있습니다.")

        # 같은 연도 파일이 폴더에 2개 이상 있으면, 신고건수가 두 배로 잡힐 수 있으므로 중단
        if source_year in seen_source_years:
            raise ValueError(f"{source_year}년 결함신고 CSV가 data/raw/defect에 2개 이상 있습니다.\n연도별 원본 파일은 1개만 남겨주세요.")
        seen_source_years.add(source_year)

        results.append(file_result)
        source_infos.append(info)
        print(f"[확인] {source_year} | 원본 {info['raw_rows']:,}행 | 대상모델 {info['target_rows']:,}행 | 제외 {info['excluded_rows']:,}행")

    if not results:
        raise ValueError("전처리할 D-DEF 데이터가 없습니다.")

    result = pd.concat(results, ignore_index=True)
    result = result.sort_values(["report_date", "model_key", "model_original"]).reset_index(drop=True)

    # 데이터정의서에 정의된 컬럼 순서로 정리
    result = result[["report_date", "manufacturer", "model_original", "model_year", "model_key", "source_url", "loaded_at"]]

    validate_final_result(result, source_infos)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 70 + "\nD-DEF 결함신고 전처리 완료\n" + "=" * 70)
    print(f"저장 위치: {OUTPUT_PATH}")
    print(f"저장 행 수: {len(result):,}")


# ── 17. 이 파일을 직접 실행했을 때만 동작 ─────────────────────────
if __name__ == "__main__":
    run()
