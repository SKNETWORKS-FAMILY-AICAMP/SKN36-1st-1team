"""
model_mapping.py
=================
이 파일이 하는 일 (한 줄 요약):
  판매량/결함신고/리콜, 이 3가지 원본 데이터마다 자동차 이름이 제각각 적혀 있는데
  ("아반떼(CN7)", "아반떼 N", "아반떼 하이브리드" 등) 이걸 전부 우리 프로젝트 안에서
  쓰는 "하나의 이름표"(model_key, 예: HYU_AVANTE)로 통일해주는 작업입니다.

  결과물은 data/processed/model_mapping.csv 파일 하나입니다.

중요한 원칙 (실수 방지):
  글자 안에 "K5"가 들어있다고 무조건 K5로 인식하지 않습니다.
  우리가 원본 파일에서 실제로 눈으로 확인한 표기(alias)만 미리 목록으로 정해두고,
  그 목록에 정확히 있는 것만 매칭합니다. (짐작으로 연결하지 않는다는 뜻)
"""

import argparse
from pathlib import Path      # 파일/폴더 경로를 쉽게 다루는 도구
import re                     # 정규표현식 — 문자열에서 괄호·공백 등을 규칙적으로 지우거나 바꿀 때 사용
import unicodedata             # 겉보기엔 같은 글자인데 컴퓨터 내부 저장 방식이 다른 경우를 통일해주는 도구

import pandas as pd            # 표(엑셀 같은 데이터)를 다루고 CSV로 저장하는 라이브러리


# ── 1. 프로젝트 경로 ─────────────────────────────────────────────
# 이 파일 기준 2단계 위 폴더가 프로젝트 최상위 폴더입니다.
# 예: SKN36-1st-1team/src/preprocessing/model_mapping.py 라면
#     parents[2] 는 SKN36-1st-1team 폴더를 가리킵니다.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 완성된 결과 CSV를 저장할 위치
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "model_mapping.csv"


# ── 2. 서비스가 다루는 기간 (v2.5 문서 기준: 2020~2025년) ───────────
START_YEAR = 2020
END_YEAR = 2025


# ── 3. 제조사별 공식 고객지원 페이지 주소 ───────────────────────────
# S-04(FAQ) 화면에서 "선택한 모델의 제조사 고객지원으로 이동" 버튼에 씁니다.
MANUFACTURER_SUPPORT_URL = {
    "현대자동차": "https://www.hyundai.com/kr/ko/e/customer/center",
    "기아": "https://www.kia.com/kr/customer-service/center/default",
}


# ── 4. 우리 서비스가 지원하는 27개 모델 ─────────────────────────────
# model_key는 각 모델을 구분하는 프로젝트 내부 표준 키입니다.
# 원본 데이터에서 이름이 어떻게 적혀있든, 검증된 alias를 통해 아래 27개 모델 중 하나로 매핑합니다.
MODEL_MASTER = {
    # 현대자동차
    "HYU_AVANTE":        ("현대자동차", "아반떼"),
    "HYU_SONATA":        ("현대자동차", "쏘나타"),
    "HYU_GRANDEUR":      ("현대자동차", "그랜저"),
    "HYU_KONA":          ("현대자동차", "코나"),
    "HYU_TUCSON":        ("현대자동차", "투싼"),
    "HYU_SANTAFE":       ("현대자동차", "싼타페"),
    "HYU_PALISADE":      ("현대자동차", "팰리세이드"),
    "HYU_IONIQ5":        ("현대자동차", "아이오닉 5"),
    "HYU_IONIQ6":        ("현대자동차", "아이오닉 6"),
    "HYU_CASPER":        ("현대자동차", "캐스퍼"),
    "HYU_GRAND_STAREX":  ("현대자동차", "그랜드 스타렉스"),
    "HYU_STARIA":        ("현대자동차", "스타리아"),
    "HYU_PORTER":        ("현대자동차", "포터"),

    # 기아
    "KIA_MORNING":       ("기아", "모닝"),
    "KIA_RAY":           ("기아", "레이"),
    "KIA_K3":            ("기아", "K3"),
    "KIA_K5":            ("기아", "K5"),
    "KIA_K7":            ("기아", "K7"),
    "KIA_K8":            ("기아", "K8"),
    "KIA_NIRO":          ("기아", "니로"),
    "KIA_SELTOS":        ("기아", "셀토스"),
    "KIA_SPORTAGE":      ("기아", "스포티지"),
    "KIA_SORENTO":       ("기아", "쏘렌토"),
    "KIA_CARNIVAL":      ("기아", "카니발"),
    "KIA_EV3":           ("기아", "EV3"),
    "KIA_EV6":           ("기아", "EV6"),
    "KIA_BONGO3":        ("기아", "봉고 III"),
}


