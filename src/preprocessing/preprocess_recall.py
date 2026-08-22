"""
preprocess_recall.py
=====================
이 파일이 하는 일 (한 줄 요약):
  한국교통안전공단의 "차종별 리콜대수" 누적 CSV에서, 우리 서비스 6개 모델 +
  리콜개시일 2020~2025년 것만 뽑아서 최종 D-REC 파일(data/processed/recall.csv)을 만듭니다.

지켜야 하는 핵심 규칙 (v2.5 문서 기준):
  - D-MAP에서 source_type='REC' 이면서 match_status='검증완료'인 것만 사용
  - 원본 차명/생산기간/개시일/리콜대수/리콜사유는 그대로 보존 (임의로 요약·수정 안 함)
  - recall_category는 사람이 원문을 직접 읽고 확인한 사유만 사용 (키워드로 자동 분류 안 함)
  - source_url(원본 CSV 출처)과 official_check_url(사용자용 재확인 버튼)의 역할을 분리
  - 리콜대수 합계는 "고유 차량 수"가 아님 (같은 차가 여러 캠페인에 겹쳐서 들어갈 수 있음)
  - 판매량/등록대수로 나눈 "리콜률" 같은 지표는 절대 만들지 않음
"""

from datetime import datetime   # 전처리한 날짜를 loaded_at에 기록하기 위한 도구
import hashlib                  # 문자열로부터 "지문"(고유한 짧은 코드)을 만드는 도구
from pathlib import Path        # 파일/폴더 경로를 다루는 도구
import re                       # 문자열에서 괄호·공백 등을 규칙적으로 지우거나 바꾸는 도구
import unicodedata              # 겉보기엔 같은 글자인데 컴퓨터 내부 저장 방식이 다른 경우를 통일하는 도구

import pandas as pd             # CSV 읽기·필터링·정렬·저장을 담당하는 라이브러리


# ── 1. 프로젝트 폴더 위치 ─────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "recall"          # 리콜 원본 CSV를 넣는 폴더
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"          # 전처리 결과가 저장되는 폴더
MODEL_MAPPING_PATH = PROCESSED_DIR / "model_mapping.csv"     # 이전 단계(D-MAP)가 만든 파일
OUTPUT_PATH = PROCESSED_DIR / "recall.csv"                    # 이 스크립트가 최종적으로 만들 파일


# ── 2. 서비스가 다루는 기간 ────────────────────────────────────────
# 리콜은 "생산연도"가 아니라 반드시 "리콜개시일" 기준 2020~2025년만 사용합니다.
START_DATE = pd.Timestamp("2020-01-01")
END_DATE = pd.Timestamp("2025-12-31")


# ── 3. 공식 URL 두 가지 (역할이 다름) ───────────────────────────────
SOURCE_URL = "https://www.data.go.kr/data/15125831/fileData.do"        # 우리가 쓴 리콜 CSV 자체의 출처
OFFICIAL_CHECK_URL = "https://www.car.go.kr/home/main.do"                # "자동차리콜센터에서 공식 확인" 버튼용 주소


# ── 4. 원본 CSV에 꼭 있어야 하는 컬럼들 ─────────────────────────────
REQUIRED_COLUMNS = {"제작자", "차명", "생산기간(부터)", "생산기간(까지)", "리콜개시일", "리콜대수", "리콜사유"}


# ── 5. 문서에서 허용한 recall_category 목록 ─────────────────────────
# 데이터정의서의 '리콜사유_분류기준' 시트와 동일합니다.
ALLOWED_RECALL_CATEGORIES = {
    "제동장치", "조향장치", "엔진·동력장치", "전기·전자장치",
    "연료장치", "탑승자보호", "차체·구조", "등화장치", "기타",
}


