"""
자동차 두 모델(예: 아반떼 vs K5)을 비교하는 스크립트입니다.

무슨 일을 하나요?
1. DB(데이터베이스)에 접속합니다.
2. "SQL"이라는 질문 문장을 DB에 보내서 원하는 표(데이터)를 받아옵니다.
   - SQL은 사람이 쓰는 문장처럼 생겼지만, DB가 알아듣는 '질문 언어'라고 생각하면 됩니다.
3. 받아온 표들을 딕셔너리(이름표가 붙은 상자들의 묶음) 하나에 정리해서 돌려줍니다.

원래 코드는 "판매량 가져오기", "결함 가져오기", "리콜 가져오기" 같은
비슷한 함수를 A모델용, B모델용으로 따로따로 만들어서 길어졌습니다.
아래 버전은 "SQL 하나 실행해서 표로 받기"라는 동작을 함수 하나(run_sql)로
공통화하고, A/B를 반복문(for)으로 처리해서 줄을 크게 줄였습니다.
"""

import os
import pandas as pd
import pymysql
from dotenv import load_dotenv

load_dotenv(override=True)

# DB 접속 정보 (.env 파일에서 읽어옵니다)
DB = dict(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME", "skn36_1st_1team"),
    charset="utf8mb4",
)

# 판매량 데이터 중 '믿을 수 있는' 데이터로 인정하는 상태값
VALID_SALES_STATUS = ("공식자료", "교차검증")


def run_sql(conn, sql, params):
    """SQL 문장을 실행하고 결과를 표(DataFrame) 형태로 돌려주는 공통 함수."""
    return pd.read_sql(sql, conn, params=params)


def get_model_info(conn, model_key):
    """model_key(예: 'HYU_AVANTE')로 제조사/모델명 등 기본 정보를 가져옵니다."""
    sql = """
        SELECT model_key, manufacturer_std, model_std, manufacturer_support_url
        FROM model_master
        WHERE model_key = %s
    """
    return run_sql(conn, sql, [model_key])


def get_common_sales(conn, key_a, key_b):
    """
    두 모델이 '같은 해'에 대해 각각 판매량을 갖고 있고,
    그 판매량이 믿을 수 있는 데이터(VALID_SALES_STATUS)일 때만 비교합니다.
    """
    sql = """
        SELECT a.sales_year,
               a.domestic_sales_count AS model_a_sales,
               b.domestic_sales_count AS model_b_sales
        FROM vehicle_sales a
        JOIN vehicle_sales b ON a.sales_year = b.sales_year
        WHERE a.model_key = %s AND b.model_key = %s
          AND a.domestic_sales_count IS NOT NULL
          AND b.domestic_sales_count IS NOT NULL
          AND a.verification_status IN ('공식자료', '교차검증')
          AND b.verification_status IN ('공식자료', '교차검증')
        ORDER BY a.sales_year
    """
    return run_sql(conn, sql, [key_a, key_b])


def get_defect_summary(conn, model_key):
    """
    결함신고 건수, 첫/마지막 신고일을 가져옵니다.
    ※ 2023년 데이터는 원래 없는 것(수집 안 됨)이라 0건과는 다릅니다.
    """
    sql = """
        SELECT COUNT(*) AS defect_count,
               MIN(report_date) AS first_report_date,
               MAX(report_date) AS latest_report_date
        FROM defect_reports
        WHERE model_key = %s
    """
    return run_sql(conn, sql, [model_key])


def get_defect_yearly(conn, model_key):
    """연도별 결함신고 건수를 가져옵니다."""
    sql = """
        SELECT YEAR(report_date) AS report_year, COUNT(*) AS defect_count
        FROM defect_reports
        WHERE model_key = %s
        GROUP BY YEAR(report_date)
        ORDER BY report_year
    """
    return run_sql(conn, sql, [model_key])


def get_recall_summary(conn, model_key):
    """리콜 캠페인 횟수, 대상 대수 합계, 최근 리콜 시작일을 가져옵니다."""
    sql = """
        SELECT COUNT(*) AS campaign_count,
               COALESCE(SUM(recall_count), 0) AS recall_target_sum,
               MAX(recall_start_date) AS latest_recall_date
        FROM recall_campaigns
        WHERE model_key = %s
    """
    return run_sql(conn, sql, [model_key])


def get_recall_categories(conn, model_key):
    """리콜 사유(카테고리)별로 몇 번 있었는지 가져옵니다."""
    sql = """
        SELECT recall_category, COUNT(*) AS campaign_count
        FROM recall_campaigns
        WHERE model_key = %s
        GROUP BY recall_category
        ORDER BY campaign_count DESC, recall_category
    """
    return run_sql(conn, sql, [model_key])


def compare_models(model_key_a, model_key_b):
    """
    두 모델(A, B)을 비교하는 데 필요한 모든 데이터를 한 번에 모아서 돌려줍니다.

    주의할 점:
    - 판매량은 두 모델 다 '믿을 수 있는' 데이터가 있는 연도만 비교합니다.
    - 결함신고 2023년은 데이터가 아예 없는 상태입니다(0건 아님).
    - recall_target_sum은 캠페인들의 대상 대수를 '합친 것'이지,
      실제로 겹치지 않는 고유한 차량 수는 아닙니다.
    - 판매량/결함/리콜 사이의 비율(%) 계산은 여기서 하지 않습니다.
    """
    if model_key_a == model_key_b:
        raise ValueError("서로 다른 두 모델을 선택해야 합니다.")

    conn = pymysql.connect(**DB)
    try:
        result = {"sales_common": get_common_sales(conn, model_key_a, model_key_b)}

        # A모델, B모델을 반복문으로 한 번에 처리 (원래 코드는 이 부분이 A/B 따로 반복돼서 길었음)
        for label, key in (("a", model_key_a), ("b", model_key_b)):
            info = get_model_info(conn, key)
            if info.empty:
                raise ValueError(f"존재하지 않는 model_key입니다: {key}")

            result[f"model_{label}"] = info.iloc[0].to_dict()
            result[f"defect_{label}"] = get_defect_summary(conn, key).iloc[0].to_dict()
            result[f"defect_yearly_{label}"] = get_defect_yearly(conn, key)
            result[f"recall_{label}"] = get_recall_summary(conn, key).iloc[0].to_dict()
            result[f"recall_categories_{label}"] = get_recall_categories(conn, key)

        return result
    finally:
        conn.close()  # DB 연결은 꼭 닫아줘야 자원이 낭비되지 않습니다.


if __name__ == "__main__":
    result = compare_models("HYU_AVANTE", "KIA_K5")

    print("\n=== 모델 A ===")
    print(result["model_a"])

    print("\n=== 모델 B ===")
    print(result["model_b"])

    print("\n=== 공통 판매연도 ===")
    print(result["sales_common"])

    print("\n=== 결함 요약 ===")
    print("A:", result["defect_a"])
    print("B:", result["defect_b"])

    print("\n=== 리콜 요약 ===")
    print("A:", result["recall_a"])
    print("B:", result["recall_b"])