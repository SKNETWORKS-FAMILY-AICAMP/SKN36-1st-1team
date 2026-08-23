"""
load_to_mysql.py
=================
이 파일의 역할:
  data/processed 폴더의 전처리 완료 CSV 파일을 읽어
  MySQL 데이터베이스에 Full Refresh 방식으로 적재합니다.

기준 문서:
  - 데이터정의서 v2.6
  - 요구사항정의서 v2.6
  - DB_물리설계 시트

전체 처리 흐름:
  1) 전처리 완료 CSV의 컬럼, 필수값, 허용값, 중복 여부를 검증
  2) 기존 DB 데이터를 삭제
  3) 검증이 끝난 데이터를 다시 INSERT
  4) 행 수, model_key 연결, 주요 데이터 정책을 최종 검증
  5) 모든 단계가 정상적으로 완료되면 COMMIT
     중간에 오류가 발생하면 전체 작업을 ROLLBACK

DELETE부터 INSERT 및 최종 검증까지 하나의 트랜잭션으로 처리하므로,
재적재 도중 오류가 발생해도 DB가 일부만 갱신된 상태로 남지 않습니다.

D-MAP 주요 규칙:
  - match_status='검증완료'인 행은 model_key가 반드시 존재해야 합니다.
  - match_status='제외' 또는 '검토중'인 행은 model_key가 NULL일 수 있습니다.
"""

# ── 1. 필요한 도구(라이브러리) 불러오기 ─────────────────────────────
import os                        # 운영체제 기능(환경변수 읽기 등)을 쓰기 위한 표준 라이브러리
from pathlib import Path         # 파일/폴더 경로를 다루기 쉽게 해주는 라이브러리

import numpy as np                # 숫자 계산용 라이브러리 (pandas가 내부적으로 사용)
import pandas as pd                # 표(엑셀 같은 데이터)를 다루는 라이브러리 — CSV를 여기로 읽음
import pymysql                     # 파이썬에서 MySQL 데이터베이스에 접속하게 해주는 라이브러리
from dotenv import load_dotenv     # .env 파일(비밀번호 등을 적어두는 설정 파일)을 읽어오는 도구


# ── 2. 프로젝트 폴더 위치와 설정값 준비 ─────────────────────────────

# 이 파이썬 파일 기준으로 3단계 위 폴더가 프로젝트의 맨 꼭대기(루트) 폴더라는 뜻입니다.
# 예: SKN36-1st-1team/src/db/load_to_mysql.py 라면
#     parents[2] 는 SKN36-1st-1team 폴더를 가리킵니다.
ROOT = Path(__file__).resolve().parents[2]

# 전처리(정제)가 끝난 CSV 파일들이 들어있는 폴더 경로입니다.
PROCESSED = ROOT / "data" / "processed"

# .env 파일(DB 주소, 아이디, 비밀번호 등 비밀 설정을 적어두는 파일)을 불러옵니다.
# .env 파일은 깃허브에 올리지 않는 것이 보통이라, 팀원마다 자기 컴퓨터의 .env를 따로 둡니다.
load_dotenv(ROOT / ".env")

# .env에서 읽어온 값들을 하나의 딕셔너리(이름표가 붙은 상자들의 모음)로 정리합니다.
# os.getenv("이름", "기본값") 은 "그 이름의 환경변수가 있으면 쓰고, 없으면 기본값을 쓴다"는 뜻입니다.
DB = dict(
    host=os.getenv("DB_HOST", "localhost"),     # DB 서버 주소 (없으면 내 컴퓨터로 간주)
    port=int(os.getenv("DB_PORT", "3306")),     # DB 접속 포트 번호 (MySQL 기본값 3306)
    user=os.getenv("DB_USER"),                  # DB 로그인 아이디
    password=os.getenv("DB_PASSWORD"),          # DB 로그인 비밀번호
    database=os.getenv("DB_NAME", "skn36_1st_1team"),  # 사용할 데이터베이스 이름
)

# 아이디가 아예 없거나 비밀번호가 설정 자체가 안 되어 있으면, 더 진행하지 않고 바로 에러를 냅니다.
# (비밀번호가 빈 문자열 ""인 것과 아예 안 적혀 있는 것(None)을 구분하려고 "is None"을 씁니다.)
if not DB["user"] or DB["password"] is None:
    raise ValueError(".env에 DB_USER/DB_PASSWORD가 없습니다.")

# DB 이름이 우리가 약속한 이름과 다르면, 엉뚱한 DB에 잘못 적재하는 사고를 막기 위해 바로 멈춥니다.
if DB["database"] != "skn36_1st_1team":
    raise ValueError(f"DB_NAME이 DB_물리설계와 다릅니다: {DB['database']}")


# ── 3. 프로젝트에서 정한 "규칙표"들을 미리 정의 ─────────────────────

