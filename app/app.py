import base64
from pathlib import Path

import streamlit as st

from lib.ui import apply_ui, navbar, site_footer


st.set_page_config(
    page_title="REDLINE",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_ui()

ASSET_DIR = Path(__file__).resolve().parent / "assets"


def data_uri(name: str) -> str:
    path = ASSET_DIR / name
    raw = base64.b64encode(path.read_bytes()).decode("ascii")

    ext = path.suffix.lower().lstrip(".")
    mime = "jpeg" if ext in {"jpg", "jpeg"} else ext

    return f"data:image/{mime};base64,{raw}"


# =========================================================
# ASSETS
# =========================================================

logo_uri = data_uri("logo.png")
hero_uri = data_uri("hero_full.jpg")
model_uri = data_uri("service_model.jpg")
map_uri = data_uri("service_map.jpg")
faq_uri = data_uri("service_faq.jpg")


# =========================================================
# NAVBAR
# =========================================================

navbar(logo_uri=logo_uri)


# =========================================================
# HERO IMAGE
# =========================================================

hero_html = (
    f'<section class="home-hero">'
    f'<div class="home-hero-bg" '
    f'style="background-image:url(&quot;{hero_uri}&quot;)"></div>'
    f'<div class="home-hero-shade"></div>'
    f'<div class="home-hero-content">'
    f'<h1>'
    f'차를 고르기 전,<br>'
    f'<span>신호를 확인하세요.</span>'
    f'</h1>'
    f'<p>'
    f'등록현황부터 리콜·결함신고까지, 데이터로 확인하는 현명한 선택'
    f'</p>'
    f'</div>'
    f'</section>'
)

st.markdown(
    hero_html,
    unsafe_allow_html=True,
)

# =========================================================
# HERO INFO RIBBON
# =========================================================

hero_info_html = (
    f'<div class="hero-info-ribbon">'

    # 신뢰할 수 있는 데이터
    f'<div class="hero-info-item">'
    f'<div class="hero-info-icon">◇</div>'
    f'<div>'
    f'<b>신뢰할 수 있는 데이터</b>'
    f'<span>공공데이터 기반 정확한 정보</span>'
    f'</div>'
    f'</div>'

    # 통합 정보
    f'<div class="hero-info-item">'
    f'<div class="hero-info-icon">▥</div>'
    f'<div>'
    f'<b>한눈에 보는 통합 정보</b>'
    f'<span>등록현황, 리콜, 결함신고 통합 제공</span>'
    f'</div>'
    f'</div>'

    # 전국 현황
    f'<div class="hero-info-item">'
    f'<div class="hero-info-icon">◎</div>'
    f'<div>'
    f'<b>전국 단위 현황</b>'
    f'<span>지역별·연도별 상세 통계 제공</span>'
    f'</div>'
    f'</div>'

    # 공식 출처
    f'<div class="hero-info-item">'
    f'<div class="hero-info-icon">ⓘ</div>'
    f'<div>'
    f'<b>공식 출처 기반</b>'
    f'<span>국토교통부, 교통안전공단 등</span>'
    f'</div>'
    f'</div>'

    f'</div>'
)

st.markdown(
    hero_info_html,
    unsafe_allow_html=True,
)


# =========================================================
# SERVICE + DATA NOTICE
# =========================================================

service_html = (
    f'<section id="service" class="home-section">'

    # 제목
    f'<h2>주요 서비스</h2>'
    f'<div class="section-underline"></div>'

    # 카드 영역
    f'<div class="service-grid">'

    # -----------------------------------------------------
    # 모델 검색
    # -----------------------------------------------------
    f'<a class="service-card" '
    f'href="/S01_model_search" '
    f'target="_self">'

    f'<div class="service-copy">'
    f'<span>모델 검색</span>'
    f'<p>'
    f'선택한 모델의 판매량, 리콜, 결함신고,<br>'
    f'공식 리콜 정보를 한 화면에서 확인할 수 있습니다.'
    f'</p>'
    f'<b>모델 검색 바로가기 &nbsp;→</b>'
    f'</div>'

    f'<div class="service-image model" '
    f'style="background-image:url(&quot;{model_uri}&quot;)">'
    f'</div>'

    f'</a>'

    # -----------------------------------------------------
    # 전국 등록현황
    # -----------------------------------------------------
    f'<a class="service-card" '
    f'href="/S03_registration" '
    f'target="_self">'

    f'<div class="service-copy">'
    f'<span>전국 등록현황</span>'
    f'<p>'
    f'연도별, 지역별, 차종별 등록대수를<br>'
    f'다양한 차트와 표로 확인할 수 있습니다.'
    f'</p>'
    f'<b>등록현황 바로가기 &nbsp;→</b>'
    f'</div>'

    f'<div class="service-image map" '
    f'style="background-image:url(&quot;{map_uri}&quot;)">'
    f'</div>'

    f'</a>'

    # -----------------------------------------------------
    # FAQ
    # -----------------------------------------------------
    f'<a class="service-card" '
    f'href="/S04_FAQ" '
    f'target="_self">'

    f'<div class="service-copy">'
    f'<span>FAQ / 공식 안내</span>'
    f'<p>'
    f'리콜 절차, 데이터 출처 등<br>'
    f'궁금한 내용을 빠르게 찾아보세요.'
    f'</p>'
    f'<b>FAQ 바로가기 &nbsp;→</b>'
    f'</div>'

    f'<div class="service-image faq" '
    f'style="background-image:url(&quot;{faq_uri}&quot;)">'
    f'</div>'

    f'</a>'

    # service-grid 종료
    f'</div>'

    # =====================================================
    # DATA NOTICE
    # =====================================================

    f'<section id="data-guide" class="data-notice">'

    f'<div class="notice-icon">!</div>'

    f'<div class="notice-body">'

    f'<h3>데이터 이용 시 주의사항</h3>'

    f'<div class="notice-items">'

    f'<span>'
    f'• 2023년 결함신고 데이터는 미확보 상태입니다.'
    f'</span>'

    f'<span>'
    f'• 판매량 공란은 0이 아니며, 미제공된 값입니다.'
    f'</span>'

    f'<span>'
    f'• 리콜 대상대수는 여러 캠페인에서 중복될 수 있습니다.'
    f'</span>'

    f'<span>'
    f'• 판매량·결함신고·리콜 대상대수·전국 등록대수는 '
    f'기준이 달라 직접 비율로 계산하지 않습니다.'
    f'</span>'

    f'</div>'  # notice-items
    f'</div>'  # notice-body

    f'</section>'  # data-notice

    f'</section>'  # home-section
)

st.markdown(
    service_html,
    unsafe_allow_html=True,
)


# =========================================================
# FOOTER
# =========================================================

site_footer(
    logo_uri=logo_uri
)