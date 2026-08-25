import streamlit as st
import base64
from pathlib import Path

_UI_ASSET_DIR = Path(__file__).resolve().parent.parent / "assets"

def _default_logo_uri():
    path = _UI_ASSET_DIR / "logo.png"
    if not path.exists():
        return None
    raw = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{raw}"

GLOBAL_CSS = r'''
<style>
:root{
  --charcoal:#14171b; --charcoal2:#0e1013; --red:#c8102e; --red2:#a50e27; --red-bright:#e31b2e;
  --ink:#17181c; --muted:#5f6d7d; --line:#dbe2ea; --bg:#f7f9fc; --white:#fff;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body,p,div,label,button,input,textarea{font-family:"Noto Sans KR",Arial,sans-serif!important}

/* Streamlit / BaseWeb 아이콘 폰트 보호
   전역 span 폰트 강제가 Material Symbols 아이콘을
   "sortascending", "more_vert" 같은 글자로 노출시키는 문제 방지 */
span[data-testid="stIconMaterial"],
.material-symbols-rounded,
.material-symbols-outlined{
  font-family:"Material Symbols Rounded","Material Symbols Outlined" !important;
  font-weight:normal !important;
  font-style:normal !important;
  font-size:inherit;
  line-height:1;
  letter-spacing:normal;
  text-transform:none;
  white-space:nowrap;
  word-wrap:normal;
  direction:ltr;
  font-feature-settings:"liga";
  -webkit-font-feature-settings:"liga";
  -webkit-font-smoothing:antialiased;
}
[data-testid="stSidebar"],[data-testid="stExpandSidebarButton"],#MainMenu,footer:not(.auto-footer){display:none!important}
[data-testid="stHeader"]{display:none!important}
[data-testid="stAppViewContainer"]{background:#f7f9fc}
.block-container,[data-testid="stAppViewBlockContainer"]{max-width:100%!important;padding:0 6%!important}
[data-testid="stVerticalBlock"]{gap:0!important}

/* 콘텐츠 폭을 꽉 채우는 배경(내비/히어로/푸터)은 block-container의 6% 여백을
   뚫고 나가 화면 끝까지 이어지도록 함(풀블리드 트릭) — 배경은 전체 폭,
   안쪽 텍스트/버튼은 각 섹션이 자체 padding으로 정렬함 */
.auto-nav,.home-hero,.hero-info-ribbon,.home-section,.auto-footer{width:100vw;position:relative;left:50%;right:50%;margin-left:-50vw;margin-right:-50vw}

/* NAV */
/* =========================================================
    NAV - BLACK → RED GRADIENT
   ========================================================= */

.auto-nav{
    height: 70px;

    background:
        linear-gradient(
            110deg,
            #111216 0%,
            #2a0f14 15%,
            #7f1722 42%,
            #b32635 100%
        );

    display: grid;
    grid-template-columns: 220px 1fr 220px;
    align-items: center;

    padding: 0 38px;

    border-bottom: 1px solid rgba(255,255,255,0.08);

    box-shadow:
        0 5px 18px rgba(0,0,0,0.18);

    position: relative;
    z-index: 1000;
}


/* 로고 */
.auto-brand{
    display: flex;
    align-items: center;
    justify-content: flex-start;
    text-decoration: none !important;
}

.auto-brand img{
    width: 180px;
    height: auto;
    display: block;
}


/* 메뉴 영역 */
.auto-nav-links{
    display: flex;
    align-items: center;
    justify-content: center;

    /* 메뉴 사이 간격 */
    gap: 120px;

    height: 100%;

    /* 중요: 강제 이동 제거 */
    transform: none;
}


/* 메뉴 글씨 */
.auto-nav-links a{
    color: rgba(255,255,255,0.92) !important;
    text-decoration: none !important;

    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.02em;

    white-space: nowrap;

    padding: 10px 16px;
    border-radius: 8px;

    transition:
        color 0.2s ease,
        background 0.2s ease,
        transform 0.2s ease;
}


/* hover */
.auto-nav-links a:hover{
    color: #ffffff !important;
    background: rgba(255,255,255,0.10);
    transform: translateY(-1px);
}

.auto-nav-links a::after{
    display: none !important;
}


/* RESPONSIVE */
@media (max-width: 1100px){

    .auto-nav{
        grid-template-columns: 190px 1fr;
        padding: 0 28px;
    }

    .auto-brand img{
        width: 165px;
    }

    .auto-nav-links{
        gap: 55px;
        transform: none;
    }

    .auto-nav-links a{
        font-size: 16px;
        padding: 9px 13px;
    }
}

/* HERO */
.home-hero{height:580px;position:relative;overflow:visible;background:#14171b}
.home-hero-bg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    background-size: cover;
    background-position: center center;
    background-repeat: no-repeat;
}
 .home-hero-shade{
    position:absolute;
    inset:0;
    z-index:1;
    background:
        linear-gradient(90deg,
            rgba(5,7,10,.78) 0%,
            rgba(5,7,10,.62) 27%,
            rgba(5,7,10,.28) 52%,
            rgba(5,7,10,.08) 78%,
            rgba(5,7,10,.04) 100%),
        linear-gradient(180deg,
            rgba(5,7,10,.08) 0%,
            rgba(5,7,10,.08) 58%,
            rgba(5,7,10,.26) 100%);
}

.home-hero-content{
    position:absolute;
    inset:0;
    z-index:2;
    display:flex;
    flex-direction:column;
    justify-content:center;
    align-items:flex-start;
    width:100%;
    padding:0 6%;
}

.home-hero-content h1{
    margin:0;
    max-width:780px;
    color:#d65356;
    font-size:42px;
    line-height:1.15;
    letter-spacing:-.055em;
    font-weight:900;
    text-shadow:0 3px 14px rgba(0,0,0,.34);
}

.home-hero-content h1 span{
    display:inline-block;
    margin-top:14px;
    color:#d65356;
}

.home-hero-content p{
    margin:0;
    max-width:680px;
    color:rgba(255,255,255,.88);
    font-size:16px;
    line-height:2;
    font-weight:500;
    letter-spacing:-.02em;
    text-shadow:0 2px 10px rgba(0,0,0,.28);
}

.hero-info-ribbon{
    /* 사진 아래에서 문서 흐름대로 배치 */
    position:relative!important;
    top:auto!important;
    bottom:auto!important;
    transform:none!important;

    /* 4개 항목을 정확히 같은 폭으로 4등분 */
    display:grid;
    grid-template-columns:repeat(4, minmax(0, 1fr));
    align-items:center;

    margin-top:0!important;
    margin-bottom:0!important;

    /* 전체 그룹을 화면 중앙에 보이도록 좌우 여백 동일 */
    padding:18px 7%;

    background:#17191c;
    border:none;
    border-radius:0;
    box-sizing:border-box;

    z-index:2;
}

.hero-info-item{
    display:flex;
    align-items:center;

    /* 각 1/4 영역 내부에서 아이콘+텍스트 묶음을 중앙 정렬 */
    justify-content:center;

    gap:18px;
    min-width:0;
    padding:0 20px;

    border-right:1px solid rgba(255,255,255,.10);
}

/* 텍스트 영역 폭을 동일하게 맞춰 시각적으로도 균형 있게 */
.hero-info-item > div:last-child{
    width:220px;
    min-width:0;
}
.hero-info-item:last-child {
    border-right: none;
}
.hero-info-icon {
    flex-shrink: 0;
    font-size: 30px;
    color: #D83232;
}
.hero-info-item b {
    display: block;
    color: #FFFFFF;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 5px;
}
.hero-info-item span {
    display: block;
    color: #8F9298;
    font-size: 12px;
    white-space: nowrap;
}

/* SERVICES */
.home-section{
    position:relative!important;
    top:auto!important;
    bottom:auto!important;
    transform:none!important;

    margin-top:0!important;
    margin-bottom:0!important;

    padding:48px 5% 42px!important;

    /* 흰색 배경 제거 */
    background:transparent!important;

    z-index:1!important;
    clear:both!important;
    box-sizing:border-box;
}
.home-section h2{font-size:21px;letter-spacing:-.045em;color:#17181c;margin:0;font-weight:900}
.section-underline{width:110px;height:3px;background:#c8102e;margin:8px 0 24px}
.service-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.service-card{height:212px;background:#fff;border:1px solid #e2e2e4;border-radius:11px;text-decoration:none!important;overflow:hidden;position:relative;display:block;transition:.2s ease;box-shadow:0 2px 7px rgba(0,0,0,.03)}
.service-card:hover{transform:translateY(-4px);box-shadow:0 14px 30px rgba(0,0,0,.12);border-color:#d9b9bd}
.service-copy{position:relative;z-index:3;padding:20px 18px;width:64%}
.service-copy span{font-size:18px;font-weight:900;color:#c8102e}
.service-copy h3{font-size:18px;line-height:1.25;color:#17181c;margin:8px 0 8px;font-weight:900;letter-spacing:-.04em}
.service-copy p{margin:12px 0 18px;font-size:12px;line-height:1.65;color:#6a7786;white-space:nowrap}
.service-copy b{font-size:14px;color:#c8102e;font-weight:900}
.service-image{position:absolute;right:0;bottom:0;top:0;width:49%;background-size:cover;background-position:center;transition:.24s ease}
.service-card:hover .service-image{transform:scale(1.025)}
.service-image:before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,#fff 0%,rgba(255,255,255,.8) 18%,rgba(255,255,255,.02) 56%)}
.service-image.model{background-position:center}.service-image.map{background-position:center}.service-image.faq{background-position:center}

/* NOTICE */
.data-notice{
    width:100% !important;
    margin:18px 0 0 !important;

    background:#FDEEEE !important;
    border:1px solid #F0C4C4 !important;
    border-radius:8px !important;

    min-height:58px !important;
    padding:12px 16px !important;

    display:flex !important;
    align-items:center !important;
    gap:14px !important;

    box-sizing:border-box !important;
}

.notice-icon{
    width:32px !important;
    height:32px !important;

    border:2px solid #C8102E !important;
    border-radius:50% !important;

    display:flex !important;
    align-items:center !important;
    justify-content:center !important;

    color:#C8102E !important;
    font-size:18px !important;
    font-weight:900 !important;

    flex:none !important;
}

.notice-body{
    flex:1 !important;
    min-width:0 !important;
}

.notice-body h3{
    color:#C8102E !important;
    font-size:13px !important;
    font-weight:900 !important;

    margin:0 0 7px !important;
}

.notice-items{
    display:flex !important;
    align-items:center !important;
    gap:30px !important;
    flex-wrap:wrap !important;

    color:#6B5A5C !important;
    font-size:10.5px !important;
    line-height:1.4 !important;
    
    transform:translateY(-15px);  /* ← 이거 추가 */
}
/* FOOTER */
.auto-footer{background:linear-gradient(90deg,#14171b,#0e1013);color:#c7cad0;min-height:106px;padding:17px 3.2%;display:grid;grid-template-columns:1.3fr 1.3fr 1.3fr 1.2fr 2fr .35fr;align-items:center;gap:28px}
.footer-logo img{width:165px;height:auto;opacity:.98}
.footer-col b{display:block;color:#fff;font-size:12px;margin-bottom:10px}.footer-col span{font-size:10px;color:#9ba1a8;line-height:1.7}
.footer-copy{text-align:right;font-size:10px;color:#8b9198;white-space:nowrap}.footer-top{width:38px;height:38px;border:1px solid rgba(255,255,255,.25);border-radius:7px;color:#fff!important;text-decoration:none!important;display:flex;align-items:center;justify-content:center;font-size:20px}

/* shared widgets/pages */
.ai-pagehead{
    position:relative;
    padding:46px 0 28px;
    background:transparent;
    border-bottom:none;
}
.ai-pagehead::after{
    content:"";
    position:absolute;
    left:0;
    right:0;
    bottom:18px;
    height:1px;
    background:#e6e6e8;
}
.ai-title{font-size:38px;font-weight:900;color:#17181c}
.ai-sub{margin-top:10px;color:#667788;font-size:14px}
.ai-eyebrow,.ai-kicker{display:inline-block;color:#c8102e;font-size:10px;font-weight:900;letter-spacing:.1em;margin-bottom:10px}
.ai-section-label{font-size:10px;color:#c8102e;font-weight:900;letter-spacing:.1em}
.ai-section-title{font-size:26px;font-weight:900;color:#17181c;margin-top:6px}
.ai-section-sub{font-size:13px;color:#667788;margin-top:6px}
.ai-footer{display:none}

/* 카드형 섹션(STEP 라벨 + 제목, S01/S02에서 사용) */
.ai-badge{display:inline-block;color:#c8102e;font-size:10px;font-weight:900;letter-spacing:.12em;text-transform:uppercase}
.ai-card{background:#fff;border:1px solid #e5e5e7;border-radius:12px;padding:26px 28px;margin:28px 0 16px;box-shadow:0 2px 7px rgba(0,0,0,.03)}
.ai-card h3{margin:8px 0 0;font-size:19px;font-weight:900;color:#17181c;letter-spacing:-.02em}

/* 안내/콜아웃 박스 (선택 후보 등, S01/S02에서 사용) */
.ai-notice{border:1px solid #e5e5e7;background:#f7f7f8;border-radius:10px;padding:16px 20px;margin:14px 0 24px}
.ai-notice .ai-badge{margin-bottom:6px}
.ai-notice p{margin:2px 0 0;color:#4b4142;font-size:13.5px;line-height:1.6}

/* 선택 모델 배너 (S02 상단) */
.ai-model-banner{background:linear-gradient(120deg,#14171b,#1f2328);border-radius:14px;padding:26px 30px;margin:22px 0 8px}
.ai-model-banner .ai-badge{color:#ff8b90}
.ai-model-banner h2{margin:10px 0 6px;font-size:25px;font-weight:900;color:#fff;letter-spacing:-.02em}
.ai-model-banner p{margin:0;color:#c3d1e6;font-size:13px}

[data-testid="stMetric"]{background:#fff;border:1px solid #e5e5e7;border-radius:10px!important;padding:20px}
[data-testid="stMetricValue"]{color:#17181c!important;font-weight:900!important}
[data-testid="stMetricLabel"]{color:#5f6d7d!important;font-weight:700!important}
.stButton>button,.stLinkButton>a,.stDownloadButton>button{border-radius:7px!important;min-height:46px!important;font-weight:800!important;border-color:#d6d0d1!important;color:#2a2426!important}
.stButton>button[kind="primary"]{background:#c8102e!important;border-color:#c8102e!important;color:#fff!important}
.stButton>button[kind="primary"]:hover{background:#a50e27!important;border-color:#a50e27!important}
.stButton>button:not([kind="primary"]):hover,.stLinkButton>a:hover{border-color:#c8102e!important;color:#c8102e!important}
[data-baseweb="select"]>div,.stTextInput input{border-radius:7px!important;min-height:48px;background:#fff!important;border-color:#e2e2e4!important}
[data-testid="stDataFrame"]{border:1px solid #e5e5e7;border-radius:8px;overflow:hidden;background:#fff}
[data-testid="stExpander"]{background:#fff;border:1px solid #e5e5e7!important;border-radius:10px!important;overflow:hidden;margin-bottom:10px!important}
[data-testid="stExpander"] summary{font-weight:700!important;color:#17181c!important}
[data-testid="stTabs"] [data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid #e5e5e7}
[data-testid="stTabs"] [data-baseweb="tab"]{height:44px;font-weight:800!important;color:#5f6d7d!important}
[data-testid="stTabs"] [aria-selected="true"]{color:#c8102e!important}
[data-testid="stTabs"] [data-baseweb="tab-highlight"]{background-color:#c8102e!important}
div[data-testid="stAlert"]{border-radius:10px!important}
hr{border-color:#e6e6e8!important;margin:28px 0!important}

@media(max-width:1000px){
 .auto-nav{gap:16px;padding:0 16px}.auto-brand{min-width:190px}.auto-brand img{width:140px}.auto-nav-links{gap:20px}.auto-nav-links a{font-size:14px}.auto-favorite{display:none}
 .home-hero-content{padding:0 5%}.home-hero-content h1{font-size:38px}.home-hero-content p{font-size:14px}.hero-info-ribbon{padding:12px 4%}.hero-info-item{padding:4px 9px;gap:10px}.hero-info-item span{white-space:normal}
 .service-grid{grid-template-columns:1fr}.service-card{height:220px}.notice-items{gap:10px}.auto-footer{grid-template-columns:1fr 1fr 1fr}.footer-copy{text-align:left}
}
</style>
'''