# ── 5. 판매량 데이터에 적힌 모델명 ───────────────────────────────
# 판매량 원본은 이미 이름이 깔끔해서, 표준 이름 그대로 한 개씩만 있으면 됩니다.
# ── 5. 판매량 데이터에 적힌 모델명 ───────────────────────────────
SALES_ALIASES = {
    # 현대자동차
    "HYU_AVANTE":       ["아반떼"],
    "HYU_SONATA":       ["쏘나타"],
    "HYU_GRANDEUR":     ["그랜저"],
    "HYU_KONA":         ["코나"],
    "HYU_TUCSON":       ["투싼"],
    "HYU_SANTAFE":      ["싼타페"],
    "HYU_PALISADE":     ["팰리세이드"],
    "HYU_IONIQ5":       ["아이오닉 5"],
    "HYU_IONIQ6":       ["아이오닉 6"],
    "HYU_CASPER":       ["캐스퍼"],
    "HYU_GRAND_STAREX": ["그랜드 스타렉스"],
    "HYU_STARIA":       ["스타리아"],
    "HYU_PORTER":       ["포터"],

    # 기아
    "KIA_MORNING":      ["모닝"],
    "KIA_RAY":          ["레이"],
    "KIA_K3":           ["K3"],
    "KIA_K5":           ["K5"],
    "KIA_K7":           ["K7"],
    "KIA_K8":           ["K8"],
    "KIA_NIRO":         ["니로"],
    "KIA_SELTOS":       ["셀토스"],
    "KIA_SPORTAGE":     ["스포티지"],
    "KIA_SORENTO":      ["쏘렌토"],
    "KIA_CARNIVAL":     ["카니발"],
    "KIA_EV3":          ["EV3"],
    "KIA_EV6":          ["EV6"],
    "KIA_BONGO3":       ["봉고 III"],
}


