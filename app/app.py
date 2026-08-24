
import streamlit as st

st.set_page_config(
    page_title="전국 자동차 등록현황 · 모델 안전정보",
    page_icon="🚗",
    layout="wide",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stExpandSidebarButton"] { display: none; }

    .block-container, [data-testid="stAppViewBlockContainer"] {
      padding-top: 3rem !important;
      padding-bottom: 2rem !important;
      max-width: 1200px !important;
      margin-left: auto !important;
      margin-right: auto !important;
    }
    [data-testid="stVerticalBlock"] { gap: 0.6rem; }

    .s00-eyebrow {
      text-align: center; color: #1C59D9; font-weight: 600; font-size: 14px;
      letter-spacing: 0.04em; margin: 0 0 6px 0;
    }
    .s00-hero-title {
      text-align: center; color: #121726; font-weight: 800; font-size: 2.7rem;
      line-height: 1.3 !important; max-width: 760px !important;
      margin: 0 auto 14px auto !important; padding-top: 2px;
    }
    .s00-hero-sub {
      text-align: center; color: #4B5563; font-size: 1.05rem; line-height: 1.6;
      max-width: 640px !important; margin: 0 auto !important;
    }
    div[data-testid="stButton"] button[kind="primary"] {
      border-radius: 12px; padding-top: 0.75rem; padding-bottom: 0.75rem; font-size: 1.05rem;
    }

    .s00-card-link {
      display: block !important; text-decoration: none !important; color: inherit !important;
      cursor: pointer; border: 1px solid #E5E8ED; border-radius: 16px; padding: 24px;
      transition: box-shadow 0.2s ease, transform 0.2s ease, border-color 0.2s ease;
    }
    .s00-card-link:hover {
      box-shadow: 0 8px 20px rgba(17,24,39,0.08); transform: translateY(-2px); border-color: #C7D2E5;
    }
    .s00-card-icon { display: block !important; font-size: 30px; margin-bottom: 6px; text-decoration: none !important; }
    .s00-card-title {
      display: block !important; font-weight: 700; font-size: 1.05rem;
      color: #121726 !important; margin-bottom: 6px; text-decoration: none !important;
    }
    .s00-card-desc {
      display: block !important; color: #4B5563 !important; font-size: 0.9rem;
      line-height: 1.55; text-decoration: none !important;
    }

    .s00-footer { text-align: center; color: #8C949E; font-size: 13px; margin-top: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<p class="s00-eyebrow">전국 자동차 등록현황 · 모델 안전정보 통합 조회</p>', unsafe_allow_html=True)
st.markdown(
    '<h1 class="s00-hero-title">관심 모델의 판매·결함신고·리콜 정보를<br>한 번에 확인하세요</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="s00-hero-sub">차량 모델을 검색하면 국내 판매량, 소비자 결함신고, 공식 리콜 정보를 '
    '한 곳에서 확인할 수 있어요. 전국 자동차 등록현황도 함께 살펴보세요.</p>',
    unsafe_allow_html=True,
)

st.write("")
cta_cols = st.columns([1, 1.1, 1])
with cta_cols[1]:
    if st.button("🔎 모델 검색 시작하기 →", use_container_width=True, type="primary"):
        st.switch_page("pages/S01_모델검색.py")

st.write("")
st.write("")

FEATURES = [
    ("📊", "전국 등록현황", "지역·차종·연료별 전국 자동차 등록현황(시장 전체 규모)을 한눈에 확인해요.", "/S03_등록현황상세"),
    ("💬", "리콜 FAQ / 공식 안내", "자동차리콜센터가 공개한 공통 FAQ와 공식 확인 링크를 제공해요.", "/S04_FAQ"),
]

_gutter, _card = 1, 2
feat_cols = st.columns([_gutter] + [_card] * len(FEATURES) + [_gutter])[1:-1]
for col, (icon, title, desc, target_url) in zip(feat_cols, FEATURES):
    with col:
        st.markdown(
            f'<a href="{target_url}" target="_self" class="s00-card-link">'
            f'<span class="s00-card-icon">{icon}</span>'
            f'<span class="s00-card-title">{title}</span>'
            f'<span class="s00-card-desc">{desc}</span>'
            f'</a>',
            unsafe_allow_html=True,
        )

st.write("")

st.info(
    "지원 범위 안내 — 검증완료된 현대·기아 지원 모델만 조회할 수 있어요. "
    "검토중/제외 상태인 모델은 통합 화면으로 연결되지 않아요.",
    icon="ℹ️",
)

st.write("")

st.markdown(
    '<p class="s00-footer">출처: 국토교통부 통계누리 · 공공데이터포털(data.go.kr) · 자동차리콜센터</p>',
    unsafe_allow_html=True,
)
