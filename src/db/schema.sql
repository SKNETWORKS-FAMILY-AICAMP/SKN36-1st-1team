-- ============================================================
-- schema.sql
-- ============================================================
-- 이 파일이 하는 일 (한 줄 요약):
--   프로젝트에서 쓸 MySQL 데이터베이스와, 그 안에 필요한 표(테이블) 7개를 만듭니다.
--
-- ★ 이 파일은 "빈 표 틀"만 만듭니다. 표 안에 실제 데이터를 채워 넣는 건
--   다음 단계인 load_to_mysql.py가 담당합니다. (지금은 뼈대만 세우는 단계)
--
-- 기준 문서: 데이터정의서 v2.6 > DB_물리설계 시트 / 요구사항정의서 v2.6 > NFR-2.6, NFR-5.3
--
-- 전체 구조를 그림으로 보면:
--
--                    model_master (표준 모델 6개, 모든 것의 "부모" 테이블)
--                          │
--        ┌─────────────┬──┴──────────────┬───────────────┐
--        ▼             ▼                  ▼               ▼
--   model_mapping  vehicle_sales   defect_reports   recall_campaigns
--   (별칭 매핑)      (판매량)        (결함신고)         (리콜)
--
--   registration_summary(등록현황)와 faq_master(FAQ)는 위 구조와 무관하게 독립적으로 존재합니다.
--   (특정 모델 하나에 속한 데이터가 아니라서 model_master를 참조하지 않습니다.)
-- ============================================================


-- ── 1. 데이터베이스 생성 ────────────────────────────────────────
-- utf8mb4: 한글은 물론 이모지·특수문자까지 안전하게 저장할 수 있는 문자셋입니다.
-- utf8mb4_unicode_ci: 문자열을 비교하거나 정렬할 때 쓰는 규칙(collation)입니다.
CREATE DATABASE IF NOT EXISTS skn36_1st_1team
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- 지금부터 나오는 모든 CREATE TABLE은 위에서 만든 이 데이터베이스 안에 만들어집니다.
USE skn36_1st_1team;


