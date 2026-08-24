"""
이 파일은 화면(S01~S04)에서 필요한 데이터를 DB에서 꺼내오는 함수 모음입니다.

패턴이 다 똑같습니다:
    1) "SQL"이라는 질문 문장을 하나 만든다 (DB에게 "이런 데이터 줘"라고 요청하는 문장)
    2) run_sql() 함수에 그 문장을 넘긴다
    3) run_sql()이 DB에 접속해서 질문을 던지고, 결과를 표(DataFrame)로 돌려준다

그래서 원래 코드처럼 함수마다 DB 접속(pymysql.connect)과 접속 종료(conn.close)를
반복해서 쓸 필요 없이, run_sql() 하나가 그 반복 작업을 도맡아 처리합니다.
"""

import os
import pandas as pd  # 표(DataFrame) 형태로 데이터를 다루는 도구
import pymysql        # 파이썬에서 MySQL(DB)에 접속하게 해주는 도구
from dotenv import load_dotenv  # .env 파일에 적어둔 비밀번호 등을 불러오는 도구

load_dotenv(override=True)  # .env 파일의 값을 읽어서 환경변수로 등록

# DB 접속에 필요한 정보 (주소, 포트, 계정, 비밀번호, DB 이름 등)
DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME", "skn36_1st_1team"),
    charset="utf8mb4",
)


def run_sql(sql, params=None):
    """SQL 문장 하나를 실행하고, 결과를 표(DataFrame)로 돌려주는 공통 함수."""
    conn = pymysql.connect(**DB)  # DB에 접속
    try:
        return pd.read_sql(sql, conn, params=params)  # 질문(sql)을 던지고 결과를 표로 받기
    finally:
        conn.close()  # 성공하든 실패하든 접속은 반드시 닫기 (자원 낭비 방지)


def get_models():
    """S01/S02: 서비스에서 지원하는 자동차 모델 목록을 가져옵니다."""
    sql = """
        SELECT
            model_key,
            manufacturer_std,
            model_std,
            manufacturer_support_url
        FROM model_master
        ORDER BY manufacturer_std, model_std
    """
    return run_sql(sql)


def get_sales(model_key):
    """S02: 선택한 모델의 연도별 판매량을 가져옵니다."""
    sql = """
        SELECT
            model_key,
            sales_year,
            manufacturer,
            model_original,
            domestic_sales_count,
            verification_status,
            source_url,
            loaded_at
        FROM vehicle_sales
        WHERE model_key = %s
        ORDER BY sales_year
    """

    df = run_sql(sql, [model_key])

    if not df.empty:
        df["loaded_at"] = pd.to_datetime(df["loaded_at"], errors="coerce")

    return df


def get_defects(model_key):
    """S02: 선택한 모델의 결함신고 원본 기록을 가져옵니다."""
    sql = """
        SELECT
            defect_report_id,
            model_key,
            report_date,
            manufacturer,
            model_original,
            model_year,
            source_url,
            loaded_at
        FROM defect_reports
        WHERE model_key = %s
        ORDER BY report_date DESC
    """

    df = run_sql(sql, [model_key])

    if not df.empty:
        df["report_date"] = pd.to_datetime(df["report_date"], errors="coerce")
        df["loaded_at"] = pd.to_datetime(df["loaded_at"], errors="coerce")

    return df


def get_defect_yearly(model_key):
    """S02: 선택한 모델의 결함신고 건수를 연도별로 묶어서 가져옵니다."""
    # report_date에서 연도만 뽑아 그룹으로 묶고(GROUP BY), 그룹별 건수를 세는 질문
    sql = "SELECT YEAR(report_date) AS report_year, COUNT(*) AS report_count FROM defect_reports WHERE model_key = %s GROUP BY YEAR(report_date) ORDER BY report_year"
    return run_sql(sql, [model_key])


def get_recalls(model_key):
    """S02: 선택한 모델의 리콜 캠페인 목록을 가져옵니다."""
    sql = """
        SELECT
            recall_id,
            model_key,
            manufacturer,
            model_original,
            production_from,
            production_to,
            recall_start_date,
            recall_count,
            recall_reason,
            recall_category,
            source_url,
            official_check_url,
            loaded_at
        FROM recall_campaigns
        WHERE model_key = %s
        ORDER BY recall_start_date DESC
    """

    df = run_sql(sql, [model_key])

    if not df.empty:
        for col in [
            "production_from",
            "production_to",
            "recall_start_date",
            "loaded_at",
        ]:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def get_recall_categories(model_key):
    """S02: 선택한 모델의 리콜 사유별 캠페인 수/대상대수를 집계합니다."""
    # 사유(recall_category)별로 묶어서 캠페인 수와 대상대수 합계를 계산하는 질문
    sql = "SELECT recall_category, COUNT(*) AS campaign_count, COALESCE(SUM(recall_count), 0) AS total_recall_count FROM recall_campaigns WHERE model_key = %s GROUP BY recall_category ORDER BY campaign_count DESC"
    return run_sql(sql, [model_key])


