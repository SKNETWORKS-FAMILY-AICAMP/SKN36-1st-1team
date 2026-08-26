"""
preprocess_registration.py
===========================
이 파일이 하는 일 (한 줄 요약):
  국토교통부 "자동차 등록현황" 엑셀에서 4가지 통계
  (①전국 총 등록대수, ②지역별, ③차종별, ④연료별)를 뽑아서 CSV 한 장으로 합쳐줍니다.

결과 저장 위치: data/processed/registration_summary.csv

원본 엑셀은 사람이 보기 좋게 만들어진 "복잡한 표"라서(제목·소계·합계가 뒤섞여 있음),
pandas가 자동으로 표 형태를 인식하지 못합니다. 그래서 이 스크립트는
"몇 번째 줄, 몇 번째 칸에 어떤 숫자가 있다"를 직접 좌표로 지정해서 값을 꺼냅니다.
(코드에 나오는 iloc[행, 열] 이라는 표현이 바로 "엑셀에서 이 위치의 칸"이라는 뜻입니다.)
"""

import argparse                    # 터미널에서 --input 옵션을 받기 위한 도구
from datetime import datetime      # 오늘 날짜를 기록하기 위한 도구
from pathlib import Path           # 파일/폴더 경로를 다루는 도구

import pandas as pd                # 엑셀 읽기 · 표 정리 · CSV 저장을 담당하는 라이브러리


# ── 1. 프로젝트 폴더 위치 ─────────────────────────────────────────
# 이 파일 기준 2단계 위 폴더가 프로젝트 최상위 폴더입니다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "registration"       # 등록현황 원본 엑셀을 넣어두는 폴더
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"             # 전처리 결과가 저장될 폴더
OUTPUT_PATH = PROCESSED_DIR / "registration_summary.csv"        # 이 스크립트가 최종적으로 만들 파일


# ── 2. 엑셀 안의 시트(탭) 이름들 ───────────────────────────────────
SHEET_REGION = "01.통계표"              # 전국 합계 + 지역별 + 차종별 정보가 모두 담긴 시트
SHEET_FUEL = "10.연료별_등록현황"        # 연료(휘발유/경유/전기 등)별 정보가 담긴 시트


# ── 3. 이 데이터의 공식 출처 주소 (모든 행에 그대로 기록됨) ────────────
SOURCE_URL = "https://stat.molit.go.kr/portal/cate/statView.do?hRsId=58&hFormId=5498&hDivEng=&month_yn="


