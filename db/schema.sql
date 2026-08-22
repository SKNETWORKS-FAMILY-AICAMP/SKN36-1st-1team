-- ============================================================
-- schema.sql
--
-- 프로젝트:
-- 전국 자동차 등록현황 및 주요 차종 판매·안전정보·
-- 공식 FAQ 통합 조회 시스템
--
-- 기준 문서:
-- 데이터정의서 v2.6 > DB_물리설계
-- 요구사항정의서 v2.6 > NFR-2.6 / NFR-5.3
--
-- 역할:
-- 프로젝트에서 사용할 MySQL 데이터베이스와
-- 7개의 물리 테이블을 생성합니다.
--
-- 주의:
-- 이 파일은 "테이블 구조"만 만듭니다.
-- 실제 CSV 데이터 적재는 다음 단계의
-- load_to_mysql.py에서 수행합니다.
-- ============================================================



-- ============================================================
-- 1. 데이터베이스 생성
-- ============================================================

-- DB_물리설계에서 전역 문자셋을 utf8mb4로 정했습니다.
--
-- utf8mb4:
-- 한글뿐 아니라 특수문자/이모지까지 안전하게 저장합니다.
--
-- utf8mb4_unicode_ci:
-- 문자열 비교/정렬에 사용할 collation입니다.
CREATE DATABASE IF NOT EXISTS skn36_1st_1team
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;


-- 지금부터 실행하는 CREATE TABLE 명령은
-- 이 데이터베이스 안에서 실행합니다.
USE skn36_1st_1team;



-- ============================================================
-- 2. model_master
-- ============================================================
--
-- DB 전용 표준 모델 마스터입니다.
--
-- 왜 필요한가?
--
-- model_mapping에서는 같은 model_key가
-- 여러 alias마다 반복됩니다.
--
-- 예:
--
-- HYU_AVANTE | 아반떼
-- HYU_AVANTE | 아반떼(AD)
-- HYU_AVANTE | 아반떼(CN7)
--
-- 따라서 model_mapping.model_key 자체는 UNIQUE하지 않아서
-- 다른 테이블의 FK 부모가 될 수 없습니다.
--
-- 그래서 표준 6개 모델만 따로 model_master에 둡니다.
--
-- CSV에는 존재하지 않는 DB 전용 테이블입니다.
-- ============================================================

CREATE TABLE IF NOT EXISTS model_master (

    -- --------------------------------------------------------
    -- 프로젝트 표준 모델키
    --
    -- 예:
    -- HYU_AVANTE
    -- KIA_K5
    --
    -- 이 테이블의 PK이며
    -- 다른 모델 단위 테이블 FK의 기준이 됩니다.
    -- --------------------------------------------------------
    model_key VARCHAR(50) NOT NULL,


    -- --------------------------------------------------------
    -- 표준 제조사명
    --
    -- 현대자동차 / 기아
    -- --------------------------------------------------------
    manufacturer_std VARCHAR(50) NOT NULL,


    -- --------------------------------------------------------
    -- 사용자 화면에 보여줄 표준 모델명
    --
    -- 아반떼 / 쏘나타 / K5 등
    -- --------------------------------------------------------
    model_std VARCHAR(100) NOT NULL,


    -- --------------------------------------------------------
    -- 선택 모델의 제조사 공식 고객지원 URL
    -- --------------------------------------------------------
    manufacturer_support_url VARCHAR(1000) NOT NULL,


    -- model_key는 한 모델을 유일하게 식별
    PRIMARY KEY (model_key),


    -- --------------------------------------------------------
    -- 같은 제조사에 같은 표준 모델이
    -- 두 번 등록되는 것을 막습니다.
    --
    -- 예:
    --
    -- 현대자동차 + 아반떼
    -- 현대자동차 + 아반떼
    --
    -- 같은 조합이 두 번 들어오면 오류가 납니다.
    -- --------------------------------------------------------
    UNIQUE KEY uk_model_master_manufacturer_model (
        manufacturer_std,
        model_std
    )

)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;