# ── 6. 차명을 "비교하기 좋은 모양"으로 다듬는 함수 ──────────────────
def normalize_alias(value):
    """D-MAP의 alias_normalized와 비교할 수 있게 원본 차명을 정리합니다.
    예) "K5 (DL3 PE)" → "k5 dl3 pe" / "아반떼(CN7)" → "아반떼 cn7"
    ★ 주의: 이 함수 결과만 보고 "이건 아반떼다/K5다"라고 자동으로 확정하지 않습니다.
    실제 model_key는 D-MAP의 검증완료 REC 별칭과 정확히 일치할 때만 부여됩니다."""
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.strip().lower()
    text = re.sub(r"[()\[\]{}]", " ", text)   # 괄호류 → 공백 (괄호 안 CN7 같은 정보는 지우지 않음)
    text = re.sub(r"[-_/]", " ", text)        # -, _, / → 공백
    text = re.sub(r"[^0-9a-z가-힣\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── 7. 리콜사유 비교용 정규화 함수 ──────────────────────────────────
def normalize_reason_text(value):
    """recall_reason 원문 자체는 절대 수정하지 않고 그대로 저장합니다.
    다만 "분류 작업(=해시 계산)을 할 때만" 줄바꿈이나 연속 공백 때문에
    똑같은 사유가 다른 문자열처럼 보이는 걸 막기 위해 공백만 정리해서 비교합니다."""
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKC", str(value)).strip()
    return re.sub(r"\s+", " ", text)


# ── 8. "우리 6개 모델처럼 보이는지" 1차로 걸러내는 함수 ───────────────
def looks_like_target_model(model_name):
    """이 함수는 model_key를 정하지 않습니다. 그냥 "D-MAP에 새로 등록해야 할지도 모르는
    우리 대상 모델 후보"를 놓치지 않고 찾아내기 위한 1차 필터일 뿐입니다."""
    name = normalize_alias(model_name)

    if any(keyword in name for keyword in ["아반떼", "쏘나타", "그랜저", "스포티지", "쏘렌토"]):
        return True

    # K5는 단순히 "k5 in name"으로 검사하면 SLK55, AK550 같은 전혀 다른 차량도 걸릴 수 있어서,
    # 문자열이 정확히 "k5"로 시작할 때만("k5" 뒤에 공백이 오거나 문자열이 끝날 때만) 인정합니다.
    return re.match(r"^k5(?:\s|$)", name) is not None


# ── 9. 사람이 직접 원문을 확인해서 분류해둔 리콜사유 목록 ─────────────
# 이번 원본 기준 대상 리콜 캠페인 88건 중 서로 다른 리콜사유는 48개입니다.
# 데이터정의서는 "키워드만으로 자동 확정하지 않고 문맥을 확인"하도록 정해두었으므로,
# 48개 원문을 실제로 읽고 사람이 직접 분류를 확정했습니다.
#
# 원문 48개를 코드에 그대로 적으면 너무 길어지므로, 원문의 SHA-256 "지문"만 저장해둡니다.
#   공식 리콜사유 원문 → SHA-256 계산 → "9f6c6f..." → "연료장치"
# 이 방식의 핵심: 글자가 하나라도 다른 새로운 사유가 들어오면 지문(해시)이 완전히 달라지므로
# 절대 자동으로 분류되지 않고, 아래 get_recall_category()에서 에러를 내며 멈춥니다.
# → 사람이 새 사유를 직접 읽고 이 목록에 추가해줘야만 다음 실행이 통과됩니다.
REVIEWED_REASON_CATEGORY = {
    # 형식: "원문 리콜사유의 SHA-256 해시": "분류",  # 그 사유의 실제 내용(사람이 원문을 읽고 남긴 요약)
    "9f6c6feb09b539749fa313c46e0d0a48cab3488194c9438c0b56664f4b81cfb0": "연료장치",  # 연료펌프 제어유닛 PCB 제조불량
    "c2f09025c7fa88d81ae6802d8e8397928189a5a7a71d200b3b475ca33201dc3d": "제동장치",  # ABS/ESC 모듈 전원부 합선
    "9d45cb5dc5e008a4632121471b156277d6fba9bb26ef666fee561dcad1437cde": "전기·전자장치",  # 원격 스마트 주차 보조 제어로직
    "e3a9e426521905ca5e2f674c298741349b32947a83cc7d1c175be880f55526f8": "전기·전자장치",  # 원격 스마트 주차 보조 제어로직 - 원문 표현 차이
    "cbf153ce36d2eb34617dee0e2fd714d1a6a200a11d4cc38a1fb3b8b6423d849b": "탑승자보호",  # 운전석 에어백 인플레이터
    "cae8d9db73c177ab7b95cb30aaf17f808bba374ff2186f373c278c223b067664": "제동장치",  # ESC 오류로 간헐적 제동 불가
    "ede845ddce94c43bb1274e2805005faf88f5cd47b993885eff63f230961bafaa": "연료장치",  # 연료공급호스 클램프 체결불량
    "ed1700963cb795a3de6185d567d5e94cf7602016ee6bbff76ef343e4cb7030e0": "제동장치",  # HECU 회로기판 합선
    "6922a8efef1b75c7deb337b47e74447aa18c7ec6e272c5e29c2f156ede7a99c2": "등화장치",  # 방향지시등 오인식
    "3305e3d9d67a3c0d4f03f1f49acbab0fe9d67f25b6d5c6aa479549322abc183e": "기타",  # 시동꺼짐/화재 가능성은 있으나 / 원문만으로 특정 장치를 단정할 수 없음
    "573ed7fca041a603f6c6a86e3b79ede7406038a86b19da9f97eb68081e77f78b": "엔진·동력장치",  # KSDS 오류 / 엔진 내부 손상
    "38b9c5fe57e7ee8f7c304dbc5e811f5064c972cef224700be52cd58693851c14": "전기·전자장치",  # PTC 히터 커넥터 과열
    "0c35df7907d8e9ffc90a57f3593e56027c56fc0c90852f5fb4f8713031dae062": "연료장치",  # 연료공급호스 체결력 부족
    "21f397f80ce51f4c35e0ac6d0b51c0f6896cff3fba2b83bc966c79bb23c8da61": "탑승자보호",  # 앞좌석 안전띠 조절장치
    "830e792579d93e8d79546ad3b1aa085d9d0199e6c234a39d7a20712eb56d1b02": "탑승자보호",  # 앞좌석 안전띠 조절장치 - 원문 표현 차이
    "b9738e467b30d4ce589a2883cc0f59c3c2625db0f1a1a0633745809a7f695987": "제동장치",  # 브레이크 진공펌프
    "363fa03419fe200b719baf6625ad80688da0ed1df119fe04d0e57d6b79a62d10": "연료장치",  # 연료필터 / 고압펌프
    "c9ee4659254dce948675f39c6c0f26cebea98d46be4bf00d2d574a61ecd3c323": "탑승자보호",  # 안전띠 프리텐셔너
    "5afed06892f6e55bf100d7c0147dfc413021d684b32939e4feeb36ab9fd9de37": "엔진·동력장치",  # 변속레버 잠금장치
    "5413766641be27941a807a1d4d340d88b57c717c1001b444c8e7f680b3d76bd9": "탑승자보호",  # 에어백 전개 시 조향핸들 엠블럼 이탈
    "bc3f035fe66bbd4c5ab402dcb407750a6c7ad70c26ab5cea6703e42148a3e951": "전기·전자장치",  # 좌석 하부 전기배선 손상
    "5f9993bf440ba6c4cb8e450ea0dc94e7bf0746fb0f2ca662485fc4ad0baaab6c": "전기·전자장치",  # PTC 커넥터 전기배선
    "a55d128ed229e56485dc203a14bf5c6b3a30deafb22accb9ee2c5f0e7bbe435d": "엔진·동력장치",  # TCU / 변속기 오일펌프
    "e6eedaf2dd4347196a3d1c7a0555b26aeefee77612c4dd81c0df75d29c560dac": "엔진·동력장치",  # TCU / 전동식 오일펌프
    "ff180d36ffb85fe388169943bbfaf97c2f4ab0c5d33eda2ec87f522127367f8f": "제동장치",  # HECU 합선
    "0a77e339c5625cb352485a35dabc2454f4c583f375c0a271a24231d7731233fc": "제동장치",  # HECU 재리콜 / 합선
    "8f601183a074b94fbb9d228426a481c523cf3996783dd42eada0596623a1ef46": "조향장치",  # MDPS 제어기 소프트웨어
    "2719ccd01fbec118f8bff1f39315d1b795e3a25d1ee882e5f7dc8bc1a78e76db": "제동장치",  # 통합형 전자식 브레이크 IEB
    "536db4f6965570e386f86d3896d08c33cb411bdaf9a0164ff015beb7252ce1e4": "전기·전자장치",  # 계기판 부팅 소프트웨어
    "b00cc3da52b6199e3322b595ce1e1f2c8702604c607e39321fb305f229fe17f9": "탑승자보호",  # 안전띠 프리텐셔너
    "7cb6dc3ad02927120772d87a509da7828acb3de1a39ce8794e34da21611878be": "등화장치",  # 방향지시등 미점등
    "5a32d9c87486488516e6152968d7125031d8461896775f4099f782ed02cc815e": "엔진·동력장치",  # 변속기 EOP 내부 단락
    "44fc4e52fd84ea5057b0480b4ea3d80041550b7a44315e2325dd5fd0ba725d1d": "엔진·동력장치",  # 변속기 EOP 제어기 단락
    "27b84719115ed3235242810e8270e4759165be2d35c94cb6dbf434962a5bd181": "엔진·동력장치",  # 하이브리드 구동모터 제어
    "cbf1a904ee88f29b3d801478b21c958bbe47b79912fb2f7f70c7005fd1173e99": "등화장치",  # 전조등 상향등 고정
    "4f460b1807d08f2d8b9e1f81d5a88bf1f5f7a3519488e80a67950cb03b0a2e3f": "전기·전자장치",  # 계기판 주행거리 표시 오류
    "7e557a4c9245d18d10768b8b7d1cbb1e697b8c84ea5b81ef7fb6e374e706bff0": "엔진·동력장치",  # EGR 밸브 단락 / 시동꺼짐
    "ed091ce6d0db35acb16d69e594a1c72fbd94493a65930929b4c5b701d389d468": "엔진·동력장치",  # EGR 밸브 제조불량
    "df773d445b08e9a7ba12e23534a084e45e5f78f99e19e1610ac7e504bc8d99f0": "제동장치",  # HECU 합선 / 엔진룸 소손
    "fbb5de74c68bc45af1005c23553d8a1176e276b8a4508a5480eeeb237e1fd7b1": "제동장치",  # HECU 밀폐성 저하 / 합선
    "39b93f1000f02399e0ddfb31a1ca8095e4938ee87bb98ca21c9ae898b9d75334": "탑승자보호",  # 에어백제어장치 ACU
    "fc2b84d10ff4761c04cf0f5c0f9e7c6f7809a01f40c77e073d5b646158d7e138": "탑승자보호",  # 에어백제어장치 ACU - 현대 원문
    "060dc4157126600b70ee40156c976d7d6f324b45ee02523e94a9f228a3d3bf11": "연료장치",  # 고압 연료펌프
    "cf270b5495e2a55b6f5b572b40ed4346d4581630c4577ce5960e5a5c5d9fea96": "등화장치",  # 전조등 / 주간주행등
    "178032761cba25cda74203d595d06394ab76936d2df8edb885f09686986c8cfa": "등화장치",  # 바디도메인 제어장치 오류로 전조등 꺼짐
    "22c4dda38109a0b2f496eccbf36664dfe136b1dc6ae44db757cae35ac0011f84": "연료장치",  # 고압 파이프 연료 누유
    "5d1e4eed729127f95a08dd646d445701ff7f829ea7e39ec0051f618a27f00615": "탑승자보호",  # 운전석 에어백 인플레이터
    "9bbcc06c6d2838bdd85c26543d39d24948c53d6dce9c2ea355a60e7b9fed32fc": "연료장치",  # 연료필터 재시정 / 고압펌프 손상
}


# ── 10. 리콜사유 원문으로 recall_category를 찾는 함수 ────────────────
def get_recall_category(recall_reason):
    """이 사유가 우리가 이미 검토한 사유인지 확인합니다.
    목록에 없는 새 사유가 나오면, 임의로 '기타'를 넣지 않고 즉시 에러를 내서 멈춥니다."""
    normalized = normalize_reason_text(recall_reason)
    reason_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    category = REVIEWED_REASON_CATEGORY.get(reason_hash)
    if category is None:
        raise ValueError(
            "수동 검토되지 않은 새로운 리콜사유가 있습니다.\n"
            "원문을 확인한 뒤 REVIEWED_REASON_CATEGORY에 추가해야 합니다.\n\n"
            f"신규 사유:\n{recall_reason}"
        )
    if category not in ALLOWED_RECALL_CATEGORIES:
        raise ValueError(f"허용되지 않은 recall_category: {category}")
    return category


# ── 11. D-MAP(model_mapping.csv)에서 리콜용 별칭만 불러오기 ──────────
def load_recall_mapping():
    """model_mapping.csv에서 source_type='REC'인 리콜 별칭만 가져옵니다."""
    if not MODEL_MAPPING_PATH.exists():
        raise FileNotFoundError(
            "model_mapping.csv가 없습니다.\n먼저 아래 명령을 실행하세요.\n\n"
            "uv run python src/preprocessing/model_mapping.py"
        )

    df = pd.read_csv(MODEL_MAPPING_PATH, encoding="utf-8-sig")

    required = {"model_key", "manufacturer_std", "source_type", "alias_name", "alias_normalized", "match_status"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"model_mapping.csv 필수 컬럼 누락: {sorted(missing)}")

    df = df[df["source_type"] == "REC"].copy()
    if df.empty:
        raise ValueError("D-MAP에 source_type='REC' 데이터가 없습니다.")

    # model_mapping.py가 만든 alias_normalized 값과, 지금 이 파일의 normalize_alias() 결과가
    # 서로 다르면 두 스크립트의 정규화 규칙이 어긋난 것이므로 미리 잡아냅니다.
    df["_check"] = df["alias_name"].apply(normalize_alias)
    mismatch = df[df["alias_normalized"].fillna("") != df["_check"]]
    if not mismatch.empty:
        raise ValueError(
            "D-MAP의 alias_normalized와 현재 정규화 규칙이 다릅니다.\nmodel_mapping.py를 다시 실행해주세요."
        )
    return df


# ── 12. (정규화된 차명) → D-MAP 행을 바로 찾는 사전 만들기 ────────────
def build_mapping_lookup(mapping_df):
    """차명을 매번 표 전체에서 찾지 않고, alias_normalized 하나로 D-MAP 정보를 바로 꺼낼 수 있게 합니다."""
    lookup = {}
    for _, row in mapping_df.iterrows():
        alias = str(row["alias_normalized"]).strip()

        if alias in lookup:
            previous = lookup[alias]
            # 같은 차명(alias)인데 이전에 저장된 model_key/match_status와 다르면 모순이므로 에러
            if str(previous["model_key"]) != str(row["model_key"]) or \
               str(previous["match_status"]) != str(row["match_status"]):
                raise ValueError(f"D-MAP REC alias 충돌: {row['alias_name']}")

        lookup[alias] = row.to_dict()
    return lookup


# ── 13. 원본 리콜 CSV 파일 찾기 ─────────────────────────────────────
def find_input_file():
    """data/raw/recall 폴더 안에서 CSV를 찾습니다.
    리콜 파일은 계속 누적되는 파일이라, 여러 개를 동시에 넣으면 같은 리콜이 중복 집계될 위험이 있어서
    폴더 안에 정확히 1개만 있을 때만 허용합니다."""
    if not RAW_DIR.exists():
        raise FileNotFoundError(f"리콜 원본 폴더가 없습니다:\n{RAW_DIR}")

    files = sorted(RAW_DIR.glob("*.csv"))
    if len(files) == 0:
        raise FileNotFoundError("data/raw/recall 폴더에 리콜 CSV가 없습니다.")
    if len(files) > 1:
        raise RuntimeError("data/raw/recall에는 누적 리콜 CSV를 1개만 두세요.")
    return files[0]


# ── 14. 날짜 컬럼을 실제 날짜형으로 변환 ────────────────────────────
def parse_date_column(series, column_name, required):
    """required=True면 반드시 날짜가 있어야 하고(예: 리콜개시일),
    required=False면 원본에 값이 없을 수도 있습니다(예: 생산기간은 선택 항목)."""
    cleaned = series.astype("string").str.strip().replace("", pd.NA)
    parsed = pd.to_datetime(cleaned, errors="coerce")  # 변환 안 되는 값은 NaT(빈 날짜)로 처리

    # 값은 있었는데 날짜로 못 바꾼 경우 = 형식이 이상한 값이 섞여있다는 뜻이므로 에러
    invalid = cleaned.notna() & parsed.isna()
    if invalid.any():
        bad_values = cleaned[invalid].drop_duplicates().tolist()
        raise ValueError(f"{column_name} 날짜 변환 실패: {bad_values[:10]}")

    if required and parsed.isna().any():
        raise ValueError(f"필수 날짜 {column_name}에 결측이 있습니다.")
    return parsed


# ── 15. "리콜대수" 문자열을 깔끔한 숫자로 변환 ───────────────────────
def parse_recall_count(series):
    """★ 중요: 리콜대수가 비어 있다고 해서 0대로 바꾸지 않습니다. 원본이 비어 있으면
    <NA>(빈 값)로 그대로 유지합니다. ("안 팔렸다"와 "모른다"가 다른 것과 같은 이치입니다.)"""
    cleaned = (
        series.astype("string")
        .str.replace(",", "", regex=False)   # "10,000" 같은 값의 쉼표 제거
        .str.strip()
        .replace("", pd.NA)
    )
    numeric = pd.to_numeric(cleaned, errors="coerce")

    invalid = cleaned.notna() & numeric.isna()
    if invalid.any():
        bad_values = cleaned[invalid].drop_duplicates().tolist()
        raise ValueError(f"리콜대수 숫자 변환 실패: {bad_values[:10]}")

    # 차량 대수는 정수여야 함 (15200.5대 같은 값은 있을 수 없음)
    non_integer = numeric.notna() & (numeric != numeric.round())
    if non_integer.any():
        raise ValueError("정수가 아닌 리콜대수가 있습니다.")

    if numeric.dropna().lt(0).any():
        raise ValueError("음수 리콜대수가 있습니다.")

    # 보통의 정수(int) 타입은 빈 값(NA)을 담을 수 없지만, pandas의 "Int64"(대문자 I)는
    # 15200 이나 <NA> 를 함께 담을 수 있어서 이 타입으로 저장합니다.
    return numeric.astype("Int64")


# ── 16. 서비스 내부용 recall_id(리콜 고유번호) 만들기 ────────────────
def make_recall_id(row):
    """원본 CSV에는 캠페인 고유번호가 따로 없습니다. 그렇다고 REC-000001, REC-000002처럼
    그냥 순서대로 번호를 매기면, 나중에 원본이 갱신돼서 행 순서가 바뀌면 같은 캠페인인데도
    번호가 달라지는 문제가 생깁니다.
    그래서 제작사·차명·생산기간·개시일·대수·사유를 전부 합쳐 "지문"(SHA-256)을 만들고,
    그 앞 16자리만 사용합니다. → 같은 내용이면 언제 다시 실행해도 항상 같은 recall_id가 나옵니다."""

    def fmt_date(v):
        return "" if pd.isna(v) else v.strftime("%Y-%m-%d")

    parts = [
        row["manufacturer"],
        row["model_original"],
        fmt_date(row["production_from"]),
        fmt_date(row["production_to"]),
        row["recall_start_date"].strftime("%Y-%m-%d"),
        "" if pd.isna(row["recall_count"]) else str(int(row["recall_count"])),
        row["recall_reason"],
    ]
    raw_key = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16].upper()
    return f"REC-{digest}"


