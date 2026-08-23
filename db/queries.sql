-- ============================================================
-- queries.sql
--
-- 프로젝트: 전국 자동차 등록현황 및 주요 차종 판매·안전정보·
--          공식 FAQ 통합 조회 시스템
--
-- 역할: Streamlit 화면에서 사용할 조회 쿼리 6종
--       (판매량 / 결함신고 / 리콜내역 / 리콜사유 집계 /
--        등록현황 / FAQ)
--
-- 표기: :model_key, :stat_year 처럼 콜론(:)이 붙은 것은
--       화면에서 사용자가 고르는 파라미터 자리표시자입니다.
--       DBeaver에서는 그대로 실행하면 값 입력창이 뜨고,
--       Python에서 pymysql로 실행할 때는 %s로 바꿔서 쓰면 됩니다.
-- ============================================================


-- ============================================================
-- 0. (참고) 모델 선택 드롭다운용 — 6개 표준 모델 목록
-- ============================================================
SELECT
    model_key,
    manufacturer_std,
    model_std
FROM model_master
ORDER BY manufacturer_std, model_std;


-- ============================================================
-- 1. 모델별 판매량 조회 (D-SALES)
-- 특정 모델의 연도별 국내 판매량 추이 (2020~2025)
-- ============================================================
SELECT
    vs.sales_year,
    vs.manufacturer,
    vs.model_original,
    vs.domestic_sales_count,
    vs.verification_status,
    vs.source_url
FROM vehicle_sales vs
WHERE vs.model_key = :model_key
ORDER BY vs.sales_year;


-- ============================================================
-- 2. 모델별 결함신고 조회 (D-DEF)
-- 특정 모델의 제작결함 신고 원본 레코드 목록 (최신순)
-- ============================================================
SELECT
    dr.defect_report_id,
    dr.report_date,
    dr.manufacturer,
    dr.model_original,
    dr.model_year,
    dr.source_url
FROM defect_reports dr
WHERE dr.model_key = :model_key
ORDER BY dr.report_date DESC;


-- 2-1. (참고) 모델별 결함신고 연도별 추이 — 화면에 그래프로 쓸 때
SELECT
    YEAR(dr.report_date) AS report_year,
    COUNT(*)             AS report_count
FROM defect_reports dr
WHERE dr.model_key = :model_key
GROUP BY YEAR(dr.report_date)
ORDER BY report_year;


-- ============================================================
-- 3. 모델별 리콜 내역 조회 (D-REC)
-- 특정 모델의 리콜 캠페인 목록 (최신순)
-- ============================================================
SELECT
    rc.recall_id,
    rc.manufacturer,
    rc.model_original,
    rc.production_from,
    rc.production_to,
    rc.recall_start_date,
    rc.recall_count,
    rc.recall_reason,
    rc.recall_category,
    rc.source_url,
    rc.official_check_url
FROM recall_campaigns rc
WHERE rc.model_key = :model_key
ORDER BY rc.recall_start_date DESC;


-- ============================================================
-- 4. 리콜 사유별 집계
-- 특정 모델의 recall_category(9종)별 캠페인 건수 / 대상대수 합계
-- (전체 모델 기준으로 보고 싶으면 WHERE 절만 빼면 됨)
-- ============================================================
SELECT
    rc.recall_category,
    COUNT(*)                 AS campaign_count,
    SUM(rc.recall_count)     AS total_recall_count
FROM recall_campaigns rc
WHERE rc.model_key = :model_key
GROUP BY rc.recall_category
ORDER BY campaign_count DESC;


-- ============================================================
-- 5. 등록현황 조회 (D-REG)
-- 기준연도 + 집계축(TOTAL/REGION/VEHICLE_TYPE/FUEL)으로 조회
-- stat_month가 NULL이면 "연간 집계" 행
-- ============================================================
SELECT
    rs.stat_year,
    rs.stat_month,
    rs.dimension_value,
    rs.registration_count,
    rs.source_url
FROM registration_summary rs
WHERE rs.stat_year = :stat_year
  AND rs.dimension_type = :dimension_type
ORDER BY rs.stat_month IS NULL, rs.stat_month, rs.registration_count DESC;


-- ============================================================
-- 6. FAQ 조회 (D-FAQ)
-- 자동차리콜센터 공통 FAQ — 특정 모델과 연결되지 않음
-- category가 NULL로 넘어오면 전체 조회
-- ============================================================
SELECT
    fm.faq_id,
    fm.provider,
    fm.category,
    fm.question,
    fm.answer,
    fm.source_url,
    fm.collected_at
FROM faq_master fm
WHERE (:category IS NULL OR fm.category = :category)
ORDER BY fm.collected_at DESC;