-- ============================================================
-- 3. model_mapping
-- ============================================================
--
-- D-MAP 물리 테이블
--
-- 역할:
-- 각 원천의 차명을 표준 model_key와 연결합니다.
--
-- DB_물리설계에 따라
-- CSV의 아래 3개 컬럼은 이 테이블에 중복 저장하지 않습니다.
--
-- manufacturer_std
-- model_std
-- manufacturer_support_url
--
-- 위 값들은 model_master에 있고
-- model_key JOIN으로 가져옵니다.
-- ============================================================

CREATE TABLE IF NOT EXISTS model_mapping (

    -- DB 전용 surrogate key
    --
    -- CSV에는 없고 화면에도 노출하지 않습니다.
    mapping_id BIGINT NOT NULL AUTO_INCREMENT,


    -- 표준 모델 FK
    model_key VARCHAR(50) NOT NULL,


    -- 세대/프로젝트 코드 참고정보
    --
    -- 예:
    -- AD / CN7 / DL3
    --
    -- 없는 alias도 있으므로 NULL 허용
    generation_name VARCHAR(100) NULL,


    -- 원천 데이터 종류
    --
    -- SALES / DEFECT / REC
    source_type VARCHAR(20) NOT NULL,


    -- 실제 원천에서 사용된 차명
    alias_name VARCHAR(255) NOT NULL,


    -- 검색/매칭용 정규화 이름
    alias_normalized VARCHAR(255) NOT NULL,


    -- 검증완료 / 검토중 / 제외
    match_status VARCHAR(20) NOT NULL,


    -- 매핑 근거/주의사항
    review_note VARCHAR(500) NULL,


    -- DB 내부 행 식별자
    PRIMARY KEY (mapping_id),


    -- --------------------------------------------------------
    -- 같은 데이터 종류에서
    -- 동일 alias가 두 개의 모델에 매핑되는 것을 방지합니다.
    --
    -- 예:
    --
    -- REC + 아반떼(CN7)
    --
    -- 조합은 하나만 존재해야 합니다.
    -- --------------------------------------------------------
    UNIQUE KEY uk_model_mapping_source_alias (
        source_type,
        alias_name
    ),


    -- --------------------------------------------------------
    -- model_master와 FK 연결
    --
    -- RESTRICT:
    -- 자식 데이터가 있는 상태에서
    -- 부모 model_master를 함부로 삭제/변경하지 못하게 합니다.
    -- --------------------------------------------------------
    CONSTRAINT fk_model_mapping_model
        FOREIGN KEY (model_key)
        REFERENCES model_master (model_key)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT

)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;



-- 검색/매칭 보조 인덱스
CREATE INDEX idx_model_mapping_alias
ON model_mapping (
    source_type,
    alias_normalized,
    match_status
);


-- 특정 model_key의 별칭을 찾을 때 사용
CREATE INDEX idx_model_mapping_model
ON model_mapping (
    model_key
);



-- ============================================================
-- 4. registration_summary
-- ============================================================
--
-- D-REG
--
-- 전국 자동차 시장의 등록현황 Stock 데이터입니다.
--
-- 중요:
-- 모델별 데이터가 아니므로 model_master와 FK를 걸지 않습니다.
--
-- UNIQUE도 일부러 걸지 않습니다.
--
-- 이유:
-- stat_month는 NULL이 가능하고
-- MySQL UNIQUE에서는 NULL을 서로 다른 값으로 취급하기 때문에
-- DB UNIQUE만으로 중복을 완전히 막을 수 없습니다.
--
-- 따라서 중복은 다음 단계 load_to_mysql.py에서
-- 반드시 검사합니다.
-- ============================================================

CREATE TABLE IF NOT EXISTS registration_summary (

    -- DB 전용 PK
    registration_id BIGINT NOT NULL AUTO_INCREMENT,


    -- 등록현황 기준 연도
    stat_year SMALLINT UNSIGNED NOT NULL,


    -- 기준 월
    --
    -- 연간 자료는 NULL 가능
    stat_month TINYINT UNSIGNED NULL,


    -- 집계축
    --
    -- TOTAL
    -- REGION
    -- VEHICLE_TYPE
    -- FUEL
    dimension_type VARCHAR(30) NOT NULL,


    -- 실제 집계값
    --
    -- 전국
    -- 서울특별시
    -- 승용
    -- 휘발유
    -- 등
    dimension_value VARCHAR(100) NOT NULL,


    -- 등록 차량 대수
    registration_count BIGINT UNSIGNED NOT NULL,


    -- 공식 출처 URL
    source_url VARCHAR(1000) NOT NULL,


    -- 데이터 적재일
    loaded_at DATE NOT NULL,


    PRIMARY KEY (registration_id)

)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;