# ── 6. 리콜 원본에서 실제로 확인한 표기들 ─────────────────────────
# 2020~2025 리콜 원본에서 직접 확인된 alias만 사용합니다.
RECALL_ALIASES = {
    # ── 현대자동차 ──────────────────────────────────────────────
    "HYU_AVANTE": [
        "아반떼 N",
        "아반떼 N Line",
        "아반떼 N(CN7 N)",
        "아반떼 N-Line(CN7 N-Line)",
        "아반떼 하이브리드 (CN7 HEV)",
        "아반떼 하이브리드(CN7 HEV)",
        "아반떼(AD)",
        "아반떼(CN7)",
        "아반떼(HD)",
        "아반떼N (CN7 KN)",
        "아반떼N (CN7 N)",
        "아반떼N (CN7N)",
    ],

    "HYU_SONATA": [
        "쏘나타 (DN8)",
        "쏘나타 플러그인 하이브리드(LF PHEV)",
        "쏘나타 하이브리드 (LF HEV)",
        "쏘나타 하이브리드 (YF HEV)",
        "쏘나타 하이브리드(LF HEV)",
        "쏘나타 하이브리드(YFE)",
        "쏘나타(DN8)",
        "쏘나타(LF)",
        "쏘나타(YF)",
        "쏘나타N Line (DN8)",
    ],

    "HYU_GRANDEUR": [
        "그랜저 하이브리드 (GN7 HEV)",
        "그랜저 하이브리드(IG HEV)",
        "그랜저(GN7)",
        "그랜저(HG)",
        "그랜저(IG)",
        "그랜저하이브리드(GN7 HEV)",
    ],

    "HYU_KONA": [
        "코나 EV (SX2 EV)",
        "코나 Electric (OS EV)",
        "코나 전기차 (OS EV)",
        "코나(OS PE)",
        "코나(OS)",
        "코나(OS) EV",
        "코나(OS) HEV",
        "코나(SX2)",
        "코나N (OS N)",
        "코나N (OSN)",
    ],

    "HYU_TUCSON": [
        "투싼 (TL)",
        "투싼 수소연료전지(LMFC)",
        "투싼(LM)",
        "투싼(NX4)",
        "투싼(TL)",
    ],

    "HYU_SANTAFE": [
        "싼타페 (TM PE)",
        "싼타페 DM)",
        "싼타페 하이브리드 (TM PE HEV)",
        "싼타페 하이브리드(MX5 HEV)",
        "싼타페 하이브리드(TM HEV)",
        "싼타페(CM)",
        "싼타페(DM)",
        "싼타페(MX5)",
        "싼타페(TM PE)",
        "싼타페(TM)",
    ],

    "HYU_PALISADE": [
        "더 뉴 팰리세이드",
        "더 뉴 팰리세이드(LX2 PE)",
        "팰리세이드 (LX2 PE)",
        "팰리세이드 하이브리드(LX3 HEV)",
        "팰리세이드(LX2)",
        "팰리세이드(LX3)",
    ],

    "HYU_IONIQ5": [
        "아이오닉5 (NE)",
        "아이오닉5 N(NE N)",
        "아이오닉5(NE)",
        "아이오닉5(NE1 PE)",
        "아이오닉5NE",
    ],

    "HYU_IONIQ6": [
        "아이오닉6 (CE)",
        "아이오닉6(CE)",
    ],

    "HYU_CASPER": [
        "캐스퍼 일렉트릭 (AX1 EV)",
        "캐스퍼(AX1)",
    ],

    "HYU_GRAND_STAREX": [
        "그랜드 스타렉스(TQ)",
        "그랜드스타렉스(TQ)",
    ],

    "HYU_STARIA": [
        "스타리아 카고 (US4)",
        "스타리아 하이브리드 (US4 HEV)",
    ],

    "HYU_PORTER": [
        "포터2 (HR)",
        "포터2 EV(HR EV)",
        "포터2 Electric (HR EV)",
        "포터2(HR)",
        "포터II",
        "포터II EV",
        "포터II 일렉트릭(HR EV)",
        "포터II(HR)",
    ],

    # ── 기아 ───────────────────────────────────────────────────
    "KIA_MORNING": [
        "모닝 (JA PE2)",
        "모닝(JA)",
    ],

    "KIA_RAY": [
        "레이 (TAM PE2)",
        "레이 전기차(TAM EV)",
        "레이(TAM)",
        "레이(TAMPE)",
    ],

    "KIA_K3": [
        "K3 (BD PE)",
        "K3(BD)",
        "K3(YDPE)",
    ],

    "KIA_K5": [
        "K5 (DL3 PE)",
        "K5 (DL3)",
        "K5 하이브리드(TF HEV)",
        "K5(DL3)",
        "K5(TF HEV)",
        "K5(TF)",
        "K5플러그인하이브리드 (JF PHEV)",
        "K5하이브리드 (JF HEV)",
    ],

    "KIA_K7": [
        "K7(VG)",
        "K7(YG)",
    ],

    "KIA_K8": [
        "K8 (GL3)",
    ],

    "KIA_NIRO": [
        "니로 (SG2 HEV)",
        "니로 EV (SG2 EV)",
        "니로 EV(DE EV)",
        "니로 EV(SG2 EV)",
        "니로 전기차(DE EV)",
        "니로 플러그인하이브리드 (DE PHEV)",
        "니로 플러스(DE PBV)",
        "니로 하이브리드 (DE HEV)",
        "니로(DE)",
        "니로(SG2)",
        "니로EV (DE EV)",
        "니로EV(DE EV)",
        "니로EV(SG2 EV)",
    ],

    "KIA_SELTOS": [
        "셀토스 (SP2 PE)",
        "셀토스 (SP2)",
        "셀토스(SP2)",
    ],

    "KIA_SPORTAGE": [
        "스포티지 (NQ5)",
        "스포티지 (QL)",
        "스포티지 (QL/QL PE)",
        "스포티지 하이브리드 (NQ5 HEV)",
        "스포티지(KM)",
        "스포티지(NQ5)",
        "스포티지(QL)",
        "스포티지(SL)",
    ],

    "KIA_SORENTO": [
        "쏘렌토 (MQ4 PE)",
        "쏘렌토 (MQ4)",
        "쏘렌토 (UM/UM PE)",
        "쏘렌토 하이브리드(MQ4 HEV PE)",
        "쏘렌토 하이브리드(MQ4 HEV)",
        "쏘렌토(BL)",
        "쏘렌토(MQ4)",
        "쏘렌토(XM)",
        "쏘렌토R (XM 페이스리프트)",
        "쏘렌토R(XM페이스리프트)",
        "올뉴쏘렌토(UM)",
    ],

    "KIA_CARNIVAL": [
        "그랜드카니발(VQ) 승용",
        "그랜드카니발(VQ) 승합",
        "올뉴카니발(YP)",
        "카니발",
        "카니발 (KA4)",
        "카니발 (YP)",
        "카니발 하이브리드(KA4 HEV)",
        "카니발(KA4)",
        "카니발(VQ)",
        "카니발(YP)",
    ],

    "KIA_EV3": [
        "EV3",
    ],

    "KIA_EV6": [
        "EV6 (CV)",
        "EV6(CV)",
    ],

    "KIA_BONGO3": [
        "봉고 Ⅲ EV (PU EV)",
        "봉고Ⅲ (PU)",
        "봉고Ⅲ EV(PU EV)",
        "봉고Ⅲ 전기차(PUEV)",
        "봉고Ⅲ(PU)",
    ],
}


