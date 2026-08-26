# 파일 경로를 편하게 다루기 위한 도구를 불러옵니다.
# 예: "data/output/파일.csv" 같은 경로를 운영체제에 맞게 안전하게 만들 수 있습니다.
from pathlib import Path

# CSV 파일을 표(DataFrame) 형태로 읽고 다루기 위해 pandas를 불러옵니다.
import pandas as pd


# 현재 이 파이썬 파일의 위치를 기준으로 프로젝트 최상위 폴더 경로를 구합니다.
# __file__       → 현재 실행 중인 faq_preprocessing.py 파일 위치
# .resolve()     → 절대경로로 바꿈
# .parents[2]    → 현재 파일에서 두 단계 위 폴더로 올라감
# 예:
# src/preprocessing/faq_preprocessing.py
#        ↑              ↑
#      1단계          2단계
# 결과적으로 프로젝트 루트 폴더를 가리킵니다.
ROOT = Path(__file__).resolve().parents[2]


# 크롤링으로 수집한 원본 FAQ CSV 파일의 위치를 지정합니다.
# ROOT / "data" / "output" ... 처럼 / 기호를 사용하면 경로를 이어붙일 수 있습니다.
INPUT_PATH = (
    ROOT
    / "data"
    / "output"
    / "car_go_all_faq_complete.csv"
)


# 전처리가 끝난 FAQ 데이터를 저장할 최종 파일 위치를 지정합니다.
# data/processed 폴더 아래에 faq_master.csv라는 이름으로 저장합니다.
OUTPUT_PATH = (
    ROOT
    / "data"
    / "processed"
    / "faq_master.csv"
)


