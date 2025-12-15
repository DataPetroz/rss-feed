import json
import streamlit as st
from typing import Dict, Any, List
from config.settings import DETAIL_PAGE_TITLE, DETAIL_PAGE_ICON, AHREFS_API_TOKEN
from utils.ui_components import (
    inject_custom_css, 
    display_structure_preview,
    display_keywords_with_volumes,
    display_questions_list
)
from utils.ai_services import (
    extract_keywords,
    generate_summary_with_questions,
    generate_blog_structure,
    generate_intelligent_blog_draft
)
from utils.ahrefs_api import get_multiple_keywords_volumes
from utils.analytics import track_event

# NON usare set_page_config qui, è già impostato in main.py

# Inietta CSS
inject_custom_css()

# ============================================================================
# INIZIALIZZAZIONE SESSION STATE
# ============================================================================

def init_session_state():
    """Inizializza tutte le chiavi necessarie in session state"""
    
    # Articolo corrente
    if 'current_article' not in st.session_state:
        st.session_state['current_article'] = None
    
    if 'current_article_id' not in st.session_state:
        st.session_state['current_article_id'] = None
    
    # Step 1: Keywords
    if 'keywords_extracted' not in st.session_state:
        st.session_state['keywords_extracted'] = None
    
    if 'keywords_edited' not in st.session_state:
        st.session_state['keywords_edited'] = None
    
    if 'keywords_volumes' not in st.session_state:
        st.session_state['keywords_volumes'] = {}
    
    if 'show_keywords_editor' not in st.session_state:
        st.session_state['show_keywords_editor'] = False
    
    # Step 2: Summary + Questions
    if 'summary_generated' not in st.session_state:
        st.session_state['summary_generated'] = None
    
    if 'questions_generated' not in st.session_state:
        st.session_state['questions_generated'] = None
    
    if 'questions_edited' not in st.session_state:
        st.session_state['questions_edited'] = None
    
    if 'show_questions_editor' not in st.session_state:
        st.session_state['show_questions_editor'] = False
    
    # Step 3: Struttura
    if 'structure_generated' not in st.session_state:
        st.session_state['structure_generated'] = None
    
    if 'structure_edited' not in st.session_state:
        st.session_state['structure_edited'] = None
    
    if 'system_prompt_structure' not in st.session_state:
        st.session_state['system_prompt_structure'] = ""
    
    if 'show_structure_editor' not in st.session_state:
        st.session_state['show_structure_editor'] = False
    
    # Step 4: Blog Draft
    if 'blog_draft_generated' not in st.session_state:
        st.session_state['blog_draft_generated'] = None
    
    if 'blog_draft_edited' not in st.session_state:
        st.session_state['blog_draft_edited'] = None
    
    if 'show_blog_editor' not in st.session_state:
        st.session_state['show_blog_editor'] = False

# Inizializza
init_session_state()

# Verifica che ci sia un articolo
if st.session_state['current_article'] is None:
    st.warning("⚠️ Nessun articolo selezionato.")
    if st.button("⬅️ Vai alla Lista", type="primary"):
        st.switch_page("pages/lista_articoli.py")
    st.stop()

article = st.session_state['current_article']

# Sidebar con torna indietro
with st.sidebar:
    st.markdown("### 🔗 Azioni Rapide")
    st.link_button("🌐 Leggi Originale", article['link'], use_container_width=True)
    st.markdown("---")
    
    if st.button("⬅️ Torna alla Lista", use_container_width=True, type="primary"):
        track_event("torna_lista", "elaborazione_articolo", {
            "article_id": st.session_state.get('current_article_id')
        })
        st.switch_page("pages/lista_articoli.py")

# Qui inserisci tutto il resto del codice di elaborazione che avevi già...
st.title(f"📊 Elaborazione: {article['title']}")
st.markdown("*Pagina di elaborazione in costruzione - Qui vanno gli step*")

# TODO: Inserire qui tutte le funzioni display_keywords_step, display_questions_step, ecc.