# 우리 서비스가 실제로 지원하는 자동차 모델 6개의 표준 코드(model_key) 목록입니다.
# 이 목록에 없는 model_key가 데이터에 등장하면 "우리가 모르는 모델"이므로 에러로 처리합니다.
EXPECTED_MODEL_KEYS = {
    "HYU_AVANTE", "HYU_SONATA", "HYU_GRANDEUR",
    "KIA_K5", "KIA_SPORTAGE", "KIA_SORENTO",
}

# 각 컬럼(열)에 들어올 수 있는 "허용된 값"들을 미리 정해둔 것입니다.
# 예를 들어 match_status 칸에는 '검증완료', '검토중', '제외' 세 가지만 들어올 수 있습니다.
# 여기 없는 값이 들어오면 오타이거나 잘못된 데이터로 보고 에러를 냅니다.
ALLOWED = {
    "match_status": {"검증완료", "검토중", "제외"},
    "source_type": {"SALES", "DEFECT", "REC"},
    "verification_status": {"공식자료", "교차검증", "보완필요"},
    "dimension_type": {"TOTAL", "REGION", "VEHICLE_TYPE", "FUEL"},
}

# 결함신고 데이터는 2023년 원본 파일을 아예 구하지 못했기 때문에,
# 서비스에서 실제로 다루는 연도는 2020·2021·2022·2024·2025년 뿐입니다(2023년은 통째로 제외).
DEFECT_ALLOWED_YEARS = {2020, 2021, 2022, 2024, 2025}

# 각 CSV 파일에 "정확히 이 순서로 이 컬럼들이 있어야 한다"는 약속을 적어둔 것입니다.
# 데이터정의서에 정의된 컬럼명과 순서를 그대로 옮겨온 것이라, 여기가 곧 "정답지" 역할을 합니다.
COLUMNS = {
    "model_mapping": [
        "model_key", "manufacturer_std", "model_std", "generation_name", "source_type",
        "alias_name", "alias_normalized", "match_status", "review_note", "manufacturer_support_url",
    ],
    "registration_summary": [
        "stat_year", "stat_month", "dimension_type", "dimension_value",
        "registration_count", "source_url", "loaded_at",
    ],
    "vehicle_sales": [
        "sales_year", "manufacturer", "model_original", "model_key", "domestic_sales_count",
        "verification_status", "source_url", "loaded_at",
    ],
    "defect_reports": [
        "report_date", "manufacturer", "model_original", "model_year", "model_key",
        "source_url", "loaded_at",
    ],
    "recall": [
        "recall_id", "manufacturer", "model_original", "model_key", "production_from", "production_to",
        "recall_start_date", "recall_count", "recall_reason", "recall_category",
        "source_url", "official_check_url", "loaded_at",
    ],
    "faq": [
        "faq_id", "provider", "category", "question", "answer", "source_url", "collected_at",
    ],
}

# 각 데이터가 어느 CSV 파일에서 오는지, 그리고 그 파일이 "반드시 있어야 하는지(True)"
# 아니면 "없어도 괜찮은지(False)"를 적어둔 표입니다. (FAQ는 아직 준비가 안 됐어도 진행 가능하게 False)
FILES = {
    "model_mapping": ("model_mapping.csv", True),
    "registration_summary": ("registration_summary.csv", True),
    "vehicle_sales": ("vehicle_sales.csv", True),
    "defect_reports": ("defect_reports.csv", True),
    "recall": ("recall.csv", True),
    "faq": ("faq_master.csv", True),
}

# DB에 실제로 데이터를 넣을 때, "어느 테이블에 어떤 컬럼 순서로 넣을지"를 정리한 표입니다.
# CSV의 컬럼 순서와 DB 테이블의 컬럼 순서가 완전히 같지 않을 수 있어서 따로 정의합니다.
# (예: vehicle_sales는 DB에서 model_key를 맨 앞에 두는데, 이게 DB의 기본키 순서와 맞추기 위함입니다.)
INSERT_SPEC = {
    "model_master": ["model_key", "manufacturer_std", "model_std", "manufacturer_support_url"],
    "model_mapping": [
        "model_key", "manufacturer_std", "model_std", "generation_name", "source_type",
        "alias_name", "alias_normalized", "match_status", "review_note", "manufacturer_support_url",
    ],
    "registration_summary": COLUMNS["registration_summary"],
    "vehicle_sales": [
        "model_key", "sales_year", "manufacturer", "model_original",
        "domestic_sales_count", "verification_status", "source_url", "loaded_at",
    ],
    "defect_reports": COLUMNS["defect_reports"],
    "recall_campaigns": COLUMNS["recall"],
    "faq_master": COLUMNS["faq"],
}

# 기존 데이터를 지울 때의 순서입니다. "자식 → 부모" 순서로 지워야 합니다.
# model_master(부모 테이블, 6개 표준 모델)를 다른 테이블(자식들)이 참조하고 있기 때문에,
# 자식들을 먼저 지우지 않으면 "아직 나를 참조하는 데이터가 있어요"라며 DB가 삭제를 거부합니다.
DELETE_ORDER = [
    "model_mapping", "vehicle_sales", "defect_reports", "recall_campaigns",
    "registration_summary", "faq_master", "model_master",
]


