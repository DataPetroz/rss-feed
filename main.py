
# App RSS Feed Reader per analisi competitor e generazione bozze blog
##Debuggata e semplificata.

#= Salvare su DB gli articoli scaricati con data, sito e categoria
#= Utilizzare gli articoli simili (App per calcolo di similarità) per produrre articoli ancora più prestanti.
## https://chatgpt.com/share/68908f88-f180-8006-ae8e-a4b80e64bcea

# python -m streamlit run feed.py 

import streamlit as st
import feedparser
import requests
from datetime import datetime
import re
from bs4 import BeautifulSoup
import logging
import json
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from openai import AzureOpenAI
import http.client
import urllib.parse
import time

 # Configurazione logging
logging.basicConfig(level=logging.WARNING)

# Configurazione della pagina
st.set_page_config(
    page_title="RSS Feed Reader",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizzato
st.markdown("""
<style>
    .article-card {
        border: 1px solid #e1e5e9;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        background-color: #fafafa;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
    .summary-header {
        font-weight: bold;
        color: #1e40af;
        margin-bottom: 8px;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .keywords-header {
        font-weight: bold;
        color: #065f46;
        margin-bottom: 8px;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .approval-section {
        background-color: #f8f9fa;
        border: 2px dashed #6c757d;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
    }
    .keywords-approval-section {
        background-color: #f0fdf4;
        border: 2px dashed #10b981;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
    }
    .blog-draft-section {
        background-color: #fef7e0;
        border-left: 4px solid #f59e0b;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        color: #92400e;
        width: 100%;
        margin-top: 20px;
    }
    .blog-draft-header {
        font-weight: bold;
        color: #92400e;
        margin-bottom: 8px;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 5px;
    }
    .keywords-editor {
        background-color: #fef7e0;
        border-left: 4px solid #f59e0b;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        color: #92400e;
    }
    .keywords-editor-header {
        font-weight: bold;
        color: #92400e;
        margin-bottom: 8px;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Carica le variabili d'ambiente
load_dotenv("secure.env")

# Recupera endpoint e chiave API
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
ahrefs_api_token = os.getenv("AHREFS_API_KEY")

# Inizializza il client Azure OpenAI
try:
    client = AzureOpenAI(
        api_key=azure_api_key,
        api_version="2024-10-01-preview",
        azure_endpoint=azure_endpoint
    )
    deployment_name = 'gpt-4o-mini'
    AZURE_AVAILABLE = True
except Exception as e:
    logging.error(f"Errore inizializzazione Azure OpenAI: {e}")
    AZURE_AVAILABLE = False

# ============================================================================
# FUNZIONI AHREFS PER RICERCA VOLUMI
# ============================================================================

@st.cache_data(ttl=3600)  # Cache per 1 ora
def get_keyword_volume_ahrefs(keyword: str, country: str = "it") -> Dict[str, Any]:
    """Ottiene il volume di ricerca per una singola keyword usando Ahrefs API"""
    if not ahrefs_api_token:
        return {
            "keyword": keyword,
            "volume": 0,
            "status": "error",
            "message": "Token API Ahrefs non configurato"
        }
    
    try:
        conn = http.client.HTTPSConnection("api.ahrefs.com")
        kw_encoded = urllib.parse.quote_plus(keyword.lower().strip())
        endpoint = f"/v3/keywords-explorer/overview?select=volume_monthly&country={country}&keywords={kw_encoded}"
        
        headers = {
            'Accept': "application/json",
            'Authorization': f"Bearer {ahrefs_api_token}"
        }
        
        conn.request("GET", endpoint, headers=headers)
        response = conn.getresponse()
        
        result = {
            "keyword": keyword,
            "volume": 0,
            "status": "success",
            "message": ""
        }
        
        if response.status == 200:
            data = response.read().decode("utf-8")
            parsed = json.loads(data)
            keywords_data = parsed.get("keywords", [])
            
            if keywords_data:
                volume = keywords_data[0].get("volume_monthly", 0)
                result["volume"] = volume if volume is not None else 0
        
        conn.close()
        return result
        
    except Exception as e:
        return {
            "keyword": keyword,
            "volume": 0,
            "status": "error", 
            "message": f"Errore connessione: {str(e)}"
        }

def get_multiple_keywords_volumes(keywords_list: List[str], country: str = "it") -> Dict[str, Dict[str, Any]]:
    """Ottiene i volumi per una lista di keywords con rate limiting"""
    results = {}
    total_keywords = len(keywords_list)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, keyword in enumerate(keywords_list):
        progress = (i + 1) / total_keywords
        progress_bar.progress(progress)
        status_text.text(f"Processando keyword {i+1}/{total_keywords}: {keyword}")
        
        result = get_keyword_volume_ahrefs(keyword, country)
        results[keyword] = result
        
        if i < total_keywords - 1:
            time.sleep(0.5)  # Rate limiting
    
    progress_bar.empty()
    status_text.empty()
    
    return results

# ============================================================================
# FUNZIONI DI UTILITY PER IMMAGINI
# ============================================================================

def extract_images_from_html(html_content):
    """Estrae tutte le immagini dal contenuto HTML"""
    if not html_content:
        return []
    
    images = []
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        img_tags = soup.find_all('img')
        
        for img in img_tags:
            src = img.get('src')
            if src and src.strip() and not src.startswith('data:'):
                if not any(skip in src.lower() for skip in ['placeholder', 'avatar', 'logo-automotive-avatar']):
                    images.append(src.strip())
    except:
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        matches = re.findall(img_pattern, html_content, re.IGNORECASE)
        
        for match in matches:
            clean_url = match.strip()
            if clean_url and not clean_url.startswith('data:'):
                if not any(skip in clean_url.lower() for skip in ['placeholder', 'avatar', 'logo-automotive-avatar']):
                    images.append(clean_url)
    
    return images

def extract_first_image_from_feed_entry(entry):
    """Estrae la prima immagine valida da un entry del feed RSS"""
    content_fields = []
    
    if hasattr(entry, 'content') and entry.content:
        for content_item in entry.content:
            if hasattr(content_item, 'value'):
                content_fields.append(content_item.value)
    
    if hasattr(entry, 'summary') and entry.summary:
        content_fields.append(entry.summary)
    
    if hasattr(entry, 'description') and entry.description:
        content_fields.append(entry.description)
    
    for content in content_fields:
        if content:
            images = extract_images_from_html(content)
            if images:
                return images[0]
    
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enclosure in entry.enclosures:
            if hasattr(enclosure, 'type') and enclosure.type and 'image' in enclosure.type:
                return enclosure.href
    
    return None

def clean_html_content(html_content):
    """Pulisce il contenuto HTML e estrae solo il testo"""
    if not html_content:
        return ""
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for element in soup(['script', 'style', 'nav', 'header', 'footer']):
        element.decompose()
    
    text = soup.get_text()
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r' +', ' ', text)
    text = text.strip()
    
    return text

# ============================================================================
# FUNZIONI AI AZURE OPENAI
# ============================================================================

@st.cache_data(ttl=1800)  # Cache per 30 minuti
def generate_summary_with_questions(content: str, title: str) -> Dict[str, Any]:
    """Genera un riassunto completo dell'articolo con domande correlate"""
    if not AZURE_AVAILABLE:
        return {
            "summary": "⚠️ Servizio AI non configurato.",
            "questions": []
        }
    
    if not content or len(content.strip()) < 50:
        return {
            "summary": "Contenuto troppo breve per generare un riassunto.",
            "questions": []
        }
    
    content_truncated = content[:3000] if len(content) > 3000 else content
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": """Sei un copywriter specializzato nei riassunti di contenuti industriali su ferramenta e utensili per cantieri.
                    
                    ###ISTRUZIONE###
                    Analizza il testo fornito e restituisci un JSON completo con:
                    1. "summary": riassunto strutturato e dettagliato del contenuto
                    2. "questions": array di 5-8 domande specifiche a cui l'articolo potrebbe rispondere
                    
                    ###STRUTTURA RIASSUNTO###
                    Il riassunto deve includere:
                    - Topic principale dell'articolo
                    - Contenuto iniziale e conclusioni principali
                    - Brand, prodotti o tecnologie specifiche citate
                    - Dettagli tecnici rilevanti
                    - Applicazioni pratiche discusse
                    - Target di riferimento (se identificabile)
                    
                    ###FORMATO OUTPUT###
                    Restituisci SOLO un JSON valido nel formato:
                    {
                      "summary": "<strong>Topic Principale:</strong> [topic]\\n\\n<strong>Contenuto:</strong> [riassunto dettagliato con contenuto iniziale e conclusioni]\\n\\n<strong>Brand/Prodotti Citati:</strong> [elenco brand e prodotti specifici, se presenti]\\n\\n<strong>Dettagli Tecnici:</strong> [specifiche tecniche rilevanti]\\n\\n<strong>Applicazioni Pratiche:</strong> [usi concreti discussi]",
                      "questions": [
                        "Domanda pratica 1?",
                        "Domanda pratica 2?",
                        "Domanda pratica 3?"
                      ]
                    }
                    
                    ###CRITERI DOMANDE###
                    - Domande pratiche che un professionista del settore potrebbe cercare
                    - Focus su "come", "quale", "quando", "perché", "dove"
                    - Specifiche per il contenuto dell'articolo
                    - Orientate all'uso pratico, scelta prodotti, implementazione tecnologie
                    """
                },
                {
                    "role": "user",
                    "content": f"""Analizza questo articolo del settore industriale:
                        TITOLO: {title}
                        CONTENUTO: {content_truncated}
                        Restituisci SOLO il JSON richiesto, senza spiegazioni aggiuntive."""
                }
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        try:
            parsed_response = json.loads(ai_response)
            
            if "summary" in parsed_response and "questions" in parsed_response:
                questions = []
                for q in parsed_response["questions"][:8]:
                    clean_q = q.strip()
                    if clean_q and len(clean_q) > 10:
                        if not clean_q.endswith('?'):
                            clean_q += '?'
                        questions.append(clean_q)
                
                return {
                    "summary": parsed_response["summary"],
                    "questions": questions
                }
            else:
                return {
                    "summary": ai_response,
                    "questions": []
                }
                
        except json.JSONDecodeError:
            return extract_summary_and_questions_from_text(ai_response)
        
    except Exception as e:
        logging.error(f"Errore Azure OpenAI: {e}")
        return {
            "summary": "⚠️ Errore nella generazione del riassunto.",
            "questions": []
        }

def extract_summary_and_questions_from_text(text: str) -> Dict[str, Any]:
    """Estrae summary e questions da testo non-JSON"""
    lines = text.split('\n')
    summary_lines = []
    questions = []
    
    current_section = "summary"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        is_question = (
            line.endswith('?') and 
            len(line) > 15 and
            any(word in line.lower() for word in ['come', 'quale', 'quando', 'perché', 'dove', 'cosa', 'chi'])
        )
        
        if is_question:
            current_section = "questions"
            clean_q = line.strip()
            clean_q = re.sub(r'^[\d\-\*\•\s"]+', '', clean_q).strip()
            clean_q = re.sub(r'",?\s*$', '', clean_q).strip()
            
            if clean_q and len(clean_q) > 10:
                if not clean_q.endswith('?'):
                    clean_q += '?'
                questions.append(clean_q)
        else:
            if current_section == "summary":
                if not any(marker in line.lower() for marker in [
                    '"summary":', '"questions":', '{', '}', '['
                ]):
                    summary_lines.append(line)
    
    summary = '\n'.join(summary_lines).strip()
    
    return {
        "summary": summary if summary else text,
        "questions": questions[:8]
    }

@st.cache_data(ttl=1800)  # Cache per 30 minuti
def extract_keywords(content: str, title: str) -> List[str]:
    """Estrae le keyword principali dell'articolo usando Azure OpenAI GPT-4o-mini"""
    if not AZURE_AVAILABLE:
        return ["⚠️ Servizio AI non configurato"]
    
    if not content or len(content.strip()) < 50:
        return ["Contenuto troppo breve"]
    
    content_truncated = content[:3000] if len(content) > 3000 else content
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": """Sei un esperto SEO e analista di contenuti specializzato nel settore industriale, logistica, ferramenta, utensili per cantieri e automazione. Il tuo compito è analizzare testi tecnici e identificare le query SEO per cui sembrano essere ottimizzati.

                    ### ISTRUZIONE
                    Estrai keyword rilevanti per il SEO, concentrandoti su termini che le persone potrebbero realmente cercare su Google.

                    ### CRITERI PER L'ESTRAZIONE:
                    - Dai priorità a keyword tecniche, specifiche del settore.
                    - Includi nomi di strumenti, tecnologie, processi, sistemi o applicazioni concrete.
                    - Inserisci anche entità rilevanti (es. brand, tecnologie emergenti, soluzioni software).
                    - Non estrarre parole troppo generiche o slegate dal contesto tecnico/logistico.
                    - Le keyword possono essere singole parole o frasi brevi usabili come query di ricerca.
                    - Evita articoli, preposizioni e parole funzionali.
                    - Massimo 10 keyword per mantenere la qualità

                    ### FORMATO OUTPUT:
                    Restituisci SOLO le keyword separate da virgola, senza spiegazioni aggiuntive.
                    Non includere numerazioni, trattini o altri caratteri speciali.
                        """
                },
                {
                    "role": "user",
                    "content": f"""Estrai le keyword principali da questo articolo del settore industriale:

                TITOLO: {title}
                
                CONTENUTO: {content_truncated}
                
                Restituisci SOLO le keyword separate da virgola, senza spiegazioni aggiuntive."""
                }
            ],
            max_tokens=200,
            temperature=0.2
        )
        
        keywords_text = response.choices[0].message.content.strip()
        
        if not keywords_text or len(keywords_text) < 3:
            return ["Impossibile estrarre keyword"]
        
        keywords = [kw.strip() for kw in keywords_text.split(',') if kw.strip()]
        
        cleaned_keywords = []
        for kw in keywords[:10]:
            clean_kw = re.sub(r'[^\w\s-]', '', kw).strip()
            if clean_kw and len(clean_kw) > 2:
                cleaned_keywords.append(clean_kw.title())
        
        return cleaned_keywords if cleaned_keywords else ["Nessuna keyword identificata"]
        
    except Exception as e:
        logging.error(f"Errore Azure OpenAI per keywords: {e}")
        return ["⚠️ Errore nell'estrazione keywords"]

@st.cache_data(ttl=1800)  # Cache per 30 minuti  
def generate_intelligent_blog_draft(content: str, title: str, structured_summary: str, keywords: List[str], questions: List[str]) -> str:
    """Genera una bozza di articolo intelligente usando riassunto, keywords e domande"""
    if not AZURE_AVAILABLE:
        return "⚠️ Servizio AI non configurato."
    
    if not content or len(content.strip()) < 50:
        return "Contenuto troppo breve per generare una bozza."
    
    content_truncated = content[:3500] if len(content) > 3500 else content
    keywords_text = ", ".join(keywords[:10]) if keywords else ""
    questions_text = "\n".join([f"- {q}" for q in questions[:8]]) if questions else ""
    summary_for_prompt = structured_summary if structured_summary else ""
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": """Sei un copywriter esperto specializzato nel settore industriale, ferramenta e utensili per cantieri.
                    
                    ###ISTRUZIONE###
                    Trasforma l'articolo fornito in una bozza ottimizzata per blog aziendale seguendo questi criteri:
                    
                    STRUTTURA:
                    1. Titolo accattivante e SEO-friendly
                    2. Introduzione coinvolgente (2-3 paragrafi)
                    3. Corpo dell'articolo con sottotitoli H2/H3
                    4. Conclusione con call-to-action
                    
                    STILE:
                    - Tono professionale ma accessibile
                    - Integra naturalmente le keyword fornite
                    - Usa elenchi puntati quando appropriato
                    - Includi informazioni tecniche precise
                    - Aggiungi valore pratico per il lettore
                    - Incorpora le domande fornite come sezioni o FAQ
                    - Utilizza le informazioni del riassunto per arricchire il contenuto
                    
                    OTTIMIZZAZIONE SEO:
                    - Keyword density equilibrata
                    - Titoli dei paragrafi ottimizzati
                    
                    FORMATO OUTPUT:
                    Restituisci la bozza in formato Markdown con:
                    - # per il titolo principale
                    - ## per i sottotitoli
                    - **grassetto** per enfasi
                    - * per elenchi puntati"""
                },
                {
                    "role": "user",
                    "content": f"""Trasforma questo articolo in una bozza ottimizzata per il nostro blog aziendale:

TITOLO ORIGINALE: {title}

KEYWORDS DA INTEGRARE: {keywords_text}

RIASSUNTO STRUTTURATO (usa per arricchire il contenuto):
{summary_for_prompt}

DOMANDE DA INCORPORARE (come sezioni o FAQ):
{questions_text}

CONTENUTO ORIGINALE: {content_truncated}

Crea una bozza completa, professionale e ottimizzata SEO mantenendo l'accuratezza tecnica. Integra naturalmente le informazioni del riassunto e trasforma le domande in sezioni utili."""
                }
            ],
            max_tokens=1800,
            temperature=0.4
        )
        
        blog_draft = response.choices[0].message.content.strip()
        
        if not blog_draft or len(blog_draft) < 100:
            return "Impossibile generare la bozza intelligente dell'articolo."
            
        return blog_draft
        
    except Exception as e:
        logging.error(f"Errore Azure OpenAI per blog draft intelligente: {e}")
        return "⚠️ Errore nella generazione della bozza intelligente."

