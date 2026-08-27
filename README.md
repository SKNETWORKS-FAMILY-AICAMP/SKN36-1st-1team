# 🚗 전국 자동차 등록현황 및 주요 차종 판매·안전정보 통합 조회 서비스

<p align="center">
  <b>
    전국 자동차 등록현황부터 관심 모델의 판매량, 제작결함 신고, 공식 리콜,
    FAQ까지 한 흐름으로 확인하는 자동차 정보 통합 서비스
  </b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-Data%20Processing-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-Web%20App-FF4B4B?logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/MySQL-Database-4479A1?logo=mysql&logoColor=white" />
  <img src="https://img.shields.io/badge/Playwright-Crawling-2EAD33?logo=playwright&logoColor=white" />
  <img src="https://img.shields.io/badge/Git%20%2F%20GitHub-Collaboration-181717?logo=github&logoColor=white" />
</p>

---

## 1. 프로젝트 소개

자동차 관련 정보는 판매량, 제작결함 신고, 리콜, 전국 자동차 등록현황,
자동차리콜센터 FAQ 등 여러 출처에 분산되어 있습니다.

본 프로젝트는 이러한 데이터를 하나의 서비스에서 연결하여 사용자가

> **시장 전체 현황 → 관심 모델 → 판매 흐름 → 제작결함 신고 → 공식 리콜 → FAQ**

순서로 확인할 수 있도록 구현한 **Streamlit 기반 자동차 정보 통합 조회 서비스**입니다.

---

## 2. 주요 기능

### 🔎 S01. 모델 검색

- 검증 완료된 지원 모델 목록 제공
- `selectbox` 기반 모델 선택
- 선택 모델 상세 페이지 이동
- 전국 자동차 등록현황 요약 제공

### 🚘 S02. 모델 통합 상세

- 최근 확인 판매량
- 연도별 국내 판매량 추이
- 제작결함 신고 건수 및 추이
- 모델년도별 신고 분포
- 공식 리콜 캠페인 수
- 리콜 대상대수 합계
- 리콜 사유 구성 및 상세 조회
- 두 모델의 판매량 / 제작결함 신고 / 리콜 비교
- 공식 FAQ 페이지 이동

### 📊 S03. 전국 자동차 등록현황 상세

- 전국 총 등록대수
- 지역별 등록현황
- 차종별 등록현황
- 연료별 등록현황
- 복수 기준시점 존재 시 등록대수 시계열
- 공식 데이터 출처 및 기준시점 확인

### 💬 S04. 리콜 FAQ

- 자동차리콜센터 FAQ 조회 및 검색
- 공식 FAQ 원문 연결
- 자동차리콜센터 공식 사이트 연결
- 선택 모델의 제조사 고객지원 페이지 연결

---

## 3. 지원 모델

판매량 / 제작결함 신고 / 리콜 데이터를 전처리하고 모델명을 표준화한 결과

**세 데이터에 모두 공통으로 존재하면서 실제 분석 및 비교가 가능한
검증 완료 모델 27개**를 최종 지원 대상으로 선정했습니다.

### 현대자동차 — 13개

아반떼, 쏘나타, 그랜저, 코나, 투싼, 싼타페, 팰리세이드,
아이오닉5, 아이오닉6, 캐스퍼, 그랜드 스타렉스, 스타리아, 포터

### 기아 — 14개

모닝, 레이, K3, K5, K7, K8, 니로, 셀토스, 스포티지,
쏘렌토, 카니발, EV3, EV6, 봉고3

---

## 4. 사용 데이터

| 데이터                         | 출처                                       | 역할               | 주요 기준                       |
| ------------------------------ | ------------------------------------------ | ------------------ | ------------------------------- |
| **전국 자동차 등록현황** | 국토교통부 통계누리                        | 시장 전체 Stock    | 기준 연·월                     |
| **모델별 국내 판매량**   | 현대자동차·기아 공식 판매자료 중심 검증본 | 모델 판매 Flow     | 2020~2025                       |
| **자동차 제작결함 신고** | 한국교통안전공단 / 공공데이터포털          | 소비자 Signal      | 접수일 기준                     |
| **차종별 리콜정보**      | 한국교통안전공단 / 공공데이터포털          | 공식 Action        | 리콜개시일 2020~2025            |
| **자동차리콜센터 FAQ**   | 자동차리콜센터                             | 공식 안내          | 수집일시                        |
| **모델명 매핑**          | 프로젝트팀 내부 검증                       | 원천별 차명 표준화 | `model_key`, `match_status` |

---

## 5. 데이터 해석 시 주의사항