# ── 4. 여러 곳에서 반복해서 쓰는 "공용 도구" 함수들 ──────────────────

def is_blank(s):
    """어떤 컬럼(s)의 각 칸이 '비어있는지'를 True/False로 알려줍니다.
    비어있다는 것은: 값이 아예 없거나(NaN) / 빈 문자열("") / 공백만 있는 경우("   ") 를 뜻합니다."""
    # s.isna() → 값이 원래부터 없는 칸은 True
    # s.astype("string").str.strip().eq("") → 문자로 바꾸고 앞뒤 공백을 지운 뒤 완전히 빈 문자열인지 확인
    # 둘 중 하나라도 해당하면(|  = "또는") 비어있다고 판단합니다.
    return s.isna() | s.astype("string").str.strip().eq("")


def check(condition, message):
    """condition(조건)이 참(True)이면, message 내용으로 에러를 발생시켜 프로그램을 멈춥니다.
    "문제가 있으면 즉시 알리고 멈춘다"는 규칙을 한 줄로 재사용하기 위한 도우미 함수입니다."""
    if condition:
        raise ValueError(message)


def check_allowed(df, column, allowed, label=None):
    """df(표) 안의 특정 column(컬럼)에, allowed(허용된 값 목록)에 없는 값이 섞여 있으면 에러를 냅니다."""
    # dropna() → 빈 값은 검사에서 제외 (빈 값 자체는 다른 함수에서 따로 검사하므로 여기선 생략)
    # astype(str).str.strip() → 모두 문자로 바꾸고 앞뒤 공백 제거 (실수로 " 검증완료" 처럼 들어와도 잡아내기 위함)
    # set(...) → 중복을 없앤 "실제로 등장한 값들의 목록"
    # - allowed → "실제 등장한 값" 중에서 "허용된 값"을 뺀 나머지 = 허용되지 않은 값들
    bad = set(df[column].dropna().astype(str).str.strip()) - allowed
    check(bool(bad), f"{label or column}에 허용되지 않은 값: {sorted(bad)}")


def check_no_duplicates(df, subset, label):
    """df(표)에서 subset(컬럼 조합)이 완전히 똑같은 행이 두 개 이상 있으면 에러를 냅니다.
    예: (모델, 연도) 조합이 같은 행이 두 개면, "같은 모델의 같은 해 판매량"이 중복 등록된 것이므로 문제입니다."""
    # duplicated(subset=..., keep=False) → 중복된 행 전부에 True 표시 (keep=False라 "처음 것만 봐주기" 없음)
    check(df.duplicated(subset=subset, keep=False).any(), f"{label}에 {subset} 중복이 있습니다.")


def clean_value(v):
    """엑셀/판다스에서 온 값 하나(v)를, MySQL이 알아들을 수 있는 파이썬 기본 값으로 바꿔줍니다."""
    if pd.isna(v):
        # 값이 없는 칸(NaN)은 DB에서 "값 없음"을 뜻하는 None(=NULL)으로 바꿔줍니다.
        return None
    if isinstance(v, np.generic):
        # numpy 전용 숫자 타입(예: np.int64)은 파이썬 기본 숫자로 바꿔줍니다. (DB 라이브러리 호환성 때문)
        v = v.item()
    if isinstance(v, pd.Timestamp):
        # pandas의 날짜/시간 타입은 파이썬 기본 datetime 타입으로 바꿔줍니다.
        return v.to_pydatetime()
    if isinstance(v, float) and v.is_integer():
        # 2025.0 처럼 소수점이 있지만 사실상 정수인 값은 2025(정수)로 깔끔하게 바꿔줍니다.
        return int(v)
    # 위 어디에도 해당하지 않으면 원래 값을 그대로 돌려줍니다.
    return v


def to_rows(df, columns):
    """df(표) 전체를, DB에 한꺼번에 넣기 좋은 "행(row) 튜플들의 리스트" 형태로 바꿔줍니다.
    예: [(값1, 값2, 값3), (값1, 값2, 값3), ...] 같은 모양이 됩니다."""
    # df.iterrows() → 표를 한 줄(행)씩 순서대로 꺼내옵니다.
    # columns에 적힌 순서대로 각 칸의 값을 꺼내면서 clean_value로 DB용 값으로 바꿉니다.
    return [tuple(clean_value(row[c]) for c in columns) for _, row in df.iterrows()]


def validate_model_keys(df, label, allow_null=False):
    """df(표)의 model_key 컬럼이 올바른지 검사합니다.
    allow_null=True 이면 model_key가 비어있어도 괜찮다고 봐줍니다. (D-MAP의 제외/검토중 행처럼)"""
    missing = is_blank(df["model_key"])  # 비어있는 칸 표시

    # allow_null이 아닌데(=필수인데) 비어있는 칸이 하나라도 있으면 에러
    check((not allow_null) and missing.any(), f"{label}에 model_key 결측이 있습니다.")

    # 실제로 값이 채워진 model_key들만 모아서, "우리가 지원하는 6개 모델"에 속하는지 검사
    keys = set(df.loc[~missing, "model_key"].astype(str).str.strip())
    bad = keys - EXPECTED_MODEL_KEYS  # 6개 목록에 없는 이상한 model_key가 있는지 확인
    check(bool(bad), f"{label}에 지원하지 않는 model_key: {sorted(bad)}")