# ── 7. 결함신고 원본에서 실제로 확인한 표기들 ───────────────────────
# 현대자동차/기아 제작사 원본값 중 실제 확인된 alias만 사용합니다.
# 특장업체 제작 차량, 순찰차, 어린이보호차, 캠핑카 등은 자동 포함하지 않습니다.
DEFECT_ALIASES = {
    # ── 현대자동차 ──────────────────────────────────────────────
    "HYU_AVANTE": [
        "뉴아반떼XD(NEW AVANTE XD)",
        "아반떼 (AVANTE)",
        "아반떼 Hybrid N Line (AVANTE Hybrid N Line)",
        "아반떼 Hybrid(AVANTE Hybrid)",
        "아반떼 N (AVANTE N)",
        "아반떼 N 라인 (AVANTE N Line)",
        "아반떼 N 라인(AVANTE N Line)",
        "아반떼 N(AVANTE N)",
        "아반떼 스포츠(AVANTE SPORT)",
        "아반떼 쿠페 (AVANTE COUPE)",
        "아반떼 하이브리드(AVANTE HYBRID)",
        "아반떼(AVANTE)",
    ],

    "HYU_SONATA": [
        "쏘나타",
        "쏘나타 (SONATA)",
        "쏘나타 (SONATA) 하이브리드",
        "쏘나타 N 라인 (SONATA N Line)",
        "쏘나타 하이브리드 (SONATA HYBRID)",
        "쏘나타 하이브리드 (SONATA Hybrid)",
        "쏘나타 하이브리드(SONATA HYBRID)",
        "쏘나타(SONATA)",
        "쏘나타(SONATA) 하이브리드",
    ],

    "HYU_GRANDEUR": [
        "그랜저 하이브리드",
        "그랜저 하이브리드 (GRANDEUR HYBRID)",
        "그랜저 하이브리드(GRANDEUR HYBRID)",
        "그랜저(GRANDEUR)",
        "그랜저(GRANDEUR) 하이브리드",
        "그랜저",
    ],

    "HYU_KONA": [
        "코나 N(KONA N)",
        "코나 일렉트릭 (KONA ELECTRIC)",
        "코나 일렉트릭(KONA Electric)",
        "코나 하이브리드(KONA HYBRID)",
        "코나(KONA)",
    ],

    "HYU_TUCSON": [
        "투싼 하이브리드(TUCSON HYBRID)",
        "투싼(TUCSON)",
        "투싼(TUCSON) 수소연료전지",
        "투싼",
    ],

    "HYU_SANTAFE": [
        "싼타페",
        "싼타페 하이브리드(SANTAFE HYBRID)",
        "싼타페(SANTAFE)",
    ],

    "HYU_PALISADE": [
        "팰리세이드",
        "팰리세이드 하이브리드(PALISADE HYBRID)",
        "팰리세이드(PALISADE)",
        "팰리세이드(Palisade)",
    ],

    "HYU_IONIQ5": [
        "아이오닉5 (IONIQ5)",
        "아이오닉5 N(IONIQ5 N)",
        "아이오닉5(IONIQ5)",
    ],

    "HYU_IONIQ6": [
        "아이오닉6 (IONIQ6)",
    ],

    "HYU_CASPER": [
        "캐스퍼 일렉트릭(CASPER ELECTRIC)",
        "캐스퍼 일렉트릭(CASPER Electric)",
        "캐스퍼(CASPER)",
    ],

    "HYU_GRAND_STAREX": [
        "그랜드 스타렉스(GRAND STAREX)",
        "그랜드스타렉스(GRAND STAREX)",
    ],

    "HYU_STARIA": [
        "스타리아 (STARIA)",
        "스타리아 HYBRID (STARIA HYBRID)",
        "스타리아 라운지 (STARIA LOUNGE)",
        "스타리아 라운지 HYBRID (STARIA LOUNGE HYBRID)",
        "스타리아(US)",
    ],

    "HYU_PORTER": [
        "포터Ⅱ (PORTERⅡ)",
        "포터Ⅱ 일렉트릭 (PORTERⅡ ELECTRIC)",
        "포터Ⅱ 일렉트릭 내장탑(PORTERⅡ ELECTRIC)",
        "포터Ⅱ 일렉트릭 윙바디 (PORTERⅡ ELECTRIC)",
        "포터Ⅱ 일렉트릭 파워게이트 (PORTERⅡ ELECTRIC)",
        "포터Ⅱ(PORTERⅡ)",
        "포터Ⅱ내장탑차 (PORTER Ⅱ)",
        "포터Ⅱ냉동탑차 (PORTER Ⅱ)",
        "포터Ⅱ냉장탑차 (PORTER Ⅱ)",
        "포터Ⅱ시티밴 (PORTER Ⅱ)",
        "포터Ⅱ윙바디 (PORTER Ⅱ)",
        "포터Ⅱ저상냉동탑차 (PORTER Ⅱ)",
        "포터Ⅱ전동식윙바디 (PORTER Ⅱ)",
        "포터Ⅱ트랜스파워게이트 (PORTER Ⅱ)",
        "포터Ⅱ파워게이트 (PORTER Ⅱ)",
        "포터Ⅱ하이내장탑차 (PORTER Ⅱ)",
        "포터Ⅱ하이냉동탑차 (PORTER Ⅱ)",
        "포터",
    ],

    # ── 기아 ───────────────────────────────────────────────────
    "KIA_MORNING": [
        "모닝",
    ],

    "KIA_RAY": [
        "레이",
        "레이 EV",
        "레이 전기차",
    ],

    "KIA_K3": [
        "K3",
        "K3 쿱(K3 KOUP)",
    ],

    "KIA_K5": [
        "K5",
        "K5 하이브리드",
    ],

    "KIA_K7": [
        "K7",
        "K7 하이브리드",
    ],

    "KIA_K8": [
        "K8",
        "K8 하이브리드",
    ],

    "KIA_NIRO": [
        "니로 EV",
        "니로 PHEV",
        "니로 플러스",
        "니로 하이브리드",
    ],

    "KIA_SELTOS": [
        "셀토스",
    ],

    "KIA_SPORTAGE": [
        "스포티지",
        "스포티지 하이브리드",
    ],

    "KIA_SORENTO": [
        "쏘렌토",
        "쏘렌토 GL",
        "쏘렌토 GLS",
        "쏘렌토 하이브리드",
    ],

    "KIA_CARNIVAL": [
        "그랜드 카니발",
        "그랜드 카니발 리무진",
        "그랜드카니발",
        "그랜드카니발 리무진",
        "카니발",
        "카니발 리무진",
        "카니발 아웃도어",
        "카니발 하이리무진",
        "카니발 하이브리드",
    ],

    "KIA_EV3": [
        "EV3",
    ],

    "KIA_EV6": [
        "EV6",
        "EV6 GT",
    ],

    "KIA_BONGO3": [
        "봉고Ⅲ 1.2톤",
        "봉고Ⅲ 1.4톤",
        "봉고Ⅲ 1톤",
        "봉고Ⅲ 1톤 EV",
        "봉고Ⅲ 4륜구동",
        "봉고Ⅲ EV 내장차",
        "봉고Ⅲ EV 윙바디",
        "봉고Ⅲ EV 파워게이트",
        "봉고Ⅲ EV 플러스내장차",
        "봉고Ⅲ 고급형 내장탑차",
        "봉고Ⅲ 내장차",
        "봉고Ⅲ 냉동차",
        "봉고Ⅲ 미닫이차",
        "봉고Ⅲ 워크스루밴",
        "봉고Ⅲ 윙바디",
        "봉고Ⅲ 일반덤프",
        "봉고Ⅲ 파워게이트",
        "봉고Ⅲ 플러스 택배전용차",
        "봉고Ⅲ 플러스내장차",
        "봉고Ⅲ 플러스냉동차",
        "봉고Ⅲ 하이 택배전용차",
        "봉고Ⅲ 하이내장차",
    ],
}