# ── 17. 리콜 원본 CSV를 실제로 전처리하는 핵심 함수 ───────────────────
def preprocess_recall(input_path, mapping_lookup, loaded_at):
    """누적 리콜 CSV 전체를, 우리 6개 모델의 2020~2025년 D-REC로 만듭니다."""

    raw_df = pd.read_csv(input_path, encoding="cp949")  # 실제 업로드된 CSV는 cp949(한글 윈도우) 인코딩

    missing = REQUIRED_COLUMNS - set(raw_df.columns)
    if missing:
        raise ValueError(f"리콜 원본 필수 컬럼 누락: {sorted(missing)}")

    # 문서에 정의된 7개 원본 컬럼만 사용
    df = raw_df[["제작자", "차명", "생산기간(부터)", "생산기간(까지)", "리콜개시일", "리콜대수", "리콜사유"]].copy()

    # 날짜 변환 (생산기간은 선택값이라 결측 허용, 리콜개시일은 필수)
    df["production_from"] = parse_date_column(df["생산기간(부터)"], "생산기간(부터)", required=False)
    df["production_to"] = parse_date_column(df["생산기간(까지)"], "생산기간(까지)", required=False)
    df["recall_start_date"] = parse_date_column(df["리콜개시일"], "리콜개시일", required=True)

    df["recall_count"] = parse_recall_count(df["리콜대수"])

    # 리콜개시일 2020~2025년만 남김
    df = df[df["recall_start_date"].between(START_DATE, END_DATE, inclusive="both")].copy()

    # 우리 6개 모델 후보로 보이는 행만 1차로 추림
    candidate_df = df[df["차명"].apply(looks_like_target_model)].copy()
    candidate_df["_alias_normalized"] = candidate_df["차명"].apply(normalize_alias)

    # 대상 모델처럼 보이는데 D-MAP에 아예 없는 새 차명이 있으면, 조용히 버리지 않고 바로 알림
    unmapped = (
        candidate_df[~candidate_df["_alias_normalized"].isin(mapping_lookup.keys())]["차명"]
        .dropna().drop_duplicates().tolist()
    )
    if unmapped:
        raise ValueError(
            "대상 모델처럼 보이지만 D-MAP에 없는 REC alias가 있습니다.\n\n"
            + "\n".join(f"- {name}" for name in unmapped)
        )

    # D-MAP에 실제로 등록된 alias만 남기고, model_key/match_status/표준 제조사명을 붙임
    mapped_df = candidate_df[candidate_df["_alias_normalized"].isin(mapping_lookup.keys())].copy()

    def mapping_value(alias, column):
        return mapping_lookup[alias].get(column)

    mapped_df["_match_status"] = mapped_df["_alias_normalized"].apply(lambda a: mapping_value(a, "match_status"))
    mapped_df["model_key"] = mapped_df["_alias_normalized"].apply(lambda a: mapping_value(a, "model_key"))
    mapped_df["_manufacturer_std"] = mapped_df["_alias_normalized"].apply(lambda a: mapping_value(a, "manufacturer_std"))

    # 검증완료인 매핑만 실제 서비스에 사용
    verified_df = mapped_df[mapped_df["_match_status"] == "검증완료"].copy()

    # 원본 값들을 그대로 보존
    verified_df["manufacturer"] = verified_df["제작자"].astype("string").str.strip()
    verified_df["model_original"] = verified_df["차명"].astype("string").str.strip()
    verified_df["recall_reason"] = verified_df["리콜사유"].astype("string").str.strip()

    # 원본에 적힌 제작사와, D-MAP이 알고 있는 표준 제작사가 다르면 모순이므로 에러
    maker_mismatch = verified_df[verified_df["manufacturer"] != verified_df["_manufacturer_std"]]
    if not maker_mismatch.empty:
        raise ValueError("원본 제작자와 D-MAP 표준 제작사가 충돌합니다.")

    for column in ["manufacturer", "model_original", "recall_reason"]:
        if verified_df[column].isna().any():
            raise ValueError(f"필수값 {column}에 결측이 있습니다.")

    # 생산 시작일이 종료일보다 늦으면 안 됨 (둘 다 있는 경우에만 비교)
    bad_period = verified_df[
        verified_df["production_from"].notna() & verified_df["production_to"].notna()
        & (verified_df["production_from"] > verified_df["production_to"])
    ]
    if not bad_period.empty:
        raise ValueError("생산기간 시작일이 종료일보다 늦은 행이 있습니다.")

    verified_df["recall_category"] = verified_df["recall_reason"].apply(get_recall_category)
    verified_df["recall_id"] = verified_df.apply(make_recall_id, axis=1)
    verified_df["source_url"] = SOURCE_URL
    verified_df["official_check_url"] = OFFICIAL_CHECK_URL
    verified_df["loaded_at"] = loaded_at

    # 데이터정의서에 정의된 컬럼 순서로 정리
    result = verified_df[[
        "recall_id", "manufacturer", "model_original", "model_key",
        "production_from", "production_to", "recall_start_date", "recall_count",
        "recall_reason", "recall_category", "source_url", "official_check_url", "loaded_at",
    ]].copy()

    # 날짜 컬럼들을 "YYYY-MM-DD" 문자열로 저장 (CSV에 저장하기 좋은 형태)
    for column in ["production_from", "production_to", "recall_start_date"]:
        result[column] = result[column].dt.strftime("%Y-%m-%d")

    return raw_df, candidate_df, result


