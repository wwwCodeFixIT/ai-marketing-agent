"""
AI Marketing Agent SaaS - Główna aplikacja Streamlit
- Campaign Builder
- Studio Graficzne
- Brand DNA Manager
- Feedback System
"""

import streamlit as st
import os
import io
import time
import base64
import html
import zipfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

from core.memory_system import BrandMemory, FeedbackManager, PostsHistory
from core.prompt_builder import Platform, ContentGoal, ContentStyle
from core.model_router import ModelRouter
from core.agent_engine import AgentEngine, AgentResult

from graphics.card_generator import GraphicsEngine, GraphicCard
from graphics.templates import (
    VISUAL_TEMPLATES, 
    PALETTES, 
    AspectRatio,
    list_templates,
    list_palettes
)

# Konfiguracja
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === KONFIGURACJA STRONY ===
st.set_page_config(
    page_title="AI Marketing Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === STYLE CSS ===
st.markdown("""
<style>
    /* Główne style */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #3B82F6, #8B5CF6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        color: #94A3B8;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Karty */
    .content-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* Agent logs */
    .agent-log {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 0.85rem;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 6px;
        background: #0F172A;
        border-left: 3px solid #3B82F6;
    }
    
    .agent-log.success { border-left-color: #22C55E; }
    .agent-log.warning { border-left-color: #F59E0B; }
    .agent-log.error { border-left-color: #EF4444; }
    
    /* Przyciski */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        font-weight: 600;
        font-size: 1rem;
    }
    
    /* Metrics */
    .metric-card {
        background: linear-gradient(135deg, #1E293B, #0F172A);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #3B82F6;
    }
    
    .metric-label {
        font-size: 0.85rem;
        color: #94A3B8;
    }
    
    /* Preview card */
    .preview-card {
        background: #1E1E1E;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 1.5rem;
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .preview-header {
        display: flex;
        align-items: center;
        margin-bottom: 1rem;
    }
    
    .preview-avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3B82F6, #8B5CF6);
        margin-right: 12px;
    }
    
    .preview-name {
        font-weight: 600;
        color: #fff;
    }
    
    .preview-meta {
        font-size: 0.85rem;
        color: #888;
    }
    
    .preview-content {
        color: #E5E5E5;
        line-height: 1.6;
        white-space: pre-wrap;
    }
    
    /* Tabs customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# === INICJALIZACJA SESSION STATE ===
def init_session_state():
    """Inicjalizuje stan sesji"""
    
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        st.session_state.brand_memory = BrandMemory()
        st.session_state.feedback_manager = FeedbackManager()
        st.session_state.posts_history = PostsHistory()
        st.session_state.campaign_results = {}
        st.session_state.current_graphics = {}
        st.session_state.generation_count = 0
        logger.info("Session state initialized")


# === HELPER FUNCTIONS ===

def check_api_key() -> bool:
    """Sprawdza czy klucz API jest dostępny"""
    return bool(os.environ.get("GROQ_API_KEY"))


def get_engine() -> AgentEngine:
    """Tworzy lub zwraca AgentEngine"""
    if "agent_engine" not in st.session_state:
        router = ModelRouter()
        st.session_state.agent_engine = AgentEngine(
            router=router,
            brand_memory=st.session_state.brand_memory,
            feedback_manager=st.session_state.feedback_manager,
            posts_history=st.session_state.posts_history
        )
    return st.session_state.agent_engine


def get_graphics_engine() -> GraphicsEngine:
    """Tworzy lub zwraca GraphicsEngine"""
    if "graphics_engine" not in st.session_state:
        st.session_state.graphics_engine = GraphicsEngine()
    return st.session_state.graphics_engine


def img_to_base64(img) -> str:
    """Konwertuje PIL Image do base64"""
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


def render_post_preview(content: str, platform: str, author: str = "Your Name"):
    """Renderuje podgląd posta"""
    
    # Formatuj content
    formatted_content = content.replace('\n', '<br>')
    
    # Ikona platformy
    platform_icons = {
        "LinkedIn": "💼",
        "Twitter": "🐦",
        "Facebook": "📘",
        "Instagram": "📸",
        "Threads": "🧵"
    }
    icon = platform_icons.get(platform, "📝")
    
    st.markdown(f"""
    <div class="preview-card">
        <div class="preview-header">
            <div class="preview-avatar"></div>
            <div>
                <div class="preview-name">{author}</div>
                <div class="preview-meta">{icon} {platform} • Just now</div>
            </div>
        </div>
        <div class="preview-content">{formatted_content}</div>
    </div>
    """, unsafe_allow_html=True)


def render_agent_logs(logs: List[str]):
    """Renderuje logi agenta"""
    for log in logs:
        # Określ typ logu
        log_class = "agent-log"
        if "✅" in log or "success" in log.lower():
            log_class += " success"
        elif "⚠️" in log or "warning" in log.lower():
            log_class += " warning"
        elif "❌" in log or "error" in log.lower():
            log_class += " error"
        
        st.markdown(f'<div class="{log_class}">{log}</div>', unsafe_allow_html=True)


def render_metric_card(value: str, label: str):
    """Renderuje kartę z metryką"""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


# === KOMPONENTY UI ===

def render_sidebar():
    """Renderuje sidebar"""
    
    with st.sidebar:
        st.markdown("## 🧠 AI Marketing Agent")
        st.markdown("---")
        
        # Status API
        if check_api_key():
            st.success("✅ API Key aktywny", icon="🔑")
        else:
            st.error("❌ Brak API Key", icon="🔑")
            st.info("Dodaj GROQ_API_KEY do pliku .env")
            return False
        
        st.markdown("---")
        
        # Quick Stats
        st.markdown("### 📊 Statystyki")
        
        col1, col2 = st.columns(2)
        with col1:
            posts_count = st.session_state.posts_history.count()
            st.metric("Posty", posts_count)
        
        with col2:
            feedback_stats = st.session_state.feedback_manager.get_stats()
            st.metric("Feedback", feedback_stats.get("total_positive", 0))
        
        st.markdown("---")
        
        # Brand DNA Quick View
        st.markdown("### 🧬 Brand DNA")
        dna = st.session_state.brand_memory.dna
        
        st.caption(f"**Marka:** {dna.get('brand_name', 'Nie ustawiono')}")
        st.caption(f"**Ton:** {dna.get('tone_of_voice', 'Nie ustawiono')[:30]}...")
        
        if st.button("⚙️ Konfiguruj Brand DNA", use_container_width=True):
            st.session_state.active_tab = 2  # Przełącz na ustawienia
        
        st.markdown("---")
        
        # Recent Activity
        st.markdown("### 📝 Ostatnia aktywność")
        recent = st.session_state.posts_history.get_recent(3)
        
        if recent:
            for post in reversed(recent):
                platform = post.get("platform", "Unknown")
                created = post.get("created_at", "")[:10]
                st.caption(f"• {platform} - {created}")
        else:
            st.caption("Brak wygenerowanych postów")
        
        return True


def render_campaign_tab():
    """Renderuje zakładkę Campaign Builder"""
    
    st.markdown('<h2>📢 Campaign Builder</h2>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Generuj profesjonalne treści z wieloetapowym agentem AI</p>', unsafe_allow_html=True)
    
    # Inicjalizacja
    if "topic_value" not in st.session_state:
        st.session_state.topic_value = ""
    if "preview_modal_open" not in st.session_state:
        st.session_state.preview_modal_open = False
    if "preview_modal_platform" not in st.session_state:
        st.session_state.preview_modal_platform = ""
    if "preview_modal_content" not in st.session_state:
        st.session_state.preview_modal_content = ""
    
    # === INPUT SECTION ===
    col_input, col_settings = st.columns([2, 1])
    
    with col_input:
        st.markdown("#### 💡 Twój pomysł")
        
        topic = st.text_area(
            "Temat / Pomysł / Notatka",
            value=st.session_state.topic_value,
            height=120,
            placeholder="np. Dlaczego code review to nie krytyka, a inwestycja w zespół...",
            key="topic_input"
        )
        
        # Quick prompts
        st.markdown("##### ⚡ Szybkie starty")
        qc = st.columns(4)
        
        prompts = [
            ("💡 Lekcja", "Najważniejsza lekcja z mojego ostatniego projektu"),
            ("🔥 Hot Take", "Kontrowersyjna opinia o AI w programowaniu"),
            ("📊 Statystyka", "73% deweloperów używa AI - co to oznacza?"),
            ("🎯 Poradnik", "5 kroków do lepszego code review")
        ]
        
        for i, (label, prompt) in enumerate(prompts):
            with qc[i]:
                if st.button(label, key=f"quick_{i}", use_container_width=True):
                    st.session_state.topic_value = prompt
                    st.rerun()
    
    with col_settings:
        st.markdown("#### ⚙️ Ustawienia")
        
        platforms = st.multiselect(
            "Platformy",
            ["LinkedIn", "Twitter", "Facebook", "Instagram"],
            default=["LinkedIn"]
        )
        
        goals = {
            "🎯 Zaangażowanie": ContentGoal.ENGAGEMENT,
            "👑 Autorytet": ContentGoal.AUTHORITY,
            "🚀 Viralowy": ContentGoal.VIRAL,
            "📚 Edukacyjny": ContentGoal.EDUCATION
        }
        goal_name = st.selectbox("Cel treści", list(goals.keys()))
        goal = goals[goal_name]
        
        styles = {
            "💼 Profesjonalny": ContentStyle.PROFESSIONAL,
            "😊 Casual": ContentStyle.CASUAL,
            "🔥 Kontrowersyjny": ContentStyle.CONTROVERSIAL,
            "🧠 Analityczny": ContentStyle.ANALYTICAL
        }
        style_name = st.selectbox("Styl", list(styles.keys()))
        style = styles[style_name]
        
        mode = st.radio("Tryb", ["🚀 Pełny Pipeline", "⚡ Szybki"], horizontal=True)
        use_full = "Pełny" in mode
    
    st.markdown("---")
    
    # Generate button
    current_topic = topic if topic else st.session_state.topic_value
    
    col_btn, _ = st.columns([1, 2])
    with col_btn:
        generate_btn = st.button(
            "🚀 Generuj Kampanię",
            type="primary",
            use_container_width=True,
            disabled=not current_topic or not platforms
        )
    
    # === GENERATION ===
    if generate_btn and current_topic and platforms:
        engine = get_engine()
        st.session_state.campaign_results = {}
        
        with st.status("🧠 Agent pracuje...", expanded=True) as status:
            for platform_name in platforms:
                platform = Platform[platform_name.upper()]
                st.write(f"**{platform_name}**: Generuję...")
                
                if use_full:
                    result = engine.run_pipeline(current_topic, platform, goal, style)
                else:
                    result = engine.run_quick(current_topic, platform, style)
                
                st.session_state.campaign_results[platform_name] = result
                
                for log in result.get_logs_formatted()[-2:]:
                    st.write(f"  {log}")
                
                time.sleep(0.2)
            
            status.update(label="✅ Gotowe!", state="complete", expanded=False)
        
        st.session_state.generation_count += 1
        st.rerun()
    
    # === RESULTS ===
    if st.session_state.get("campaign_results"):
        st.markdown("---")
        st.markdown("### 📄 Wygenerowane treści")
        
        for platform_name, result in st.session_state.campaign_results.items():
            render_post_result_card(platform_name, result, current_topic)
    
    # === MODAL - wywoływany tylko raz, kontrolowany przez session state ===
    if st.session_state.get("preview_modal_open", False):
        show_post_preview_dialog()


def render_post_result_card(platform_name: str, result, topic: str):
    """Renderuje pojedynczy wynik posta jako kartę"""
    
    with st.expander(f"📱 {platform_name}", expanded=True):
        col_content, col_meta = st.columns([2, 1])
        
        with col_content:
            # Edytowalny tekst
            edited = st.text_area(
                "Treść (możesz edytować)",
                value=result.content,
                height=250,
                key=f"content_{platform_name}"
            )
            
            # Zapisz edytowaną treść do session state dla modala
            st.session_state[f"edited_content_{platform_name}"] = edited
            
            # Akcje w jednej linii
            st.markdown("**Akcje:**")
            ac = st.columns(6)
            
            with ac[0]:
                if st.button("👍", key=f"like_{platform_name}", help="Podoba mi się"):
                    st.session_state.feedback_manager.add_positive(edited, platform_name)
                    st.toast("✅ Zapisano!", icon="💾")
            
            with ac[1]:
                if st.button("👎", key=f"dislike_{platform_name}", help="Nie podoba mi się"):
                    st.session_state.feedback_manager.add_negative(edited, platform_name, "disliked")
                    st.toast("Zapisano", icon="📝")
            
            with ac[2]:
                if st.button("📋", key=f"copy_{platform_name}", help="Kopiuj"):
                    st.code(edited, language=None)
            
            with ac[3]:
                if st.button("🔄", key=f"regen_{platform_name}", help="Regeneruj"):
                    with st.spinner("..."):
                        engine = get_engine()
                        platform = Platform[platform_name.upper()]
                        new_result = engine.run_quick(topic, platform)
                        st.session_state.campaign_results[platform_name] = new_result
                        st.rerun()
            
            with ac[4]:
                if st.button("🎨", key=f"gfx_{platform_name}", help="Grafika"):
                    first_line = edited.split('\n')[0][:50]
                    st.session_state.graphic_headline = first_line
                    st.toast("Przejdź do Studio Graficzne", icon="🎨")
            
            with ac[5]:
                # Przycisk otwierający modal
                if st.button("👁️", key=f"preview_{platform_name}", help="Podgląd"):
                    st.session_state.preview_modal_open = True
                    st.session_state.preview_modal_platform = platform_name
                    st.session_state.preview_modal_content = edited
                    st.rerun()
        
        with col_meta:
            st.markdown("##### 🧠 Proces agenta")
            
            if result.state:
                st.caption(f"⏱️ {result.state.total_duration_ms}ms")
                st.caption(f"🔄 {result.state.iterations} iteracji")
                st.caption(f"📊 Ocena: {result.state.critique_score}/10")
                st.caption(f"🛡️ Brand: {'✅' if result.state.brand_approved else '⚠️'}")
            
            st.markdown("---")
            
            with st.container(height=150):
                for log in result.get_logs_formatted():
                    st.caption(log)


@st.dialog("👁️ Podgląd posta", width="large")
def show_post_preview_dialog():
    """Dialog z podglądem posta - jeden dla całej aplikacji"""
    
    platform_name = st.session_state.get("preview_modal_platform", "LinkedIn")
    content = st.session_state.get("preview_modal_content", "")
    author = st.session_state.brand_memory.dna.get("brand_name", "Your Name")
    
    # Nagłówek z platformą
    st.markdown(f"### 📱 {platform_name}")
    
    # Podgląd w stylu platformy
    render_platform_preview(platform_name, content, author)
    
    # Licznik znaków
    char_count = len(content)
    if platform_name == "Twitter" and char_count > 280:
        st.error(f"⚠️ {char_count}/280 znaków - przekroczono limit Twittera!")
    elif platform_name == "Twitter":
        st.success(f"✅ {char_count}/280 znaków")
    else:
        st.caption(f"📝 {char_count} znaków")
    
    st.markdown("---")
    
    # Akcje
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Kopiuj treść", use_container_width=True):
            st.code(content, language=None)
            st.toast("Skopiuj tekst powyżej", icon="📋")
    
    with col2:
        if st.button("🎨 Stwórz grafikę", use_container_width=True):
            first_line = content.split('\n')[0][:50]
            st.session_state.graphic_headline = first_line
            st.session_state.preview_modal_open = False
            st.toast("Przejdź do zakładki Studio Graficzne", icon="🎨")
            st.rerun()
    
    with col3:
        if st.button("✕ Zamknij", use_container_width=True, type="primary"):
            st.session_state.preview_modal_open = False
            st.rerun()


def render_platform_preview(platform: str, content: str, author: str):
    """Renderuje podgląd w stylu platformy"""
    
    # Escape HTML
    safe_content = html.escape(content).replace('\n', '<br>')
    initials = author[0].upper() if author else "U"
    
    if platform == "LinkedIn":
        st.markdown(f"""
        <div style="
            background: #1b1f23;
            border-radius: 12px;
            border: 1px solid #333;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            overflow: hidden;
            margin: 10px 0;
        ">
            <div style="display: flex; align-items: center; padding: 16px; gap: 12px;">
                <div style="
                    width: 48px; height: 48px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #0077b5, #00a0dc);
                    display: flex; align-items: center; justify-content: center;
                    font-size: 20px; font-weight: bold; color: white;
                ">{initials}</div>
                <div>
                    <div style="color: #fff; font-weight: 600; font-size: 14px;">{author}</div>
                    <div style="color: rgba(255,255,255,0.6); font-size: 12px;">Teraz • 🌐</div>
                </div>
            </div>
            <div style="
                padding: 0 16px 16px 16px;
                color: #fff;
                font-size: 14px;
                line-height: 1.6;
                max-height: 300px;
                overflow-y: auto;
            ">{safe_content}</div>
            <div style="
                display: flex;
                justify-content: space-around;
                padding: 12px 16px;
                border-top: 1px solid #333;
                color: rgba(255,255,255,0.7);
                font-size: 13px;
            ">
                <span>👍 Lubię to</span>
                <span>💬 Komentarz</span>
                <span>🔄 Udostępnij</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    elif platform == "Twitter":
        st.markdown(f"""
        <div style="
            background: #15202b;
            border-radius: 12px;
            border: 1px solid #333;
            padding: 16px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            margin: 10px 0;
        ">
            <div style="display: flex; gap: 12px;">
                <div style="
                    width: 48px; height: 48px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #1da1f2, #0d8bd9);
                    display: flex; align-items: center; justify-content: center;
                    font-size: 20px; font-weight: bold; color: white;
                    flex-shrink: 0;
                ">{initials}</div>
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <span style="color: #fff; font-weight: 700;">{author}</span>
                        <span style="color: #8899a6;">@{author.lower().replace(' ', '_')} · teraz</span>
                    </div>
                    <div style="color: #fff; font-size: 15px; line-height: 1.5;">{safe_content}</div>
                    <div style="
                        display: flex;
                        gap: 40px;
                        margin-top: 12px;
                        color: #8899a6;
                        font-size: 13px;
                    ">
                        <span>💬 0</span>
                        <span>🔄 0</span>
                        <span>❤️ 0</span>
                        <span>📊 0</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    elif platform == "Facebook":
        st.markdown(f"""
        <div style="
            background: #242526;
            border-radius: 12px;
            border: 1px solid #333;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            overflow: hidden;
            margin: 10px 0;
        ">
            <div style="display: flex; align-items: center; padding: 12px 16px; gap: 10px;">
                <div style="
                    width: 40px; height: 40px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #1877f2, #42b72a);
                    display: flex; align-items: center; justify-content: center;
                    font-size: 18px; font-weight: bold; color: white;
                ">{initials}</div>
                <div>
                    <div style="color: #e4e6eb; font-weight: 600; font-size: 14px;">{author}</div>
                    <div style="color: #b0b3b8; font-size: 12px;">Teraz · 🌍</div>
                </div>
            </div>
            <div style="
                padding: 0 16px 16px 16px;
                color: #e4e6eb;
                font-size: 15px;
                line-height: 1.5;
                max-height: 300px;
                overflow-y: auto;
            ">{safe_content}</div>
            <div style="
                display: flex;
                justify-content: space-around;
                padding: 8px 16px;
                border-top: 1px solid #3e4042;
                color: #b0b3b8;
                font-size: 14px;
                font-weight: 600;
            ">
                <span>👍 Lubię to</span>
                <span>💬 Komentuj</span>
                <span>📤 Udostępnij</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    elif platform == "Instagram":
        st.markdown(f"""
        <div style="
            background: #000;
            border-radius: 12px;
            border: 1px solid #333;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            overflow: hidden;
            margin: 10px 0;
        ">
            <div style="display: flex; align-items: center; padding: 14px 16px; gap: 10px;">
                <div style="
                    width: 32px; height: 32px;
                    border-radius: 50%;
                    background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
                    display: flex; align-items: center; justify-content: center;
                    font-size: 14px; font-weight: bold; color: white;
                ">{initials}</div>
                <span style="color: #fff; font-weight: 600; font-size: 14px; flex: 1;">
                    {author.lower().replace(' ', '_')}
                </span>
            </div>
            <div style="
                background: linear-gradient(45deg, #405DE6, #5851DB, #833AB4, #C13584, #E1306C);
                height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <span style="font-size: 48px;">📸</span>
            </div>
            <div style="padding: 10px 16px;">
                <div style="color: #fff; font-size: 24px; margin-bottom: 8px;">♡ 💬 📤</div>
            </div>
            <div style="
                padding: 0 16px 16px 16px;
                color: #fff;
                font-size: 14px;
                line-height: 1.5;
                max-height: 150px;
                overflow-y: auto;
            ">
                <strong>{author.lower().replace(' ', '_')}</strong> {safe_content}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    else:
        st.markdown(f"""
        <div style="
            background: #1a1a2e;
            border-radius: 12px;
            border: 1px solid #333;
            padding: 20px;
            color: #fff;
            line-height: 1.6;
            margin: 10px 0;
        ">{safe_content}</div>
        """, unsafe_allow_html=True)


def render_post_result(platform_name: str, result, topic: str):
    """Renderuje pojedynczy wynik posta"""
    
    with st.expander(f"📱 {platform_name}", expanded=True):
        col_content, col_meta = st.columns([2, 1])
        
        with col_content:
            # Edytowalny tekst
            edited = st.text_area(
                "Treść (możesz edytować)",
                value=result.content,
                height=250,
                key=f"content_{platform_name}"
            )
            
            # Akcje w jednej linii
            st.markdown("**Akcje:**")
            ac = st.columns(6)
            
            with ac[0]:
                if st.button("👍", key=f"like_{platform_name}", help="Podoba mi się"):
                    st.session_state.feedback_manager.add_positive(edited, platform_name)
                    st.toast("✅ Zapisano!", icon="💾")
            
            with ac[1]:
                if st.button("👎", key=f"dislike_{platform_name}", help="Nie podoba mi się"):
                    st.session_state.feedback_manager.add_negative(edited, platform_name, "disliked")
                    st.toast("Zapisano", icon="📝")
            
            with ac[2]:
                if st.button("📋", key=f"copy_{platform_name}", help="Kopiuj"):
                    st.code(edited, language=None)
            
            with ac[3]:
                if st.button("🔄", key=f"regen_{platform_name}", help="Regeneruj"):
                    with st.spinner("..."):
                        engine = get_engine()
                        platform = Platform[platform_name.upper()]
                        new_result = engine.run_quick(topic, platform)
                        st.session_state.campaign_results[platform_name] = new_result
                        st.rerun()
            
            with ac[4]:
                if st.button("🎨", key=f"gfx_{platform_name}", help="Grafika"):
                    first_line = edited.split('\n')[0][:50]
                    st.session_state.graphic_headline = first_line
                    st.toast("Przejdź do Studio Graficzne", icon="🎨")
            
            with ac[5]:
                # PRZYCISK PODGLĄDU - OTWIERA MODAL
                show_preview_modal(platform_name, edited)
        
        with col_meta:
            st.markdown("##### 🧠 Proces agenta")
            
            if result.state:
                st.caption(f"⏱️ {result.state.total_duration_ms}ms")
                st.caption(f"🔄 {result.state.iterations} iteracji")
                st.caption(f"📊 Ocena: {result.state.critique_score}/10")
                st.caption(f"🛡️ Brand: {'✅' if result.state.brand_approved else '⚠️'}")
            
            st.markdown("---")
            
            with st.container(height=150):
                for log in result.get_logs_formatted():
                    st.caption(log)


@st.dialog("👁️ Podgląd posta", width="large")
def show_preview_modal(platform_name: str, content: str):
    """Modal z podglądem posta - wyskakujące okienko na środku"""
    
    author = st.session_state.brand_memory.dna.get("brand_name", "Your Name")
    
    # Nagłówek
    st.markdown(f"### 📱 {platform_name}")
    
    # Podgląd w stylu platformy
    render_platform_preview(platform_name, content, author)
    
    # Licznik znaków
    char_count = len(content)
    if platform_name == "Twitter" and char_count > 280:
        st.warning(f"⚠️ {char_count}/280 znaków - przekroczono limit!")
    else:
        st.caption(f"📝 {char_count} znaków")
    
    st.markdown("---")
    
    # Akcje
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Kopiuj", use_container_width=True):
            st.code(content, language=None)
            st.toast("Skopiuj tekst powyżej", icon="📋")
    
    with col2:
        if st.button("🎨 Stwórz grafikę", use_container_width=True):
            first_line = content.split('\n')[0][:50]
            st.session_state.graphic_headline = first_line
            st.toast("Przejdź do zakładki Studio Graficzne", icon="🎨")
            st.rerun()
    
    with col3:
        if st.button("✕ Zamknij", use_container_width=True, type="primary"):
            st.rerun()


def render_platform_preview(platform: str, content: str, author: str):
    """Renderuje podgląd w stylu platformy"""
    
    # Escape HTML
    safe_content = html.escape(content).replace('\n', '<br>')
    initials = author[0].upper() if author else "U"
    
    if platform == "LinkedIn":
        st.markdown(f"""
        <div style="
            background: #1b1f23;
            border-radius: 12px;
            border: 1px solid #333;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            overflow: hidden;
        ">
            <div style="display: flex; align-items: center; padding: 16px; gap: 12px;">
                <div style="
                    width: 48px; height: 48px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #0077b5, #00a0dc);
                    display: flex; align-items: center; justify-content: center;
                    font-size: 20px; font-weight: bold; color: white;
                ">{initials}</div>
                <div>
                    <div style="color: #fff; font-weight: 600; font-size: 14px;">{author}</div>
                    <div style="color: rgba(255,255,255,0.6); font-size: 12px;">Teraz • 🌐</div>
                </div>
            </div>
            <div style="
                padding: 0 16px 16px 16px;
                color: #fff;
                font-size: 14px;
                line-height: 1.6;
                max-height: 350px;
                overflow-y: auto;
            ">{safe_content}</div>
            <div style="
                display: flex;
                justify-content: space-around;
                padding: 12px 16px;
                border-top: 1px solid #333;
                color: rgba(255,255,255,0.7);
                font-size: 13px;
            ">
                <span>👍 Lubię to</span>
                <span>💬 Komentarz</span>
                <span>🔄 Udostępnij</span>
                <span>📤 Wyślij</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    elif platform == "Twitter":
        st.markdown(f"""
        <div style="
            background: #15202b;
            border-radius: 12px;
            border: 1px solid #333;
            padding: 16px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        ">
            <div style="display: flex; gap: 12px;">
                <div style="
                    width: 48px; height: 48px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #1da1f2, #0d8bd9);
                    display: flex; align-items: center; justify-content: center;
                    font-size: 20px; font-weight: bold; color: white;
                    flex-shrink: 0;
                ">{initials}</div>
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <span style="color: #fff; font-weight: 700;">{author}</span>
                        <span style="color: #8899a6;">@{author.lower().replace(' ', '_')} · teraz</span>
                    </div>
                    <div style="color: #fff; font-size: 15px; line-height: 1.5;">{safe_content}</div>
                    <div style="
                        display: flex;
                        justify-content: space-between;
                        margin-top: 12px;
                        max-width: 350px;
                        color: #8899a6;
                        font-size: 13px;
                    ">
                        <span>💬</span>
                        <span>🔄</span>
                        <span>❤️</span>
                        <span>📊</span>
                        <span>📤</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    elif platform == "Facebook":
        st.markdown(f"""
        <div style="
            background: #242526;
            border-radius: 12px;
            border: 1px solid #333;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            overflow: hidden;
        ">
            <div style="display: flex; align-items: center; padding: 12px 16px; gap: 10px;">
                <div style="
                    width: 40px; height: 40px;
                    border-radius: 50%;
                    background: linear-gradient(135deg, #1877f2, #42b72a);
                    display: flex; align-items: center; justify-content: center;
                    font-size: 18px; font-weight: bold; color: white;
                ">{initials}</div>
                <div>
                    <div style="color: #e4e6eb; font-weight: 600; font-size: 14px;">{author}</div>
                    <div style="color: #b0b3b8; font-size: 12px;">Teraz · 🌍</div>
                </div>
            </div>
            <div style="
                padding: 0 16px 16px 16px;
                color: #e4e6eb;
                font-size: 15px;
                line-height: 1.5;
                max-height: 350px;
                overflow-y: auto;
            ">{safe_content}</div>
            <div style="
                display: flex;
                justify-content: space-around;
                padding: 8px 16px;
                border-top: 1px solid #3e4042;
                color: #b0b3b8;
                font-size: 14px;
                font-weight: 600;
            ">
                <span>👍 Lubię to</span>
                <span>💬 Komentarz</span>
                <span>📤 Udostępnij</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    elif platform == "Instagram":
        st.markdown(f"""
        <div style="
            background: #000;
            border-radius: 12px;
            border: 1px solid #333;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            overflow: hidden;
        ">
            <div style="display: flex; align-items: center; padding: 14px 16px; gap: 10px;">
                <div style="
                    width: 32px; height: 32px;
                    border-radius: 50%;
                    background: linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888);
                    display: flex; align-items: center; justify-content: center;
                    font-size: 14px; font-weight: bold; color: white;
                ">{initials}</div>
                <span style="color: #fff; font-weight: 600; font-size: 14px; flex: 1;">
                    {author.lower().replace(' ', '_')}
                </span>
                <span style="color: #8899a6;">•••</span>
            </div>
            <div style="
                background: linear-gradient(45deg, #405DE6, #5851DB, #833AB4, #C13584, #E1306C, #FD1D1D);
                height: 250px;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <span style="font-size: 64px;">📸</span>
            </div>
            <div style="
                padding: 12px 16px;
                color: #fff;
                font-size: 14px;
                line-height: 1.5;
                max-height: 200px;
                overflow-y: auto;
            ">
                <strong>{author.lower().replace(' ', '_')}</strong> {safe_content}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    else:
        st.markdown(f"""
        <div style="
            background: #1a1a2e;
            border-radius: 12px;
            border: 1px solid #333;
            padding: 20px;
            color: #fff;
            line-height: 1.6;
        ">{safe_content}</div>
        """, unsafe_allow_html=True)

def render_post_preview_modal():
    """Renderuje modal z podglądem posta w stylu platformy"""
    
    platform = st.session_state.get("modal_platform", "LinkedIn")
    content = st.session_state.get("modal_content", "")
    author = st.session_state.brand_memory.dna.get("brand_name", "Your Name")
    
    # Header
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"## 👁️ Podgląd: {platform}")
    with col2:
        if st.button("✕ Zamknij", key="close_post_modal"):
            st.session_state.show_post_modal = False
            st.rerun()
    
    st.markdown("---")
    
    # Środkowa kolumna dla podglądu
    _, col_center, _ = st.columns([1, 2, 1])
    
    with col_center:
        # Generuj HTML podglądu
        preview_html = generate_platform_preview_html(platform, content, author)
        st.markdown(preview_html, unsafe_allow_html=True)
        
        # Licznik znaków
        char_count = len(content)
        char_class = ""
        if platform == "Twitter" and char_count > 280:
            char_class = "danger"
        elif char_count > 2000:
            char_class = "warning"
        
        st.markdown(f"""
        <div class="char-counter">
            <span class="char-count {char_class}">📝 {char_count} znaków</span>
            <span class="copy-hint">Ctrl+C aby skopiować z pola edycji</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Akcje
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        if st.button("📋 Kopiuj treść", use_container_width=True):
            st.code(content, language=None)
            st.toast("Skopiuj powyższy tekst", icon="📋")
    
    with col_b:
        if st.button("🎨 Stwórz grafikę", use_container_width=True):
            first_line = content.split('\n')[0][:50]
            st.session_state.graphic_headline = first_line
            st.session_state.show_post_modal = False
            st.toast("Przejdź do zakładki Studio Graficzne", icon="🎨")
    
    with col_c:
        if st.button("⬅️ Wróć do edycji", use_container_width=True):
            st.session_state.show_post_modal = False
            st.rerun()


def generate_platform_preview_html(platform: str, content: str, author: str) -> str:
    """Generuje HTML podglądu w stylu platformy"""
    
    # Escape HTML w content
    import html
    safe_content = html.escape(content).replace('\n', '<br>')
    initials = author[0].upper() if author else "U"
    
    if platform == "LinkedIn":
        return f"""
        <div class="post-preview-container">
            <div class="linkedin-preview">
                <div class="linkedin-header">
                    <div class="linkedin-avatar">{initials}</div>
                    <div class="linkedin-meta">
                        <div class="linkedin-name">{author}</div>
                        <div class="linkedin-info">Teraz • 🌐</div>
                    </div>
                </div>
                <div class="linkedin-content">{safe_content}</div>
                <div class="linkedin-actions">
                    <div class="linkedin-action">👍 Lubię to</div>
                    <div class="linkedin-action">💬 Komentarz</div>
                    <div class="linkedin-action">🔄 Udostępnij</div>
                    <div class="linkedin-action">📤 Wyślij</div>
                </div>
            </div>
        </div>
        """
    
    elif platform == "Twitter":
        return f"""
        <div class="post-preview-container">
            <div class="twitter-preview">
                <div class="twitter-header">
                    <div class="twitter-avatar">{initials}</div>
                    <div class="twitter-body">
                        <div class="twitter-meta">
                            <span class="twitter-name">{author}</span>
                            <span class="twitter-handle">@{author.lower().replace(' ', '_')}</span>
                            <span class="twitter-handle">· teraz</span>
                        </div>
                        <div class="twitter-content">{safe_content}</div>
                        <div class="twitter-actions">
                            <div class="twitter-action">💬 0</div>
                            <div class="twitter-action">🔄 0</div>
                            <div class="twitter-action">❤️ 0</div>
                            <div class="twitter-action">📊 0</div>
                            <div class="twitter-action">📤</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    elif platform == "Facebook":
        return f"""
        <div class="post-preview-container">
            <div class="facebook-preview">
                <div class="facebook-header">
                    <div class="facebook-avatar">{initials}</div>
                    <div class="facebook-meta">
                        <div class="facebook-name">{author}</div>
                        <div class="facebook-info">Teraz · 🌍</div>
                    </div>
                </div>
                <div class="facebook-content">{safe_content}</div>
                <div class="facebook-actions">
                    <div class="facebook-action">👍 Lubię to</div>
                    <div class="facebook-action">💬 Komentarz</div>
                    <div class="facebook-action">📤 Udostępnij</div>
                </div>
            </div>
        </div>
        """
    
    elif platform == "Instagram":
        return f"""
        <div class="post-preview-container">
            <div class="instagram-preview">
                <div class="instagram-header">
                    <div class="instagram-avatar">{initials}</div>
                    <div class="instagram-name">{author.lower().replace(' ', '_')}</div>
                    <span style="color: #8899a6;">•••</span>
                </div>
                <div style="background: linear-gradient(45deg, #405DE6, #5851DB, #833AB4, #C13584, #E1306C, #FD1D1D); height: 300px; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white; font-size: 48px;">📸</span>
                </div>
                <div class="instagram-content">
                    <strong>{author.lower().replace(' ', '_')}</strong> {safe_content}
                </div>
            </div>
        </div>
        """
    
    else:
        return f"""
        <div class="post-preview-container" style="padding: 20px; background: #1a1a2e;">
            <div style="color: #fff; white-space: pre-wrap;">{safe_content}</div>
        </div>
        """


def render_graphics_tab():
    """Renderuje zakładkę Studio Graficzne"""
    
    st.markdown('<h2>🎨 Studio Graficzne</h2>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Twórz profesjonalne grafiki do postów</p>', unsafe_allow_html=True)
    
    engine = get_graphics_engine()
    
    # === CSS ===
    st.markdown("""
    <style>
    .preview-card {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border: 2px solid #333;
        border-radius: 16px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.3s ease;
        position: relative;
    }
    
    .preview-card:hover {
        border-color: #3b82f6;
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(59, 130, 246, 0.3);
    }
    
    .info-pill {
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
        color: white;
        padding: 8px 16px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;
        margin: 5px 5px 5px 0;
    }
    
    .info-pill.secondary {
        background: rgba(255,255,255,0.1);
    }
    
    .placeholder-box {
        background: linear-gradient(145deg, #1a1a2e, #16213e);
        border: 2px dashed #444;
        border-radius: 16px;
        padding: 60px 40px;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # === GŁÓWNY LAYOUT ===
    col_settings, col_preview = st.columns([1, 1.2])
    
    with col_settings:
        st.markdown("### ✏️ Treść")
        
        default_headline = st.session_state.get("graphic_headline", "Twój nagłówek tutaj")
        
        headline = st.text_input("Nagłówek", value=default_headline, key="gfx_headline")
        subheadline = st.text_input("Podtytuł", placeholder="Opcjonalny tekst")
        author = st.text_input(
            "Autor / Marka",
            value=st.session_state.brand_memory.dna.get("brand_name", "YourBrand")
        )
        
        st.markdown("---")
        st.markdown("### 🎴 Typ karty")
        
        card_type = st.radio(
            "Typ",
            ["📝 Standardowa", "💬 Cytat", "📊 Statystyka", "📋 Lista"],
            horizontal=True,
            label_visibility="collapsed"
        )
        
        # Dodatkowe pola
        extra_data = {}
        
        if "Cytat" in card_type:
            extra_data["quote_author"] = st.text_input("Autor cytatu", placeholder="np. Steve Jobs")
        
        elif "Statystyka" in card_type:
            c1, c2 = st.columns(2)
            with c1:
                extra_data["stat_value"] = st.text_input("Wartość", placeholder="73%")
            with c2:
                extra_data["stat_label"] = st.text_input("Etykieta", placeholder="deweloperów")
            extra_data["stat_desc"] = st.text_input("Opis (opcjonalnie)")
        
        elif "Lista" in card_type:
            list_text = st.text_area(
                "Punkty (jeden na linię)",
                placeholder="Punkt 1\nPunkt 2\nPunkt 3",
                height=100
            )
            extra_data["list_items"] = [x.strip() for x in list_text.split("\n") if x.strip()]
        
        st.markdown("---")
        st.markdown("### 🎭 Styl")
        
        c1, c2 = st.columns(2)
        
        with c1:
            templates = {
                "🌙 Tech Dark": "tech_dark",
                "⬛ Minimal": "minimal_dark",
                "🌈 Gradient": "gradient_bold",
                "💼 Corporate": "corporate_clean",
                "💡 Neon": "neon_statement"
            }
            selected_template = st.selectbox("Szablon", list(templates.keys()))
            template_name = templates[selected_template]
        
        with c2:
            formats = {
                "LinkedIn (1200×630)": AspectRatio.LINKEDIN_POST,
                "Square (1080×1080)": AspectRatio.INSTAGRAM_SQUARE,
                "Story (1080×1920)": AspectRatio.INSTAGRAM_STORY,
                "Twitter (1200×675)": AspectRatio.TWITTER_POST
            }
            selected_format = st.selectbox("Format", list(formats.keys()))
        
        add_effects = st.checkbox("✨ Efekty wizualne", value=True)
        
        st.markdown("---")
        
        # Przycisk generowania
        if st.button("🎨 Generuj Grafikę", type="primary", use_container_width=True):
            with st.spinner("Tworzę grafikę..."):
                try:
                    # Generuj kartę
                    if "Cytat" in card_type and headline:
                        card = engine.create_quote_card(
                            quote=headline,
                            author=extra_data.get("quote_author", author),
                            template_name=template_name,
                            add_effects=add_effects
                        )
                    elif "Statystyka" in card_type and extra_data.get("stat_value"):
                        card = engine.create_stats_card(
                            stat_value=extra_data["stat_value"],
                            stat_label=extra_data.get("stat_label", ""),
                            description=extra_data.get("stat_desc", ""),
                            template_name=template_name,
                            add_effects=add_effects
                        )
                    elif "Lista" in card_type and extra_data.get("list_items"):
                        card = engine.create_list_card(
                            title=headline,
                            items=extra_data["list_items"],
                            template_name=template_name,
                            add_effects=add_effects
                        )
                    else:
                        card = engine.create_card(
                            headline=headline,
                            template_name=template_name,
                            subheadline=subheadline,
                            author=author,
                            add_effects=add_effects
                        )
                    
                    # Resize
                    target = formats[selected_format].value
                    if (card.width, card.height) != target:
                        card = card.resize(target)
                    
                    st.session_state.current_graphic = card
                    st.toast("Grafika gotowa! 🎨", icon="✅")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Błąd: {e}")
    
    with col_preview:
        st.markdown("### 👁️ Podgląd")
        
        if "current_graphic" in st.session_state:
            card = st.session_state.current_graphic
            
            # Podgląd
            st.image(card.image, use_container_width=True)
            
            # Info
            st.markdown(f"""
            <div style="margin: 15px 0;">
                <span class="info-pill">📐 {card.width} × {card.height}</span>
                <span class="info-pill secondary">🎨 {card.template_name}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Przyciski
            c1, c2 = st.columns(2)
            
            with c1:
                if st.button("🔍 Pełny podgląd", use_container_width=True):
                    st.session_state.show_graphics_modal = True
                    st.rerun()
            
            with c2:
                png_bytes = card.to_bytes("PNG")
                st.download_button(
                    "📥 Pobierz PNG",
                    data=png_bytes,
                    file_name=f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )
            
            # Export dla platform
            st.markdown("##### 📱 Eksport dla platform")
            exp_cols = st.columns(4)
            platforms = ["LinkedIn", "Instagram", "Twitter", "Facebook"]
            
            for i, platform in enumerate(platforms):
                with exp_cols[i]:
                    if st.button(platform, key=f"gfx_exp_{platform}", use_container_width=True):
                        exports = engine.export_for_platform(card, platform)
                        st.session_state.platform_exports = exports
                        st.session_state.export_platform = platform
                        st.session_state.show_export_modal = True
                        st.rerun()
        
        else:
            # Placeholder
            st.markdown("""
            <div class="placeholder-box">
                <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.5;">🎨</div>
                <div style="color: #888; font-size: 16px;">Podgląd grafiki</div>
                <div style="color: #666; font-size: 14px; margin-top: 8px;">
                    Ustaw parametry i kliknij "Generuj Grafikę"
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # === MODAL PEŁNEGO PODGLĄDU ===
    if st.session_state.get("show_graphics_modal", False):
        render_graphics_modal(engine)
    
    # === MODAL EKSPORTU ===
    if st.session_state.get("show_export_modal", False):
        render_export_modal(engine)
    
    # === CAROUSEL BUILDER ===
    st.markdown("---")
    st.markdown("### 📑 Carousel Builder")
    
    with st.expander("Stwórz karuzelę slajdów", expanded=False):
        render_carousel_builder(engine)


def render_graphics_modal(engine):
    """Modal pełnego podglądu grafiki"""
    
    card = st.session_state.current_graphic
    
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown("## 🖼️ Podgląd grafiki")
    with col2:
        if st.button("✕ Zamknij", key="close_gfx_modal"):
            st.session_state.show_graphics_modal = False
            st.rerun()
    
    st.markdown("---")
    
    col_img, col_actions = st.columns([2, 1])
    
    with col_img:
        st.image(card.image, use_container_width=True)
        st.markdown(f"""
        <div style="text-align: center; margin-top: 15px;">
            <span class="info-pill">📐 {card.width} × {card.height} px</span>
            <span class="info-pill secondary">🎨 {card.template_name}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_actions:
        st.markdown("### 💾 Pobierz")
        
        png_bytes = card.to_bytes("PNG")
        st.download_button(
            "📥 PNG (wysoka jakość)",
            data=png_bytes,
            file_name=f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            mime="image/png",
            use_container_width=True,
            type="primary"
        )
        
        jpg_buffer = io.BytesIO()
        card.image.convert("RGB").save(jpg_buffer, format="JPEG", quality=95)
        st.download_button(
            "📥 JPG (mniejszy)",
            data=jpg_buffer.getvalue(),
            file_name=f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
            mime="image/jpeg",
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("### 📱 Eksport dla platformy")
        
        for platform in ["LinkedIn", "Instagram", "Twitter", "Facebook"]:
            if st.button(f"📤 {platform}", key=f"modal_gfx_{platform}", use_container_width=True):
                exports = engine.export_for_platform(card, platform)
                st.session_state.platform_exports = exports
                st.session_state.export_platform = platform
                st.session_state.show_graphics_modal = False
                st.session_state.show_export_modal = True
                st.rerun()
        
        st.markdown("---")
        
        if st.button("💾 Zapisz na dysk", use_container_width=True):
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)
            filepath = output_dir / f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            card.save(str(filepath))
            st.success(f"✅ Zapisano: {filepath}")


def render_export_modal(engine):
    """Modal eksportu dla platformy"""
    
    exports = st.session_state.get("platform_exports", {})
    platform = st.session_state.get("export_platform", "Platform")
    
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"## 📱 Eksport dla {platform}")
    with col2:
        if st.button("✕ Zamknij", key="close_exp_modal"):
            st.session_state.show_export_modal = False
            st.rerun()
    
    st.markdown("---")
    
    if not exports:
        st.warning("Brak eksportów")
        return
    
    cols = st.columns(len(exports))
    
    for i, (format_name, exp_card) in enumerate(exports.items()):
        with cols[i]:
            st.markdown(f"**{format_name.upper()}**")
            st.caption(f"{exp_card.width} × {exp_card.height}")
            st.image(exp_card.image, use_container_width=True)
            
            exp_bytes = exp_card.to_bytes("PNG")
            st.download_button(
                f"📥 Pobierz",
                data=exp_bytes,
                file_name=f"{platform.lower()}_{format_name}.png",
                mime="image/png",
                use_container_width=True,
                key=f"dl_exp_{format_name}_{i}"
            )
    
    st.markdown("---")
    
    # ZIP
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for format_name, exp_card in exports.items():
                zf.writestr(f"{platform.lower()}_{format_name}.png", exp_card.to_bytes("PNG"))
        
        st.download_button(
            "📦 Pobierz wszystkie (ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"{platform.lower()}_all_formats.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary"
        )
    
    if st.button("⬅️ Wróć", use_container_width=True):
        st.session_state.show_export_modal = False
        st.session_state.show_graphics_modal = True
        st.rerun()


def render_carousel_builder(engine):
    """Sekcja Carousel Builder"""
    
    col_set, col_prev = st.columns([1, 1])
    
    with col_set:
        num_slides = st.slider("Liczba slajdów", 2, 10, 4)
        
        templates = {
            "🌙 Tech Dark": "tech_dark",
            "⬛ Minimal": "minimal_dark",
            "🌈 Gradient": "gradient_bold"
        }
        carousel_tpl = st.selectbox("Szablon", list(templates.keys()), key="car_tpl_select")
        
        st.markdown("**Treść slajdów:**")
        
        slides_data = []
        for i in range(num_slides):
            c1, c2 = st.columns([2, 1])
            with c1:
                h = st.text_input(f"Slajd {i+1}", key=f"car_h_{i}", placeholder="Nagłówek")
            with c2:
                s = st.text_input("Sub", key=f"car_s_{i}", placeholder="Podtytuł", label_visibility="collapsed")
            slides_data.append({"headline": h, "subheadline": s})
        
        if st.button("🎨 Generuj Karuzelę", type="primary", use_container_width=True):
            valid = [s for s in slides_data if s["headline"]]
            if valid:
                with st.spinner(f"Generuję {len(valid)} slajdów..."):
                    carousel = engine.create_carousel(valid, templates[carousel_tpl])
                    st.session_state.current_carousel = carousel
                    st.toast(f"Gotowe! {len(carousel)} slajdów 📑", icon="✅")
                    st.rerun()
            else:
                st.warning("Dodaj treść do przynajmniej jednego slajdu")
    
    with col_prev:
        if "current_carousel" in st.session_state:
            carousel = st.session_state.current_carousel
            
            st.markdown("**Podgląd:**")
            
            slide_idx = st.slider("Slajd", 1, len(carousel), 1, key="car_slider_idx") - 1
            st.image(carousel[slide_idx].image, use_container_width=True)
            st.caption(f"Slajd {slide_idx + 1} z {len(carousel)}")
            
            c1, c2 = st.columns(2)
            
            with c1:
                st.download_button(
                    f"📥 Slajd {slide_idx + 1}",
                    data=carousel[slide_idx].to_bytes("PNG"),
                    file_name=f"slide_{slide_idx + 1:02d}.png",
                    mime="image/png",
                    use_container_width=True
                )
            
            with c2:
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, 'w') as zf:
                    for i, c in enumerate(carousel):
                        zf.writestr(f"slide_{i+1:02d}.png", c.to_bytes("PNG"))
                
                st.download_button(
                    "📦 ZIP",
                    data=zip_buf.getvalue(),
                    file_name="carousel.zip",
                    mime="application/zip",
                    use_container_width=True
                )
            
            # Miniaturki
            st.markdown("**Wszystkie:**")
            thumb_cols = st.columns(min(len(carousel), 5))
            for i, c in enumerate(carousel):
                with thumb_cols[i % 5]:
                    st.image(c.image, caption=str(i + 1), use_container_width=True)
        else:
            st.info("👆 Wypełnij slajdy i kliknij 'Generuj Karuzelę'")


def render_graphics_settings(engine):
    """Renderuje panel ustawień grafiki"""
    
    st.markdown("### ✏️ Treść")
    
    default_headline = st.session_state.get("graphic_headline", "Twój nagłówek tutaj")
    
    headline = st.text_input("Nagłówek", value=default_headline, key="gfx_headline")
    subheadline = st.text_input("Podtytuł", placeholder="Opcjonalny tekst pod nagłówkiem")
    author = st.text_input(
        "Autor / Marka",
        value=st.session_state.brand_memory.dna.get("brand_name", "YourBrand")
    )
    
    st.markdown("---")
    st.markdown("### 🎴 Typ karty")
    
    card_type = st.radio(
        "Wybierz typ",
        ["📝 Standardowa", "💬 Cytat", "📊 Statystyka", "📋 Lista"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    # Dodatkowe pola w zależności od typu
    extra_data = {}
    
    if "Cytat" in card_type:
        extra_data["quote_author"] = st.text_input("Autor cytatu", placeholder="np. Steve Jobs")
    
    elif "Statystyka" in card_type:
        c1, c2 = st.columns(2)
        with c1:
            extra_data["stat_value"] = st.text_input("Wartość", placeholder="73%")
        with c2:
            extra_data["stat_label"] = st.text_input("Etykieta", placeholder="deweloperów")
        extra_data["stat_desc"] = st.text_input("Opis (opcjonalnie)")
    
    elif "Lista" in card_type:
        list_text = st.text_area(
            "Punkty (jeden na linię)",
            placeholder="Pierwszy punkt\nDrugi punkt\nTrzeci punkt",
            height=100
        )
        extra_data["list_items"] = [x.strip() for x in list_text.split("\n") if x.strip()]
    
    st.markdown("---")
    st.markdown("### 🎭 Styl")
    
    c1, c2 = st.columns(2)
    
    with c1:
        templates = {
            "🌙 Tech Dark": "tech_dark",
            "⬛ Minimal": "minimal_dark",
            "🌈 Gradient": "gradient_bold",
            "💼 Corporate": "corporate_clean",
            "💡 Neon": "neon_statement"
        }
        selected_template = st.selectbox("Szablon", list(templates.keys()))
        template_name = templates[selected_template]
    
    with c2:
        formats = {
            "LinkedIn (1200×630)": AspectRatio.LINKEDIN_POST,
            "Square (1080×1080)": AspectRatio.INSTAGRAM_SQUARE,
            "Story (1080×1920)": AspectRatio.INSTAGRAM_STORY,
            "Twitter (1200×675)": AspectRatio.TWITTER_POST
        }
        selected_format = st.selectbox("Format", list(formats.keys()))
    
    add_effects = st.checkbox("✨ Efekty wizualne", value=True)
    
    st.markdown("---")
    
    # Przycisk generowania
    if st.button("🎨 Generuj Grafikę", type="primary", use_container_width=True):
        with st.spinner("Tworzę grafikę..."):
            try:
                card = generate_card(
                    engine, headline, subheadline, author,
                    card_type, extra_data, template_name, add_effects
                )
                
                # Resize do formatu
                target = formats[selected_format].value
                if (card.width, card.height) != target:
                    card = card.resize(target)
                
                st.session_state.current_graphic = card
                st.toast("Grafika gotowa! 🎨", icon="✅")
                st.rerun()
                
            except Exception as e:
                st.error(f"Błąd: {e}")
    
    # Zapisz ustawienia do session state
    st.session_state.gfx_settings = {
        "headline": headline,
        "subheadline": subheadline,
        "author": author,
        "card_type": card_type,
        "extra_data": extra_data,
        "template_name": template_name,
        "add_effects": add_effects
    }


def generate_card(engine, headline, subheadline, author, card_type, extra_data, template_name, add_effects):
    """Generuje kartę na podstawie typu"""
    
    if "Cytat" in card_type and headline:
        return engine.create_quote_card(
            quote=headline,
            author=extra_data.get("quote_author", author),
            template_name=template_name,
            add_effects=add_effects
        )
    
    elif "Statystyka" in card_type and extra_data.get("stat_value"):
        return engine.create_stats_card(
            stat_value=extra_data["stat_value"],
            stat_label=extra_data.get("stat_label", ""),
            description=extra_data.get("stat_desc", ""),
            template_name=template_name,
            add_effects=add_effects
        )
    
    elif "Lista" in card_type and extra_data.get("list_items"):
        return engine.create_list_card(
            title=headline,
            items=extra_data["list_items"],
            template_name=template_name,
            add_effects=add_effects
        )
    
    else:
        return engine.create_card(
            headline=headline,
            template_name=template_name,
            subheadline=subheadline,
            author=author,
            add_effects=add_effects
        )


def render_graphics_preview(engine):
    """Renderuje podgląd grafiki z klikaniem do modala"""
    
    st.markdown("### 👁️ Podgląd")
    
    if "current_graphic" in st.session_state:
        card = st.session_state.current_graphic
        
        # Konwertuj obraz do base64
        img_b64 = img_to_base64(card.image)
        
        # Klikalna karta podglądu
        st.markdown(f"""
        <div class="preview-card" onclick="document.getElementById('modal-overlay').classList.add('active')">
            <img src="data:image/png;base64,{img_b64}" style="width: 100%; display: block;">
            <div class="preview-overlay">
                <div class="preview-overlay-text">
                    🔍 Kliknij aby powiększyć
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Info pills
        st.markdown(f"""
        <div class="info-pills">
            <span class="info-pill">📐 {card.width} × {card.height}</span>
            <span class="info-pill secondary">🎨 {card.template_name}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Przyciski akcji
        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("🔍 Pełny podgląd", use_container_width=True):
                st.session_state.show_modal = True
                st.session_state.modal_type = "preview"
                st.rerun()
        
        with c2:
            png_bytes = card.to_bytes("PNG")
            st.download_button(
                "📥 Pobierz PNG",
                data=png_bytes,
                file_name=f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png",
                use_container_width=True
            )
        
        # Export buttons
        st.markdown("##### 📱 Eksport dla platform")
        
        exp_cols = st.columns(4)
        platforms = ["LinkedIn", "Instagram", "Twitter", "Facebook"]
        
        for i, platform in enumerate(platforms):
            with exp_cols[i]:
                if st.button(platform, key=f"exp_{platform}", use_container_width=True):
                    exports = engine.export_for_platform(card, platform)
                    st.session_state.platform_exports = exports
                    st.session_state.export_platform = platform
                    st.session_state.show_modal = True
                    st.session_state.modal_type = "export"
                    st.rerun()
    
    else:
        # Placeholder
        st.markdown("""
        <div class="placeholder-box">
            <div class="placeholder-icon">🎨</div>
            <div class="placeholder-text">Podgląd grafiki</div>
            <div class="placeholder-subtext">Ustaw parametry i kliknij "Generuj Grafikę"</div>
        </div>
        """, unsafe_allow_html=True)


def render_fullscreen_modal(engine):
    """Renderuje pełnoekranowy modal"""
    
    modal_type = st.session_state.get("modal_type", "preview")
    
    # Nagłówek modala
    if modal_type == "export":
        platform = st.session_state.get("export_platform", "Platform")
        title = f"📱 Eksport dla {platform}"
    else:
        title = "🖼️ Podgląd grafiki"
    
    # Przycisk zamknięcia
    col1, col2 = st.columns([6, 1])
    with col1:
        st.markdown(f"## {title}")
    with col2:
        if st.button("✕ Zamknij", key="close_modal", type="secondary"):
            st.session_state.show_modal = False
            st.rerun()
    
    st.markdown("---")
    
    if modal_type == "export" and "platform_exports" in st.session_state:
        render_export_modal_content(engine)
    else:
        render_preview_modal_content(engine)


def render_preview_modal_content(engine):
    """Renderuje zawartość modala podglądu"""
    
    card = st.session_state.current_graphic
    
    col_img, col_actions = st.columns([2, 1])
    
    with col_img:
        # Ramka obrazu
        st.markdown("""
        <div class="modal-image-container">
        """, unsafe_allow_html=True)
        
        st.image(card.image, use_container_width=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Info
        st.markdown(f"""
        <div class="info-pills" style="justify-content: center;">
            <span class="info-pill">📐 {card.width} × {card.height} px</span>
            <span class="info-pill secondary">🎨 {card.template_name}</span>
            <span class="info-pill secondary">📁 PNG / JPG</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_actions:
        st.markdown("### 💾 Pobierz")
        
        # PNG
        png_bytes = card.to_bytes("PNG")
        st.download_button(
            "📥 Pobierz PNG (wysoka jakość)",
            data=png_bytes,
            file_name=f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            mime="image/png",
            use_container_width=True,
            type="primary"
        )
        
        # JPG
        jpg_buffer = io.BytesIO()
        card.image.convert("RGB").save(jpg_buffer, format="JPEG", quality=95)
        st.download_button(
            "📥 Pobierz JPG (mniejszy rozmiar)",
            data=jpg_buffer.getvalue(),
            file_name=f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
            mime="image/jpeg",
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("### 📱 Eksportuj dla platformy")
        
        for platform in ["LinkedIn", "Instagram", "Twitter", "Facebook"]:
            if st.button(f"📤 {platform}", key=f"modal_exp_{platform}", use_container_width=True):
                exports = engine.export_for_platform(card, platform)
                st.session_state.platform_exports = exports
                st.session_state.export_platform = platform
                st.session_state.modal_type = "export"
                st.rerun()
        
        st.markdown("---")
        
        # Zapisz lokalnie
        if st.button("💾 Zapisz na dysk", use_container_width=True):
            output_dir = Path("outputs")
            output_dir.mkdir(exist_ok=True)
            filepath = output_dir / f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            card.save(str(filepath))
            st.success(f"✅ Zapisano: {filepath}")


def render_export_modal_content(engine):
    """Renderuje zawartość modala eksportu"""
    
    exports = st.session_state.platform_exports
    platform = st.session_state.export_platform
    
    st.markdown(f"Dostępne formaty dla **{platform}**:")
    
    # Siatka eksportów
    cols = st.columns(len(exports))
    
    for i, (format_name, exp_card) in enumerate(exports.items()):
        with cols[i]:
            st.markdown(f"""
            <div class="export-item">
                <div class="export-label">{format_name}</div>
                <div class="export-size">{exp_card.width} × {exp_card.height}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.image(exp_card.image, use_container_width=True)
            
            exp_bytes = exp_card.to_bytes("PNG")
            st.download_button(
                f"📥 Pobierz",
                data=exp_bytes,
                file_name=f"{platform.lower()}_{format_name}.png",
                mime="image/png",
                use_container_width=True,
                key=f"dl_{format_name}_{i}"
            )
    
    st.markdown("---")
    
    # Pobierz wszystkie jako ZIP
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for format_name, exp_card in exports.items():
                zf.writestr(f"{platform.lower()}_{format_name}.png", exp_card.to_bytes("PNG"))
        
        st.download_button(
            "📦 Pobierz wszystkie formaty (ZIP)",
            data=zip_buffer.getvalue(),
            file_name=f"{platform.lower()}_all_formats.zip",
            mime="application/zip",
            use_container_width=True,
            type="primary"
        )
    
    # Przycisk powrotu
    st.markdown("---")
    if st.button("⬅️ Wróć do podglądu", use_container_width=True):
        st.session_state.modal_type = "preview"
        st.rerun()


def render_carousel_section(engine):
    """Renderuje sekcję Carousel Builder"""
    
    st.markdown("### 📑 Carousel Builder")
    
    with st.expander("Stwórz karuzelę slajdów", expanded=False):
        col_set, col_prev = st.columns([1, 1])
        
        with col_set:
            num_slides = st.slider("Liczba slajdów", 2, 10, 4)
            
            templates = {
                "🌙 Tech Dark": "tech_dark",
                "⬛ Minimal": "minimal_dark",
                "🌈 Gradient": "gradient_bold"
            }
            carousel_tpl = st.selectbox("Szablon", list(templates.keys()), key="car_tpl")
            
            st.markdown("**Treść slajdów:**")
            
            slides_data = []
            for i in range(num_slides):
                st.markdown(f"**Slajd {i+1}**")
                c1, c2 = st.columns([2, 1])
                with c1:
                    h = st.text_input(f"Nagłówek", key=f"car_h_{i}", placeholder=f"Nagłówek {i+1}", label_visibility="collapsed")
                with c2:
                    s = st.text_input(f"Podtytuł", key=f"car_s_{i}", placeholder="Podtytuł", label_visibility="collapsed")
                slides_data.append({"headline": h, "subheadline": s})
            
            if st.button("🎨 Generuj Karuzelę", type="primary", use_container_width=True):
                valid = [s for s in slides_data if s["headline"]]
                if valid:
                    with st.spinner(f"Generuję {len(valid)} slajdów..."):
                        carousel = engine.create_carousel(valid, templates[carousel_tpl])
                        st.session_state.current_carousel = carousel
                        st.toast(f"Gotowe! {len(carousel)} slajdów 📑", icon="✅")
                        st.rerun()
                else:
                    st.warning("Dodaj treść do przynajmniej jednego slajdu")
        
        with col_prev:
            if "current_carousel" in st.session_state:
                carousel = st.session_state.current_carousel
                
                st.markdown("**Podgląd:**")
                
                # Slider do przeglądania
                slide_idx = st.slider("Slajd", 1, len(carousel), 1, key="car_idx") - 1
                
                # Aktualny slajd
                st.image(carousel[slide_idx].image, use_container_width=True)
                st.caption(f"Slajd {slide_idx + 1} z {len(carousel)}")
                
                # Przyciski
                c1, c2 = st.columns(2)
                
                with c1:
                    st.download_button(
                        f"📥 Slajd {slide_idx + 1}",
                        data=carousel[slide_idx].to_bytes("PNG"),
                        file_name=f"slide_{slide_idx + 1:02d}.png",
                        mime="image/png",
                        use_container_width=True
                    )
                
                with c2:
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, 'w') as zf:
                        for i, c in enumerate(carousel):
                            zf.writestr(f"slide_{i+1:02d}.png", c.to_bytes("PNG"))
                    
                    st.download_button(
                        "📦 Wszystkie (ZIP)",
                        data=zip_buf.getvalue(),
                        file_name="carousel.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                
                # Miniaturki
                st.markdown("**Wszystkie slajdy:**")
                thumb_cols = st.columns(min(len(carousel), 5))
                for i, c in enumerate(carousel):
                    with thumb_cols[i % 5]:
                        st.image(c.image, caption=str(i + 1), use_container_width=True)
            else:
                st.info("👆 Wypełnij slajdy i kliknij 'Generuj Karuzelę'")


def render_preview_popup():
    """Renderuje popup z pełnym podglądem grafiki"""
    
    card = st.session_state.current_graphic
    
    # Popup container
    popup_container = st.container()
    
    with popup_container:
        # Header z przyciskiem zamknięcia
        col_title, col_close = st.columns([4, 1])
        
        with col_title:
            st.markdown("## 🖼️ Podgląd grafiki")
        
        with col_close:
            if st.button("✕ Zamknij", key="close_preview"):
                st.session_state.show_preview_popup = False
                st.rerun()
        
        st.markdown("---")
        
        # Główny podgląd
        col_img, col_actions = st.columns([2, 1])
        
        with col_img:
            # Ramka obrazu
            st.markdown("""
            <div class="image-frame">
            """, unsafe_allow_html=True)
            
            st.image(card.image, use_container_width=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Info
            st.markdown(f"""
            <div style="text-align: center; margin-top: 15px;">
                <span class="info-badge">📐 {card.width} × {card.height} px</span>
                <span class="info-badge">🎨 {card.template_name}</span>
                <span class="info-badge">📁 PNG</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col_actions:
            st.markdown("### 💾 Pobierz")
            
            # PNG
            png_bytes = card.to_bytes("PNG")
            st.download_button(
                "📥 Pobierz PNG",
                data=png_bytes,
                file_name=f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                mime="image/png",
                use_container_width=True,
                type="primary"
            )
            
            # JPG
            jpg_buffer = io.BytesIO()
            card.image.convert("RGB").save(jpg_buffer, format="JPEG", quality=95)
            st.download_button(
                "📥 Pobierz JPG",
                data=jpg_buffer.getvalue(),
                file_name=f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                mime="image/jpeg",
                use_container_width=True
            )
            
            st.markdown("---")
            st.markdown("### 📱 Eksport dla platform")
            
            engine = get_graphics_engine()
            
            for platform in ["LinkedIn", "Instagram", "Twitter", "Facebook"]:
                if st.button(f"📤 {platform}", key=f"popup_exp_{platform}", use_container_width=True):
                    exports = engine.export_for_platform(card, platform)
                    st.session_state.platform_exports = exports
                    st.session_state.export_platform = platform
                    st.session_state.show_preview_popup = False
                    st.session_state.show_export_popup = True
                    st.rerun()
            
            st.markdown("---")
            
            # Zapisz lokalnie
            if st.button("💾 Zapisz na dysk", use_container_width=True):
                output_dir = Path("outputs")
                output_dir.mkdir(exist_ok=True)
                filepath = output_dir / f"graphic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                card.save(str(filepath))
                st.success(f"Zapisano: {filepath}")


def render_export_popup():
    """Renderuje popup z eksportami dla platformy"""
    
    exports = st.session_state.platform_exports
    platform = st.session_state.get("export_platform", "Platform")
    
    # Header
    col_title, col_close = st.columns([4, 1])
    
    with col_title:
        st.markdown(f"## 📱 Eksport dla {platform}")
    
    with col_close:
        if st.button("✕ Zamknij", key="close_export"):
            st.session_state.show_export_popup = False
            st.rerun()
    
    st.markdown("---")
    st.markdown("Wybierz format do pobrania:")
    
    # Siatka eksportów
    num_exports = len(exports)
    cols = st.columns(min(num_exports, 3))
    
    for i, (format_name, exp_card) in enumerate(exports.items()):
        with cols[i % 3]:
            # Obraz
            st.markdown(f"""
            <div style="
                background: #1a1a2e;
                border: 2px solid #333;
                border-radius: 12px;
                padding: 15px;
                text-align: center;
                margin-bottom: 10px;
            ">
                <div style="
                    color: #3B82F6;
                    font-weight: bold;
                    font-size: 14px;
                    margin-bottom: 10px;
                    text-transform: uppercase;
                ">{format_name}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.image(exp_card.image, use_container_width=True)
            
            st.caption(f"📐 {exp_card.width} × {exp_card.height}")
            
            # Przycisk pobierania
            exp_bytes = exp_card.to_bytes("PNG")
            st.download_button(
                f"📥 Pobierz {format_name}",
                data=exp_bytes,
                file_name=f"{platform.lower()}_{format_name}_{datetime.now().strftime('%H%M%S')}.png",
                mime="image/png",
                use_container_width=True,
                key=f"dl_exp_{format_name}_{i}"
            )
    
    st.markdown("---")
    
    # Pobierz wszystkie jako ZIP
    if st.button("📦 Pobierz wszystkie jako ZIP", use_container_width=True):
        import zipfile
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for format_name, exp_card in exports.items():
                img_bytes = exp_card.to_bytes("PNG")
                zf.writestr(f"{platform.lower()}_{format_name}.png", img_bytes)
        
        st.download_button(
            "💾 Zapisz ZIP",
            data=zip_buffer.getvalue(),
            file_name=f"{platform.lower()}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            mime="application/zip",
            use_container_width=True
        )


def render_carousel_builder(engine):
    """Renderuje sekcję Carousel Builder"""
    
    st.markdown("### 📑 Carousel Builder")
    
    with st.expander("Stwórz karuzelę slajdów", expanded=False):
        col_set, col_prev = st.columns([1, 1])
        
        with col_set:
            num_slides = st.slider("Liczba slajdów", 2, 10, 4)
            
            template_options = {
                "🌙 Tech Dark": "tech_dark",
                "⬛ Minimal": "minimal_dark",
                "🌈 Gradient": "gradient_bold"
            }
            carousel_template = st.selectbox(
                "Szablon",
                options=list(template_options.keys()),
                key="carousel_tpl"
            )
            
            st.markdown("**Treść slajdów:**")
            
            slides_data = []
            for i in range(num_slides):
                with st.container():
                    st.markdown(f"**Slajd {i+1}**")
                    c1, c2 = st.columns([2, 1])
                    with c1:
                        h = st.text_input(
                            "Nagłówek",
                            key=f"car_h_{i}",
                            placeholder=f"Nagłówek {i+1}",
                            label_visibility="collapsed"
                        )
                    with c2:
                        s = st.text_input(
                            "Podtytuł",
                            key=f"car_s_{i}",
                            placeholder="Podtytuł",
                            label_visibility="collapsed"
                        )
                    slides_data.append({"headline": h, "subheadline": s})
            
            if st.button("🎨 Generuj Karuzelę", key="gen_car_btn", type="primary"):
                valid = [s for s in slides_data if s["headline"]]
                if valid:
                    with st.spinner(f"Generuję {len(valid)} slajdów..."):
                        carousel = engine.create_carousel(valid, template_options[carousel_template])
                        st.session_state.current_carousel = carousel
                        st.toast(f"Gotowe! {len(carousel)} slajdów", icon="📑")
                        st.rerun()
                else:
                    st.warning("Dodaj treść do przynajmniej jednego slajdu")
        
        with col_prev:
            if "current_carousel" in st.session_state:
                carousel = st.session_state.current_carousel
                
                st.markdown("**Podgląd:**")
                
                # Slider do przeglądania
                if len(carousel) > 1:
                    slide_idx = st.slider(
                        "Slajd",
                        1, len(carousel), 1,
                        key="car_slider"
                    ) - 1
                else:
                    slide_idx = 0
                
                # Pokaż aktualny slajd
                current_slide = carousel[slide_idx]
                st.image(current_slide.image, use_container_width=True)
                st.caption(f"Slajd {slide_idx + 1} z {len(carousel)} | {current_slide.width}×{current_slide.height}")
                
                # Przyciski
                c1, c2 = st.columns(2)
                
                with c1:
                    slide_bytes = current_slide.to_bytes("PNG")
                    st.download_button(
                        f"📥 Pobierz slajd {slide_idx + 1}",
                        data=slide_bytes,
                        file_name=f"slide_{slide_idx + 1:02d}.png",
                        mime="image/png",
                        use_container_width=True
                    )
                
                with c2:
                    # ZIP wszystkich
                    import zipfile
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w') as zf:
                        for i, card in enumerate(carousel):
                            zf.writestr(f"slide_{i+1:02d}.png", card.to_bytes("PNG"))
                    
                    st.download_button(
                        "📦 Pobierz ZIP",
                        data=zip_buffer.getvalue(),
                        file_name=f"carousel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
                
                # Miniaturki wszystkich slajdów
                st.markdown("**Wszystkie slajdy:**")
                thumb_cols = st.columns(min(len(carousel), 5))
                for i, card in enumerate(carousel):
                    with thumb_cols[i % 5]:
                        st.image(card.image, caption=f"{i+1}", use_container_width=True)
            else:
                st.info("👆 Wypełnij slajdy i kliknij 'Generuj Karuzelę'")


def render_settings_tab():
    """Renderuje zakładkę Ustawień / Brand DNA"""
    
    st.markdown('<h2>⚙️ Ustawienia & Brand DNA</h2>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Skonfiguruj tożsamość marki i preferencje agenta</p>', unsafe_allow_html=True)
    
    dna = st.session_state.brand_memory.dna
    
    # === BRAND DNA ===
    st.markdown("### 🧬 Brand DNA")
    st.info("Te ustawienia wpływają na KAŻDY wygenerowany post. Agent zawsze je uwzględnia.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📛 Podstawy")
        
        brand_name = st.text_input(
            "Nazwa marki / Twoje imię",
            value=dna.get("brand_name", ""),
            key="dna_brand_name"
        )
        
        tagline = st.text_input(
            "Tagline (opcjonalnie)",
            value=dna.get("tagline", ""),
            placeholder="np. 'Pomagam deweloperom rosnąć'"
        )
        
        target_audience = st.text_area(
            "Grupa docelowa",
            value=dna.get("target_audience", ""),
            height=100,
            placeholder="Opisz swoją grupę docelową..."
        )
    
    with col2:
        st.markdown("#### 🎭 Ton i styl")
        
        tone_of_voice = st.text_area(
            "Tone of Voice",
            value=dna.get("tone_of_voice", ""),
            height=80,
            placeholder="np. 'Ekspercki ale przystępny, z humorem'"
        )
        
        formality_options = ["low", "medium", "high"]
        formality_index = formality_options.index(dna.get("formality_level", "medium"))
        formality = st.select_slider(
            "Poziom formalności",
            options=["Casual", "Balanced", "Formal"],
            value=["Casual", "Balanced", "Formal"][formality_index]
        )
        
        personality_traits = st.text_input(
            "Cechy osobowości (oddziel przecinkami)",
            value=", ".join(dna.get("personality_traits", []))
        )
    
    st.markdown("---")
    st.markdown("#### 🚫 Zasady treści")
    
    col3, col4 = st.columns(2)
    
    with col3:
        forbidden_words = st.text_area(
            "Zakazane słowa / frazy",
            value=", ".join(dna.get("forbidden_words", [])),
            height=100,
            help="Słowa których agent NIGDY nie użyje"
        )
        
        preferred_phrases = st.text_area(
            "Preferowane frazy (opcjonalnie)",
            value=", ".join(dna.get("preferred_phrases", [])),
            height=80,
            help="Frazy które agent chętnie wykorzysta"
        )
    
    with col4:
        emoji_policy = st.select_slider(
            "Polityka emoji",
            options=["none", "minimal", "moderate", "heavy"],
            value=dna.get("emoji_policy", "minimal")
        )
        
        max_emojis = st.number_input(
            "Max emoji na post",
            min_value=0,
            max_value=20,
            value=dna.get("max_emojis_per_post", 3)
        )
        
        hashtag_policy = st.select_slider(
            "Polityka hashtagów",
            options=["none", "minimal", "moderate"],
            value=dna.get("hashtag_policy", "minimal")
        )
        
        max_hashtags = st.number_input(
            "Max hashtagów",
            min_value=0,
            max_value=15,
            value=dna.get("max_hashtags", 3)
        )
    
    st.markdown("---")
    
    # Save button
    if st.button("💾 Zapisz Brand DNA", type="primary", use_container_width=False):
        # Mapuj formality
        formality_map = {"Casual": "low", "Balanced": "medium", "Formal": "high"}
        
        # Prepare updates
        updates = {
            "brand_name": brand_name,
            "tagline": tagline,
            "target_audience": target_audience,
            "tone_of_voice": tone_of_voice,
            "formality_level": formality_map.get(formality, "medium"),
            "personality_traits": [t.strip() for t in personality_traits.split(",") if t.strip()],
            "forbidden_words": [w.strip() for w in forbidden_words.split(",") if w.strip()],
            "preferred_phrases": [p.strip() for p in preferred_phrases.split(",") if p.strip()],
            "emoji_policy": emoji_policy,
            "max_emojis_per_post": max_emojis,
            "hashtag_policy": hashtag_policy,
            "max_hashtags": max_hashtags
        }
        
        st.session_state.brand_memory.update_bulk(updates)
        st.toast("Brand DNA zapisane!", icon="🧬")
        st.balloons()
    
    # === FEEDBACK & HISTORY ===
    st.markdown("---")
    st.markdown("### 📊 Feedback & Historia")
    
    col_fb, col_hist = st.columns(2)
    
    with col_fb:
        st.markdown("#### 👍👎 Statystyki feedbacku")
        
        stats = st.session_state.feedback_manager.get_stats()
        
        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Pozytywne", stats.get("total_positive", 0), delta=None)
        with metric_cols[1]:
            st.metric("Negatywne", stats.get("total_negative", 0), delta=None)
        with metric_cols[2]:
            st.metric("Korekty", stats.get("total_adjustments", 0), delta=None)
        
        if st.button("🗑️ Wyczyść feedback", key="clear_feedback"):
            st.session_state.feedback_manager = FeedbackManager()
            st.toast("Feedback wyczyszczony", icon="🗑️")
    
    with col_hist:
        st.markdown("#### 📝 Historia postów")
        
        posts_count = st.session_state.posts_history.count()
        st.metric("Łącznie postów", posts_count)
        
        recent = st.session_state.posts_history.get_recent(5)
        
        if recent:
            for post in reversed(recent):
                with st.container():
                    st.caption(f"**{post.get('platform')}** - {post.get('created_at', '')[:10]}")
                    st.caption(f"Score: {post.get('score', 'N/A')}/10")
        
        if st.button("🗑️ Wyczyść historię", key="clear_history"):
            st.session_state.posts_history = PostsHistory()
            st.toast("Historia wyczyszczona", icon="🗑️")
    
    # === API & DEBUG ===
    st.markdown("---")
    
    with st.expander("🔧 Debug & API", expanded=False):
        st.markdown("#### 🔑 Status API")
        
        if "agent_engine" in st.session_state:
            router = st.session_state.agent_engine.router
            provider_status = router.get_provider_status()
            
            for provider, status in provider_status.items():
                col_p1, col_p2 = st.columns([1, 3])
                with col_p1:
                    st.write(f"**{provider.upper()}**")
                with col_p2:
                    if status["available"]:
                        st.success(f"✅ Aktywny | Requests: {status['requests_count']}")
                    else:
                        st.error(f"❌ {status['status']} | {status.get('last_error', '')}")
            
            # Stats
            st.markdown("#### 📊 Statystyki wywołań")
            call_stats = router.get_stats()
            st.json(call_stats)
        
        st.markdown("#### 🧬 Raw Brand DNA")
        st.json(st.session_state.brand_memory.dna)


# === GŁÓWNA FUNKCJA ===

def main():
    """Główna funkcja aplikacji"""
    
    # Inicjalizacja
    init_session_state()
    
    # Sidebar
    api_ready = render_sidebar()
    
    if not api_ready:
        st.warning("⚠️ Skonfiguruj API Key aby kontynuować")
        st.stop()
    
    # Header
    st.markdown('<h1 class="main-header">AI Marketing Agent</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Twój osobisty zespół marketingowy napędzany AI</p>', unsafe_allow_html=True)
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📢 Campaign Builder",
        "🎨 Studio Graficzne", 
        "⚙️ Ustawienia"
    ])
    
    with tab1:
        render_campaign_tab()
    
    with tab2:
        render_graphics_tab()
    
    with tab3:
        render_settings_tab()
    
    # Footer
    st.markdown("---")
    st.caption(
        f"AI Marketing Agent v2.0 | "
        f"Posty: {st.session_state.posts_history.count()} | "
        f"Sesja: {st.session_state.generation_count} generacji"
    )


if __name__ == "__main__":
    main()