-- ============================================================
-- queries.sql
--
-- 프로젝트: 전국 자동차 등록현황 및 주요 차종 판매·안전정보·
--          공식 FAQ 통합 조회 시스템
--
-- 역할: Streamlit 화면에서 사용할 조회 쿼리
--       (판매량 / 결함신고 / 리콜내역 / 리콜사유 집계 /
--        등록현황 / FAQ 검색 / 모델 A·B 비교)
--
-- 표기: :model_key, :stat_year 처럼 콜론(:)이 붙은 것은
--       화면에서 사용자가 고르는 파라미터 자리표시자입니다.
--       Python에서 pymysql로 실행할 때는 %s로 바꿔서 쓰면 됩니다.
-- ============================================================


-- ============================================================
-- 0. (참고) 모델 선택 드롭다운용 — 27개 표준 모델 목록
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
-- category는 화면 필터로 쓰지 않음. 검색어(:keyword) 기준으로
--   - 검색어 없음(NULL 또는 빈 문자열) → 전체 FAQ 조회
--   - 검색어 있음 → question 또는 answer에 검색어가 포함된 결과만
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
WHERE (
    :keyword IS NULL
    OR :keyword = ''
    OR fm.question LIKE CONCAT('%', :keyword, '%')
    OR fm.answer LIKE CONCAT('%', :keyword, '%')
)
ORDER BY fm.collected_at DESC;


-- ============================================================
-- 7. 모델 A/B 비교 조회
-- 비교 대상은 D-MAP 검증완료로 매핑된 표준 모델(=model_master의
-- 27개 모델) 중 서로 다른 2개(:model_a, :model_b).
-- 결함률·리콜률·자체 안전점수처럼 서로 다른 모수를 나누거나
-- 우열을 매기는 파생 지표는 만들지 않고, 같은 기준의 원자료만
-- 나란히 비교함.
-- ============================================================

-- 7-1. 판매량 비교
-- 두 모델 모두 값이 존재(NULL 아님)하고 공식자료/교차검증인
-- 동일 연도만 비교 대상으로 삼음 (한쪽만 있는 연도는 제외)
SELECT
    a.sales_year,
    a.domestic_sales_count AS model_a_sales,
    a.verification_status  AS model_a_status,
    b.domestic_sales_count AS model_b_sales,
    b.verification_status  AS model_b_status
FROM vehicle_sales a
JOIN vehicle_sales b
    ON a.sales_year = b.sales_year
WHERE a.model_key = :model_a
  AND b.model_key = :model_b
  AND a.domestic_sales_count IS NOT NULL
  AND b.domestic_sales_count IS NOT NULL
  AND a.verification_status IN ('공식자료', '교차검증')
  AND b.verification_status IN ('공식자료', '교차검증')
ORDER BY a.sales_year;


-- 7-2. 결함신고 비교
-- 동일 접수기간(연도) 기준, 2023년은 데이터 미확보 연도라 제외
SELECT
    YEAR(dr.report_date) AS report_year,
    dr.model_key,
    COUNT(*)              AS report_count
FROM defect_reports dr
WHERE dr.model_key IN (:model_a, :model_b)
  AND YEAR(dr.report_date) <> 2023
GROUP BY YEAR(dr.report_date), dr.model_key
ORDER BY report_year, dr.model_key;


-- 7-3. 리콜 요약 비교
-- 2020~2025 기준, 모델별 캠페인 수 / 대상대수 합계 / 최근 개시일
SELECT
    rc.model_key,
    COUNT(*)                  AS campaign_count,
    SUM(rc.recall_count)      AS total_recall_count,
    MAX(rc.recall_start_date) AS latest_recall_date
FROM recall_campaigns rc
WHERE rc.model_key IN (:model_a, :model_b)
  AND rc.recall_start_date BETWEEN '2020-01-01' AND '2025-12-31'
GROUP BY rc.model_key;


-- 7-4. 리콜 사유 구성 비교
-- 2020~2025 기준, 모델별 recall_category 분포
SELECT
    rc.model_key,
    rc.recall_category,
    COUNT(*)               AS campaign_count,
    SUM(rc.recall_count)   AS total_recall_count
FROM recall_campaigns rc
WHERE rc.model_key IN (:model_a, :model_b)
  AND rc.recall_start_date BETWEEN '2020-01-01' AND '2025-12-31'
GROUP BY rc.model_key, rc.recall_category
ORDER BY rc.model_key, campaign_count DESC;