# ============================================================================
# FUNZIONI PER FETCH E PROCESSING FEED RSS
# ============================================================================

@st.cache_data(ttl=1800)  # Cache per 30 minuti
def fetch_feed(url, category):
    """Recupera e processa un feed RSS con estrazione delle immagini"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        
        articles = []
        
        for entry in feed.entries:
            content = ""
            if hasattr(entry, 'content') and entry.content:
                content = clean_html_content(entry.content[0].value)
            elif hasattr(entry, 'summary'):
                content = clean_html_content(entry.summary)
            elif hasattr(entry, 'description'):
                content = clean_html_content(entry.description)
            
            preview = content[:700] + "..." if len(content) > 300 else content
            
            published = "Data non disponibile"
            if hasattr(entry, 'published'):
                try:
                    pub_date = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
                    published = pub_date.strftime('%d/%m/%Y %H:%M')
                except:
                    try:
                        pub_date = datetime.strptime(entry.published[:25], '%a, %d %b %Y %H:%M:%S')
                        published = pub_date.strftime('%d/%m/%Y %H:%M')
                    except:
                        published = entry.published
            
            categories = []
            if hasattr(entry, 'tags'):
                categories = [tag.term for tag in entry.tags]
            elif hasattr(entry, 'categories'):
                categories = entry.categories
            
            first_image_url = extract_first_image_from_feed_entry(entry)
            image_validated = bool(first_image_url)
            
            article = {
                'title': entry.get('title', 'Titolo non disponibile'),
                'link': entry.get('link', '#'),
                'published': published,
                'preview': preview,
                'full_content': content,
                'categories': categories,
                'source_category': category,
                'source_url': url,
                'image_url': first_image_url if image_validated else None,
                'has_image': image_validated
            }
            
            articles.append(article)
        
        return articles, len(articles)
        
    except Exception as e:
        st.error(f"❌ Errore nel recuperare il feed da {url}: {str(e)}")
        return [], 0

# ============================================================================
# FUNZIONI DI VISUALIZZAZIONE UI
# ============================================================================

def display_ai_summary_section(article, tab_name, article_index, enable_ai_summary):
    """Visualizza la sezione del riassunto AI con domande editabili"""
    if enable_ai_summary:
        summary_key = f"summary_{tab_name}_{article_index}_{hash(article['link'])}"
        questions_key = f"questions_{tab_name}_{article_index}_{hash(article['link'])}"
        edited_questions_key = f"edited_questions_{tab_name}_{article_index}_{hash(article['link'])}"
        approval_key = f"approve_{tab_name}_{article_index}_{hash(article['link'])}"
        show_questions_editor_key = f"show_questions_editor_{tab_name}_{article_index}_{hash(article['link'])}"
        
        if summary_key not in st.session_state:
            st.session_state[summary_key] = None
        if questions_key not in st.session_state:
            st.session_state[questions_key] = None
        if show_questions_editor_key not in st.session_state:
            st.session_state[show_questions_editor_key] = False
        
        if st.session_state[summary_key] is None:
            st.markdown(f"""
            <div class="approval-section">
                <h4 style="color: #6c757d; margin-bottom: 15px;">🤖 Step 2: Riassunto AI + Domande</h4>
                <p style="color: #6c757d; margin-bottom: 15px;">
                    Genera un riassunto automatico con domande correlate usando Azure OpenAI.<br>
                    <small>💰 <em>Questa operazione consumerà token API</em></small>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("✅ Genera Riassunto + Domande", key=approval_key, type="primary"):
                with st.spinner("🤖 Generazione riassunto e domande in corso..."):
                    ai_result = generate_summary_with_questions(article['full_content'], article['title'])
                    
                    summary = ai_result.get("summary", "")
                    questions = ai_result.get("questions", [])
                    
                    st.session_state[summary_key] = summary
                    st.session_state[questions_key] = questions
                st.rerun()

        else:
            summary = st.session_state[summary_key]
            original_questions = st.session_state.get(questions_key, [])
            
            if edited_questions_key in st.session_state:
                final_questions = st.session_state[edited_questions_key]
                questions_source = "personalizzate"
            else:
                safe_original_questions = original_questions if original_questions is not None else []
                st.session_state[edited_questions_key] = safe_original_questions.copy()
                final_questions = safe_original_questions
                questions_source = "AI originali"
            
            st.markdown(f"""
            <div class="ai-summary">
                <div class="summary-header">🤖 Riassunto AI</div>
                {summary}
            </div>
            """, unsafe_allow_html=True)
            
            questions_header_color = "#f59e0b" if st.session_state[show_questions_editor_key] else "#3b82f6"
            questions_bg_color = "#fef7e0" if st.session_state[show_questions_editor_key] else "#f0f9ff"
            
            st.markdown(f"""
            <div style="background-color: {questions_bg_color}; border-left: 4px solid {questions_header_color}; 
                       padding: 15px; margin: 10px 0; border-radius: 8px;">
                <h4 style="color: {questions_header_color}; margin-bottom: 10px;">
                    ❓ Domande Correlate ({len(final_questions)} {questions_source})
                </h4>
            </div>
            """, unsafe_allow_html=True)
            
            if final_questions:
                if not st.session_state[show_questions_editor_key]:
                    questions_html = ""
                    for i, question in enumerate(final_questions, 1):
                        questions_html += f"""
                        <div style="background-color: rgba(59, 130, 246, 0.1); border-radius: 6px; 
                                   padding: 8px 12px; margin: 5px 0; border-left: 3px solid #3b82f6;">
                            <strong>{i}.</strong> {question}
                        </div>
                        """
                    
                    st.markdown(questions_html, unsafe_allow_html=True)
                
                else:
                    display_questions_editor(final_questions, edited_questions_key, tab_name, article_index, hash(article['link']))
            
            else:
                st.markdown("""
                <div style="color: #6b7280; font-style: italic; text-align: center; padding: 20px;">
                    Nessuna domanda generata
                </div>
                """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                editor_text = "🔧 Chiudi Editor" if st.session_state[show_questions_editor_key] else "🎯 Modifica domande"
                editor_key = f"toggle_questions_editor_{tab_name}_{article_index}_{hash(article['link'])}"
                if st.button(editor_text, key=editor_key, type="secondary", 
                           disabled=len(final_questions) == 0):
                    st.session_state[show_questions_editor_key] = not st.session_state[show_questions_editor_key]
            
            with col2:
                regen_key = f"regen_{tab_name}_{article_index}_{hash(article['link'])}"
                if st.button("🔄 Rigenera", key=regen_key, type="secondary"):
                    with st.spinner("🤖 Rigenerazione riassunto e domande..."):
                        ai_result = generate_summary_with_questions(article['full_content'], article['title'])
                        
                        summary = ai_result.get("summary", "")
                        questions = ai_result.get("questions", [])
                        
                        st.session_state[summary_key] = summary
                        st.session_state[questions_key] = questions
                        
                        if edited_questions_key in st.session_state:
                            del st.session_state[edited_questions_key]
                        st.session_state[show_questions_editor_key] = False
                    st.rerun()
            
            with col3:
                if st.button("📋 Export JSON", key=f"export_questions_{tab_name}_{article_index}", 
                           type="secondary", disabled=len(final_questions) == 0):
                    
                    export_data = {
                        "article_title": article['title'],
                        "extraction_timestamp": datetime.now().isoformat(),
                        "questions": final_questions,
                        "questions_source": questions_source,
                        "total_questions": len(final_questions)
                    }
                    
                    json_output = json.dumps(export_data, ensure_ascii=False, indent=2)
                    st.text_area(
                        "Domande JSON:", 
                        value=json_output, 
                        height=150,
                        key=f"questions_json_output_{tab_name}_{article_index}",
                        help="Seleziona tutto (Ctrl+A) e copia (Ctrl+C)"
                    )
    
    else:
        st.markdown(f"""
        <div class="ai-summary" style="background-color: #f9fafb; border-left-color: #9ca3af;">
            <div class="summary-header" style="color: #6b7280;">🤖 Riassunto AI disabilitato</div>
            <em style="color: #9ca3af;">Abilita i riassunti AI dalla sidebar per vedere il contenuto generato automaticamente.</em>
        </div>
        """, unsafe_allow_html=True)

def display_questions_editor(questions_list, edited_questions_key, tab_name, article_index, article_hash):
    """Editor per le domande correlate"""
    safe_questions_list = questions_list if questions_list is not None else []
    current_questions = st.session_state.get(edited_questions_key, safe_questions_list.copy())
    
    st.markdown("""
    <div style="background-color: #fef7e0; border: 1px dashed #f59e0b; border-radius: 8px; padding: 15px; margin: 10px 0;">
        <h4 style="color: #92400e; margin-bottom: 10px;">✏️ Editor Domande</h4>
    </div>
    """, unsafe_allow_html=True)
    
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
                remove_key = f"remove_question_{i}_{article_hash}"
                if st.button("✕", key=remove_key, help=f"Rimuovi domanda {i+1}", 
                           type="secondary"):
                    questions_to_remove.append(question)
        
        if questions_to_remove:
            for question in questions_to_remove:
                if question in current_questions:
                    current_questions.remove(question)
            st.session_state[edited_questions_key] = current_questions
            st.rerun()
    
    col_input, col_add = st.columns([4, 1])
    
    with col_input:
        manual_question_key = f"manual_question_{tab_name}_{article_index}_{article_hash}"
        manual_question = st.text_input(
            "Aggiungi domanda:",
            key=manual_question_key,
            placeholder="es: Quali sono i migliori utensili per...?"
        )
    
    with col_add:
        add_question_key = f"add_question_{tab_name}_{article_index}_{article_hash}"
        if st.button("➕", key=add_question_key, type="primary", 
                   disabled=not manual_question.strip()):
            if manual_question.strip():
                clean_question = manual_question.strip()
                if not clean_question.endswith('?'):
                    clean_question += '?'
                    
                if clean_question not in current_questions:
                    current_questions.append(clean_question)
                    st.session_state[edited_questions_key] = current_questions
                    del st.session_state[manual_question_key]
                    st.success(f"✅ Aggiunta domanda!")
                    st.rerun()
                else:
                    st.warning(f"⚠️ Domanda già presente!")
    
    with st.expander("⚡ Aggiunta multipla domande"):
        bulk_questions = st.text_area(
            "Una domanda per riga:",
            placeholder="Come scegliere gli utensili giusti?\nQuali sono i brand migliori?\nDove acquistare i prodotti?",
            height=100,
            key=f"bulk_questions_{tab_name}_{article_index}_{article_hash}"
        )
        
        if st.button("➕ Aggiungi tutte", key=f"add_bulk_questions_{tab_name}_{article_index}_{article_hash}"):
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
                    st.session_state[edited_questions_key] = current_questions
                    st.success(f"✅ Aggiunte {added_count} domande!")
                    st.rerun()
    
    st.markdown(f"**📊 Totale domande:** {len(current_questions)}")
    
    col_reset, col_clear = st.columns(2)
    
    with col_reset:
        if st.button("🔄 Reset Originali", key=f"reset_questions_{tab_name}_{article_index}_{article_hash}", 
                   type="secondary"):
            safe_questions_list = questions_list if questions_list is not None else []
            st.session_state[edited_questions_key] = safe_questions_list.copy()
            st.rerun()
    
    with col_clear:
        if st.button("🗑️ Cancella Tutte", key=f"clear_questions_{tab_name}_{article_index}_{article_hash}", 
                   type="secondary"):
            st.session_state[edited_questions_key] = []
            st.rerun()

def display_keywords_section(article, tab_name, article_index, enable_keywords):
    """Visualizza la sezione delle keywords con editor e volumi Ahrefs"""
    if enable_keywords:
        keywords_key = f"keywords_{tab_name}_{article_index}_{hash(article['link'])}"
        volumes_key = f"volumes_{tab_name}_{article_index}_{hash(article['link'])}"
        edited_keywords_key = f"edited_keywords_{tab_name}_{article_index}_{hash(article['link'])}"
        keywords_approval_key = f"keywords_approve_{tab_name}_{article_index}_{hash(article['link'])}"
        show_editor_key = f"show_editor_{tab_name}_{article_index}_{hash(article['link'])}"
        
        if keywords_key not in st.session_state:
            st.session_state[keywords_key] = None
        if volumes_key not in st.session_state:
            st.session_state[volumes_key] = {}
        if show_editor_key not in st.session_state:
            st.session_state[show_editor_key] = False
        
        if st.session_state[keywords_key] is None:
            st.markdown(f"""
            <div class="keywords-approval-section">
                <h4 style="color: #065f46; margin-bottom: 15px;">🏷️ Step 1: Estrazione Keywords AI</h4>
                <p style="color: #065f46; margin-bottom: 15px;">
                    Prima estrai le keywords dall'articolo con l'AI, poi potrai personalizzarle.
                    <br><small>💰 <em>Questa operazione consumerà token OpenAI</em></small>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("🤖 Estrai Keywords AI", key=keywords_approval_key, type="primary"):
                with st.spinner("🤖 Estrazione keywords in corso..."):
                    keywords = extract_keywords(article['full_content'], article['title'])
                    st.session_state[keywords_key] = keywords
                    if edited_keywords_key in st.session_state:
                        del st.session_state[edited_keywords_key]
                    st.session_state[volumes_key] = {}
                st.rerun()
        
        else:
            original_keywords = st.session_state[keywords_key]
            
            if edited_keywords_key in st.session_state:
                final_keywords = st.session_state[edited_keywords_key]
                keywords_source = "personalizzate"
            else:
                valid_keywords = [kw.strip() for kw in original_keywords 
                                if kw and not kw.startswith("⚠️") and len(kw.strip()) >= 3]
                st.session_state[edited_keywords_key] = valid_keywords.copy()
                final_keywords = valid_keywords
                keywords_source = "AI originali"
            
            volumes = st.session_state.get(volumes_key, {})
            has_volumes = volumes and any(v > 0 for v in volumes.values())
            
            # Header dinamico
            if not has_volumes:
                if st.session_state[show_editor_key]:
                    header_text = "🎯 Step 2: Personalizza Keywords (Editor Attivo)"
                    header_color = "#f59e0b"
                    bg_color = "#fef7e0"
                else:
                    header_text = f"🏷️ Step 2: Keywords {keywords_source.title()}"
                    header_color = "#065f46"
                    bg_color = "#f0fdf4"
            else:
                header_text = "✅ Keywords Finalizzate con Volumi"
                header_color = "#059669"
                bg_color = "#ecfdf5"
            
            st.markdown(f"""
            <div style="background-color: {bg_color}; border-left: 4px solid {header_color}; padding: 15px; margin: 10px 0; border-radius: 8px;">
                <h4 style="color: {header_color}; margin-bottom: 10px;">{header_text}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            if final_keywords:
                if has_volumes:
                    # Mostra con volumi
                    keywords_tags = ""
                    total_volume = 0
                    high_volume_count = 0
                    
                    # Ordina per volume
                    keywords_with_volumes = [(kw, volumes.get(kw, 0)) for kw in final_keywords]
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
                        ⭐ <strong>High-volume (1k+):</strong> {high_volume_count}/{len(final_keywords)}</small>
                    </div>
                    """ if total_volume > 0 else ""
                    
                    st.markdown(f"""
                    <div style="margin: 10px 0;">
                        {keywords_tags}
                        {volume_summary}
                    </div>
                    """, unsafe_allow_html=True)
                    
                else:
                    # Mostra senza volumi
                    keywords_tags = ""
                    for keyword in final_keywords:
                        keywords_tags += f'<span class="keyword-tag">{keyword} <span class="keyword-volume">-</span></span>'
                    
                    st.markdown(f"""
                    <div style="margin: 10px 0;">
                        {keywords_tags}
                    </div>
                    <div style="margin-top: 10px; padding: 8px; background-color: rgba(107, 114, 128, 0.1); border-radius: 6px;">
                        <small>📝 <strong>Keywords pronte:</strong> {len(final_keywords)} | 
                        🎯 <strong>Fonte:</strong> {keywords_source}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            if st.session_state[show_editor_key] and not has_volumes:
                st.markdown("---")
                display_inline_keywords_editor(final_keywords, edited_keywords_key, tab_name, article_index, hash(article['link']))
                final_keywords = st.session_state.get(edited_keywords_key, final_keywords)
            
            # Pulsanti azioni
            if not has_volumes:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    editor_text = "🔧 Chiudi Editor" if st.session_state[show_editor_key] else "🎯 Modifica keyword"
                    editor_key = f"toggle_editor_{tab_name}_{article_index}_{hash(article['link'])}"
                    if st.button(editor_text, key=editor_key, type="secondary"):
                        st.session_state[show_editor_key] = not st.session_state[show_editor_key]
                
                with col2:
                    volumes_button_key = f"get_volumes_{tab_name}_{article_index}_{hash(article['link'])}"
                    volumes_disabled = len(final_keywords) == 0 or not ahrefs_api_token
                    button_text = "📊 Ottieni Volumi" if ahrefs_api_token else "📊 API Non Config."
                    if st.button(button_text, key=volumes_button_key, type="primary", 
                               disabled=volumes_disabled,
                               help="Cerca volumi Ahrefs per le keywords selezionate" if ahrefs_api_token else "API Ahrefs non configurata"):
                        if final_keywords and ahrefs_api_token:
                            with st.spinner(f"📊 Ricerca volumi per {len(final_keywords)} keywords..."):
                                batch_results = get_multiple_keywords_volumes(final_keywords, "it")
                                
                                new_volumes = {}
                                for keyword, result in batch_results.items():
                                    if result["status"] == "success":
                                        new_volumes[keyword] = result["volume"]
                                
                                st.session_state[volumes_key] = new_volumes
                                st.session_state[show_editor_key] = False
                            st.rerun()
                
                with col3:
                    if st.button("🔄 Rigenera AI", key=f"regen_ai_{tab_name}_{article_index}", type="secondary",
                               help="Rigenera keywords con AI (perderà personalizzazioni)"):
                        with st.spinner("🤖 Rigenerazione keywords AI..."):
                            keywords = extract_keywords(article['full_content'], article['title'])
                            st.session_state[keywords_key] = keywords
                            if edited_keywords_key in st.session_state:
                                del st.session_state[edited_keywords_key]
                            st.session_state[volumes_key] = {}
                            st.session_state[show_editor_key] = False
                        st.rerun()
                        
            else:
                # Dopo aver ottenuto i volumi
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🎯 Modifica Keywords", key=f"edit_after_volumes_{tab_name}_{article_index}", 
                               type="secondary", help="Modifica keywords (resetterà volumi)"):
                        st.session_state[volumes_key] = {}
                        st.session_state[show_editor_key] = True
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Aggiorna Volumi", key=f"refresh_volumes_{tab_name}_{article_index}", 
                               type="secondary", help="Ricarica volumi da Ahrefs"):
                        if final_keywords and ahrefs_api_token:
                            with st.spinner("🔄 Aggiornamento volumi..."):
                                batch_results = get_multiple_keywords_volumes(final_keywords, "it")
                                new_volumes = {}
                                for keyword, result in batch_results.items():
                                    if result["status"] == "success":
                                        new_volumes[keyword] = result["volume"]
                                st.session_state[volumes_key] = new_volumes
                            st.rerun()
                
                with col3:
                    if st.button("📋 Esporta JSON", key=f"export_json_{tab_name}_{article_index}", 
                               type="secondary", help="Copia risultati in JSON"):
                        
                        export_data = {
                            "article_title": article['title'],
                            "extraction_timestamp": datetime.now().isoformat(),
                            "keywords_with_volumes": [
                                {
                                    "keyword": kw,
                                    "volume_monthly": volumes.get(kw, 0),
                                    "status": "success" if volumes.get(kw, 0) > 0 else "no_volume"
                                }
                                for kw in final_keywords
                            ],
                            "summary": {
                                "total_keywords": len(final_keywords),
                                "keywords_with_volume": len([v for v in volumes.values() if v > 0]),
                                "total_volume": sum(volumes.values()),
                                "source": keywords_source
                            }
                        }
                        
                        json_output = json.dumps(export_data, ensure_ascii=False, indent=2)
                        st.text_area(
                            "JSON Output:", 
                            value=json_output, 
                            height=200,
                            key=f"json_output_{tab_name}_{article_index}",
                            help="Seleziona tutto (Ctrl+A) e copia (Ctrl+C)"
                        )
    
    else:
        st.markdown(f"""
        <div class="keywords-section" style="background-color: #f9fafb; border-left-color: #9ca3af;">
            <div class="keywords-header" style="color: #6b7280;">🏷️ Keywords AI disabilitate</div>
            <em style="color: #9ca3af;">Abilita l'estrazione keywords dalla sidebar.</em>
        </div>
        """, unsafe_allow_html=True)