# ── 18. 완성된 D-REC 표가 규칙을 잘 지켰는지 최종 점검 ────────────────
def validate_result(raw_df, candidate_df, result):
    """필수값·중복·날짜범위·음수·분류값 등을 검사하고, 참고용 요약도 함께 보여줍니다."""
    print("\n" + "=" * 70 + "\nD-REC 정합성 검사\n" + "=" * 70)
    print(f"원본 전체 행 수              : {len(raw_df):,}")
    print(f"2020~2025 대상모델 후보 행 수: {len(candidate_df):,}")
    print(f"최종 D-REC 행 수             : {len(result):,}")

    # 지금 검증해둔 원본(2025-12-31 누적본) 기준으로는 정확히 88건이어야 합니다.
    # (나중에 공식 파일이 새로 갱신되면 이 숫자도 다시 확인해서 바꿔야 합니다.)
    EXPECTED_CURRENT_ROWS = 88
    if len(result) != EXPECTED_CURRENT_ROWS:
        raise ValueError(f"현재 검증 원본 기준 D-REC는 {EXPECTED_CURRENT_ROWS}건입니다. 실제는 {len(result)}건입니다.")

    required_output = [
        "recall_id", "manufacturer", "model_original", "model_key", "recall_start_date",
        "recall_reason", "recall_category", "source_url", "official_check_url", "loaded_at",
    ]
    for column in required_output:
        if result[column].isna().any():
            raise ValueError(f"필수 컬럼 {column}에 결측이 있습니다.")

    if result["recall_id"].duplicated().any():
        raise ValueError("중복 recall_id가 있습니다.")

    recall_dates = pd.to_datetime(result["recall_start_date"])
    if not recall_dates.between(START_DATE, END_DATE, inclusive="both").all():
        raise ValueError("2020~2025 밖의 리콜이 포함되어 있습니다.")

    recall_counts = pd.to_numeric(result["recall_count"], errors="coerce")
    if recall_counts.dropna().lt(0).any():
        raise ValueError("음수 recall_count가 있습니다.")

    actual_categories = set(result["recall_category"].dropna().unique().tolist())
    invalid_categories = actual_categories - ALLOWED_RECALL_CATEGORIES
    if invalid_categories:
        raise ValueError(f"허용되지 않은 recall_category: {sorted(invalid_categories)}")

    # 아래는 에러가 아니라 참고용 요약 출력입니다. (S-02 화면에서 쓸 값들을 미리 확인하는 용도)
    model_summary = result.groupby("model_key").agg(
        campaign_count=("recall_id", "count"),        # M09: 리콜 캠페인 수
        recall_target_sum=("recall_count", "sum"),      # M10: 리콜 대상대수 합계
        latest_recall_date=("recall_start_date", "max"),  # M15 등에 쓸 최근 리콜일
    ).sort_index()
    print("\n모델별 리콜 요약\n" + "-" * 70)
    print(model_summary.to_string())

    category_summary = result["recall_category"].value_counts()  # S-02 M11/M12 검증용
    print("\n사유별 캠페인 수\n" + "-" * 70)
    print(category_summary.to_string())

    print()
    print(f"production_from 결측: {result['production_from'].isna().sum():,}")
    print(f"production_to 결측  : {result['production_to'].isna().sum():,}")
    print(f"recall_count 결측   : {result['recall_count'].isna().sum():,}")

    print(
        "\n※ recall_count 합계는 캠페인별 대상대수 합계이며 고유 차량 수가 아닙니다."
        "\n※ 같은 차량이 여러 캠페인에 중복 포함될 수 있습니다."
        "\n※ 판매량·등록대수와 나눈 리콜률은 계산하지 않습니다."
    )
    print("\n[OK] D-REC 정합성 검사 통과")


# ── 19. 전체 흐름 실행 ─────────────────────────────────────────────
def run():
    """1) 원본 CSV 찾기 → 2) D-MAP 읽기 → 3) 리콜 전처리 → 4) 정합성 검사 → 5) recall.csv 저장"""
    print("\n" + "=" * 70 + "\nD-REC 리콜 전처리 시작\n" + "=" * 70)

    input_path = find_input_file()
    print(f"원본 파일: {input_path}")

    loaded_at = datetime.now().astimezone().date().isoformat()

    mapping_df = load_recall_mapping()
    mapping_lookup = build_mapping_lookup(mapping_df)

    raw_df, candidate_df, result = preprocess_recall(input_path, mapping_lookup, loaded_at)

    validate_result(raw_df, candidate_df, result)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 70 + "\nD-REC 리콜 전처리 완료\n" + "=" * 70)
    print(f"저장 위치: {OUTPUT_PATH}")
    print(f"저장 행 수: {len(result):,}")


# ── 20. 이 파일을 직접 실행했을 때만 동작 ─────────────────────────
if __name__ == "__main__":
    run()
