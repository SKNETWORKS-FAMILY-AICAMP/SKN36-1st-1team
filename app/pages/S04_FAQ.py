
import sys
from pathlib import Path

# app/pages에서 실행할 때 app/lib 모듈을 찾을 수 있도록 경로를 추가합니다.
sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st

# FAQ 화면에서 사용하는 공통 데이터/검색/링크 함수입니다.
from lib.common import (
    load_faq,
    search_faq,
    get_verified_models,
    link_or_gap,
)

# ------------------------------------------------------------
# 페이지 기본 설정
# ------------------------------------------------------------

st.set_page_config(page_title="리콜 FAQ / 공식 안내", page_icon="💬", layout="wide")

# Streamlit 기본 사이드바를 숨깁니다.
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stExpandSidebarButton"] { display: none; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 상단 제목 / Home 버튼
# ------------------------------------------------------------

header_cols = st.columns([5, 1])

with header_cols[0]:
    st.title("💬 리콜 FAQ / 공식 안내")

with header_cols[1]:
    st.write("")
    if st.button("🏠 Home"):
        st.switch_page("app.py")

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

st.divider()

# ------------------------------------------------------------
# FAQ 데이터 로딩
# ------------------------------------------------------------

# 자동차리콜센터 FAQ 데이터를 불러옵니다.
faq_df = load_faq()

# ------------------------------------------------------------
# FAQ 검색
# ------------------------------------------------------------

search_cols = st.columns([5, 1])

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

st.divider()

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

    # FAQ 한 건씩 카드 형태로 표시합니다.
    for _, row in results.iterrows():
        with st.container(border=True):
            st.markdown(
                f"**Q. {row['question']}**"
            )

            st.caption(
                f"제공기관 {row['provider']}"
            )

            st.write(
                f"A. {row['answer']}"
            )

            # 각 FAQ의 공식 원문 URL이 있으면 이동 버튼을 제공합니다.
            link_or_gap(
                row["source_url"],
                "자동차리콜센터 FAQ 원문에서 확인",
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

# 자동차리콜센터 공식 리콜 정보 페이지
with link_cols[0]:
    st.link_button(
        "자동차리콜센터 공식 리콜 정보 확인",
        "https://www.car.go.kr/home/main.do",
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