def display_inline_keywords_editor(keywords_list, edited_keywords_key, tab_name, article_index, article_hash):
    """Editor keywords inline ottimizzato per lo spazio"""
    current_keywords = st.session_state.get(edited_keywords_key, keywords_list.copy())
    
    st.markdown("""
    <div style="background-color: #fef7e0; border: 1px dashed #f59e0b; border-radius: 8px; padding: 15px; margin: 10px 0;">
        <h4 style="color: #92400e; margin-bottom: 10px;">✏️ Editor Keywords</h4>
    </div>
    """, unsafe_allow_html=True)
    
    if current_keywords:
        st.markdown("**Keywords attuali:**")
        
        keywords_to_remove = []
        
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
                        remove_key = f"remove_inline_{keyword}_{i}_{j}_{article_hash}"
                        if st.button("✕", key=remove_key, help=f"Rimuovi '{keyword}'", 
                                   type="secondary"):
                            keywords_to_remove.append(keyword)
        
        if keywords_to_remove:
            for keyword in keywords_to_remove:
                if keyword in current_keywords:
                    current_keywords.remove(keyword)
            st.session_state[edited_keywords_key] = current_keywords
            st.rerun()
    
    col_input, col_add = st.columns([3, 1])
    
    with col_input:
        manual_keyword_key = f"manual_inline_{tab_name}_{article_index}_{article_hash}"
        manual_keyword = st.text_input(
            "Aggiungi keyword:",
            key=manual_keyword_key,
            placeholder="es: utensili professionali"
        )
    
    with col_add:
        add_key = f"add_inline_{tab_name}_{article_index}_{article_hash}"
        if st.button("➕", key=add_key, type="primary", 
                   disabled=not manual_keyword.strip()):
            if manual_keyword.strip():
                clean_keyword = manual_keyword.strip().title()
                if clean_keyword not in current_keywords:
                    current_keywords.append(clean_keyword)
                    st.session_state[edited_keywords_key] = current_keywords
                    st.session_state[manual_keyword_key] = ""
                    st.success(f"✅ Aggiunta: '{clean_keyword}'")
                    st.rerun()
                else:
                    st.warning(f"⚠️ '{clean_keyword}' già presente!")
    
    with st.expander("⚡ Aggiunta multipla"):
        bulk_keywords = st.text_area(
            "Una keyword per riga:",
            placeholder="ferramenta\nutensili cantiere\nsicurezza lavoro",
            height=80,
            key=f"bulk_inline_{tab_name}_{article_index}_{article_hash}"
        )
        
        if st.button("➕ Aggiungi tutte", key=f"add_bulk_inline_{tab_name}_{article_index}_{article_hash}"):
            if bulk_keywords.strip():
                new_keywords = [kw.strip().title() for kw in bulk_keywords.split('\n') 
                              if kw.strip() and len(kw.strip()) >= 3]
                
                added_count = 0
                for keyword in new_keywords:
                    if keyword not in current_keywords:
                        current_keywords.append(keyword)
                        added_count += 1
                
                if added_count > 0:
                    st.session_state[edited_keywords_key] = current_keywords
                    st.success(f"✅ Aggiunte {added_count} keywords!")
                    st.rerun()
    
    st.markdown(f"**📊 Totale keywords:** {len(current_keywords)}")

