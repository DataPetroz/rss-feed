import json
import base64
import hashlib
from urllib.parse import unquote
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
import json

st.set_page_config(
    page_title=DETAIL_PAGE_TITLE,
    page_icon=DETAIL_PAGE_ICON,
    layout="wide",
    initial_sidebar_state="collapsed"
)

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


# ============================================================================
# HEADER CON IMMAGINE + RIASSUNTO
# ============================================================================

def display_article_header(article: Dict[str, Any]):
    """Mostra header con immagine (40%) e riassunto AI (60%)"""
    
    st.markdown('<div class="elaboration-layout">', unsafe_allow_html=True)
    
    # Titolo articolo
    st.markdown(f"<h2>{article['title']}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #6b7280;'><span class='category-tag'>{article['source_category']}</span> • 📅 {article['published']}</p>", unsafe_allow_html=True)
    
    # Layout immagine + riassunto
    if article['has_image'] and article['image_url']:
        image_html = f'<img src="{article["image_url"]}" class="article-image" alt="Immagine articolo">'
    else:
        image_html = '<div class="no-image-placeholder">📄</div>'
    
    # Genera riassunto se non presente
    if st.session_state['summary_generated'] is None:
        with st.spinner("Generazione riassunto in corso..."):
            result = generate_summary_with_questions(article['full_content'], article['title'])
            st.session_state['summary_generated'] = result.get('summary', '')
            st.session_state['questions_generated'] = result.get('questions', [])
    
    summary_text = st.session_state['summary_generated']
    
    st.markdown(f"""
    <div class="summary-row">
        <div class="image-column">
            <div class="image-container">
                {image_html}
            </div>
        </div>
        <div class="summary-column">
            <div class="summary-container">
                <h3>📝 Riassunto AI</h3>
                <div class="summary-text">
                    {summary_text}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")


# ============================================================================
# STEP 1: KEYWORDS
# ============================================================================

def display_keywords_step(article: Dict[str, Any]):
    """Step 1: Estrazione e gestione keywords"""
    
    st.markdown('<div class="step-section">', unsafe_allow_html=True)
    st.markdown('<div class="step-header">🏷️ Step 1: Keywords AI</div>', unsafe_allow_html=True)
    
    # Se keywords non ancora estratte
    if st.session_state['keywords_extracted'] is None:
        st.markdown("""
        <div style="background-color: #f0fdf4; border: 2px dashed #10b981; border-radius: 8px; padding: 20px; text-align: center;">
            <h4 style="color: #065f46;">Estrai Keywords con AI</h4>
            <p style="color: #065f46;">Genera automaticamente le keyword principali dall'articolo.</p>
            <small>💰 <em>Questa operazione consumerà token OpenAI</em></small>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🤖 Estrai Keywords AI", key="extract_keywords_btn", type="primary"):
            track_event("estrai_keywords", "elaborazione_articolo", {
                "article_id": st.session_state.get('current_article_id')
            })
            
            with st.spinner("🤖 Estrazione keywords in corso..."):
                keywords = extract_keywords(article['full_content'], article['title'])
                st.session_state['keywords_extracted'] = keywords
                st.session_state['keywords_edited'] = keywords.copy()
            
            st.rerun()
    
    else:
        # Keywords estratte - mostra risultati
        final_keywords = st.session_state.get('keywords_edited', st.session_state['keywords_extracted'])
        volumes = st.session_state.get('keywords_volumes', {})
        has_volumes = volumes and any(v > 0 for v in volumes.values())
        
        # Header dinamico
        if has_volumes:
            st.success("✅ Keywords con volumi di ricerca")
        else:
            st.info(f"🏷️ {len(final_keywords)} keywords estratte")
        
        # Mostra keywords
        if has_volumes:
            display_keywords_with_volumes(final_keywords, volumes)
        else:
            # Mostra senza volumi
            keywords_html = ""
            for kw in final_keywords:
                keywords_html += f'<span class="keyword-tag">{kw} <span class="keyword-volume">-</span></span>'
            st.markdown(f'<div style="margin: 10px 0;">{keywords_html}</div>', unsafe_allow_html=True)
        
        # Editor inline se attivo
        if st.session_state['show_keywords_editor'] and not has_volumes:
            st.markdown("---")
            display_keywords_editor(final_keywords)
        
        # Pulsanti azioni
        if not has_volumes:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                editor_text = "🔧 Chiudi Editor" if st.session_state['show_keywords_editor'] else "✏️ Modifica"
                if st.button(editor_text, key="toggle_kw_editor", type="secondary"):
                    st.session_state['show_keywords_editor'] = not st.session_state['show_keywords_editor']
                    st.rerun()
            
            with col2:
                volumes_disabled = len(final_keywords) == 0 or not AHREFS_API_TOKEN
                button_text = "📊 Ottieni Volumi" if AHREFS_API_TOKEN else "📊 API Non Config."
                
                if st.button(button_text, key="get_volumes_btn", type="primary", disabled=volumes_disabled):
                    track_event("ottieni_volumi", "elaborazione_articolo", {
                        "num_keywords": len(final_keywords)
                    })
                    
                    with st.spinner(f"📊 Ricerca volumi per {len(final_keywords)} keywords..."):
                        batch_results = get_multiple_keywords_volumes(final_keywords, AHREFS_API_TOKEN, "it")
                        
                        new_volumes = {}
                        for keyword, result in batch_results.items():
                            if result["status"] == "success":
                                new_volumes[keyword] = result["volume"]
                        
                        st.session_state['keywords_volumes'] = new_volumes
                        st.session_state['show_keywords_editor'] = False
                    
                    st.rerun()
            
            with col3:
                if st.button("🔄 Rigenera AI", key="regen_keywords", type="secondary"):
                    with st.spinner("🤖 Rigenerazione keywords..."):
                        keywords = extract_keywords(article['full_content'], article['title'])
                        st.session_state['keywords_extracted'] = keywords
                        st.session_state['keywords_edited'] = keywords.copy()
                        st.session_state['keywords_volumes'] = {}
                        st.session_state['show_keywords_editor'] = False
                    st.rerun()
        
        else:
            # Dopo aver ottenuto volumi
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("✏️ Modifica Keywords", key="edit_after_volumes", type="secondary"):
                    st.session_state['keywords_volumes'] = {}
                    st.session_state['show_keywords_editor'] = True
                    st.rerun()
            
            with col2:
                if st.button("🔄 Aggiorna Volumi", key="refresh_volumes", type="secondary"):
                    with st.spinner("🔄 Aggiornamento volumi..."):
                        batch_results = get_multiple_keywords_volumes(final_keywords, AHREFS_API_TOKEN, "it")
                        new_volumes = {}
                        for keyword, result in batch_results.items():
                            if result["status"] == "success":
                                new_volumes[keyword] = result["volume"]
                        st.session_state['keywords_volumes'] = new_volumes
                    st.rerun()
            
            with col3:
                if st.button("📋 Export JSON", key="export_kw_json", type="secondary"):
                    export_data = {
                        "article_title": article['title'],
                        "keywords_with_volumes": [
                            {"keyword": kw, "volume_monthly": volumes.get(kw, 0)}
                            for kw in final_keywords
                        ],
                        "total_keywords": len(final_keywords),
                        "total_volume": sum(volumes.values())
                    }
                    
                    json_output = json.dumps(export_data, ensure_ascii=False, indent=2)
                    st.text_area("JSON Output:", value=json_output, height=200)
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_keywords_editor(keywords_list: List[str]):
    """Editor inline per keywords"""
    st.markdown("""
    <div style="background-color: #fef7e0; border: 1px dashed #f59e0b; border-radius: 8px; padding: 15px;">
        <h4 style="color: #92400e;">✏️ Editor Keywords</h4>
    </div>
    """, unsafe_allow_html=True)
    
    current_keywords = st.session_state.get('keywords_edited', keywords_list.copy())
    
    if current_keywords:
        st.markdown("**Keywords attuali:**")
        
        keywords_to_remove = []
        
        # Mostra keywords in righe di 3
        cols_per_row = 3
        for i in range(0, len(current_keywords), cols_per_row):
            row_keywords = current_keywords[i:i + cols_per_row]
            cols = st.columns(cols_per_row)
            
            for j, keyword in enumerate(row_keywords):
                with cols[j]:
                    col_text, col_btn = st.columns([4, 1])
                    
                    with col_text:
                        st.markdown(f"""
                        <div style="background-color: #10b981; color: white; padding: 4px 8px; 
                                   border-radius: 12px; font-size: 11px; text-align: center; margin: 2px 0;">
                            {keyword}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col_btn:
                        if st.button("✕", key=f"remove_kw_{i}_{j}", help=f"Rimuovi '{keyword}'"):
                            keywords_to_remove.append(keyword)
        
        # Rimuovi keywords selezionate
        if keywords_to_remove:
            for kw in keywords_to_remove:
                if kw in current_keywords:
                    current_keywords.remove(kw)
            st.session_state['keywords_edited'] = current_keywords
            st.rerun()
    
    # Aggiungi nuova keyword
    col_input, col_add = st.columns([3, 1])
    
    with col_input:
        new_keyword = st.text_input(
            "Aggiungi keyword:",
            key="new_keyword_input",
            placeholder="es: utensili professionali"
        )
    
    with col_add:
        if st.button("➕", key="add_keyword_btn", type="primary", disabled=not new_keyword.strip()):
            if new_keyword.strip():
                clean_keyword = new_keyword.strip().title()
                if clean_keyword not in current_keywords:
                    current_keywords.append(clean_keyword)
                    st.session_state['keywords_edited'] = current_keywords
                    st.success(f"✅ Aggiunta: '{clean_keyword}'")
                    st.rerun()
                else:
                    st.warning(f"⚠️ '{clean_keyword}' già presente!")
    
    # Aggiunta multipla
    with st.expander("⚡ Aggiunta multipla"):
        bulk_keywords = st.text_area(
            "Una keyword per riga:",
            placeholder="ferramenta\nutensili cantiere\nsicurezza lavoro",
            height=80,
            key="bulk_keywords"
        )
        
        if st.button("➕ Aggiungi tutte", key="add_bulk_keywords"):
            if bulk_keywords.strip():
                new_keywords = [kw.strip().title() for kw in bulk_keywords.split('\n') 
                              if kw.strip() and len(kw.strip()) >= 3]
                
                added_count = 0
                for keyword in new_keywords:
                    if keyword not in current_keywords:
                        current_keywords.append(keyword)
                        added_count += 1
                
                if added_count > 0:
                    st.session_state['keywords_edited'] = current_keywords
                    st.success(f"✅ Aggiunte {added_count} keywords!")
                    st.rerun()
    
    st.markdown(f"**📊 Totale keywords:** {len(current_keywords)}")

# Continuazione di Elaborazione_Articolo.py

# ============================================================================
# STEP 2: RIASSUNTO + DOMANDE (già generato nell'header, qui gestiamo le domande)
# ============================================================================

def display_questions_step(article: Dict[str, Any]):
    """Step 2: Gestione domande correlate"""
    
    st.markdown('<div class="step-section">', unsafe_allow_html=True)
    st.markdown('<div class="step-header">❓ Step 2: Domande Correlate</div>', unsafe_allow_html=True)
    
    # Le domande sono già state generate nell'header insieme al riassunto
    original_questions = st.session_state.get('questions_generated', [])
    
    if not original_questions:
        st.info("ℹ️ Nessuna domanda generata automaticamente. Puoi aggiungerne manualmente.")
        st.session_state['questions_edited'] = []
    else:
        # Usa versione editata se esiste, altrimenti originale
        if st.session_state['questions_edited'] is None:
            st.session_state['questions_edited'] = original_questions.copy()
        
        final_questions = st.session_state['questions_edited']
        
        # Header
        questions_source = "personalizzate" if st.session_state['questions_edited'] != original_questions else "AI originali"
        header_color = "#f59e0b" if st.session_state['show_questions_editor'] else "#3b82f6"
        bg_color = "#fef7e0" if st.session_state['show_questions_editor'] else "#f0f9ff"
        
        st.markdown(f"""
        <div style="background-color: {bg_color}; border-left: 4px solid {header_color}; 
                   padding: 15px; margin: 10px 0; border-radius: 8px;">
            <h4 style="color: {header_color};">
                ❓ Domande Correlate ({len(final_questions)} {questions_source})
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Mostra domande
        if final_questions:
            if not st.session_state['show_questions_editor']:
                display_questions_list(final_questions)
            else:
                st.markdown("---")
                display_questions_editor(final_questions)
        else:
            st.markdown("""
            <div style="color: #6b7280; font-style: italic; text-align: center; padding: 20px;">
                Nessuna domanda presente. Usa l'editor per aggiungerne.
            </div>
            """, unsafe_allow_html=True)
        
        # Pulsanti azioni
        col1, col2, col3 = st.columns(3)
        
        with col1:
            editor_text = "🔧 Chiudi Editor" if st.session_state['show_questions_editor'] else "✏️ Modifica domande"
            if st.button(editor_text, key="toggle_questions_editor", type="secondary", disabled=len(final_questions) == 0):
                st.session_state['show_questions_editor'] = not st.session_state['show_questions_editor']
                st.rerun()
        
        with col2:
            if st.button("🔄 Rigenera AI", key="regen_questions", type="secondary"):
                with st.spinner("🤖 Rigenerazione riassunto e domande..."):
                    result = generate_summary_with_questions(article['full_content'], article['title'])
                    st.session_state['summary_generated'] = result.get('summary', '')
                    st.session_state['questions_generated'] = result.get('questions', [])
                    st.session_state['questions_edited'] = None
                    st.session_state['show_questions_editor'] = False
                st.rerun()
        
        with col3:
            if st.button("📋 Export JSON", key="export_questions_json", type="secondary", disabled=len(final_questions) == 0):
                export_data = {
                    "article_title": article['title'],
                    "questions": final_questions,
                    "total_questions": len(final_questions),
                    "source": questions_source
                }
                
                json_output = json.dumps(export_data, ensure_ascii=False, indent=2)
                st.text_area("Domande JSON:", value=json_output, height=150)
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_questions_editor(questions_list: List[str]):
    """Editor per domande correlate"""
    st.markdown("""
    <div style="background-color: #fef7e0; border: 1px dashed #f59e0b; border-radius: 8px; padding: 15px;">
        <h4 style="color: #92400e;">✏️ Editor Domande</h4>
    </div>
    """, unsafe_allow_html=True)
    
    current_questions = st.session_state.get('questions_edited', questions_list.copy())
    
    if current_questions:
        st.markdown("**Domande attuali:**")
        
        questions_to_remove = []
        
        for i, question in enumerate(current_questions):
            col_text, col_btn = st.columns([6, 1])
            
            with col_text:
                st.markdown(f"""
                <div style="background-color: #3b82f6; color: white; padding: 8px 12px; 
                           border-radius: 8px; font-size: 12px; margin: 3px 0;">
                    <strong>{i+1}.</strong> {question}
                </div>
                """, unsafe_allow_html=True)
            
            with col_btn:
                if st.button("✕", key=f"remove_q_{i}", help=f"Rimuovi domanda {i+1}"):
                    questions_to_remove.append(question)
        
        # Rimuovi domande selezionate
        if questions_to_remove:
            for q in questions_to_remove:
                if q in current_questions:
                    current_questions.remove(q)
            st.session_state['questions_edited'] = current_questions
            st.rerun()
    
    # Aggiungi nuova domanda
    col_input, col_add = st.columns([4, 1])
    
    with col_input:
        new_question = st.text_input(
            "Aggiungi domanda:",
            key="new_question_input",
            placeholder="es: Quali sono i migliori utensili per...?"
        )
    
    with col_add:
        if st.button("➕", key="add_question_btn", type="primary", disabled=not new_question.strip()):
            if new_question.strip():
                clean_question = new_question.strip()
                if not clean_question.endswith('?'):
                    clean_question += '?'
                    
                if clean_question not in current_questions:
                    current_questions.append(clean_question)
                    st.session_state['questions_edited'] = current_questions
                    st.success(f"✅ Aggiunta domanda!")
                    st.rerun()
                else:
                    st.warning(f"⚠️ Domanda già presente!")
    
    # Aggiunta multipla
    with st.expander("⚡ Aggiunta multipla domande"):
        bulk_questions = st.text_area(
            "Una domanda per riga:",
            placeholder="Come scegliere gli utensili giusti?\nQuali sono i brand migliori?\nDove acquistare i prodotti?",
            height=100,
            key="bulk_questions"
        )
        
        if st.button("➕ Aggiungi tutte", key="add_bulk_questions"):
            if bulk_questions.strip():
                new_questions = []
                for q in bulk_questions.split('\n'):
                    clean_q = q.strip()
                    if clean_q and len(clean_q) > 5:
                        if not clean_q.endswith('?'):
                            clean_q += '?'
                        new_questions.append(clean_q)
                
                added_count = 0
                for question in new_questions:
                    if question not in current_questions:
                        current_questions.append(question)
                        added_count += 1
                
                if added_count > 0:
                    st.session_state['questions_edited'] = current_questions
                    st.success(f"✅ Aggiunte {added_count} domande!")
                    st.rerun()
    
    st.markdown(f"**📊 Totale domande:** {len(current_questions)}")
    
    # Pulsanti reset e clear
    col_reset, col_clear = st.columns(2)
    
    with col_reset:
        if st.button("🔄 Reset Originali", key="reset_questions", type="secondary"):
            original = st.session_state.get('questions_generated', [])
            st.session_state['questions_edited'] = original.copy()
            st.rerun()
    
    with col_clear:
        if st.button("🗑️ Cancella Tutte", key="clear_questions", type="secondary"):
            st.session_state['questions_edited'] = []
            st.rerun()

# Continuazione di Elaborazione_Articolo.py

# ============================================================================
# STEP 3: STRUTTURA PERSONALIZZATA
# ============================================================================

def display_structure_step(article: Dict[str, Any]):
    """Step 3: Generazione e modifica struttura articolo"""
    
    st.markdown('<div class="step-section">', unsafe_allow_html=True)
    st.markdown('<div class="step-header">📋 Step 3: Struttura Personalizzata</div>', unsafe_allow_html=True)
    
    # Se struttura non ancora generata
    if st.session_state['structure_generated'] is None:
        st.markdown("""
        <div style="background-color: #f0f4ff; border: 2px dashed #6366f1; border-radius: 8px; padding: 20px; text-align: center;">
            <h4 style="color: #4f46e5;">📋 Genera Struttura Personalizzata</h4>
            <p style="color: #4f46e5;">
                Crea una struttura di titoli e paragrafi usando un system prompt specifico.<br>
                <small>💰 <em>Questa operazione consumerà token API</em></small>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Campo per system prompt personalizzato
        system_prompt = st.text_area(
            "System Prompt personalizzato (opzionale):",
            value=st.session_state.get('system_prompt_structure', ''),
            height=100,
            placeholder="es: Crea una struttura per un articolo tecnico destinato a ingegneri, con focus su specifiche tecniche e casi d'uso pratici...",
            help="Lascia vuoto per usare il prompt di default ottimizzato per il settore industriale",
            key="system_prompt_input"
        )
        st.session_state['system_prompt_structure'] = system_prompt
        
        if st.button("📋 Genera Struttura", key="generate_structure_btn", type="primary"):
            track_event("genera_struttura", "elaborazione_articolo", {
                "article_id": st.session_state.get('current_article_id')
            })
            
            with st.spinner("🤖 Generazione struttura in corso..."):
                structure = generate_blog_structure(
                    article['full_content'], 
                    article['title'],
                    system_prompt
                )
                st.session_state['structure_generated'] = structure
                st.session_state['structure_edited'] = structure.copy()
            
            st.rerun()
    
    else:
        # Struttura generata - mostra risultati
        original_structure = st.session_state['structure_generated']
        final_structure = st.session_state.get('structure_edited', original_structure)
        
        structure_source = "personalizzata" if st.session_state['structure_edited'] != original_structure else "AI originale"
        header_color = "#f59e0b" if st.session_state['show_structure_editor'] else "#4f46e5"
        bg_color = "#fef7e0" if st.session_state['show_structure_editor'] else "#f0f4ff"
        
        st.markdown(f"""
        <div style="background-color: {bg_color}; border-left: 4px solid {header_color}; 
                   padding: 15px; margin: 10px 0; border-radius: 8px;">
            <h4 style="color: {header_color};">
                📋 Struttura Articolo ({len(final_structure)} elementi {structure_source})
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        # Mostra struttura
        if final_structure:
            if not st.session_state['show_structure_editor']:
                display_structure_preview(final_structure)
            else:
                st.markdown("---")
                display_structure_editor(final_structure)
        
        # Pulsanti azioni
        col1, col2, col3 = st.columns(3)
        
        with col1:
            editor_text = "🔧 Chiudi Editor" if st.session_state['show_structure_editor'] else "✏️ Modifica struttura"
            if st.button(editor_text, key="toggle_structure_editor", type="secondary", disabled=len(final_structure) == 0):
                st.session_state['show_structure_editor'] = not st.session_state['show_structure_editor']
                st.rerun()
        
        with col2:
            if st.button("🔄 Rigenera", key="regen_structure", type="secondary"):
                system_prompt = st.session_state.get('system_prompt_structure', '')
                with st.spinner("🤖 Rigenerazione struttura..."):
                    structure = generate_blog_structure(
                        article['full_content'], 
                        article['title'],
                        system_prompt
                    )
                    st.session_state['structure_generated'] = structure
                    st.session_state['structure_edited'] = structure.copy()
                    st.session_state['show_structure_editor'] = False
                st.rerun()
        
        with col3:
            if st.button("📋 Export JSON", key="export_structure_json", type="secondary", disabled=len(final_structure) == 0):
                export_data = {
                    "article_title": article['title'],
                    "structure": final_structure,
                    "total_elements": len(final_structure),
                    "source": structure_source,
                    "system_prompt_used": st.session_state.get('system_prompt_structure', 'default')
                }
                
                json_output = json.dumps(export_data, ensure_ascii=False, indent=2)
                st.text_area("Struttura JSON:", value=json_output, height=150)
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_structure_editor(structure_list: List[Dict[str, str]]):
    """Editor per la struttura dell'articolo"""
    st.markdown("""
    <div style="background-color: #fef7e0; border: 1px dashed #f59e0b; border-radius: 8px; padding: 15px;">
        <h4 style="color: #92400e;">✏️ Editor Struttura</h4>
    </div>
    """, unsafe_allow_html=True)
    
    current_structure = st.session_state.get('structure_edited', structure_list.copy())
    
    # Tipi disponibili
    available_types = [
        "titolo_principale", "sottotitolo", "sottotitolo_h3", "introduzione", 
        "paragrafo", "elenco_puntato", "conclusione", "call_to_action"
    ]
    
    if current_structure:
        st.markdown("**Elementi attuali:**")
        
        elements_to_remove = []
        
        for i, element in enumerate(current_structure):
            with st.container():
                col_content, col_type, col_actions = st.columns([3, 1, 1])
                
                with col_content:
                    new_content = st.text_area(
                        f"Elemento {i+1}:",
                        value=element.get("contenuto", ""),
                        height=80,
                        key=f"edit_content_{i}"
                    )
                    element["contenuto"] = new_content
                
                with col_type:
                    st.markdown("<br>", unsafe_allow_html=True)
                    new_type = st.selectbox(
                        "Tipo:",
                        options=available_types,
                        index=available_types.index(element.get("tipo", "paragrafo")) if element.get("tipo", "paragrafo") in available_types else 0,
                        key=f"edit_type_{i}"
                    )
                    element["tipo"] = new_type
                
                with col_actions:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    
                    col_up, col_down, col_del = st.columns(3)
                    
                    with col_up:
                        if st.button("↑", key=f"move_up_{i}", disabled=i==0, help="Sposta su"):
                            if i > 0:
                                current_structure[i], current_structure[i-1] = current_structure[i-1], current_structure[i]
                                st.session_state['structure_edited'] = current_structure
                                st.rerun()
                    
                    with col_down:
                        if st.button("↓", key=f"move_down_{i}", disabled=i==len(current_structure)-1, help="Sposta giù"):
                            if i < len(current_structure) - 1:
                                current_structure[i], current_structure[i+1] = current_structure[i+1], current_structure[i]
                                st.session_state['structure_edited'] = current_structure
                                st.rerun()
                    
                    with col_del:
                        if st.button("✕", key=f"delete_element_{i}", help="Elimina"):
                            elements_to_remove.append(element)
                
                st.markdown("<hr>", unsafe_allow_html=True)
        
        # Rimuovi elementi selezionati
        if elements_to_remove:
            for element in elements_to_remove:
                if element in current_structure:
                    current_structure.remove(element)
            st.session_state['structure_edited'] = current_structure
            st.rerun()
    
    # Aggiungi nuovo elemento
    st.markdown("**➕ Aggiungi nuovo elemento:**")
    col_new_type, col_new_content, col_add = st.columns([1, 2, 1])
    
    with col_new_type:
        new_element_type = st.selectbox(
            "Tipo elemento:",
            options=available_types,
            key="new_element_type"
        )
    
    with col_new_content:
        new_element_content = st.text_area(
            "Contenuto elemento:",
            placeholder="Inserisci il contenuto per il nuovo elemento...",
            height=80,
            key="new_element_content"
        )
    
    with col_add:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Aggiungi", key="add_element", type="primary", disabled=not new_element_content.strip()):
            if new_element_content.strip():
                new_element = {
                    "tipo": new_element_type,
                    "contenuto": new_element_content.strip()
                }
                current_structure.append(new_element)
                st.session_state['structure_edited'] = current_structure
                st.success(f"✅ Aggiunto elemento '{new_element_type}'!")
                st.rerun()
    
    # Salva modifiche
    st.session_state['structure_edited'] = current_structure
    
    st.markdown(f"**📊 Totale elementi:** {len(current_structure)}")

# Continuazione di Elaborazione_Articolo.py

# ============================================================================
# STEP 4: BOZZA BLOG INTELLIGENTE
# ============================================================================

def display_blog_draft_step(article: Dict[str, Any]):
    """Step 4: Generazione bozza blog intelligente"""
    
    st.markdown('<div class="step-section">', unsafe_allow_html=True)
    st.markdown('<div class="step-header">✍️ Step 4: Bozza Blog Intelligente</div>', unsafe_allow_html=True)
    
    # Se bozza non ancora generata
    if st.session_state['blog_draft_generated'] is None:
        # Raccoglie dati da step precedenti - CON SAFE DEFAULTS
        final_keywords = st.session_state.get('keywords_edited') or []  # FIX: garantisce lista vuota
        keywords_volumes = st.session_state.get('keywords_volumes') or {}  # FIX: garantisce dict vuoto
        final_questions = st.session_state.get('questions_edited') or []  # FIX: garantisce lista vuota
        structured_summary = st.session_state.get('summary_generated') or ''  # FIX: garantisce stringa vuota
        blog_structure = st.session_state.get('structure_edited', None)
        
        # Calcola info keywords (ora sicuro)
        high_volume_keywords = [kw for kw in final_keywords if keywords_volumes.get(kw, 0) >= 1000]
        total_volume = sum(keywords_volumes.values()) if keywords_volumes else 0
        
        st.markdown("""
        <div class="blog-draft-section">
            <h4 style="color: #92400e; text-align: center;">✍️ Genera Bozza Blog Intelligente</h4>
            <p style="color: #065f46; text-align: center;">
                Genera una bozza prioritizzando le keywords con volume di ricerca più alto.<br>
                <small>💰 <em>Questa operazione consumerà token OpenAI</em></small>
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Info sui contenuti disponibili
        if final_keywords and keywords_volumes:
            st.info(f"📊 **Keywords con volumi:** {len([kw for kw in final_keywords if keywords_volumes.get(kw, 0) > 0])} su {len(final_keywords)} | 🔥 **High-volume (1k+):** {len(high_volume_keywords)} | 📈 **Volume totale:** {total_volume:,}")
        
        optimization_info = []
        if structured_summary:
            optimization_info.append("riassunto strutturato")
        if final_keywords:
            kw_info = f"{len(final_keywords)} keywords"
            if total_volume > 0:
                kw_info += f" ({len(high_volume_keywords)} prioritarie, {total_volume:,} vol.tot)"
            optimization_info.append(kw_info)
        if final_questions:
            optimization_info.append(f"{len(final_questions)} domande")
        if blog_structure:
            optimization_info.append(f"struttura personalizzata ({len(blog_structure)} elementi)")
        
        optimization_text = " + ".join(optimization_info) if optimization_info else "contenuto base"
        
        st.info(f"🧠 **Ottimizzazioni disponibili:** {optimization_text}")
        
        has_minimum_content = bool(structured_summary or final_keywords or final_questions)
        
        if st.button("✍️ Genera Bozza Blog", key="generate_blog_draft_btn", type="primary", 
                disabled=not has_minimum_content,
                help="Genera bozza usando tutti i dati disponibili" if has_minimum_content else "Completa almeno uno step precedente"):
            
            track_event("genera_bozza_blog", "elaborazione_articolo", {
                "article_id": st.session_state.get('current_article_id'),
                "has_keywords": len(final_keywords) > 0,
                "has_questions": len(final_questions) > 0,
                "has_summary": bool(structured_summary),
                "has_structure": blog_structure is not None
            })
            
            with st.spinner("🤖 Generazione bozza blog intelligente..."):
                blog_draft = generate_intelligent_blog_draft(
                    content=article['full_content'],
                    title=article['title'], 
                    structured_summary=structured_summary,
                    keywords=final_keywords,
                    questions=final_questions,
                    blog_structure=blog_structure
                )
                st.session_state['blog_draft_generated'] = blog_draft
                st.session_state['blog_draft_edited'] = blog_draft
            
            st.rerun()
        
        if not has_minimum_content:
            st.info("💡 **Suggerimento:** Genera prima il riassunto e/o estrai keywords/domande per una bozza completa e ottimizzata.")
    
    else:
        # Bozza generata - mostra risultati
        original_blog_draft = st.session_state['blog_draft_generated']
        final_blog_draft = st.session_state.get('blog_draft_edited', original_blog_draft)
        
        blog_draft_source = "personalizzata" if st.session_state['blog_draft_edited'] != original_blog_draft else "AI originale"
        header_color = "#f59e0b" if st.session_state['show_blog_editor'] else "#065f46"
        bg_color = "#fef7e0" if st.session_state['show_blog_editor'] else "#ecfdf5"
        
        # Info sulle ottimizzazioni usate
        used_keywords = st.session_state.get('keywords_edited', [])
        used_questions = st.session_state.get('questions_edited', [])
        used_volumes = st.session_state.get('keywords_volumes', {})
        used_summary = st.session_state.get('summary_generated', '')
        
        optimization_info = []
        if used_summary:
            optimization_info.append("riassunto strutturato")
        if used_keywords:
            high_vol = len([kw for kw in used_keywords if used_volumes.get(kw, 0) >= 1000])
            total_vol = sum(used_volumes.values()) if used_volumes else 0
            kw_info = f"{len(used_keywords)} keywords"
            if total_vol > 0:
                kw_info += f" ({high_vol} prioritarie, {total_vol:,} vol.tot)"
            optimization_info.append(kw_info)
        if used_questions:
            optimization_info.append(f"{len(used_questions)} domande")
        
        optimization_text = " + ".join(optimization_info) if optimization_info else "contenuto base"
        
        st.markdown(f"""
        <div style="background-color: {bg_color}; border-left: 4px solid {header_color}; 
                   padding: 15px; margin: 10px 0; border-radius: 8px;">
            <h4 style="color: {header_color};">
                ✅ Bozza Blog ({blog_draft_source})
            </h4>
            <small style="color: {header_color};">🧠 Ottimizzata con: {optimization_text}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Mostra contenuto o editor
        if not st.session_state['show_blog_editor']:
            st.markdown("### 📖 Bozza Blog Generata")
            st.markdown(final_blog_draft)
        else:
            display_blog_draft_editor(final_blog_draft)
        
        # Pulsanti di controllo
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            editor_text = "🔧 Chiudi Editor" if st.session_state['show_blog_editor'] else "✏️ Modifica bozza"
            if st.button(editor_text, key="toggle_blog_editor", type="secondary"):
                st.session_state['show_blog_editor'] = not st.session_state['show_blog_editor']
                st.rerun()
        
        with col2:
            if st.button("📋 Copia Bozza", key="copy_blog_draft"):
                st.text_area(
                    "Bozza per copia:",
                    value=final_blog_draft,
                    height=150,
                    key="copy_area_blog",
                    help="Seleziona tutto (Ctrl+A) e copia (Ctrl+C)"
                )
        
        with col3:
            if st.button("🔄 Rigenera", key="regen_blog_draft", type="secondary"):
                with st.spinner("🤖 Rigenerazione bozza intelligente..."):
                    blog_structure = st.session_state.get('structure_edited', None)
                    
                    blog_draft = generate_intelligent_blog_draft(
                        content=article['full_content'],
                        title=article['title'], 
                        structured_summary=used_summary,
                        keywords=used_keywords,
                        questions=used_questions,
                        blog_structure=blog_structure
                    )
                    st.session_state['blog_draft_generated'] = blog_draft
                    st.session_state['blog_draft_edited'] = blog_draft
                    st.session_state['show_blog_editor'] = False
                
                st.rerun()
        
        with col4:
            if st.button("🎯 Modifica Contenuti", key="change_content_blog", type="secondary"):
                track_event("reset_blog_draft", "elaborazione_articolo", {
                    "article_id": st.session_state.get('current_article_id')
                })
                st.session_state['blog_draft_generated'] = None
                st.session_state['blog_draft_edited'] = None
                st.session_state['show_blog_editor'] = False
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)


def display_blog_draft_editor(blog_draft_text: str):
    """Editor per la bozza del blog"""
    st.markdown("""
    <div style="background-color: #fef7e0; border: 1px dashed #f59e0b; border-radius: 8px; padding: 15px; margin: 10px 0;">
        <h4 style="color: #92400e;">✏️ Editor Bozza Blog</h4>
        <p style="color: #92400e; font-size: 12px;">
            Modifica direttamente il contenuto della bozza. Le modifiche saranno salvate automaticamente.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    current_draft = st.session_state.get('blog_draft_edited', blog_draft_text)
    
    # Editor principale
    new_draft = st.text_area(
        "Contenuto bozza:",
        value=current_draft,
        height=400,
        key="blog_draft_editor",
        help="Modifica direttamente il contenuto della bozza blog. Supporta Markdown."
    )
    
    # Salva automaticamente
    st.session_state['blog_draft_edited'] = new_draft
    
    # Statistiche del testo
    word_count = len(new_draft.split())
    char_count = len(new_draft)
    lines_count = len(new_draft.split('\n'))
    
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    with col_stats1:
        st.metric("📝 Parole", word_count)
    with col_stats2:
        st.metric("📄 Caratteri", char_count)
    with col_stats3:
        st.metric("📋 Righe", lines_count)
    
    # Pulsanti utility
    col_reset, col_preview = st.columns(2)
    
    with col_reset:
        if st.button("🔄 Ripristina Originale", 
                    key="reset_blog_draft_editor", 
                    type="secondary",
                    help="Ripristina la bozza AI originale"):
            st.session_state['blog_draft_edited'] = st.session_state['blog_draft_generated']
            st.rerun()
    
    with col_preview:
        if st.button("👁️ Anteprima Markdown", 
                    key="preview_blog_draft",
                    help="Mostra come apparirà il markdown formattato"):
            with st.expander("📖 Anteprima Formattata", expanded=True):
                st.markdown(new_draft)
    
    # Suggerimenti
    with st.expander("💡 Suggerimenti per l'editing"):
        st.markdown("""
        **Formattazione Markdown supportata:**
        - `# Titolo` per intestazioni H1
        - `## Sottotitolo` per intestazioni H2  
        - `### Sottotitolo H3` per intestazioni H3
        - `**testo in grassetto**` per enfatizzare
        - `*testo in corsivo*` per corsivo
        - `- elemento lista` per elenchi puntati
        - `1. elemento numerato` per elenchi numerati
        
        **Suggerimenti SEO:**
        - Mantieni le keywords principali nei titoli
        - Usa sottotitoli per strutturare il contenuto
        - Includi call-to-action verso la fine
        - Verifica che il contenuto risponda alle domande del target
        """)

# Continuazione e conclusione di Elaborazione_Articolo.py

# ============================================================================
# SIDEBAR
# ============================================================================

def display_sidebar(article: Dict[str, Any]):
    """Sidebar con pulsanti utility"""
    with st.sidebar:
        st.markdown("### 🔗 Azioni Rapide")
        
        # Link all'articolo originale
        st.link_button("🌐 Leggi Originale", article['link'], use_container_width=True)
        
        st.markdown("---")
        
        # Pulsante torna alla lista
        if st.button("⬅️ Torna alla Lista", use_container_width=True, type="primary"):
            track_event("torna_lista", "elaborazione_articolo", {
                "article_id": st.session_state.get('current_article_id')
            })
            st.switch_page("RSS_Feed_Reader.py")
        
        st.markdown("---")
        
        # Info progresso step
        st.markdown("### 📊 Progresso Step")
        
        steps_completed = 0
        total_steps = 4
        
        # Step 1: Keywords
        if st.session_state.get('keywords_extracted') is not None:
            st.success("✅ Step 1: Keywords")
            steps_completed += 1
        else:
            st.info("⏳ Step 1: Keywords")
        
        # Step 2: Questions (già fatto nell'header)
        if st.session_state.get('questions_generated') is not None:
            st.success("✅ Step 2: Domande")
            steps_completed += 1
        else:
            st.info("⏳ Step 2: Domande")
        
        # Step 3: Structure
        if st.session_state.get('structure_generated') is not None:
            st.success("✅ Step 3: Struttura")
            steps_completed += 1
        else:
            st.info("⏳ Step 3: Struttura")
        
        # Step 4: Blog Draft
        if st.session_state.get('blog_draft_generated') is not None:
            st.success("✅ Step 4: Bozza Blog")
            steps_completed += 1
        else:
            st.info("⏳ Step 4: Bozza Blog")
        
        progress = steps_completed / total_steps
        st.progress(progress)
        st.caption(f"{steps_completed}/{total_steps} step completati")
        
        st.markdown("---")
        
        # Reset tutto
        if st.button("🔄 Reset Tutto", use_container_width=True, type="secondary"):
            if st.button("⚠️ Conferma Reset", use_container_width=True, type="secondary"):
                track_event("reset_all_steps", "elaborazione_articolo", {
                    "article_id": st.session_state.get('current_article_id')
                })
                
                # Reset tutti gli step
                st.session_state['keywords_extracted'] = None
                st.session_state['keywords_edited'] = None
                st.session_state['keywords_volumes'] = {}
                st.session_state['show_keywords_editor'] = False
                
                st.session_state['summary_generated'] = None
                st.session_state['questions_generated'] = None
                st.session_state['questions_edited'] = None
                st.session_state['show_questions_editor'] = False
                
                st.session_state['structure_generated'] = None
                st.session_state['structure_edited'] = None
                st.session_state['system_prompt_structure'] = ""
                st.session_state['show_structure_editor'] = False
                
                st.session_state['blog_draft_generated'] = None
                st.session_state['blog_draft_edited'] = None
                st.session_state['show_blog_editor'] = False
                
                st.rerun()


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Inizializza session state
    init_session_state()
    
    # ✅ NUOVO: Leggi articolo da query params se presente
    query_params = st.query_params
    
    if 'data' in query_params and st.session_state['current_article'] is None:
        try:
            # Decodifica l'articolo da base64
            article_b64 = unquote(query_params['data'])
            article_json = base64.b64decode(article_b64).decode('utf-8')
            article = json.loads(article_json)
            
            # Salva in session state
            article_id = hashlib.md5(article['link'].encode()).hexdigest()
            st.session_state['current_article'] = article
            st.session_state['current_article_id'] = article_id
            
        except Exception as e:
            st.error(f"Errore nel caricamento dell'articolo: {e}")
    
    # Verifica che ci sia un articolo
    if st.session_state['current_article'] is None:
        st.warning("⚠️ Nessun articolo selezionato.")
        if st.button("⬅️ Vai alla Lista"):
            st.markdown('<a href="/" target="_blank">Torna alla lista</a>', unsafe_allow_html=True)
        st.stop()
    
    article = st.session_state['current_article']
    
    # Sidebar
    display_sidebar(article)
    
    # Header con immagine + riassunto
    display_article_header(article)
    
    # Steps
    display_keywords_step(article)
    
    st.markdown("---")
    
    display_questions_step(article)
    
    st.markdown("---")
    
    display_structure_step(article)
    
    st.markdown("---")
    
    display_blog_draft_step(article)
    
    # Chiudi layout wrapper
    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
