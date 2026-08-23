-- ============================================================
-- schema.sql
--
-- 프로젝트: 전국 자동차 등록현황 및 주요 차종 판매·안전정보·
--          공식 FAQ 통합 조회 시스템
--
-- 기준 문서: 데이터정의서_최종본_v2_6_최종확정.xlsx > DB_물리설계 시트
--
-- 역할: MySQL 데이터베이스와 7개 물리 테이블(model_master,
--       model_mapping, vehicle_sales, defect_reports,
--       recall_campaigns, registration_summary, faq_master)을
--       생성합니다. 실제 CSV 데이터 적재는 별도 로더 스크립트에서
--       수행합니다.
--
-- 서비스 분석기간: 2020~2025 (DB_물리설계 A.전역 정책)
-- 삭제 순서: model_mapping → vehicle_sales → defect_reports
--            → recall_campaigns → model_master
-- 삽입 순서: model_master → model_mapping → vehicle_sales
--            → defect_reports → recall_campaigns
--            (registration_summary, faq_master는 FK 없어 순서 무관)
-- FK 정책: ON DELETE RESTRICT ON UPDATE RESTRICT
--          (CASCADE 미사용, FOREIGN_KEY_CHECKS=0 금지)
-- ============================================================

CREATE DATABASE IF NOT EXISTS skn36_1st_1team
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE skn36_1st_1team;