# ── 5. CSV 파일 읽기 & 데이터별 세부 검증 함수들 ─────────────────────

def load_csv(name):
    """FILES 표에 등록된 이름(name)에 해당하는 CSV 파일을 읽어옵니다.
    파일이 없으면: 필수 파일이면 에러, 선택 파일(FAQ 등)이면 그냥 None(없음)을 돌려줍니다.
    파일이 있으면: 컬럼 이름과 순서가 COLUMNS 표와 정확히 같은지도 함께 검사합니다."""
    filename, required = FILES[name]     # 파일 이름과 "필수 여부"를 꺼냄
    path = PROCESSED / filename          # 실제 파일 경로 조합

    if not path.exists():
        # 파일이 실제로 존재하지 않는 경우
        check(required, f"{filename} 파일이 없습니다: {path}")
        return None  # 선택 파일이라 없어도 되는 경우엔 그냥 None 반환

    # encoding="utf-8-sig" → 엑셀에서 저장한 한글 CSV를 깨지지 않게 읽기 위한 설정
    df = pd.read_csv(path, encoding="utf-8-sig")

    # 읽어온 컬럼들이 COLUMNS 표에 정의된 "정답 컬럼 목록"과 순서까지 완전히 같은지 확인
    check(
        df.columns.tolist() != COLUMNS[name],
        f"[{name}] 컬럼 불일치\n예상: {COLUMNS[name]}\n실제: {df.columns.tolist()}",
    )
    return df


def validate_mapping(df):
    """model_mapping(D-MAP) 데이터의 규칙들을 검사합니다."""
    # match_status(검증 상태) 칸이 비어있으면 안 됨
    check(is_blank(df["match_status"]).any(), "model_mapping: match_status 결측")
    # match_status에는 '검증완료'/'검토중'/'제외' 세 가지만 허용
    check_allowed(df, "match_status", ALLOWED["match_status"])

    # source_type(이 별칭이 어느 데이터에서 왔는지) 칸이 비어있으면 안 됨
    check(is_blank(df["source_type"]).any(), "model_mapping: source_type 결측")
    # source_type에는 'SALES'/'DEFECT'/'REC' 세 가지만 허용
    check_allowed(df, "source_type", ALLOWED["source_type"])

    # alias_name(원본 데이터에 적힌 실제 모델명) 칸이 비어있으면 안 됨
    check(is_blank(df["alias_name"]).any(), "model_mapping: alias_name 결측")

    # match_status가 정확히 '검증완료'인 행들만 True로 표시
    verified = df["match_status"].astype("string").str.strip().eq("검증완료")
    # "검증완료인데 model_key가 비어있는" 모순된 행이 있으면 에러 (둘 다 True인 행이 있는지 확인)
    check((verified & is_blank(df["model_key"])).any(), "검증완료 D-MAP 중 model_key가 비어 있는 행이 있습니다.")

    # model_key 자체에 대한 공통 검사도 실행
    # ('제외'/'검토중' 행은 전처리 단계에서 model_mapping.csv에 아예 넣지 않으므로
    #  DB에 적재되는 model_mapping은 항상 model_key가 채워져 있어야 함)
    validate_model_keys(df, "model_mapping", allow_null=False)


def build_model_master(mapping_df):
    """model_mapping.csv 안에서, 표준 모델 6개의 "기준 정보"만 뽑아 별도 표로 만듭니다.
    이 표가 DB에서 model_master(모델 마스터) 테이블이 되며, 다른 테이블들이 이 표를 참조합니다."""
    valid = ~is_blank(mapping_df["model_key"])  # model_key가 실제로 채워진 행만 사용 (~ 는 "반대로 뒤집기")
    cols = ["model_key", "manufacturer_std", "model_std", "manufacturer_support_url"]

    # 필요한 4개 컬럼만 뽑고 → 완전히 똑같은 행은 하나로 합치고(drop_duplicates)
    # → 인덱스(행 번호)를 0부터 새로 매깁니다(reset_index)
    master = mapping_df.loc[valid, cols].drop_duplicates().reset_index(drop=True)

    # 4개 컬럼 각각에 대해 빈 값이 있으면 안 됨 (모델 마스터는 기준 정보라 결측이 있으면 곤란)
    for c in cols:
        check(is_blank(master[c]).any(), f"model_master: {c} 결측")

    # 같은 model_key인데 제조사명/모델명 등이 서로 다르게 적혀있으면 모순이므로 에러
    # (groupby로 model_key별 행 개수를 세서, 2개 이상 나오면 정보가 안 겹치고 갈라져 있다는 뜻)
    check((master.groupby("model_key").size() > 1).any(), "같은 model_key에 서로 다른 표준 모델정보가 있습니다.")

    # 실제로 만들어진 model_key 집합이, 우리가 정한 6개 목록과 정확히 일치하는지 확인
    keys = set(master["model_key"])
    check(keys != EXPECTED_MODEL_KEYS, f"model_master 모델이 대상 6개와 불일치: {sorted(keys)}")
    # 혹시 몰라 행 개수도 정확히 6개인지 한 번 더 확인 (이중 안전장치)
    check(len(master) != 6, f"model_master는 정확히 6행이어야 합니다. 현재 {len(master)}행")

    return master