# ── 4. 사용할 등록현황 엑셀 파일 찾기 ────────────────────────────────
def find_input_file(input_path):
    """--input으로 경로를 직접 줬으면 그 파일을 쓰고,
    안 줬으면 data/raw/registration 폴더 안에 있는 단 하나의 xlsx 파일을 자동으로 찾아 씁니다."""
    if input_path:
        path = Path(input_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")
        return path

    if not RAW_DIR.exists():
        raise FileNotFoundError(f"폴더가 없습니다: {RAW_DIR}")

    # "~$"로 시작하는 파일은 엑셀이 만드는 임시 파일이라 제외
    candidates = [f for f in RAW_DIR.glob("*.xlsx") if not f.name.startswith("~$")]

    if len(candidates) == 0:
        raise FileNotFoundError("등록현황 Excel 파일이 없습니다.")
    if len(candidates) > 1:
        raise RuntimeError("등록현황 Excel이 여러 개입니다. --input으로 하나를 지정해주세요.")
    return candidates[0]


# ── 5. "2026.07" 같은 문자열을 연도/월 숫자로 분리 ──────────────────
def parse_snapshot(value):
    """엑셀에 적힌 "2026.07"을 (연도=2026, 월=7)로 나눠줍니다.
    점(.)이 없는 "2026"만 있는 경우엔 (연도=2026, 월=None)으로 처리합니다."""
    text = str(value).strip()
    if "." in text:
        year, month = text.split(".", 1)
        return int(year), int(month)
    return int(text), None


# ── 6. 엑셀 숫자를 깔끔한 정수로 바꾸는 함수 ─────────────────────────
def to_int(value):
    """엑셀에서 숫자가 26692775.0 처럼 소수점 붙은 형태로 읽혀도 26692775(정수)로 바꿔줍니다.
    빈 칸은 0으로 처리합니다. (등록대수는 "값이 없으면 0대"로 봐도 되는 항목이라 이렇게 처리합니다.)"""
    if pd.isna(value):
        return 0
    return int(float(value))


# ── 7. CSV 한 줄(행)을 만드는 공용 함수 ─────────────────────────────
def make_row(stat_year, stat_month, dimension_type, dimension_value, registration_count, loaded_at):
    """같은 모양의 딕셔너리를 여기저기서 반복해서 만들지 않도록 한 곳에 모아둔 함수입니다."""
    return {
        "stat_year": stat_year,               # 통계 기준 연도
        "stat_month": stat_month,             # 통계 기준 월
        "dimension_type": dimension_type,     # 무엇을 기준으로 집계했는지: TOTAL/REGION/VEHICLE_TYPE/FUEL
        "dimension_value": dimension_value,   # 그 기준의 실제 값 (예: 전국, 서울, 승용, 휘발유)
        "registration_count": registration_count,  # 등록 대수
        "source_url": SOURCE_URL,
        "loaded_at": loaded_at,
    }


# ── 8. "01.통계표" 시트 전처리 (전국 합계 + 지역별 + 차종별) ──────────
def preprocess_main_sheet(input_path, loaded_at):
    """이 시트 하나에서 TOTAL(전국), REGION(지역별), VEHICLE_TYPE(차종별) 세 종류를 뽑아냅니다."""

    # header=None → 엑셀 구조가 복잡해서(제목/소계/합계 뒤섞임) pandas가 자동으로 표 머리글을 정하지 못하게 하고,
    # 우리가 직접 "몇 번째 줄, 몇 번째 칸"으로 값을 꺼냅니다.
    df = pd.read_excel(input_path, sheet_name=SHEET_REGION, header=None, engine="openpyxl")

    # 엑셀의 B2칸(파이썬 기준 2번째 줄, 2번째 칸=iloc[1,1])에 "2026.07" 같은 기준 시점이 적혀 있음
    stat_year, stat_month = parse_snapshot(df.iloc[1, 1])

    rows = []

    # "합계"라고 적힌 행(=전국 총계 행)을 찾음
    total_rows = df[df.iloc[:, 0].astype(str).str.strip().eq("합계")]
    if total_rows.empty:
        raise ValueError("01.통계표에서 합계 행을 찾지 못했습니다.")
    total_row = total_rows.iloc[0]

    # 전국 총 등록대수는 이 합계 행의 22번째 칸(iloc 기준 21번, 0부터 세므로)에 있음
    current_total = to_int(total_row.iloc[21])

    # --- TOTAL(전국) 한 줄 추가 ---
    rows.append(make_row(stat_year, stat_month, "TOTAL", "전국", current_total, loaded_at))

    # --- REGION(지역별) 여러 줄 추가 ---
    # 지역 데이터는 엑셀 6번째 줄(iloc 기준 5번)부터 시작해서, "합계"라는 글자를 다시 만나면 끝남
    for _, row in df.iloc[5:].iterrows():
        region = row.iloc[0]
        if pd.isna(region):
            continue  # 빈 줄은 건너뜀
        region = str(region).strip()
        if region == "합계":
            break  # 지역 목록이 끝나고 다음 표(다른 집계)가 시작되는 지점이므로 반복을 멈춤

        rows.append(make_row(stat_year, stat_month, "REGION", region, to_int(row.iloc[21]), loaded_at))

    # --- VEHICLE_TYPE(차종별) 4줄 추가 ---
    # 전국 합계 행 안에서, 차종마다 값이 적힌 칸 위치가 다름 (승용=6번째 칸, 승합=10번째 칸 ...)
    vehicle_type_values = {
        "승용": to_int(total_row.iloc[5]),
        "승합": to_int(total_row.iloc[9]),
        "화물": to_int(total_row.iloc[13]),
        "특수": to_int(total_row.iloc[17]),
    }
    for vehicle_type, count in vehicle_type_values.items():
        rows.append(make_row(stat_year, stat_month, "VEHICLE_TYPE", vehicle_type, count, loaded_at))

    return rows, stat_year, stat_month, current_total


# ── 9. "10.연료별_등록현황" 시트 전처리 ─────────────────────────────
def preprocess_fuel_sheet(input_path, loaded_at, expected_year, expected_month):
    """연료(휘발유/경유/전기 등)별 전국 등록대수를 뽑아냅니다."""
    df = pd.read_excel(input_path, sheet_name=SHEET_FUEL, header=None, engine="openpyxl")

    stat_year, stat_month = parse_snapshot(df.iloc[1, 1])

    # 두 시트가 같은 시점(같은 연·월) 자료인지 확인 — 다르면 서로 다른 시점을 억지로 합치는 셈이라 위험함
    if stat_year != expected_year or stat_month != expected_month:
        raise ValueError("통계표와 연료별 시트의 기준시점이 다릅니다.")

    rows = []

    # 연료별 데이터는 엑셀 5번째 줄(iloc 기준 4번)부터 시작
    for _, row in df.iloc[4:].iterrows():
        fuel = row.iloc[0]          # 연료 종류 (휘발유, 경유 등)
        vehicle_type = row.iloc[1]  # 차종 세부구분 (여기서는 "소계"인 줄만 원함)
        usage = row.iloc[2]         # 용도 세부구분 (여기서는 "계"인 줄만 원함)

        if pd.isna(fuel):
            continue
        fuel = str(fuel).strip()
        vehicle_type = "" if pd.isna(vehicle_type) else str(vehicle_type).strip()
        usage = "" if pd.isna(usage) else str(usage).strip()

        # 우리가 원하는 건 "그 연료의 전국 최종 합계" 한 줄뿐입니다.
        # 엑셀에는 차종별/용도별로 더 잘게 쪼갠 줄들도 같이 있는데, 그런 세부 줄까지 다 더하면 중복 집계가 됩니다.
        # "종별=소계, 용도=계"인 줄이 바로 그 연료의 최종 합계 줄이라서 이 조건으로 정확히 골라냅니다.
        if vehicle_type == "소계" and usage == "계" and fuel != "총계":
            rows.append(make_row(stat_year, stat_month, "FUEL", fuel, to_int(row.iloc[19]), loaded_at))

    return rows


# ── 10. 완성된 표가 앞뒤가 맞는지 최종 검사 ─────────────────────────
def validate_result(df):
    """TOTAL(전국 합계) 숫자와, REGION/VEHICLE_TYPE/FUEL 각각을 다 더한 숫자가 서로 같은지 확인합니다.
    (지역별을 다 더한 게 전국 합계와 다르면, 어딘가 빠뜨렸거나 잘못 읽은 것이므로 바로 에러를 냅니다.)"""
    total_df = df[df["dimension_type"] == "TOTAL"]
    if len(total_df) != 1:
        raise ValueError("TOTAL 행이 1개가 아닙니다.")
    total_count = int(total_df.iloc[0]["registration_count"])

    print("\n" + "=" * 60 + "\nD-REG 정합성 검사\n" + "=" * 60)
    print(f"TOTAL : {total_count:,}")

    for dimension_type in ["REGION", "VEHICLE_TYPE", "FUEL"]:
        subset = df[df["dimension_type"] == dimension_type]
        subtotal = int(subset["registration_count"].sum())
        print(f"{dimension_type} : {subtotal:,}")
        if subtotal != total_count:
            raise ValueError(f"{dimension_type} 합계가 TOTAL과 일치하지 않습니다.")

    print("\n[OK] 정합성 검사 통과")


# ── 11. 전체 흐름 실행 ─────────────────────────────────────────────
def run(input_path):
    loaded_at = datetime.now().astimezone().date().isoformat()  # 오늘 날짜 (전처리 실행일 기록용)

    print("\n" + "=" * 60 + "\nD-REG 전처리 시작\n" + "=" * 60)

    main_rows, stat_year, stat_month, current_total = preprocess_main_sheet(input_path, loaded_at)
    fuel_rows = preprocess_fuel_sheet(input_path, loaded_at, stat_year, stat_month)

    result = pd.DataFrame(main_rows + fuel_rows)

    # 데이터정의서에 정의된 컬럼 순서로 정리
    result = result[[
        "stat_year", "stat_month", "dimension_type", "dimension_value",
        "registration_count", "source_url", "loaded_at",
    ]]

    validate_result(result)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)  # data/processed 폴더가 없으면 만들어줌
    result.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60 + "\nD-REG 전처리 완료\n" + "=" * 60)
    print(f"저장 위치: {OUTPUT_PATH}")
    print(f"기준시점: {stat_year}-{stat_month:02d}")
    print(f"전국 등록대수: {current_total:,}대")


# ── 12. 터미널에서 실행했을 때의 시작점 ──────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        help="등록현황 Excel 경로. 생략하면 raw/registration의 xlsx를 자동 사용합니다.",
    )
    args = parser.parse_args()

    input_path = find_input_file(args.input)
    run(input_path)


if __name__ == "__main__":
    main()