# ── 8. 서비스 비교에서 제외할 특수 차명 ─────────────────────────────
# 일반 소비자용 모델이 아닌 특수목적 차량(예: 순찰차)은 6개 모델 비교에서 뺍니다.
# 완전히 삭제하지 않고 "제외"로 표시해서 남겨두는 이유: 나중에 "왜 빠졌지?"를 바로 확인하기 위해서입니다.
EXCLUDED = {
    ("DEFECT", "아반떼 avante 순찰차"): "특수용도 차량(순찰차)",
    ("REC", "스타리아 us4 어린이 통학차"): "특수용도 차량(어린이 통학차)",

    ("DEFECT", "그랜드스타렉스어린이버스 grand starex"): "특수용도 차량(어린이버스)",
    ("DEFECT", "그랜드 스타렉스 어린이보호차 grand starex"): "특수용도 차량(어린이보호차)",
    ("DEFECT", "그랜드스타렉스어린이보호차 grand starex"): "특수용도 차량(어린이보호차)",
    ("DEFECT", "유니밴알티 그랜드스타렉스"): "외부 특장업체 차량",
    ("DEFECT", "스타리아 특수구급차 staria"): "특수용도 차량(구급차)",
    ("DEFECT", "스타리아 어린이 통학차 staria"): "특수용도 차량(어린이 통학차)",
    ("DEFECT", "스타리아 어린이 통학차 staria school bus"): "특수용도 차량(어린이 통학차)",
    ("DEFECT", "스타리아 라운지 캠핑카 staria lounge"): "특수용도 차량(캠핑카)",
}


# ── 9. 제조사명을 "현대자동차" / "기아" 둘 중 하나로 통일하는 함수 ────
def normalize_manufacturer(value):
    """원본에 적힌 제조사명이 무엇이든(Hyundai, 현대, HYUNDAI MOTOR 등)
    "현대자동차" 또는 "기아" 둘 중 하나로 통일합니다. 둘 다 아니면 None(모름)을 돌려줍니다."""
    if pd.isna(value):
        return None  # 값 자체가 없는 경우

    text = str(value)
    text = unicodedata.normalize("NFKC", text)   # 같은 글자의 다른 저장방식을 통일
    text = text.strip().lower()                  # 앞뒤 공백 제거 + 영문 소문자로

    # 비교하기 쉽게, 공백/괄호/마침표를 지운 버전도 하나 더 만들어둠
    compact = re.sub(r"[\s().]", "", text)

    if "현대자동차" in text or compact in ("현대", "hyundai", "hyundaimotor"):
        return "현대자동차"

    if "기아자동차" in text or "기아주식회사" in compact or compact in ("기아", "kia", "kiamotors", "kiacorporation"):
        return "기아"

    return None  # 현대/기아가 아닌 제조사(=우리 서비스 대상 아님)


# ── 10. 차명을 "비교하기 좋은 모양"으로 다듬는 함수 ──────────────────
def normalize_alias(value):
    """표기 방식이 달라도 같은 차로 인식할 수 있게 다듬습니다.
    예) "K5 (DL3 PE)" → "k5 dl3 pe" / "아반떼(CN7)" → "아반떼 cn7"
    괄호 안의 CN7 같은 세대 정보는 지우지 않고, 괄호 기호만 공백으로 바꿉니다."""
    if pd.isna(value):
        return ""

    text = str(value)
    text = unicodedata.normalize("NFKC", text)
    text = text.strip().lower()
    text = re.sub(r"[()\[\]{}]", " ", text)   # 괄호류 → 공백
    text = re.sub(r"[-_/]", " ", text)        # -, _, / → 공백
    text = re.sub(r"[^0-9a-z가-힣\s]", " ", text)  # 숫자/영문/한글/공백 외에는 전부 공백
    text = re.sub(r"\s+", " ", text)          # 공백 여러 개 → 공백 하나
    return text.strip()