def build_db_mapping(mapping_df):
    """model_mapping.csv를 DB에 저장할 모양으로 다듬습니다.
    표준 제조사명/모델명 등은 이제 model_master 테이블에만 저장하므로, 여기서는 제외하고
    "원본 별칭과 매핑 정보"에 해당하는 컬럼들만 남깁니다."""
    cols = [
        "model_key", "manufacturer_std", "model_std", "generation_name", "source_type",
        "alias_name", "alias_normalized", "match_status", "review_note", "manufacturer_support_url",
    ]
    db_df = mapping_df[cols].copy()  # 필요한 컬럼만 복사해서 새 표 생성

    # (source_type, alias_name) 조합이 중복되면 안 됨
    # → 같은 원본 별칭이 두 가지 다른 모델로 매핑되어 있다는 뜻이라 데이터 오류이기 때문
    check_no_duplicates(db_df, ["source_type", "alias_name"], "model_mapping")
    return db_df


def validate_registration(df):
    """registration_summary(D-REG, 전국 등록현황) 데이터를 검사합니다."""
    # (연도, 월, 집계축 종류, 집계축 값) 조합이 중복되면 같은 통계가 두 번 들어간 것이므로 에러
    check_no_duplicates(df, ["stat_year", "stat_month", "dimension_type", "dimension_value"], "registration_summary")
    # dimension_type(집계 기준)은 TOTAL/REGION/VEHICLE_TYPE/FUEL 네 가지만 허용
    check_allowed(df, "dimension_type", ALLOWED["dimension_type"])

    # registration_count(등록 대수)를 숫자로 변환해봅니다. 변환 안 되는 값(errors="coerce")은 NaN이 됩니다.
    counts = pd.to_numeric(df["registration_count"], errors="coerce")
    check(counts.isna().any(), "registration_count 숫자 변환 실패")   # 숫자가 아닌 값이 있었으면 에러
    check(counts.lt(0).any(), "registration_count에 음수가 있습니다.")  # 음수(0보다 작은 값)가 있으면 에러


def validate_sales(df):
    """vehicle_sales(D-SALES, 모델별 판매량) 데이터를 검사합니다."""
    # (모델, 연도) 조합이 중복되면 같은 모델의 같은 해 판매량이 두 번 들어간 것이므로 에러
    check_no_duplicates(df, ["model_key", "sales_year"], "vehicle_sales")

    years = pd.to_numeric(df["sales_year"], errors="coerce")   # 연도를 숫자로 변환
    check(years.isna().any(), "sales_year 숫자 변환 실패")
    # 서비스가 다루는 기간은 2020~2025년뿐이므로, 그 밖의 연도가 있으면 에러
    check((years.lt(2020) | years.gt(2025)).any(), "vehicle_sales에 2020~2025 밖의 연도가 있습니다.")

    # 판매량(domestic_sales_count)은 값이 없는(NULL) 것은 허용하지만, 음수는 절대 안 됨
    counts = pd.to_numeric(df["domestic_sales_count"], errors="coerce")
    check(counts.dropna().lt(0).any(), "domestic_sales_count에 음수가 있습니다.")

    # verification_status(검증 상태)는 '공식자료'/'교차검증'/'보완필요' 세 가지만 허용
    check_allowed(df, "verification_status", ALLOWED["verification_status"])


def validate_defects(df):
    """defect_reports(D-DEF, 제작결함 신고) 데이터를 검사합니다."""
    # report_date(접수일자)를 날짜 형식으로 변환해봅니다.
    dates = pd.to_datetime(df["report_date"], errors="coerce")
    check(dates.isna().any(), "defect_reports: report_date 변환 실패")  # 날짜로 못 바꾸는 값이 있으면 에러

    years = set(dates.dt.year)  # 실제로 등장한 연도들을 모음 (중복 없이)
    # 2023년 원본 파일은 확보하지 못했으므로, 2023년 데이터가 섞여 있으면 안 됨(0건 처리가 아니라 아예 없어야 함)
    check(2023 in years, "defect_reports에 2023 데이터가 있습니다(데이터 미확보 연도).")

    # 2020·2021·2022·2024·2025년 이외의 이상한 연도가 있으면 에러
    bad_years = years - DEFECT_ALLOWED_YEARS
    check(bool(bad_years), f"D-DEF에 허용되지 않은 연도: {sorted(bad_years)}")