- 전국 자동차 등록현황은 **시장 전체 집계 데이터**이며 개별 모델 등록대수는 제공하지 않습니다.
- 제작결함 신고는 소비자 신고 데이터이며 **공식 결함 판정을 의미하지 않습니다.**
- 제작결함 신고 **2023년 원천 데이터는 미확보**되어 0건으로 처리하지 않습니다.
- 판매량의 실제 `0대`와 데이터 미확보 값은 구분합니다.
- 리콜 대상대수 합계는 동일 차량이 여러 캠페인에 포함될 수 있어 **고유 차량 수와 다를 수 있습니다.**
- 판매량, 제작결함 신고, 리콜 대상대수는 모집단과 기준이 다르므로
  **결함률·리콜률·안전점수는 제공하지 않습니다.**

---

## 6. 기술 스택

| 영역               | 기술         |
| ------------------ | ------------ |
| Language           | Python       |
| Data Processing    | pandas       |
| Web App            | Streamlit    |
| Database           | MySQL        |
| DB Connection      | PyMySQL      |
| Crawling           | Playwright   |
| Package Management | uv           |
| Collaboration      | Git / GitHub |

---

## 7. 팀 구성 및 역할

| 팀원           | 주요 역할                                                                                                                                                                      |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **민지** | 데이터 수집·전처리 · 모델 매핑 데이터 구축 · MySQL 데이터 적재 및 DB 연동 · 모델 비교 기능 구현 · Streamlit 데이터 연계 및 UI 통합 · Git/GitHub 관리 · 문서 정합성 관리 |
| **홍진** | 요구사항정의서 작성 · FAQ 및 판매 데이터 크롤링 수집 · README 및 프로젝트 문서화 · 발표                                                                                    |
| **소희** | 데이터정의서 작성 · ERD 설계 · DB 테이블 생성 · SQL 조회 쿼리 작성 · Streamlit UI 디자인 고도화 및 스타일링                                                             |
| **성희** | 화면설계서 작성 · User Flow 설계 · Streamlit 화면 구조 설계 및 기본 UI 구현                                                                                                |

---

## 8. 프로젝트 구조

```text
SKN36-1st-1team/
├─ app/
│  ├─ app.py                    # Streamlit 메인 페이지
│  ├─ assets/                   # 로고 및 화면 이미지
│  ├─ lib/
│  │  ├─ common.py             # 공통 함수
│  │  └─ ui.py                 # 공통 UI 구성
│  └─ pages/
│     ├─ S01_model_search.py    # 모델 선택 및 시장 요약
│     ├─ S02_model_detail.py    # 모델 통합 상세·비교
│     ├─ S03_registration.py    # 전국 자동차 등록현황
│     └─ S04_FAQ.py             # 리콜 FAQ·공식 안내
├─ data/
│  ├─ raw/                      # 원천 데이터
│  └─ processed/                # 전처리 완료 데이터
├─ src/
│  ├─ collection/               # FAQ 데이터 수집
│  ├─ preprocessing/            # 데이터별 전처리·모델 매핑
│  ├─ validation/               # 데이터 정합성 검증
│  └─ db/
│     ├─ load_to_mysql.py       # MySQL 전체 적재
│     ├─ model_compare.py       # 두 모델 비교 조회
│     └─ query_service.py       # Streamlit DB 조회 서비스
├─ db/
│  ├─ schema.sql                # MySQL 테이블 스키마
│  ├─ erd.sql                   # ERD 정의
│  └─ queries.sql               # 주요 조회 SQL
├─ .streamlit/
│  └─ config.toml               # Streamlit 설정
├─ docker-compose.yml           # MySQL 컨테이너 설정
├─ pyproject.toml               # 프로젝트·의존성 설정
├─ uv.lock                      # 의존성 버전 잠금
└─ README.md
```

---

## 9. 실행 방법

```bash
git clone https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN36-1st-1team.git
cd SKN36-1st-1team
uv sync
```

프로젝트 루트에 `.env` 파일을 생성하고 MySQL 연결 정보를 설정합니다.

```env
DB_HOST=localhost
DB_PORT=3307
DB_USER=YOUR_DB_USER
DB_PASSWORD=YOUR_DB_PASSWORD
DB_NAME=YOUR_DB_NAME
```

Streamlit 실행:

```bash
uv run streamlit run app/app.py
```

실행 후 브라우저에서 접속:

```text
http://localhost:8501
```

---

## 10. 데이터 출처

- [국토교통부 통계누리](https://stat.molit.go.kr/portal/cate/statView.do?hRsId=58&hFormId=5498&hDivEng=&month_yn=)
- 현대자동차·기아 공식 판매자료
- [한국교통안전공단 자동차 제작결함 신고정보](https://www.data.go.kr/data/15016450/fileData.do)
- [한국교통안전공단 차종별 리콜정보](https://www.data.go.kr/data/15125831/fileData.do)
- [자동차리콜센터 FAQ](https://www.car.go.kr/rs/faq/list.do)
- [자동차리콜센터](https://www.car.go.kr/home/main.do)

---

<p align="center">
  <b>Python · pandas · MySQL · Streamlit · Playwright · Git/GitHub</b>
</p>
