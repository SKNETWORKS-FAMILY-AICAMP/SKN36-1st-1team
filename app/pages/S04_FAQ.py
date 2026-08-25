
import sys
from pathlib import Path

# app/pages에서 실행할 때 app/lib 모듈을 찾을 수 있도록 경로를 추가합니다.
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st
from lib.ui import apply_ui, navbar, page_intro, site_footer

# FAQ 화면에서 사용하는 공통 데이터/검색/링크 함수입니다.
from lib.common import (
    load_faq,
    load_recall,
    search_faq,
    get_verified_models,
    link_or_gap,
)

# ------------------------------------------------------------
# 페이지 기본 설정
# ------------------------------------------------------------

st.set_page_config(page_title="리콜 FAQ / 공식 안내", page_icon="💬", layout="wide")

# Streamlit 기본 사이드바를 숨깁니다.
apply_ui()
navbar("FAQ")

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stExpandSidebarButton"] { display: none; }
    /* FAQ 검색 영역 전체를 아래로 이동 */
    .st-key-faq_search_row {
        margin-top: 12px !important;
        margin-bottom: 8px !important;
    }

    /* 검색창 높이 */
    .st-key-faq_search_row [data-testid="stTextInput"] div[data-baseweb="input"] {
        height: 48px !important;
        min-height: 48px !important;
        max-height: 48px !important;
        box-sizing: border-box !important;
    }

    .st-key-faq_search_row [data-testid="stTextInput"] input {
        height: 100% !important;
        min-height: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }

    /* 검색 버튼은 검색창보다 작게 */
    .st-key-faq_search_row [data-testid="stButton"] button {
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        width: 100% !important;
        padding: 0 12px !important;
        box-sizing: border-box !important;
    }
    /* FAQ 답변 글씨와 원문 확인 버튼 사이 여백 */
    [class*="st-key-faq_card_"] [data-testid="stLinkButton"] {
        margin-top: 12px !important;
    }

    /* FAQ 건수 문구 ↔ 첫 번째 카드 사이 여백 */
    .st-key-faq_list {
        margin-top: 16px !important;
    }
    /* FAQ 큰 박스 내부 여백 */
    [class*="st-key-faq_card_"] {
        padding: 20px 28px !important;
        margin-bottom: 16px !important;
    }
    /* FAQ 원문 버튼 왼쪽으로 이동 */
    [class*="st-key-faq_card_"] [data-testid="stLinkButton"] {
        margin-left: -4px !important;
    }
    [class*="st-key-faq_card_"] [data-testid="stLinkButton"] a {
    min-width: 250px !important;
    width: auto !important;
    height: 48px !important;

    padding: 0 18px !important;

    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;

    font-size: 16px !important;
    white-space: nowrap !important;
    }
    /* FAQ 카드 기준점 */
    [class*="st-key-faq_card_"] {
        position: relative !important;
        padding: 20px 24px 20px 24px !important;
        margin-bottom: 16px !important;
    }

    /* 제공기관 → 카드 오른쪽 하단 */
    [class*="st-key-faq_card_"] .faq-provider {
        position: absolute !important;
        right: 24px !important;
        bottom: 16px !important;

        font-size: 14px !important;
        color: #8A9099 !important;
        white-space: nowrap !important;
    }
    /* FAQ 질문(Q) 아래 여백 */
    [class*="st-key-faq_card_"] [data-testid="stMarkdownContainer"]:first-child {
        margin-bottom: 10px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 상단 제목
# ------------------------------------------------------------


page_intro("리콜 FAQ / 공식 안내", "리콜·결함조사·보상 관련 자주 묻는 질문과 공식 확인 경로를 제공합니다.", "OFFICIAL GUIDE")

# ------------------------------------------------------------
# 이전 화면에서 선택한 모델 정보 확인
# ------------------------------------------------------------

# S01 또는 S02에서 선택한 model_key를 session_state에서 가져옵니다.
selected_model_key = st.session_state.get("selected_model_key")

# 선택 모델 정보가 없을 수도 있으므로 기본값은 None으로 둡니다.
selected_model_row = None

# 선택된 model_key가 있으면 현재 서비스 지원 모델 목록에서 해당 모델을 찾습니다.
if selected_model_key:
    verified_models = get_verified_models()

    match = verified_models[
        verified_models["model_key"] == selected_model_key
    ]

    if not match.empty:
        selected_model_row = match.iloc[0]

# 선택 모델이 존재하면 현재 어떤 모델 기준으로 화면을 보고 있는지 안내합니다.
if selected_model_row is not None:
    st.info(
        f"모델 선택 상태: {selected_model_row['model_std']}  |  "
        f"제조사: {selected_model_row['manufacturer_std']}"
    )

# ------------------------------------------------------------
# FAQ 데이터 로딩
# ------------------------------------------------------------

# 자동차리콜센터 FAQ / 공식 리콜 데이터를 불러옵니다.
faq_df = load_faq()
recall_df = load_recall()

# D-REC official_check_url 중 현재 화면에서 사용할 공식 확인 URL을 선택합니다.
# 모델 선택 상태가 있으면 해당 모델의 최신 리콜 캠페인 URL을 우선 사용하고,
# 선택 모델이 없으면 전체 D-REC에서 최신 유효 URL을 사용합니다.
official_recall_url = None

if "official_check_url" in recall_df.columns:
    recall_link_df = recall_df.copy()

    if selected_model_key and "model_key" in recall_link_df.columns:
        model_recall_df = recall_link_df[
            recall_link_df["model_key"] == selected_model_key
        ].copy()

        if not model_recall_df.empty:
            recall_link_df = model_recall_df

    recall_link_df = recall_link_df[
        recall_link_df["official_check_url"].notna()
        & recall_link_df["official_check_url"].astype(str).str.strip().ne("")
        & recall_link_df["official_check_url"].astype(str).str.lower().ne("nan")
    ].copy()

    if not recall_link_df.empty:
        if "recall_start_date" in recall_link_df.columns:
            recall_link_df = recall_link_df.sort_values(
                "recall_start_date",
                ascending=False,
                na_position="last",
            )

        official_recall_url = str(
            recall_link_df.iloc[0]["official_check_url"]
        ).strip()

# ------------------------------------------------------------
# FAQ 검색
# ------------------------------------------------------------

with st.container(key="faq_search_row"):
    search_cols = st.columns(
        [5.6, 1],
        gap="small",
        vertical_alignment="center",
    )

    with search_cols[0]:
        keyword = st.text_input(
            "검색어",
            placeholder="리콜 / 보상 / 결함조사 등",
            label_visibility="collapsed",
        )

    with search_cols[1]:
        st.button(
            "검색",
            use_container_width=True,
        )

# 검색어가 있으면 질문/답변 기준으로 검색하고,
# 검색어가 없으면 전체 FAQ를 표시합니다.
results = search_faq(faq_df, keyword) if keyword else faq_df.copy()

# ------------------------------------------------------------
# FAQ 검색 결과
# ------------------------------------------------------------

# 검색어가 있지만 일치하는 FAQ가 없는 경우
if keyword and results.empty:
    st.warning(
        "검색어와 일치하는 FAQ가 없습니다."
    )

    # 서비스 내부 검색 결과가 없더라도 공식 FAQ 전체 페이지로 이동할 수 있게 합니다.
    st.link_button(
        "자동차리콜센터 전체 FAQ 보기",
        "https://www.car.go.kr/rs/faq/list.do",
    )

else:
    # 검색 중이면 검색 결과 건수를 표시합니다.
    if keyword:
        st.caption(
            f"검색 결과 {len(results)}건"
        )

    # 검색어가 없으면 전체 FAQ 건수를 표시합니다.
    else:
        st.caption(
            f"자동차리콜센터 공통 FAQ 전체 {len(results)}건"
        )

    # FAQ 전체 건수 문구와 첫 번째 카드 사이 여백은 faq_list의 margin으로 제어합니다.

    with st.container(key="faq_list"):

        for idx, (_, row) in enumerate(results.iterrows()):

            with st.container(key=f"faq_card_{idx}", border=True):
                st.markdown(
                    f"**Q. {row['question']}**"
                )

                st.write(
                    f"A. {row['answer']}"
                )

                link_or_gap(
                    row["source_url"],
                    "자동차리콜센터 FAQ 원문에서 확인",
                )
                st.markdown(
                    f"""
                    <div class="faq-provider">
                        제공기관 {row['provider']}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    
        st.write("")

    # 표시된 FAQ 중 가장 최근 수집시점을 확인합니다.
    latest_collected = (
        results["collected_at"].max()
        if not results.empty
        else None
    )

    # FAQ 출처와 수집일시를 화면 하단에 표시합니다.
    st.caption(
        f"출처 "
        f"{results['source_url'].iloc[0] if not results.empty else '-'}  |  "
        f"수집일시 "
        f"{latest_collected if latest_collected else '정보 없음'}"
    )

st.divider()

# ------------------------------------------------------------
# 공식 외부 링크
# ------------------------------------------------------------

link_cols = st.columns(2)

# D-REC official_check_url 기반 공식 리콜 정보 확인
with link_cols[0]:
    if official_recall_url:
        st.link_button(
            "자동차리콜센터 공식 리콜 정보 확인",
            official_recall_url,
        )
    else:
        st.caption(
            "공식 리콜 확인 URL을 현재 D-REC에서 확인할 수 없습니다."
        )

# 선택된 모델이 있으면 해당 제조사의 공식 고객지원 페이지도 제공합니다.
with link_cols[1]:
    if selected_model_row is not None:
        support_url = selected_model_row.get(
            "manufacturer_support_url"
        )

        if support_url and str(support_url) != "nan":
            st.link_button(
                f"{selected_model_row['manufacturer_std']} 공식 고객지원 이동",
                support_url,
            )

        else:
            st.caption(
                "제조사 공식 고객지원 링크를 확인할 수 없습니다. (ST-10)"
            )
site_footer()