def validate_recalls(df):
    """recall(D-REC, 리콜) 데이터를 검사합니다."""
    # recall_id(리콜 고유번호)가 중복되면 안 됨 (이 값이 DB에서 기본키로 쓰이기 때문)
    check(df["recall_id"].duplicated().any(), "recall_id 중복이 있습니다.")

    # recall_start_date(리콜 개시일)를 날짜로 변환
    dates = pd.to_datetime(df["recall_start_date"], errors="coerce")
    check(dates.isna().any(), "recall_start_date 변환 실패")
    # 서비스가 다루는 기간(2020~2025년) 밖의 날짜가 있으면 에러
    check(
        (dates.lt("2020-01-01") | dates.gt("2025-12-31")).any(),
        "recall_campaigns에 2020~2025 밖의 데이터가 있습니다.",
    )

    # recall_count(리콜 대상대수)에 음수가 있으면 안 됨
    counts = pd.to_numeric(df["recall_count"], errors="coerce")
    check(counts.dropna().lt(0).any(), "recall_count에 음수가 있습니다.")


def validate_faq(df):
    """faq(D-FAQ, 공통 FAQ) 데이터를 검사합니다."""
    # faq_id(FAQ 고유번호)가 중복되면 안 됨 (DB에서 기본키로 쓰이기 때문)
    check(df["faq_id"].duplicated().any(), "faq_id 중복이 있습니다.")

    # question/answer/source_url/collected_at은 화면에 그대로 노출되거나
    # 검색에 쓰이는 핵심 필드라 결측이면 안 됨
    for col in ["question", "answer", "source_url", "collected_at"]:
        check(is_blank(df[col]).any(), f"faq_master: {col} 결측")

    # collected_at이 MySQL DATETIME으로 넣을 수 있는 값인지(날짜/시각으로 변환 가능한지) 확인
    dt = pd.to_datetime(df["collected_at"], errors="coerce")
    check(dt.isna().any(), "faq_master: collected_at을 날짜/시각으로 변환할 수 없는 값이 있습니다.")


def prepare_data():
    """DB를 건드리기 전에, 모든 CSV를 미리 읽고 검사해서 "적재해도 안전한 상태"로 준비합니다.
    여기서 하나라도 실패하면, DB에는 손도 대지 않은 채로 프로그램이 멈춥니다(가장 안전한 방식)."""
    print("\n" + "=" * 70 + "\n1. processed CSV 검사\n" + "=" * 70)

    # FILES에 정의된 6개 이름 각각에 대해 load_csv를 호출해서, {이름: 표} 형태의 딕셔너리로 모음
    raw = {name: load_csv(name) for name in FILES}

    # model_mapping(D-MAP)부터 검사하고, 이를 바탕으로 model_master / DB용 mapping 표를 만듦
    validate_mapping(raw["model_mapping"])
    model_master = build_model_master(raw["model_mapping"])
    db_mapping = build_db_mapping(raw["model_mapping"])

    # 나머지 데이터들도 각각의 규칙대로 검사
    validate_registration(raw["registration_summary"])
    validate_sales(raw["vehicle_sales"])
    validate_defects(raw["defect_reports"])
    validate_recalls(raw["recall"])

    # FAQ는 선택 파일이라 없을 수 있음(FILES에서 required=False) — 있을 때만 검사
    if raw["faq"] is not None:
        validate_faq(raw["faq"])

    # 모델 데이터 3종은 model_key가 "반드시" 있어야 하므로 allow_null 없이(=기본값 False로) 검사
    validate_model_keys(raw["vehicle_sales"], "vehicle_sales")
    validate_model_keys(raw["defect_reports"], "defect_reports")
    validate_model_keys(raw["recall"], "recall_campaigns")

    # 앞으로 DB에 넣을 7개 표를 이름표를 붙여 하나의 딕셔너리로 정리
    data = {
        "model_master": model_master,
        "model_mapping": db_mapping,
        "registration_summary": raw["registration_summary"],
        "vehicle_sales": raw["vehicle_sales"],
        "defect_reports": raw["defect_reports"],
        "recall_campaigns": raw["recall"],
        "faq_master": raw["faq"],   # FAQ는 파일이 없었다면 None일 수 있음
    }

    # 검사 결과를 화면에 표 형태로 출력 (팀원이 눈으로 행 개수를 바로 확인할 수 있게)
    for name, df in data.items():
        note = "" if df is not None else " (없음, 이번 적재 제외)"
        print(f"[OK] {name:<22}: {0 if df is None else len(df):,}행{note}")

    return data


# ── 6. 실제 DB 연결 / 적재(넣기) / 검증 함수들 ───────────────────────

def connect():
    """MySQL 데이터베이스에 실제로 접속합니다.
    autocommit=False → "자동으로 확정하지 않는다"는 뜻으로, 우리가 직접 commit()을 불러줘야 저장이 확정됩니다.
    이렇게 해야 중간에 실패했을 때 rollback()으로 전부 되돌릴 수 있습니다."""
    try:
        return pymysql.connect(**DB, charset="utf8mb4", autocommit=False)
    except pymysql.err.OperationalError as e:
        # 에러 코드 1049는 "그런 이름의 데이터베이스가 아예 없다"는 뜻입니다.
        if e.args and e.args[0] == 1049:
            raise RuntimeError(
                f"MySQL에 '{DB['database']}' DB가 없습니다. db/schema.sql을 먼저 실행하세요."
            ) from e
        raise  # 그 외의 에러는 원래 에러 그대로 다시 발생시킴