-- S-01/S-03에서
-- 기준시점 + 집계축으로 조회할 때 사용
CREATE INDEX idx_registration_snapshot_dimension
ON registration_summary (
    stat_year,
    stat_month,
    dimension_type
);



-- ============================================================
-- 5. vehicle_sales
-- ============================================================
--
-- D-SALES
--
-- 모델별 연간 국내 판매량
--
-- 한 모델의 한 연도는
-- 서비스 데이터에서 한 행만 존재해야 하므로:
--
-- (model_key, sales_year)
--
-- 를 복합 PK로 사용합니다.
-- ============================================================

CREATE TABLE IF NOT EXISTS vehicle_sales (

    -- 표준 모델
    model_key VARCHAR(50) NOT NULL,


    -- 판매 연도
    --
    -- DB에는 서비스 분석기간인
    -- 2020~2025만 적재합니다.
    sales_year SMALLINT UNSIGNED NOT NULL,


    -- 판매량 원천 제조사
    manufacturer VARCHAR(50) NOT NULL,


    -- 판매량 원본 모델명
    model_original VARCHAR(255) NOT NULL,


    -- 국내 판매량
    --
    -- 미확보는 0이 아니라 NULL
    domestic_sales_count BIGINT UNSIGNED NULL,


    -- 공식자료 / 교차검증 / 보완필요
    verification_status VARCHAR(20) NOT NULL,


    -- 근거 URL
    source_url VARCHAR(1000) NOT NULL,


    -- 적재일
    loaded_at DATE NOT NULL,


    -- 모델 + 연도 복합 PK
    PRIMARY KEY (
        model_key,
        sales_year
    ),


    -- model_master FK
    CONSTRAINT fk_vehicle_sales_model
        FOREIGN KEY (model_key)
        REFERENCES model_master (model_key)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT

)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;



-- ------------------------------------------------------------
-- 최근 확인 판매량(M04)을 빠르게 찾기 위한 인덱스
--
-- WHERE model_key = ?
-- AND verification_status IN (...)
-- ORDER BY sales_year DESC
--
-- 같은 조회를 지원합니다.
-- ------------------------------------------------------------
CREATE INDEX idx_vehicle_sales_model_status_year
ON vehicle_sales (
    model_key,
    verification_status,
    sales_year
);



-- ============================================================
-- 6. defect_reports
-- ============================================================
--
-- D-DEF
--
-- 제작결함 신고 데이터
--
-- 원본에는 안정적인 고유 신고 ID가 없기 때문에
-- DB 전용 defect_report_id를 AUTO_INCREMENT PK로 둡니다.
--
-- 자연키 UNIQUE는 사용하지 않습니다.
--
-- 같은 날짜 + 같은 모델 + 같은 모델년도의
-- 서로 다른 신고가 정상적으로 여러 건 존재할 수 있기 때문입니다.
-- ============================================================

CREATE TABLE IF NOT EXISTS defect_reports (

    -- DB 전용 PK
    defect_report_id BIGINT NOT NULL AUTO_INCREMENT,


    -- 신고 접수일
    report_date DATE NOT NULL,


    -- 원본 제작사
    --
    -- 원천에서 결측이 존재하므로 NULL 허용
    manufacturer VARCHAR(50) NULL,


    -- 원본 차명
    model_original VARCHAR(255) NOT NULL,


    -- 차량 모델년도
    --
    -- 원천 결측 허용
    model_year SMALLINT UNSIGNED NULL,


    -- 표준 모델키
    model_key VARCHAR(50) NOT NULL,


    -- 공식 데이터 출처
    source_url VARCHAR(1000) NOT NULL,


    -- 적재일
    loaded_at DATE NOT NULL,


    PRIMARY KEY (defect_report_id),


    -- model_master FK
    CONSTRAINT fk_defect_reports_model
        FOREIGN KEY (model_key)
        REFERENCES model_master (model_key)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT

)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;



