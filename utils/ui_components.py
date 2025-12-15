import streamlit as st
import re
from typing import List, Dict, Any

# ============================================================================
# CSS GLOBALE
# ============================================================================

def inject_custom_css():
    """Inietta CSS personalizzato per l'intera app"""
    st.markdown("""
    <style>
        /* Reset margini hr */
        hr {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* Scroll smooth */
        html {
            scroll-behavior: smooth;
        }
        
        /* Article cards per lista */
        .article-card {
            border: 1px solid #e1e5e9;
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
            background-color: #fafafa;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        
        .article-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .article-title {
            font-size: 18px;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 10px;
        }
        
        .article-meta {
            color: #6b7280;
            font-size: 14px;
            margin-bottom: 10px;
        }
        
        .article-content {
            color: #374151;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        
        .category-tag {
            background-color: #3b82f6;
            color: white;
            padding: 4px 8px;
            border-radius: 15px;
            font-size: 12px;
            margin-right: 5px;
        }
        
        /* Keywords tags */
        .keyword-tag {
            background-color: #10b981;
            color: white;
            padding: 5px 10px;
            border-radius: 12px;
            font-size: 12px;
            text-align: center;
            margin: 2px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        
        .keyword-volume {
            font-size: 9px;
            background-color: rgba(255,255,255,0.2);
            border-radius: 6px;
            padding: 1px 4px;
            margin-left: 3px;
        }
        
        /* Sezioni colorate */
        .ai-summary {
            background-color: #f0f9ff;
            border-left: 4px solid #3b82f6;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            color: #1e40af;
        }
        
        .keywords-section {
            background-color: #f0fdf4;
            border-left: 4px solid #10b981;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            color: #065f46;
        }
        
        .blog-draft-section {
            background-color: #fef7e0;
            border-left: 4px solid #f59e0b;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            color: #92400e;
        }
        
        /* Layout elaborazione articolo */
        .elaboration-layout {
            max-width: 85%;
            margin: 0 auto;
        }
        
        .summary-row {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .image-column {
            flex: 0 0 40%;
        }
        
        .summary-column {
            flex: 0 0 60%;
        }
        
        .image-container {
            width: 100%;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .article-image {
            width: 100%;
            height: auto;
            object-fit: cover;
        }
        
        .no-image-placeholder {
            width: 100%;
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #f3f4f6;
            border: 2px dashed #d1d5db;
            border-radius: 8px;
            color: #6b7280;
            font-size: 48px;
        }
        
        .summary-container {
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 24px;
            height: 100%;
        }
        
        .summary-text {
            color: #374151;
            line-height: 1.8;
            font-size: 15px;
        }
        
        /* Step sections */
        .step-section {
            margin: 30px 0;
            padding: 20px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .step-header {
            font-size: 20px;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }
    </style>
    """, unsafe_allow_html=True)


# ============================================================================
# COMPONENTI UI PER PREVIEW STRUTTURE
# ============================================================================