def apply_ui():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

def navbar(active="", logo_uri=None):
    logo_uri = logo_uri or _default_logo_uri()
    logo_html = f'<img src="{logo_uri}" alt="REDLINE">' if logo_uri else '<span style="font-weight:900;color:white;font-size:22px">REDLINE</span>'
    st.markdown(f'''
    <nav class="auto-nav" id="top">
      <a class="auto-brand" href="/" target="_self" aria-label="AUTO INSIGHT 홈">{logo_html}</a>
      <div class="auto-nav-links">
        <a href="/S01_model_search" target="_self">모델 검색</a>
        <a href="/S03_registration" target="_self">등록현황</a>
        <a href="/S04_FAQ" target="_self">FAQ / 공식 안내</a>
      </div>
    </nav>
    ''', unsafe_allow_html=True)

def page_intro(title, subtitle, badge=None):
    badge_html = f'<span class="ai-eyebrow">{badge}</span>' if badge else '<span class="ai-kicker">MODEL SEARCH</span>'
    st.markdown(f'<div class="ai-pagehead"><div>{badge_html}</div><div class="ai-title">{title}</div><div class="ai-sub">{subtitle}</div></div>', unsafe_allow_html=True)

def section_header(title, subtitle="", label="INSIGHT"):
    sub_html = f'<div class="ai-section-sub">{subtitle}</div>' if subtitle else ''
    st.markdown(f'<div style="margin:34px 0 16px"><div class="ai-section-label">{label}</div><div class="ai-section-title">{title}</div>{sub_html}</div>', unsafe_allow_html=True)

def site_footer(logo_uri=None):
    logo_uri = logo_uri or _default_logo_uri()
    logo_html = f'<img src="{logo_uri}" alt="REDLINE">' if logo_uri else '<strong>REDLINE</strong>'
    st.markdown(f'''
    <footer class="auto-footer">
      <a class="footer-logo" href="/" target="_self">{logo_html}</a>
      <div class="footer-col"><b>데이터 출처</b><span>국토교통부 &nbsp; | &nbsp; 한국교통안전공단</span></div>
      <div class="footer-col"><b>서비스 정보</b><span>이용약관 &nbsp; | &nbsp; 개인정보처리방침</span></div>
      <div class="footer-col"><b>문의</b><span>auto.insight@kotsa.or.kr</span></div>
      <div class="footer-copy">© 2026 REDLINE. All rights reserved.</div>
      <a class="footer-top" href="#top">↑</a>
    </footer>
    ''', unsafe_allow_html=True)