# FAQ 전처리 전체 과정을 하나의 함수로 묶습니다.
# 이 함수를 실행하면:
# 1. 원본 CSV 읽기
# 2. 필요한 컬럼 확인
# 3. 빈 값 검사
# 4. 최종 컬럼 생성
# 5. 중복 검사
# 6. CSV 저장
# 순서로 진행됩니다.
def preprocess_faq():

    # 크롤링으로 만든 원본 FAQ CSV 파일을 읽습니다.
    # 읽은 결과는 df라는 표 형태의 변수에 저장됩니다.
    df = pd.read_csv(
        INPUT_PATH,

        # utf-8-sig는 한글이 들어있는 CSV를 엑셀에서도 깨지지 않게 읽기 위한 인코딩입니다.
        encoding="utf-8-sig",
    )

    # 원본 CSV에 반드시 있어야 하는 컬럼 이름들을 목록으로 정합니다.
    # 이 컬럼 중 하나라도 없으면 정상적으로 전처리할 수 없습니다.
    required = [
        "faq_no",
        "question",
        "answer",
        "source_url",
        "collected_at",
    ]

    # required에 적힌 컬럼 중 실제 df에 없는 컬럼만 찾아서 missing이라는 리스트에 담습니다.
    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    # missing 리스트 안에 값이 하나라도 있으면,
    # 즉 필요한 컬럼이 빠져 있으면 에러를 발생시켜 작업을 멈춥니다.
    if missing:
        raise ValueError(
            f"FAQ 원본 필수 컬럼 누락: {missing}"
        )

    # question 컬럼에 비어있는 값(NaN)이 하나라도 있는지 확인합니다.
    # .isna()       → 빈 값인지 True/False로 표시
    # .any()        → 하나라도 True가 있으면 True
    if df["question"].isna().any():
        raise ValueError(
            "question에 빈 값이 있습니다."
        )

    # answer 컬럼에도 빈 값이 있는지 확인합니다.
    if df["answer"].isna().any():
        raise ValueError(
            "answer에 빈 값이 있습니다."
        )

    # 최종 DB 적재용 데이터를 담을 새로운 빈 표를 만듭니다.
    result = pd.DataFrame()

    # 원본 faq_no를 이용해서 프로젝트용 FAQ 고유번호를 만듭니다.
    # 예:
    # faq_no = 1  → FAQ-REC-001
    # faq_no = 2  → FAQ-REC-002
    # faq_no = 15 → FAQ-REC-015
    result["faq_id"] = (
        df["faq_no"]

        # faq_no 값을 정수형으로 바꿉니다.
        # 예: 1.0 → 1
        .astype(int)

        # 각 숫자마다 아래 규칙을 적용해서 문자열 ID로 바꿉니다.
        # :03d는 숫자를 3자리로 맞추라는 뜻입니다.
        # 1 → 001
        # 10 → 010
        # 100 → 100
        .apply(
            lambda x: f"FAQ-REC-{x:03d}"
        )
    )

    # 모든 FAQ의 제공기관은 자동차리콜센터이므로 동일한 값으로 채웁니다.
    result["provider"] = "자동차리콜센터"

    # 현재 FAQ를 하나의 공통 분류로 관리하기 위해 고정값을 넣습니다.
    result["category"] = "리콜/제작결함"

    # 원본 question 값을 최종 question 컬럼에 넣습니다.
    # .str.strip()은 문장 앞뒤의 불필요한 공백을 제거합니다.
    result["question"] = (
        df["question"]
        .str.strip()
    )

    # 원본 answer 값을 최종 answer 컬럼에 넣습니다.
    # 마찬가지로 앞뒤 공백을 제거합니다.
    result["answer"] = (
    df["answer"]
    .str.replace(r"\s*ㅇ\s+", "\n○ ", regex=True)
    .str.strip()
    )

    # FAQ 원본 페이지 주소를 저장합니다.
    # 앞뒤 공백도 제거합니다.
    result["source_url"] = (
        df["source_url"]
        .str.strip()
    )

    # 크롤링한 시각은 원본 값을 그대로 저장합니다.
    # 예: 2026-08-23T17:57:33+09:00
    result["collected_at"] = (
        df["collected_at"]
    )

    # faq_id가 중복되어 있는지 확인합니다.
    # .duplicated() → 앞에서 이미 나온 값이면 True
    # .any()        → 중복이 하나라도 있으면 True
    if result["faq_id"].duplicated().any():
        raise ValueError(
            "faq_id 중복이 있습니다."
        )

    # 최종 저장 폴더가 없으면 자동으로 생성합니다.
    # parents=True
    # → 상위 폴더가 없어도 같이 생성
    # exist_ok=True
    # → 이미 폴더가 있어도 에러를 내지 않음
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 완성된 result 표를 CSV 파일로 저장합니다.
    result.to_csv(
        OUTPUT_PATH,

        # index=False
        # → pandas가 자동으로 붙이는 0,1,2... 번호 컬럼은 저장하지 않습니다.
        index=False,

        # 한글이 깨지지 않도록 utf-8-sig로 저장합니다.
        encoding="utf-8-sig",
    )

    # 아래부터는 전처리가 잘 끝났는지 터미널에서 확인하기 위한 출력입니다.
    print("=" * 60)

    # 작업 완료 메시지를 출력합니다.
    print("D-FAQ 전처리 완료")

    # 보기 좋게 구분선을 한 번 더 출력합니다.
    print("=" * 60)

    # 실제 저장된 파일 경로를 출력합니다.
    print(
        f"저장 위치: {OUTPUT_PATH}"
    )

    # 최종 FAQ가 총 몇 행인지 출력합니다.
    print(
        f"FAQ 행 수: {len(result)}"
    )

    # 한 줄 띄워 보기 좋게 만듭니다.
    print()

    # 최종 결과의 맨 위 5개 행만 미리 보여줍니다.
    # 데이터가 제대로 만들어졌는지 빠르게 확인하기 위한 용도입니다.
    print(
        result.head()
    )


# 이 파일을 직접 실행했을 때만 아래 코드를 실행합니다.
# 다른 파이썬 파일에서 import만 했을 때는 자동 실행되지 않습니다.
if __name__ == "__main__":

    # 위에서 만든 FAQ 전처리 함수를 실제로 실행합니다.
    preprocess_faq()