def delete_existing(conn):
    """DB에 이미 들어있는 기존 데이터를 전부 지웁니다. (Full Refresh의 첫 단계)
    반드시 "자식 → 부모" 순서로 지워야 하며, 그 순서는 DELETE_ORDER에 미리 정해두었습니다."""
    print("\n" + "=" * 70 + "\n2. 기존 DB 데이터 DELETE (자식 → 부모)\n" + "=" * 70)
    with conn.cursor() as cur:   # cursor = DB에 SQL 명령을 보내는 통로
        for table in DELETE_ORDER:
            cur.execute(f"DELETE FROM `{table}`")  # 해당 테이블의 모든 행을 삭제하는 SQL 실행
            print(f"[DELETE] {table}")
    # 주의: 여기서는 아직 commit()을 하지 않습니다. (전부 끝나야 최종 확정)


def insert_all(conn, data):
    """검사를 통과한 새 데이터를 DB에 채워 넣습니다. (Full Refresh의 두 번째 단계)
    반드시 "부모 → 자식" 순서로 넣어야 하며, 그 순서는 INSERT_SPEC 딕셔너리의 등록 순서를 따릅니다."""
    print("\n" + "=" * 70 + "\n3. 신규 데이터 INSERT (부모 → 자식)\n" + "=" * 70)
    with conn.cursor() as cur:
        for table, columns in INSERT_SPEC.items():
            df = data[table]
            if df is None:
                # 예: FAQ 파일이 없었던 경우 → 그냥 건너뜀
                print(f"[SKIP] {table}: 데이터 없음")
                continue

            rows = to_rows(df, columns)  # 표를 (값1, 값2, ...) 튜플들의 리스트로 변환

            if rows:
                # 넣을 컬럼 이름들을 SQL에 쓸 수 있는 문자열로 조합 (예: `col1`, `col2`, `col3`)
                col_sql = ", ".join(f"`{c}`" for c in columns)
                # 값 개수만큼 %s(자리표시자)를 만듦 (예: %s, %s, %s)
                ph_sql = ", ".join(["%s"] * len(columns))
                # executemany → 여러 행을 한 번에 효율적으로 삽입하는 명령
                cur.executemany(f"INSERT INTO `{table}` ({col_sql}) VALUES ({ph_sql})", rows)

            print(f"[INSERT] {table}: {len(rows):,}행")


def verify_counts(conn, data):
    """DB에 실제로 들어간 행(row) 개수가, 우리가 넣으려던 개수와 정확히 같은지 확인합니다."""
    print("\n" + "=" * 70 + "\n4. DB 행 수 검증\n" + "=" * 70)
    with conn.cursor() as cur:
        for table in INSERT_SPEC:
            expected = 0 if data[table] is None else len(data[table])  # 우리가 넣으려고 했던 개수
            cur.execute(f"SELECT COUNT(*) FROM `{table}`")             # DB에 실제로 있는 개수를 조회
            actual = cur.fetchone()[0]
            print(f"{table:<22} 예상 {expected:>7,}행 | DB {actual:>7,}행")
            check(actual != expected, f"{table} 행 수 불일치")  # 다르면 뭔가 잘못 들어간 것이므로 에러
    print("\n[OK] 모든 DB 행 수 일치")


def verify_fk(conn):
    """FK(외래키) 정합성을 확인합니다.
    FK란 "이 데이터가 가리키는 model_key가, 실제로 model_master에 존재하는가"를 보장하는 장치입니다.
    즉, "존재하지도 않는 모델을 가리키는 유령 데이터"가 없는지 확인하는 단계입니다."""
    print("\n" + "=" * 70 + "\n5. model_key FK 정합성 검증\n" + "=" * 70)
    with conn.cursor() as cur:
        for table in ["model_mapping", "vehicle_sales", "defect_reports", "recall_campaigns"]:
            # 자식 테이블(c)과 model_master(m)를 model_key로 연결(LEFT JOIN)해서,
            # "c에는 model_key가 있는데 m에는 그 값이 없는" 이상한 행이 몇 개인지 셈
            cur.execute(f"""
                SELECT COUNT(*) FROM `{table}` c
                LEFT JOIN model_master m ON c.model_key = m.model_key
                WHERE c.model_key IS NOT NULL AND m.model_key IS NULL
            """)
            bad = cur.fetchone()[0]
            check(bad != 0, f"{table}에 FK 불일치 {bad}건 존재")
            print(f"[OK] {table}")