# ── 11. 세대코드(트림/모델 코드) 목록 ────────────────────────────
# 세대/프로젝트코드는 참고정보로만 저장하며
# 화면의 대표 세대명으로 단정해서 사용하지 않습니다.
PROJECT_CODES = [
    # 현대자동차
    "CN7", "AD", "HD",
    "DN8", "LF", "YF", "YFE",
    "GN7", "IG", "HG",
    "SX2", "OS", "OSN",
    "TL", "LMFC", "LM", "NX4",
    "TM", "MX5", "CM", "DM",
    "LX2", "LX3",
    "NE", "NE1",
    "CE",
    "AX1",
    "TQ",
    "US4",
    "HR",

    # 기아
    "JA",
    "TAM", "TAMPE",
    "BD", "YDPE",
    "DL3", "TF", "JF",
    "VG", "YG",
    "GL3",
    "SG2", "DE",
    "SP2",
    "NQ5", "QL", "KM", "SL",
    "MQ4", "UM", "XM", "BL",
    "VQ", "YP", "KA4",
    "CV",
    "PU", "PUEV",
]


def extract_generation_name(alias):
    """
    원본 차명 문자열에서 세대/프로젝트코드를 찾아 참고정보로 반환합니다.

    예:
    아이오닉5(NE1 PE) → NE1
    코나N(OSN) → OSN

    NE1 안에서 NE까지 중복 검출되는 것을 막기 위해
    영문/숫자 경계를 기준으로 정확히 찾습니다.
    """
    upper = str(alias).upper()

    found = []

    for code in PROJECT_CODES:
        pattern = rf"(?<![A-Z0-9]){re.escape(code)}(?![A-Z0-9])"

        if re.search(pattern, upper):
            found.append(code)

    return "/".join(dict.fromkeys(found))



# ── 12. 위의 목록들을 실제 표(CSV 행)로 변환 ─────────────────────
def build_mapping_rows():
    """SALES_ALIASES / DEFECT_ALIASES / RECALL_ALIASES에 적어둔 내용을
    CSV 한 줄 한 줄(딕셔너리 하나하나)로 풀어내는 함수입니다."""
    rows = []

    # (데이터 종류 이름, 그 종류의 별칭 목록) 세 쌍을 순서대로 처리
    sources = [
        ("SALES", SALES_ALIASES),
        ("DEFECT", DEFECT_ALIASES),
        ("REC", RECALL_ALIASES),
    ]

    for source_type, alias_dict in sources:
        for model_key, aliases in alias_dict.items():
            manufacturer_std, model_std = MODEL_MASTER[model_key]  # 표준 제조사/모델명 꺼내기
            support_url = MANUFACTURER_SUPPORT_URL[manufacturer_std]

            for alias in aliases:
                rows.append({
                    "model_key": model_key,
                    "manufacturer_std": manufacturer_std,
                    "model_std": model_std,
                    "generation_name": extract_generation_name(alias),
                    "source_type": source_type,
                    "alias_name": alias,                       # 원본 표기 그대로 보존
                    "alias_normalized": normalize_alias(alias),  # 비교용으로 다듬은 버전
                    "match_status": "검증완료",                  # 직접 확인한 목록이므로 검증완료로 표시
                    "review_note": "원천 차명 직접 대조",
                    "manufacturer_support_url": support_url,
                })
    return rows


MAPPING_ROWS = build_mapping_rows()  # 위 함수를 바로 실행해서 전체 매핑 행을 미리 만들어둠


# ── 13. 같은 alias가 서로 다른 모델로 중복 매핑되지 않았는지 확인 ────
def validate_mapping():
    """예를 들어 "쏘나타(DN8)"이라는 표기가 실수로 두 번 적히면서
    한 번은 HYU_SONATA, 한 번은 다른 모델로 연결돼 있으면 안 되므로 이를 검사합니다."""
    seen = {}  # 이미 나온 (데이터종류, 정규화된표기) → 그때의 model_key를 기억해두는 사전

    for row in MAPPING_ROWS:
        if row["match_status"] != "검증완료":
            continue  # 제외/검토중 행은 이 충돌 검사 대상이 아님

        key = (row["source_type"], row["alias_normalized"])

        if key in seen and seen[key] != row["model_key"]:
            # 같은 표기인데 이전에 저장된 model_key와 다르면 = 모순 → 에러로 즉시 알림
            raise ValueError(f"D-MAP 충돌 발생: {key}")

        seen[key] = row["model_key"]


# ── 14. (데이터종류, 표기) → 매핑행 을 바로 찾을 수 있는 사전 ─────────
# 예: LOOKUP[("REC", "아반떼 cn7")] 하면 그 행을 바로 꺼낼 수 있음 (매번 목록 전체를 뒤지지 않아도 됨)
LOOKUP = {(row["source_type"], row["alias_normalized"]): row for row in MAPPING_ROWS}