-- 접수연도 추이 M07
CREATE INDEX idx_defect_model_date
ON defect_reports (
    model_key,
    report_date
);


-- 모델년도 분포 M08
CREATE INDEX idx_defect_model_year
ON defect_reports (
    model_key,
    model_year
);



-- ============================================================
-- 7. recall_campaigns
-- ============================================================
--
-- D-REC
--
-- 테이블명을 recall이 아니라 recall_campaigns로 확정했습니다.
--
-- 이유:
-- 한 행이 차량 한 대가 아니라
-- "리콜 캠페인 한 건"을 의미하기 때문입니다.
--
-- recall_count 역시 고유 차량 수가 아니라
-- 해당 캠페인의 대상대수입니다.
-- ============================================================

CREATE TABLE IF NOT EXISTS recall_campaigns (

    -- 서비스 내부 리콜 고유키
    recall_id VARCHAR(50) NOT NULL,


    -- 제작사
    manufacturer VARCHAR(50) NOT NULL,


    -- 원본 차명
    model_original VARCHAR(255) NOT NULL,


    -- 표준 모델키
    model_key VARCHAR(50) NOT NULL,


    -- 대상 차량 생산 시작일
    production_from DATE NULL,


    -- 대상 차량 생산 종료일
    production_to DATE NULL,


    -- 리콜 개시일
    recall_start_date DATE NOT NULL,


    -- 캠페인 대상대수
    --
    -- 고유 차량 수로 해석하면 안 됨
    recall_count BIGINT UNSIGNED NULL,


    -- 공식 리콜 사유 원문
    recall_reason TEXT NOT NULL,


    -- 표준 리콜 사유분류
    recall_category VARCHAR(50) NOT NULL,


    -- 데이터 원천 URL
    source_url VARCHAR(1000) NOT NULL,


    -- 사용자 공식 재확인용 URL
    official_check_url VARCHAR(1000) NOT NULL,


    -- 적재일
    loaded_at DATE NOT NULL,


    PRIMARY KEY (recall_id),


    CONSTRAINT fk_recall_campaigns_model
        FOREIGN KEY (model_key)
        REFERENCES model_master (model_key)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT

)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;



-- 최신 리콜 조회 M09
CREATE INDEX idx_recall_model_date
ON recall_campaigns (
    model_key,
    recall_start_date
);


-- 리콜 사유 구성 분석 M12
CREATE INDEX idx_recall_model_category
ON recall_campaigns (
    model_key,
    recall_category
);



-- ============================================================
-- 8. faq_master
-- ============================================================
--
-- D-FAQ
--
-- 자동차리콜센터 공통 FAQ입니다.
--
-- 특정 모델/제조사의 FAQ가 아니므로
-- model_master와 FK를 걸지 않습니다.
-- ============================================================

CREATE TABLE IF NOT EXISTS faq_master (

    -- 프로젝트 내부 FAQ 고유키
    faq_id VARCHAR(50) NOT NULL,


    -- 제공기관
    --
    -- 현재 자동차리콜센터
    provider VARCHAR(50) NOT NULL,


    -- FAQ 내부 분류
    --
    -- 선택값이므로 NULL 허용
    category VARCHAR(50) NULL,


    -- 공식 질문 원문
    question TEXT NOT NULL,


    -- 공식 답변 원문
    answer TEXT NOT NULL,


    -- 공식 FAQ URL
    source_url VARCHAR(1000) NOT NULL,


    -- FAQ 수집 시각
    --
    -- 다른 테이블의 loaded_at과 달리
    -- FAQ는 시각까지 관리하므로 DATETIME
    collected_at DATETIME NOT NULL,


    PRIMARY KEY (faq_id)

)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8mb4
COLLATE = utf8mb4_unicode_ci;


-- ============================================================
-- 끝
--
-- 주의:
-- faq_master는 MVP 규모에서 추가 INDEX를 만들지 않습니다.
--
-- question LIKE '%검색어%'
--
-- 형태는 일반 B-Tree 인덱스 효과가 낮기 때문입니다.
--
-- 데이터 규모가 크게 늘면
-- 추후 FULLTEXT 인덱스를 검토합니다.
-- ============================================================