-- ============================================================
-- 1. model_master
-- 서비스 지원 6개 표준 모델 마스터 (DB 전용, CSV/화면 미노출)
-- FK의 기준(부모) 테이블
-- ============================================================
CREATE TABLE IF NOT EXISTS model_master (
    model_key                  VARCHAR(50)   NOT NULL,
    manufacturer_std           VARCHAR(50)   NOT NULL,
    model_std                  VARCHAR(100)  NOT NULL,
    manufacturer_support_url   VARCHAR(1000) NOT NULL,

    PRIMARY KEY (model_key),
    UNIQUE KEY uq_model_master_manufacturer_model (manufacturer_std, model_std)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 2. model_mapping  (D-MAP)
-- 원천별 차명(alias) → 표준 모델 매핑
-- manufacturer_std/model_std/manufacturer_support_url은
-- model_master로 정규화되어 이 테이블엔 없음(JOIN으로 조회)
--
-- model_key는 NULL 허용: match_status='검증완료'인 행은 반드시
-- 값이 있어야 하지만, '제외'/'검토중' 행은 표준 모델에 매핑되지
-- 않은 상태라 model_key가 비어있을 수 있음(load_to_mysql.py 검증
-- 로직 및 실제 데이터 기준, 실제로 1건 존재)
-- ============================================================
CREATE TABLE IF NOT EXISTS model_mapping (
    mapping_id          BIGINT       NOT NULL AUTO_INCREMENT,
    model_key           VARCHAR(50)  NULL,
    generation_name     VARCHAR(100) NULL,
    source_type         VARCHAR(20)  NOT NULL,
    alias_name          VARCHAR(255) NOT NULL,
    alias_normalized    VARCHAR(255) NOT NULL,
    match_status        VARCHAR(20)  NOT NULL,
    review_note         VARCHAR(500) NULL,

    PRIMARY KEY (mapping_id),
    UNIQUE KEY uq_model_mapping_source_alias (source_type, alias_name),
    KEY idx_model_mapping_alias (source_type, alias_normalized, match_status),
    KEY idx_model_mapping_model (model_key),

    CONSTRAINT fk_model_mapping_model
        FOREIGN KEY (model_key) REFERENCES model_master (model_key)
        ON DELETE RESTRICT ON UPDATE RESTRICT,

    CONSTRAINT chk_model_mapping_source_type
        CHECK (source_type IN ('SALES', 'DEFECT', 'REC')),

    CONSTRAINT chk_model_mapping_match_status
        CHECK (match_status IN ('검증완료', '검토중', '제외'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 3. vehicle_sales  (D-SALES)
-- 모델별 연간 국내 판매량. 서비스 분석기간 2020~2025만 적재
-- ============================================================
CREATE TABLE IF NOT EXISTS vehicle_sales (
    model_key               VARCHAR(50)        NOT NULL,
    sales_year               SMALLINT UNSIGNED NOT NULL,
    manufacturer             VARCHAR(50)        NOT NULL,
    model_original           VARCHAR(255)       NOT NULL,
    domestic_sales_count     BIGINT UNSIGNED    NULL,
    verification_status      VARCHAR(20)        NOT NULL,
    source_url               VARCHAR(1000)      NOT NULL,
    loaded_at                DATE               NOT NULL,

    PRIMARY KEY (model_key, sales_year),
    KEY idx_vehicle_sales_model_status_year (model_key, verification_status, sales_year),

    CONSTRAINT fk_vehicle_sales_model
        FOREIGN KEY (model_key) REFERENCES model_master (model_key)
        ON DELETE RESTRICT ON UPDATE RESTRICT,

    CONSTRAINT chk_vehicle_sales_year
        CHECK (sales_year BETWEEN 2020 AND 2025),

    CONSTRAINT chk_vehicle_sales_verification_status
        CHECK (verification_status IN ('공식자료', '교차검증', '보완필요'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 4. defect_reports  (D-DEF)
-- 제작결함 신고 원천 레코드
-- 같은 모델·같은 날 복수 신고가 정상 데이터라 자연키 UNIQUE 불가
-- ============================================================
CREATE TABLE IF NOT EXISTS defect_reports (
    defect_report_id   BIGINT             NOT NULL AUTO_INCREMENT,
    report_date         DATE               NOT NULL,
    manufacturer        VARCHAR(50)        NULL,
    model_original      VARCHAR(255)       NOT NULL,
    model_year          SMALLINT UNSIGNED  NULL,
    model_key           VARCHAR(50)        NOT NULL,
    source_url          VARCHAR(1000)      NOT NULL,
    loaded_at           DATE               NOT NULL,

    PRIMARY KEY (defect_report_id),
    KEY idx_defect_model_date (model_key, report_date),
    KEY idx_defect_model_year (model_key, model_year),

    CONSTRAINT fk_defect_reports_model
        FOREIGN KEY (model_key) REFERENCES model_master (model_key)
        ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 5. recall_campaigns  (D-REC)
-- 모델별 리콜 캠페인 (차량 1대가 아니라 캠페인 1건)
-- recall_count는 캠페인 대상대수 합계이며 고유 차량수 아님
-- recall_category는 리콜사유_분류기준 시트의 RC01~RC09에 대응
-- (별도 참조 테이블 없이 값으로만 보관 — DB_물리설계 기준)
-- ============================================================
CREATE TABLE IF NOT EXISTS recall_campaigns (
    recall_id            VARCHAR(50)      NOT NULL,
    manufacturer         VARCHAR(50)      NOT NULL,
    model_original       VARCHAR(255)     NOT NULL,
    model_key            VARCHAR(50)      NOT NULL,
    production_from      DATE             NULL,
    production_to        DATE             NULL,
    recall_start_date    DATE             NOT NULL,
    recall_count         BIGINT UNSIGNED  NULL,
    recall_reason        TEXT             NULL,
    recall_category      VARCHAR(50)      NOT NULL,
    source_url           VARCHAR(1000)    NOT NULL,
    official_check_url   VARCHAR(1000)    NOT NULL,
    loaded_at            DATE             NOT NULL,

    PRIMARY KEY (recall_id),
    KEY idx_recall_model_date (model_key, recall_start_date),
    KEY idx_recall_model_category (model_key, recall_category),

    CONSTRAINT fk_recall_campaigns_model
        FOREIGN KEY (model_key) REFERENCES model_master (model_key)
        ON DELETE RESTRICT ON UPDATE RESTRICT,

    CONSTRAINT chk_recall_category
        CHECK (recall_category IN (
            '제동장치', '조향장치', '엔진·동력장치', '전기·전자장치',
            '연료장치', '탑승자보호', '차체·구조', '등화장치', '기타'
        ))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 6. registration_summary  (D-REG)
-- 전국 등록현황 집계. 다른 모델 단위 데이터와 직접 JOIN하지 않음
-- (FK 없음, model_key 미보유)
-- 중복 방지는 DB UNIQUE로 하지 않고 전처리/로더 단계에서 검사
-- (stat_month가 NULL 가능하여 MySQL UNIQUE로는 완전히 못 막음)
-- ============================================================
CREATE TABLE IF NOT EXISTS registration_summary (
    registration_id      BIGINT             NOT NULL AUTO_INCREMENT,
    stat_year             SMALLINT UNSIGNED  NOT NULL,
    stat_month            TINYINT UNSIGNED   NULL,
    dimension_type        VARCHAR(30)        NOT NULL,
    dimension_value       VARCHAR(100)       NOT NULL,
    registration_count    BIGINT UNSIGNED    NOT NULL,
    source_url            VARCHAR(1000)      NOT NULL,
    loaded_at             DATE               NOT NULL,

    PRIMARY KEY (registration_id),
    KEY idx_registration_snapshot_dimension (stat_year, stat_month, dimension_type),

    CONSTRAINT chk_registration_dimension_type
        CHECK (dimension_type IN ('TOTAL', 'REGION', 'VEHICLE_TYPE', 'FUEL')),
    CONSTRAINT chk_registration_stat_month
        CHECK (stat_month IS NULL OR (stat_month BETWEEN 1 AND 12))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- 7. faq_master  (D-FAQ)
-- 자동차리콜센터 공통 FAQ
-- model_master/manufacturer로 FK 연결 금지(공통 FAQ이므로)
-- FAQ만 collected_at이 시각까지 포함(다른 테이블 loaded_at은 DATE)
-- ============================================================
CREATE TABLE IF NOT EXISTS faq_master (
    faq_id          VARCHAR(50)   NOT NULL,
    provider        VARCHAR(50)   NOT NULL,
    category        VARCHAR(50)   NULL,
    question        TEXT          NOT NULL,
    answer          TEXT          NOT NULL,
    source_url      VARCHAR(1000) NOT NULL,
    collected_at    DATETIME      NOT NULL,

    PRIMARY KEY (faq_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