# ── 15. 실제 원본 한 줄(제조사·차명·데이터종류)을 model_key로 연결 ────
def match_model(manufacturer, model_name, source_type):
    """전처리 중인 CSV의 한 행에서 "제조사", "차명", "데이터 종류"를 넘기면,
    그 차가 우리 6개 모델 중 무엇인지 찾아서 돌려주는 함수입니다.
    (다른 전처리 스크립트에서 이 함수를 불러다 씁니다.)"""

    source_type = str(source_type).strip().upper()
    if source_type not in {"SALES", "DEFECT", "REC"}:
        raise ValueError("source_type은 SALES / DEFECT / REC만 가능합니다.")

    manufacturer_std = normalize_manufacturer(manufacturer)
    alias_normalized = normalize_alias(model_name)

    excluded_reason = EXCLUDED.get(
    (source_type, alias_normalized)
)

    if excluded_reason:
        return {
            "model_key": None,
            "manufacturer_std": manufacturer_std,
            "model_std": None,
            "match_status": "제외",
            "review_note": excluded_reason,
        }

    mapping = LOOKUP.get((source_type, alias_normalized))

    if mapping is None:
        # 우리 목록에 아예 없는 처음 보는 표기 → 사람이 검토해야 하는 상태로 표시
        return {
            "model_key": None, "manufacturer_std": manufacturer_std, "model_std": None,
            "match_status": "검토중", "review_note": "D-MAP 미등록 alias",
        }

    expected_manufacturer = mapping["manufacturer_std"]
    if manufacturer_std is not None and manufacturer_std != expected_manufacturer:
        # 표기는 우리 목록과 같은데, 원본에 적힌 제조사가 우리가 알던 것과 다르면
        # 혹시 모를 오매칭을 막기 위해 자동으로 연결하지 않고 "검토중"으로 남김
        return {
            "model_key": None, "manufacturer_std": manufacturer_std, "model_std": None,
            "match_status": "검토중", "review_note": "제조사 불일치",
        }

    # 여기까지 통과했으면 안전하게 매칭된 것으로 확정
    return {
        "model_key": mapping["model_key"],
        "manufacturer_std": expected_manufacturer,
        "model_std": mapping["model_std"],
        "match_status": "검증완료",
        "review_note": "",
    }


# ── 16. 최종 결과를 model_mapping.csv로 저장 ─────────────────────
def save_mapping_csv():
    validate_mapping()  # 저장 전에 충돌부터 확인 (문제 있으면 여기서 멈춤)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)  # data/processed 폴더가 없으면 만들어줌

    df = pd.DataFrame(MAPPING_ROWS)

    # 데이터정의서에 정의된 컬럼 순서 그대로 맞춤
    columns = [
        "model_key", "manufacturer_std", "model_std", "generation_name",
        "source_type", "alias_name", "alias_normalized",
        "match_status", "review_note", "manufacturer_support_url",
    ]
    df = df[columns]

    # 보기 좋게 정렬 (팀원이 눈으로 훑어볼 때 편하도록)
    df = df.sort_values(["source_type", "manufacturer_std", "model_std", "alias_normalized"])

    # utf-8-sig로 저장해야 엑셀에서 열었을 때 한글이 깨지지 않음
    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print("\n" + "=" * 60 + "\nD-MAP 생성 완료\n" + "=" * 60)
    print(f"저장 위치: {OUTPUT_PATH}")
    print(f"총 매핑 행 수: {len(df)}")


# ── 17. 원본 CSV 읽기 ───────────────────────────────────────────
def read_source_csv(path):
    """공공데이터 CSV의 인코딩 차이를 고려해서 읽습니다."""
    try:
        return pd.read_csv(path, encoding="cp949")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="utf-8-sig")

# ── 18. 서비스 지원 모델 후보인지 확인 ───────────────────────────
def looks_like_target_model(model_name, source_type):
    """
    원본 차명이 현재 서비스 지원 모델 계열의 후보인지 확인합니다.

    MODEL_MASTER의 표준 모델명을 기준으로 후보를 찾고,
    실제 model_key 확정은 match_model()에서 수행합니다.

    따라서 아직 D-MAP에 등록되지 않은 새 alias도
    후보로 잡혀 검증 결과에 나타날 수 있습니다.
    """
    source_type = str(source_type).strip().upper()

    if source_type not in {"DEFECT", "REC"}:
        raise ValueError(
            "looks_like_target_model()은 DEFECT / REC만 가능합니다."
        )

    name = normalize_alias(model_name)

    for _, (_, model_std) in MODEL_MASTER.items():
        keyword = normalize_alias(model_std)

        # "아이오닉 5" ↔ "아이오닉5",
        # "그랜드 스타렉스" ↔ "그랜드스타렉스",
        # "봉고 III" ↔ "봉고Ⅲ"처럼 공백 차이를 허용
        parts = keyword.split()
        body = r"\s*".join(
            re.escape(part)
            for part in parts
        )

        compact_keyword = re.sub(r"\s+", "", keyword)

        # K3/K5/K7/K8/EV3/EV6처럼 영문·숫자로만 된 모델은
        # SK3 같은 다른 차명의 일부를 잘못 잡지 않도록 양쪽 경계 검사
        if re.fullmatch(r"[a-z0-9]+", compact_keyword):
            pattern = (
                rf"(?<![a-z0-9])"
                rf"{body}"
                rf"(?![a-z0-9])"
            )

        # 한글 모델은 단어 중간에서 시작하는 경우만 차단
        # → '트레일블레이저' 속 '레이'는 제외
        # → '포터Ⅱ', '코나N' 같은 실제 파생 표기는 후보로 허용
        else:
            pattern = (
                rf"(?<![가-힣a-z0-9])"
                rf"{body}"
            )

        if re.search(pattern, name):
            return True

    return False