def display_blog_draft_section_full_width(article, tab_name, article_index, enable_blog_draft):
    """Sezione per generazione bozza blog intelligente con volumi"""
    if enable_blog_draft:
        blog_draft_key = f"blog_draft_{tab_name}_{article_index}_{hash(article['link'])}"
        blog_approval_key = f"blog_approve_{tab_name}_{article_index}_{hash(article['link'])}"
        
        keywords_key = f"keywords_{tab_name}_{article_index}_{hash(article['link'])}"
        edited_keywords_key = f"edited_keywords_{tab_name}_{article_index}_{hash(article['link'])}"
        volumes_key = f"volumes_{tab_name}_{article_index}_{hash(article['link'])}"
        
        questions_key = f"questions_{tab_name}_{article_index}_{hash(article['link'])}"
        edited_questions_key = f"edited_questions_{tab_name}_{article_index}_{hash(article['link'])}"
        summary_key = f"summary_{tab_name}_{article_index}_{hash(article['link'])}"
        
        if blog_draft_key not in st.session_state:
            st.session_state[blog_draft_key] = None
        
        st.markdown('<div class="blog-draft-container">', unsafe_allow_html=True)
        
        if st.session_state[blog_draft_key] is None:
            final_keywords = []
            keywords_volumes = {}
            keywords_source = "nessuna"
            
            if edited_keywords_key in st.session_state and st.session_state[edited_keywords_key]:
                final_keywords = st.session_state[edited_keywords_key]
                keywords_source = "personalizzate"
            elif keywords_key in st.session_state and st.session_state[keywords_key]:
                original_keywords = st.session_state[keywords_key]
                final_keywords = [kw.strip() for kw in original_keywords 
                                if kw and not kw.startswith("⚠️") and len(kw.strip()) >= 3]
                keywords_source = "AI originali"
            
            # Ottieni volumi per le keywords
            if volumes_key in st.session_state:
                keywords_volumes = st.session_state[volumes_key]
            
            final_questions = []
            questions_source = "nessuna"
            if edited_questions_key in st.session_state and st.session_state[edited_questions_key]:
                safe_questions = st.session_state[edited_questions_key]
                final_questions = safe_questions if safe_questions is not None else []
                questions_source = "personalizzate"
            elif questions_key in st.session_state and st.session_state[questions_key]:
                safe_questions = st.session_state[questions_key]
                final_questions = safe_questions if safe_questions is not None else []
                questions_source = "AI originali"
            
            structured_summary = st.session_state.get(summary_key, "")
            
            # Calcola priorità keywords
            high_volume_keywords = [kw for kw in final_keywords if keywords_volumes.get(kw, 0) >= 1000]
            total_volume = sum(keywords_volumes.values()) if keywords_volumes else 0
                      
            st.markdown(f"""
            <div class="blog-draft-section">
                <h4 style="color: #92400e; margin-bottom: 15px;text-align: center;">✍️ Step 3: Bozza Blog Intelligente</h4>
                <p style="color: #065f46; margin-bottom: 15px;text-align: center;">
                    Genera una bozza prioritizzando le keywords con volume di ricerca più alto.
                    <br><small>💰 <em>Questa operazione consumerà token OpenAI</em></small>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Info sui contenuti disponibili
            if final_keywords and keywords_volumes:
                st.info(f"📊 **Keywords con volumi:** {len([kw for kw in final_keywords if keywords_volumes.get(kw, 0) > 0])} su {len(final_keywords)} | 🔥 **High-volume (1k+):** {len(high_volume_keywords)} | 📈 **Volume totale:** {total_volume:,}")
            
            has_minimum_content = bool(structured_summary or final_keywords or final_questions)
            
            if st.button("✍️ Genera Bozza Blog Intelligente", key=blog_approval_key, type="primary", 
                       disabled=not has_minimum_content,
                       help="Genera bozza usando tutti i dati disponibili con prioritizzazione per volume" if has_minimum_content else "Devi avere almeno riassunto, keywords o domande"):
                with st.spinner("🤖 Generazione bozza blog intelligente..."):
                    blog_draft = generate_intelligent_blog_draft(
                        content=article['full_content'],
                        title=article['title'], 
                        structured_summary=structured_summary,
                        keywords=final_keywords,
                        #keywords_volumes=keywords_volumes,
                        questions=final_questions
                    )
                    st.session_state[blog_draft_key] = blog_draft
                st.rerun()
            
            if not has_minimum_content:
                st.info("💡 **Suggerimento:** Genera prima il riassunto e/o estrai keywords/domande per una bozza completa e ottimizzata.")
        
        else:
            blog_draft = st.session_state[blog_draft_key]
            
            used_keywords = []
            used_questions = []
            used_volumes = {}
            
            if edited_keywords_key in st.session_state and st.session_state[edited_keywords_key]:
                used_keywords = st.session_state[edited_keywords_key]
                keywords_source = "personalizzate"
            else:
                used_keywords = st.session_state.get(keywords_key, [])
                keywords_source = "AI originali"
            
            if edited_questions_key in st.session_state and st.session_state[edited_questions_key]:
                safe_questions = st.session_state[edited_questions_key]
                used_questions = safe_questions if safe_questions is not None else []
                questions_source = "personalizzate"
            else:
                safe_questions = st.session_state.get(questions_key, [])
                used_questions = safe_questions if safe_questions is not None else []
                questions_source = "AI originali"
            
            used_volumes = st.session_state.get(volumes_key, {})
            used_summary = st.session_state.get(summary_key, "")
            
            optimization_info = []
            if used_summary:
                optimization_info.append("riassunto strutturato")
            if used_keywords:
                high_vol = len([kw for kw in used_keywords if used_volumes.get(kw, 0) >= 1000])
                total_vol = sum(used_volumes.values()) if used_volumes else 0
                kw_info = f"{len(used_keywords)} keywords {keywords_source}"
                if total_vol > 0:
                    kw_info += f" ({high_vol} prioritarie, {total_vol:,} vol.tot)"
                optimization_info.append(kw_info)
            if used_questions:
                optimization_info.append(f"{len(used_questions)} domande {questions_source}")
            
            optimization_text = " + ".join(optimization_info) if optimization_info else "contenuto base"
            
            st.markdown(f"""
            <div class="blog-draft-section">
                <div class="blog-draft-header">✅ Bozza Blog Intelligente Generata</div>
                <small style="color: #92400e;">🧠 Ottimizzata con: {optimization_text}</small>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 📖 Bozza Blog Generata")
            st.markdown(blog_draft)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📋 Copia Bozza", key=f"copy_blog_{tab_name}_{article_index}"):
                    st.text_area(
                        "Bozza per copia:",
                        value=blog_draft,
                        height=1,
                        key=f"copy_area_{tab_name}_{article_index}",
                        help="Seleziona tutto (Ctrl+A) e copia (Ctrl+C)"
                    )
            
            with col2:
                if st.button("🔄 Rigenera", key=f"regen_blog_{tab_name}_{article_index}", type="secondary"):
                    with st.spinner("🤖 Rigenerazione bozza intelligente..."):
                        blog_draft = generate_intelligent_blog_draft(
                            content=article['full_content'],
                            title=article['title'], 
                            structured_summary=used_summary,
                            keywords=used_keywords,
                            keywords_volumes=used_volumes,
                            questions=used_questions
                        )
                        st.session_state[blog_draft_key] = blog_draft
                    st.rerun()
            
            with col3:
                if st.button("🎯 Modifica Contenuti", key=f"change_content_blog_{tab_name}_{article_index}", type="secondary"):
                    st.session_state[blog_draft_key] = None
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    else:
        st.markdown(f"""
        <div class="blog-draft-section" style="background-color: #f9fafb; border-left-color: #9ca3af;">
            <div class="blog-draft-header" style="color: #6b7280;">✍️ Bozze Blog disabilitate</div>
            <em style="color: #9ca3af;">Abilita le bozze blog dalla sidebar.</em>
        </div>
        """, unsafe_allow_html=True)

def display_articles(articles, tab_name="", enable_ai_summary=True, enable_keywords=True, enable_blog_draft=True):
    """Visualizza gli articoli in formato card con funzionalità AI"""
    
    if not articles:
        st.info("Nessun articolo disponibile per questa categoria.")
        return
    
    try:
        articles.sort(key=lambda x: datetime.strptime(x['published'].split()[0], '%d/%m/%Y') if '/' in x['published'] else datetime.min, reverse=True)
    except:
        pass
    
    for i, article in enumerate(articles):
        with st.container():
            image_indicator = "🖼️" if article['has_image'] else "📄"

            html_card = f"""
                <div class="article-card">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 15px;">
                        <div style="flex: 1;">
                            <div class="article-title">
                                {image_indicator} {article['title']}
                            </div>
                            <span class="article-preview">{article['preview']}</span>
                            <div class="article-meta" style="margin-top: 5px;">
                                📅 {article['published']} | 
                                <span class="category-tag">{article['source_category']}</span>
                                {' | 🖼️ Con immagine' if article['has_image'] else ' | 📄 Solo testo'}
                            </div>
                        </div>
                        <div style="margin-left: 15px; display: flex; flex-direction: column; align-items: center;">
                            <a href="{article['link']}" target="_blank" style="
                                display: inline-block;
                                background-color: #3b82f6;
                                color: white;
                                padding: 8px 16px;
                                border-radius: 5px;
                                text-decoration: none;
                                font-weight: bold;
                                font-size: 14px;
                                white-space: nowrap;
                                margin-bottom: 10px;
                            ">
                                🌐 Leggi articolo
                            </a>"""

            if article['has_image'] and article.get('image_url'):
                html_card += f"""
                            <img src="{article['image_url']}" alt="Immagine articolo" style="max-width: 200px; border-radius: 6px;">"""

            html_card += """
                        </div>
                    </div>
                </div>
                """

            st.markdown(html_card, unsafe_allow_html=True)
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                display_keywords_section(article, tab_name, i, enable_keywords)
            
            with col2:
                display_ai_summary_section(article, tab_name, i, enable_ai_summary)
            
            if enable_blog_draft:
                display_blog_draft_section_full_width(article, tab_name, i, enable_blog_draft)
            
            st.markdown("---")

# ============================================================================
# FUNZIONE MAIN
# ============================================================================

def main():
    st.title("Articoli dei competitor utili - RSS Feed Reader")
    st.markdown("*Tool ideato per poter generare una bozza utile di articolo utilizzando i contenuti dei competitor* ")
    
    feeds = {
        "Automotive": "https://www.automotive-news.it/feed/",
        "Logistic": "https://www.logisticanews.it/feed/"
    }
    
    # Sidebar essenziale
    st.sidebar.header("🔍 Controlli")
    
    # Info API status Ahrefs
    if ahrefs_api_token:
        st.sidebar.success("✅ API Ahrefs configurata")
    else:
        st.sidebar.warning("⚠️ API Ahrefs non configurata")
    
    # Filtro per categoria
    selected_categories = st.sidebar.multiselect(
        "Seleziona categorie:",
        options=list(feeds.keys()),
        default=list(feeds.keys())
    )
    
    # Pulsante per aggiornare
    if st.sidebar.button("🔄 Aggiorna Feed", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # Cache per i feed
    @st.cache_data(ttl=300)  # Cache per 5 minuti
    def get_all_articles():
        all_articles = []
        feed_stats = {}
        
        for category, url in feeds.items():
            if category in selected_categories:
                articles, count = fetch_feed(url, category)
                all_articles.extend(articles[:20])
                feed_stats[category] = count
        
        return all_articles, feed_stats
    
    # Recupera tutti gli articoli
    all_articles, feed_stats = get_all_articles()
    
    # Statistiche nella sidebar
    st.sidebar.markdown("### 📊 Statistiche Feed")
    for category, count in feed_stats.items():
        articles_in_category = [a for a in all_articles if a['source_category'] == category]
        images_in_category = len([a for a in articles_in_category if a['has_image']])
        st.sidebar.metric(
            f"{category}", 
            f"{len(articles_in_category)}/{count}",
            delta=f"{images_in_category} con immagini",
            help=f"Articoli mostrati/totali. {images_in_category} articoli hanno immagini."
        )
    
    total_with_images = len([a for a in all_articles if a['has_image']])
    st.sidebar.markdown(f"**Articoli totali:** {len(all_articles)}")
    if len(all_articles) > 0:
        st.sidebar.markdown(f"**Con immagini:** {total_with_images} ({total_with_images/len(all_articles)*100:.1f}%)")
    else:
        st.sidebar.markdown(f"**Con immagini:** {total_with_images} (0%)")
    
    # Contenuto principale
    if not all_articles:
        st.warning("Nessun articolo trovato.")
        return
    
    # Info per l'utente
    st.info("""
    **Come usare l'app:**
    1. **Genera riassunto + domande** per ogni articolo che ti interessa
    2. **Estrai keywords** con l'AI e personalizzale secondo le tue esigenze
    3. **Modifica domande** per adattarle al tuo target
    4. **Genera la bozza blog** ottimizzata con i tuoi contenuti personalizzati
    """)
    
    # Tabs per le categorie
    if len(selected_categories) > 1:
        tabs = st.tabs(["Tutti"] + selected_categories)
        
        with tabs[0]:
            display_articles([a for a in all_articles], "tutti", True, True, True)
        
        for i, category in enumerate(selected_categories, 1):
            with tabs[i]:
                category_articles = [a for a in all_articles if a['source_category'] == category]
                display_articles(category_articles, category.lower(), True, True, True)
    else:
        category_name = selected_categories[0] if selected_categories else "default"
        display_articles(all_articles, category_name.lower(), True, True, True)

# ============================================================================
# ESECUZIONE PRINCIPALE 
# ============================================================================

if __name__ == "__main__":
    main()