def get_registration(stat_year, dimension_type):
    """S03: 특정 연도·집계축(지역/차종/연료 등)의 전국 등록현황을 가져옵니다."""
    # 월 정보가 없는 행은 뒤로 보내고, 있으면 월 순 → 등록대수 많은 순으로 정렬
    sql = """
        SELECT stat_year, stat_month, dimension_value, registration_count, source_url
        FROM registration_summary
        WHERE stat_year = %s AND dimension_type = %s
        ORDER BY stat_month IS NULL, stat_month, registration_count DESC
    """
    return run_sql(sql, [stat_year, dimension_type])

def get_all_registration():
    """S03: DB에 저장된 전국 자동차 등록현황 전체를 가져옵니다."""
    sql = """
        SELECT
            stat_year,
            stat_month,
            dimension_type,
            dimension_value,
            registration_count,
            source_url,
            loaded_at
        FROM registration_summary
        ORDER BY stat_year, stat_month, dimension_type, registration_count DESC
    """

    df = run_sql(sql)

    if df.empty:
        return df

    month = pd.to_numeric(df["stat_month"], errors="coerce").fillna(0).astype(int)
    year = pd.to_numeric(df["stat_year"], errors="coerce").astype(int)

    df["_snapshot_key"] = year * 100 + month
    df["loaded_at"] = pd.to_datetime(df["loaded_at"], errors="coerce")

    return df

def get_registration_years():
    """S03: DB에 등록현황 데이터가 있는 연도 목록을 가져옵니다."""
    # 중복 없이(DISTINCT) 연도만 뽑아서 오름차순 정렬
    sql = "SELECT DISTINCT stat_year FROM registration_summary ORDER BY stat_year"
    return run_sql(sql)


def get_latest_registration_snapshot():
    """S01: DB에 있는 가장 최신 기준시점의 전국 자동차 등록현황 전체를 가져옵니다."""

    latest_sql = """
        SELECT stat_year, stat_month
        FROM registration_summary
        ORDER BY stat_year DESC, COALESCE(stat_month, 0) DESC
        LIMIT 1
    """
    latest = run_sql(latest_sql)

    if latest.empty:
        return pd.DataFrame()

    stat_year = int(latest.iloc[0]["stat_year"])
    stat_month = latest.iloc[0]["stat_month"]

    if pd.isna(stat_month):
        sql = """
            SELECT
                stat_year,
                stat_month,
                dimension_type,
                dimension_value,
                registration_count,
                source_url,
                loaded_at
            FROM registration_summary
            WHERE stat_year = %s
              AND stat_month IS NULL
        """
        return run_sql(sql, [stat_year])

    sql = """
        SELECT
            stat_year,
            stat_month,
            dimension_type,
            dimension_value,
            registration_count,
            source_url,
            loaded_at
        FROM registration_summary
        WHERE stat_year = %s
          AND stat_month = %s
    """

    return run_sql(sql, [stat_year, int(stat_month)])


# 그 아래에 원래 있던 FAQ 함수
def get_faq(keyword=""):
    ...

def get_faq(keyword=""):
    """S04: FAQ 전체 목록, 또는 검색어가 포함된 질문/답변만 가져옵니다."""
    # keyword가 비어있으면 전체를, 있으면 질문 또는 답변에 그 단어가 포함된 것만 가져오는 질문
    sql = """
        SELECT faq_id, provider, category, question, answer, source_url, collected_at
        FROM faq_master
        WHERE (%s = '' OR question LIKE %s OR answer LIKE %s)
        ORDER BY collected_at DESC
    """

    # SQL 안에서 %를 조합하지 않고, 파이썬에서 미리 검색어 앞뒤에 %를 붙여서 넘깁니다.
    # 예: 검색어 "리콜" -> like_keyword "%리콜%" -> question LIKE "%리콜%" (리콜이 포함된 모든 질문)
    keyword = keyword or ""
    like_keyword = f"%{keyword}%"

    return run_sql(sql, [keyword, like_keyword, like_keyword])