# ── 19. 리콜 원본 매핑 검증 ──────────────────────────────────────
def validate_recall_file(path):
    df = read_source_csv(path)

    required = {"제작자", "차명", "리콜개시일"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"리콜 CSV 필수 컬럼 누락: {sorted(missing)}"
        )

    # 날짜 변환
    df["리콜개시일"] = pd.to_datetime(
        df["리콜개시일"],
        errors="coerce",
    )

    # 서비스 분석기간 2020~2025
    df = df[
        df["리콜개시일"]
        .dt.year
        .between(2020, 2025)
    ].copy()

    # 제조사 표준화
    df["manufacturer_std"] = (
        df["제작자"]
        .apply(normalize_manufacturer)
    )

    # ★ 현대자동차 / 기아만 남김
    df = df[
        df["manufacturer_std"].isin(
            ["현대자동차", "기아"]
        )
    ].copy()

    # 현재 서비스 지원 모델 후보만 남김
    df = df[
        df["차명"].apply(
            lambda name: looks_like_target_model(name, "REC")
        )
    ].copy()

    results = []

    for _, row in df.iterrows():
        result = match_model(
            row["제작자"],
            row["차명"],
            "REC",
        )

        results.append(
            {
                "제작자": row["제작자"],
                "차명": row["차명"],
                "match_status": result["match_status"],
                "model_key": result["model_key"],
                "review_note": result["review_note"],
            }
        )

    result_df = pd.DataFrame(results)

    print("\n" + "=" * 60)
    print("D-REC 매핑 검증 (2020~2025)")
    print("=" * 60)

    print(result_df["match_status"].value_counts())

    unresolved = (
        result_df[
            result_df["match_status"] != "검증완료"
        ][["차명", "match_status", "review_note"]]
        .drop_duplicates()
    )

    if unresolved.empty:
        print("\n[OK] 미매핑 대상 alias 없음")
    else:
        print("\n[확인 필요] 미매핑/제외 alias")
        print(unresolved.to_string(index=False))


# ── 20. 결함신고 원본 매핑 검증 ──────────────────────────────────
def validate_defect_file(path):
    df = read_source_csv(path)

    required = {"접수일자", "제작사", "차명"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"결함신고 CSV 필수 컬럼 누락: {sorted(missing)}"
        )

    # 접수일자를 날짜형으로 변환
    df["접수일자"] = pd.to_datetime(
        df["접수일자"],
        errors="coerce",
    )

    # 서비스에서 사용하는 결함신고 연도만
    # 2023년은 원천 미확보이므로 제외
    df = df[
        df["접수일자"].dt.year.isin(
            [2020, 2021, 2022, 2024, 2025]
        )
    ].copy()

    # ★ 우리 대상 6개 모델 후보만 남김
    df = df[
        df["차명"].apply(
            lambda name: looks_like_target_model(name, "DEFECT")
        )
    ].copy()

    results = []

    for _, row in df.iterrows():

        result = match_model(
            row["제작사"],
            row["차명"],
            "DEFECT",
        )

        results.append(
            {
                "접수일자": row["접수일자"],
                "제작사": row["제작사"],
                "차명": row["차명"],
                "match_status": result["match_status"],
                "model_key": result["model_key"],
                "review_note": result["review_note"],
            }
        )

    return pd.DataFrame(results)


# ── 21. 이 파일을 직접 실행했을 때만 동작 ─────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--recall",
        help="차종별 리콜대수 CSV 경로",
    )

    parser.add_argument(
        "--defect",
        nargs="*",
        help="제작결함신고 CSV 경로 (여러 개 가능)",
    )

    args = parser.parse_args()

    # 기존 D-MAP 생성
    save_mapping_csv()

    # 리콜 원본 검증
    if args.recall:
        validate_recall_file(args.recall)

    # 결함신고 원본 검증
    if args.defect:
        dfs = [
            validate_defect_file(path)
            for path in args.defect
        ]

        result_df = pd.concat(
            dfs,
            ignore_index=True,
        )

        print("\n" + "=" * 60)
        print("D-DEF 매핑 검증")
        print("=" * 60)

        print(result_df["match_status"].value_counts())

        unresolved = (
            result_df[
                result_df["match_status"] != "검증완료"
            ][["차명", "match_status", "review_note"]]
            .drop_duplicates()
        )

        if unresolved.empty:
            print("\n[OK] 미매핑 대상 alias 없음")
        else:
            print("\n[확인 필요] 미매핑/제외 alias")
            print(unresolved.to_string(index=False))