def display_structure_preview(structure_list: List[Dict[str, str]]):
    """Mostra anteprima della struttura generata con evidenziazione delle tracce"""
    structure_html = ""
    for i, element in enumerate(structure_list, 1):
        tipo = element.get("tipo", "paragrafo")
        contenuto = element.get("contenuto", "")
        
        # Colori e icone per tipo
        type_config = {
            "titolo_principale": {"color": "#dc2626", "icon": "🎯", "bg": "#fef2f2"},
            "sottotitolo": {"color": "#2563eb", "icon": "📌", "bg": "#eff6ff"}, 
            "sottotitolo_h3": {"color": "#7c3aed", "icon": "📍", "bg": "#f5f3ff"},
            "introduzione": {"color": "#059669", "icon": "🚀", "bg": "#ecfdf5"},
            "paragrafo": {"color": "#374151", "icon": "📝", "bg": "#f9fafb"},
            "elenco_puntato": {"color": "#ea580c", "icon": "📋", "bg": "#fff7ed"},
            "conclusione": {"color": "#7c2d12", "icon": "🎯", "bg": "#fef7ed"},
            "call_to_action": {"color": "#be185d", "icon": "🔔", "bg": "#fdf2f8"},
            "errore": {"color": "#dc2626", "icon": "❌", "bg": "#fef2f2"}
        }
        
        config = type_config.get(tipo, type_config["paragrafo"])
        
        # Evidenzia le tracce in modo diverso
        display_content = contenuto
        if '[TRACCIA' in contenuto.upper():
            display_content = contenuto.replace('[TRACCIA', '<strong style="color: #f59e0b;">[GUIDA</strong>')
            display_content = display_content.replace('[traccia', '<strong style="color: #f59e0b;">[GUIDA</strong>')
        
        # Mostra tutto il contenuto se contiene tracce, altrimenti tronca
        if '[TRACCIA' in contenuto.upper() or '[traccia' in contenuto.lower():
            final_content = display_content
        else:
            final_content = display_content[:200] + ('...' if len(display_content) > 200 else '')
        
        structure_html += f"""
        <div style="background-color: {config['bg']}; border-left: 3px solid {config['color']}; 
                   padding: 10px; margin: 5px 0; border-radius: 6px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 5px;">
                <span>{config['icon']}</span>
                <strong style="color: {config['color']}; font-size: 12px; text-transform: uppercase;">
                    {tipo.replace('_', ' ')}
                </strong>
                <span style="color: #6b7280; font-size: 11px;">#{i}</span>
            </div>
            <div style="color: {config['color']}; font-size: 14px; line-height: 1.4;">
                {final_content}
            </div>
        </div>
        """
    
    st.markdown(structure_html, unsafe_allow_html=True)


def display_keywords_with_volumes(keywords: List[str], volumes: Dict[str, int]):
    """Mostra keywords con volumi in formato tag"""
    keywords_tags = ""
    total_volume = 0
    high_volume_count = 0
    
    # Ordina per volume
    keywords_with_volumes = [(kw, volumes.get(kw, 0)) for kw in keywords]
    keywords_with_volumes.sort(key=lambda x: x[1], reverse=True)
    
    for keyword, volume in keywords_with_volumes:
        if volume > 0:
            total_volume += volume
            if volume >= 1000:
                high_volume_count += 1
            volume_display = f'<span class="keyword-volume">{volume:,}</span>'
            tag_style = 'style="background-color: #059669;"' if volume >= 1000 else ''
        else:
            volume_display = f'<span class="keyword-volume">0</span>'
            tag_style = 'style="background-color: #6b7280;"'
        
        keywords_tags += f'<span class="keyword-tag" {tag_style}>{keyword} {volume_display}</span>'
    
    volume_summary = f"""
    <div style="margin-top: 10px; padding: 8px; background-color: rgba(16, 185, 129, 0.1); border-radius: 6px;">
        <small>📊 <strong>Volume totale:</strong> {total_volume:,} ricerche/mese | 
        ⭐ <strong>High-volume (1k+):</strong> {high_volume_count}/{len(keywords)}</small>
    </div>
    """ if total_volume > 0 else ""
    
    st.markdown(f"""
    <div style="margin: 10px 0;">
        {keywords_tags}
        {volume_summary}
    </div>
    """, unsafe_allow_html=True)


def display_questions_list(questions: List[str]):
    """Mostra lista domande in formato card"""
    questions_html = ""
    for i, question in enumerate(questions, 1):
        questions_html += f"""
        <div style="background-color: rgba(59, 130, 246, 0.1); border-radius: 6px; 
                   padding: 8px 12px; margin: 5px 0; border-left: 3px solid #3b82f6;">
            <strong>{i}.</strong> {question}
        </div>
        """
    
    st.markdown(questions_html, unsafe_allow_html=True)