-- ── 2. model_master : 표준 모델 6개 (DB 전용, 모든 것의 "부모") ─────
-- 왜 이 표가 필요한가?
--   model_mapping 표에는 같은 model_key(예: HYU_AVANTE)가 "아반떼", "아반떼(AD)", "아반떼(CN7)"처럼
--   여러 줄에 걸쳐 반복해서 나옵니다. 그래서 model_mapping.model_key 자체는 "유일한 값"이 아니라서,
--   다른 표들이 여기에 기대서(외래키로) 연결할 수가 없습니다.
--   그래서 표준 모델 6개만 딱 한 줄씩 뽑아 별도 표로 만든 게 이 model_master입니다.
--   ※ CSV 파일에는 존재하지 않고, 오직 DB 안에서만 쓰이는 표입니다.
CREATE TABLE IF NOT EXISTS model_master (
    model_key                 VARCHAR(50)   NOT NULL,   -- 프로젝트 표준 모델키 (예: HYU_AVANTE). 이 표의 대표값(PK)
    manufacturer_std          VARCHAR(50)   NOT NULL,   -- 표준 제조사명 (현대자동차 / 기아)
    model_std                 VARCHAR(100)  NOT NULL,   -- 화면에 보여줄 표준 모델명 (아반떼 / K5 등)
    manufacturer_support_url  VARCHAR(1000) NOT NULL,   -- 제조사 공식 고객지원 페이지 주소

    PRIMARY KEY (model_key),  -- model_key가 이 표에서 한 모델을 유일하게 가리키는 값

    -- 같은 제조사에 같은 표준 모델이 실수로 두 번 등록되는 걸 막는 안전장치
    -- (예: "현대자동차+아반떼" 조합이 두 줄로 중복되면 여기서 바로 막힘)
    UNIQUE KEY uk_model_master_manufacturer_model (manufacturer_std, model_std)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


-- ── 3. model_mapping : D-MAP, 원천 차명 ↔ 표준 모델 매핑표 ─────────
-- 표준 제조사명/모델명/고객지원URL은 이제 model_master에만 두고, 여기서는 중복 저장하지 않습니다.
-- 필요하면 model_key로 model_master와 JOIN해서 가져옵니다.
CREATE TABLE IF NOT EXISTS model_mapping (
    mapping_id        BIGINT       NOT NULL AUTO_INCREMENT,  -- DB 전용 일련번호. CSV에도 화면에도 없음
    model_key         VARCHAR(50)  NOT NULL,                  -- model_master를 가리키는 연결고리(FK)
    generation_name   VARCHAR(100) NULL,                       -- 세대/프로젝트 코드 참고정보 (예: CN7). 없을 수도 있음
    source_type       VARCHAR(20)  NOT NULL,                  -- 이 별칭이 어느 데이터에서 왔는지: SALES/DEFECT/REC
    alias_name        VARCHAR(255) NOT NULL,                  -- 원천 데이터에 실제로 적혀있던 차명
    alias_normalized  VARCHAR(255) NOT NULL,                  -- 검색·비교하기 좋게 다듬은 이름
    match_status      VARCHAR(20)  NOT NULL,                  -- 검증완료 / 검토중 / 제외
    review_note       VARCHAR(500) NULL,                       -- 매핑 근거나 주의사항 메모

    PRIMARY KEY (mapping_id),

    -- 같은 데이터 종류(source_type) 안에서, 같은 원천 차명(alias_name)이
    -- 두 개의 서로 다른 모델로 매핑되는 걸 막습니다. (예: "REC + 아반떼(CN7)" 조합은 딱 하나여야 함)
    UNIQUE KEY uk_model_mapping_source_alias (source_type, alias_name),

    -- model_master와 연결. ON DELETE/UPDATE RESTRICT = "이 표에 아직 데이터가 남아있는데
    -- 부모(model_master)를 함부로 지우거나 model_key를 바꾸려 하면 DB가 막아준다"는 안전장치입니다.
    CONSTRAINT fk_model_mapping_model
        FOREIGN KEY (model_key) REFERENCES model_master (model_key)
        ON DELETE RESTRICT ON UPDATE RESTRICT
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

CREATE INDEX idx_model_mapping_alias ON model_mapping (source_type, alias_normalized, match_status);  -- 검색·매칭 보조용
CREATE INDEX idx_model_mapping_model ON model_mapping (model_key);                                     -- 특정 모델의 별칭 목록 조회용


-- ── 4. registration_summary : D-REG, 전국 등록현황 ─────────────────
-- 이 표는 특정 모델 하나에 속한 데이터가 아니라 "시장 전체" 통계라서 model_master와 연결하지 않습니다.
-- ★ 일부러 UNIQUE 제약을 안 걸었습니다. 이유: stat_month가 비어있을(NULL) 수 있는데, MySQL은 UNIQUE에서
--   NULL끼리는 "서로 다른 값"으로 취급해버려서 NULL이 낀 중복 행은 DB가 못 걸러냅니다.
--   그래서 이 중복 검사는 다음 단계(load_to_mysql.py)에서 직접 처리합니다.
CREATE TABLE IF NOT EXISTS registration_summary (
    registration_id     BIGINT             NOT NULL AUTO_INCREMENT,  -- DB 전용 일련번호
    stat_year            SMALLINT UNSIGNED  NOT NULL,                  -- 통계 기준 연도
    stat_month           TINYINT UNSIGNED   NULL,                       -- 통계 기준 월 (연간 자료는 비어있을 수 있음)
    dimension_type        VARCHAR(30)        NOT NULL,                  -- 집계 기준: TOTAL/REGION/VEHICLE_TYPE/FUEL
    dimension_value       VARCHAR(100)       NOT NULL,                  -- 그 기준의 실제 값 (전국, 서울, 승용, 휘발유 등)
    registration_count    BIGINT UNSIGNED    NOT NULL,                  -- 등록 차량 대수
    source_url            VARCHAR(1000)      NOT NULL,                  -- 공식 출처 URL
    loaded_at             DATE               NOT NULL,                  -- 데이터를 적재한 날짜

    PRIMARY KEY (registration_id)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

-- S-01/S-03 화면에서 "특정 기준시점 + 집계축" 조합으로 조회할 때 빠르게 찾기 위한 인덱스
CREATE INDEX idx_registration_snapshot_dimension ON registration_summary (stat_year, stat_month, dimension_type);


-- ── 5. vehicle_sales : D-SALES, 모델별 연간 국내 판매량 ─────────────
-- 한 모델의 한 연도치 판매량은 딱 한 줄만 있어야 하므로, (model_key, sales_year) 조합을 PK로 씁니다.
-- (이 조합 자체가 이미 "중복 방지" 역할까지 해줘서 별도 UNIQUE는 필요 없습니다.)
CREATE TABLE IF NOT EXISTS vehicle_sales (
    model_key              VARCHAR(50)       NOT NULL,  -- model_master를 가리키는 연결고리(FK)
    sales_year              SMALLINT UNSIGNED NOT NULL,  -- 판매 연도 (DB에는 서비스 기간인 2020~2025만 저장)
    manufacturer             VARCHAR(50)       NOT NULL,  -- 판매량 원본에 적힌 제조사
    model_original           VARCHAR(255)      NOT NULL,  -- 판매량 원본에 적힌 모델명
    domestic_sales_count     BIGINT UNSIGNED   NULL,       -- 국내 판매량. 미확보는 0이 아니라 빈 값(NULL)
    verification_status      VARCHAR(20)       NOT NULL,  -- 공식자료 / 교차검증 / 보완필요
    source_url               VARCHAR(1000)     NOT NULL,  -- 근거 URL
    loaded_at                 DATE              NOT NULL,  -- 적재일

    PRIMARY KEY (model_key, sales_year),  -- "모델 + 연도" 조합이 이 표의 대표값

    CONSTRAINT fk_vehicle_sales_model
        FOREIGN KEY (model_key) REFERENCES model_master (model_key)
        ON DELETE RESTRICT ON UPDATE RESTRICT
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

-- "이 모델의 최근 확인 판매량(M04)을 찾아줘" (model_key로 필터 + verification_status로 필터 + 최신 연도순 정렬)
-- 같은 조회 패턴을 빠르게 만들어주는 인덱스
CREATE INDEX idx_vehicle_sales_model_status_year ON vehicle_sales (model_key, verification_status, sales_year);


-- ── 6. defect_reports : D-DEF, 제작결함 신고 ────────────────────────
-- 원본에는 신고 하나하나를 구분해줄 고유번호가 없습니다. 그래서 DB 전용 일련번호(AUTO_INCREMENT)를 PK로 씁니다.
-- ★ 자연스러운 조합(날짜+모델+모델년도)으로 UNIQUE를 걸지 않습니다. 같은 날 같은 모델로 서로 다른 신고가
--   여러 건 들어오는 건 정상적인 상황이라서, 그런 정상 데이터를 UNIQUE가 막아버리면 안 되기 때문입니다.
CREATE TABLE IF NOT EXISTS defect_reports (
    defect_report_id  BIGINT            NOT NULL AUTO_INCREMENT,  -- DB 전용 일련번호
    report_date         DATE              NOT NULL,                  -- 신고 접수일
    manufacturer          VARCHAR(50)       NULL,                       -- 원본 제작사 (원천에 빈 값이 있어서 허용)
    model_original         VARCHAR(255)      NOT NULL,                  -- 원본 차명
    model_year              SMALLINT UNSIGNED NULL,                       -- 차량 모델년도 (원천에 빈 값이 있어서 허용)
    model_key                VARCHAR(50)       NOT NULL,                  -- model_master를 가리키는 연결고리(FK)
    source_url                VARCHAR(1000)     NOT NULL,                  -- 공식 출처 URL
    loaded_at                  DATE              NOT NULL,                  -- 적재일

    PRIMARY KEY (defect_report_id),

    CONSTRAINT fk_defect_reports_model
        FOREIGN KEY (model_key) REFERENCES model_master (model_key)
        ON DELETE RESTRICT ON UPDATE RESTRICT
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

CREATE INDEX idx_defect_model_date ON defect_reports (model_key, report_date);  -- 접수연도 추이(M07) 조회용
CREATE INDEX idx_defect_model_year ON defect_reports (model_key, model_year);    -- 모델년도 분포(M08) 조회용


-- ── 7. recall_campaigns : D-REC, 리콜 캠페인 ────────────────────────
-- 테이블명을 그냥 "recall"이 아니라 "recall_campaigns"로 정한 이유:
--   이 표의 한 줄은 "차량 한 대"가 아니라 "리콜 캠페인 한 건"을 의미하기 때문입니다.
--   recall_count도 마찬가지로 "고유 차량 수"가 아니라 "그 캠페인의 대상 대수"입니다.
CREATE TABLE IF NOT EXISTS recall_campaigns (
    recall_id            VARCHAR(50)       NOT NULL,  -- 서비스 내부 리콜 고유키 (이 표의 대표값)
    manufacturer           VARCHAR(50)       NOT NULL,  -- 제작사
    model_original           VARCHAR(255)      NOT NULL,  -- 원본 차명
    model_key                 VARCHAR(50)       NOT NULL,  -- model_master를 가리키는 연결고리(FK)
    production_from            DATE              NULL,       -- 대상 차량 생산 시작일 (없을 수 있음)
    production_to               DATE              NULL,       -- 대상 차량 생산 종료일 (없을 수 있음)
    recall_start_date            DATE              NOT NULL,  -- 리콜 개시일
    recall_count                  BIGINT UNSIGNED   NULL,       -- 캠페인 대상대수 (※ 고유 차량 수 아님)
    recall_reason                  TEXT              NOT NULL,  -- 공식 리콜 사유 원문
    recall_category                 VARCHAR(50)       NOT NULL,  -- 사람이 원문을 확인해 정한 표준 사유분류
    source_url                       VARCHAR(1000)     NOT NULL,  -- 데이터 원천 URL
    official_check_url                VARCHAR(1000)     NOT NULL,  -- 사용자가 공식 재확인할 때 이동할 URL
    loaded_at                          DATE              NOT NULL,  -- 적재일

    PRIMARY KEY (recall_id),

    CONSTRAINT fk_recall_campaigns_model
        FOREIGN KEY (model_key) REFERENCES model_master (model_key)
        ON DELETE RESTRICT ON UPDATE RESTRICT
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

CREATE INDEX idx_recall_model_date ON recall_campaigns (model_key, recall_start_date);   -- 최신 리콜 조회(M09)용
CREATE INDEX idx_recall_model_category ON recall_campaigns (model_key, recall_category);  -- 리콜 사유 구성(M12)용


-- ── 8. faq_master : D-FAQ, 자동차리콜센터 공통 FAQ ───────────────────
-- 특정 모델이나 제조사 전용 FAQ가 아니라 "공통" FAQ이므로 model_master와 연결하지 않습니다.
CREATE TABLE IF NOT EXISTS faq_master (
    faq_id         VARCHAR(50)   NOT NULL,  -- 프로젝트 내부 FAQ 고유키 (이 표의 대표값)
    provider        VARCHAR(50)   NOT NULL,  -- 제공기관 (현재는 자동차리콜센터로 고정)
    category         VARCHAR(50)   NULL,       -- FAQ 내부 분류 (있을 수도, 없을 수도 있음)
    question          TEXT          NOT NULL,  -- 공식 질문 원문
    answer             TEXT          NOT NULL,  -- 공식 답변 원문
    source_url          VARCHAR(1000) NOT NULL,  -- 공식 FAQ URL
    collected_at          DATETIME      NOT NULL,  -- FAQ 수집 시각 (다른 표는 날짜만 쓰지만, FAQ는 시각까지 기록)

    PRIMARY KEY (faq_id)
)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;

-- ※ MVP 단계에서는 faq_master에 검색용 인덱스를 추가로 만들지 않습니다.
--   question 컬럼을 "...검색어..." 식으로 뒤지는 검색은 일반 인덱스로는 속도 개선 효과가 크지 않기 때문입니다.
--   FAQ 데이터가 나중에 크게 늘어나면, 그때 FULLTEXT 인덱스 도입을 검토합니다.

-- ============================================================
-- 여기까지가 테이블 7개 생성 끝입니다.
-- 다음 단계: load_to_mysql.py로 실제 데이터를 채워 넣으세요.
-- ============================================================