def verify_business_rules(conn):
    """데이터정의서 v2.6에서 정한 "핵심 정책"들이 실제 DB에서도 지켜지고 있는지 마지막으로 확인합니다.
    각 항목은 (설명, 실행할 SQL, "이 개수(n)면 통과다"라는 조건) 세 가지로 구성됩니다."""
    print("\n" + "=" * 70 + "\n6. v2.6 핵심 데이터 정책 검증\n" + "=" * 70)

    rules = [
        # model_master는 정확히 6개여야 함
        ("model_master = 6개", "SELECT COUNT(*) FROM model_master", lambda n: n == 6),

        # '검증완료'인데 model_key가 비어있는 행은 DB에 하나도 없어야 함
        ("D-MAP 검증완료 → model_key 존재",
         "SELECT COUNT(*) FROM model_mapping WHERE match_status='검증완료' AND model_key IS NULL",
         lambda n: n == 0),

        # 판매량 데이터는 전부 2020~2025년 범위 안에 있어야 함
        ("D-SALES = 2020~2025",
         "SELECT COUNT(*) FROM vehicle_sales WHERE sales_year<2020 OR sales_year>2025",
         lambda n: n == 0),

        # 결함신고 데이터에 2023년 데이터가 하나도 없어야 함
        ("D-DEF 2023 = 데이터 미확보",
         "SELECT COUNT(*) FROM defect_reports WHERE YEAR(report_date)=2023",
         lambda n: n == 0),

        # 리콜 데이터도 전부 2020~2025년 범위 안에 있어야 함
        ("D-REC = 2020~2025",
         "SELECT COUNT(*) FROM recall_campaigns "
         "WHERE recall_start_date<'2020-01-01' OR recall_start_date>'2025-12-31'",
         lambda n: n == 0),

        # 등록현황은 (연도,월,집계축,값) 조합이 겹치는 중복 데이터가 없어야 함
        ("D-REG 논리 중복 없음",
         """SELECT COUNT(*) FROM (
                SELECT stat_year, stat_month, dimension_type, dimension_value, COUNT(*) c
                FROM registration_summary
                GROUP BY stat_year, stat_month, dimension_type, dimension_value
                HAVING COUNT(*) > 1
            ) d""",
         lambda n: n == 0),
    ]

    with conn.cursor() as cur:
        for label, sql, ok in rules:
            cur.execute(sql)
            n = cur.fetchone()[0]              # 실행 결과(개수)를 하나 꺼냄
            check(not ok(n), f"{label} 검증 실패 (값: {n})")  # ok(n)이 False면(=조건을 못 지키면) 에러
            print(f"[OK] {label}")

        # 판매량 중 값이 비어있는(NULL) 건수는 에러는 아니지만, 참고용으로 화면에 보여줍니다.
        cur.execute("SELECT COUNT(*) FROM vehicle_sales WHERE domestic_sales_count IS NULL")
        print(f"[확인] 판매량 미확보(NULL): {cur.fetchone()[0]}건")


def run():
    """이 파일의 진짜 "시작 버튼"에 해당하는 함수입니다. 위에서 만든 함수들을 순서대로 실행합니다."""
    print("\n" + "=" * 70 + "\nMySQL Full Refresh 시작\n" + "=" * 70)

    # 1단계: DB를 건드리기 전에, CSV들을 전부 읽고 검사해서 준비 (문제 있으면 여기서 멈춤 → DB는 안전)
    data = prepare_data()

    # 2단계: DB에 접속
    conn = connect()

    try:
        # 3단계: 기존 데이터 삭제 (아직 확정 아님)
        delete_existing(conn)
        # 4단계: 새 데이터 삽입 (아직 확정 아님)
        insert_all(conn, data)
        # 5단계: 여러 각도로 최종 검증 (문제 있으면 예외가 발생해서 아래 except로 넘어감)
        verify_counts(conn, data)
        verify_fk(conn)
        verify_business_rules(conn)

        # 여기까지 전부 문제없이 왔다면, 지금까지의 삭제+삽입을 진짜로 확정합니다.
        conn.commit()
        print("\n" + "=" * 70 + "\n[COMMIT] MySQL Full Refresh 성공\n" + "=" * 70)

    except Exception as e:
        # try 블록 안 어디서든 에러(예외)가 발생하면 여기로 옵니다.
        # 지금까지의 DELETE + INSERT를 전부 취소해서, DB를 시작 전 상태로 되돌립니다.
        conn.rollback()
        print("\n" + "=" * 70 + f"\n[ROLLBACK] MySQL Full Refresh 실패\n오류 내용: {e}\n" + "=" * 70)
        raise  # 에러를 다시 던져서, 이 스크립트를 실행한 사람도 실패했다는 걸 알 수 있게 함

    finally:
        # 성공하든 실패하든 마지막에는 항상 DB 연결을 닫아줍니다. (연결을 계속 열어두면 자원 낭비)
        conn.close()


# ── 7. 이 파일을 직접 실행했을 때만 동작하는 부분 ───────────────────
# (다른 파일에서 "import load_to_mysql"로 불러오기만 할 때는 실행되지 않습니다)
if __name__ == "__main__":
    run()
