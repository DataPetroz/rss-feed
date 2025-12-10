import streamlit as st
import streamlit_analytics2 as streamlit_analytics
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

import os
import ssl
import urllib3
import warnings

# 1. Disabilita la verifica SSL per tutto il runtime Python
os.environ['PYTHONHTTPSVERIFY'] = '0'
try:
    # Crea un contesto SSL che non verifica i certificati
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
# 2. Disabilita gli avvisi di sicurezza di urllib3
warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)
# 3. Monkey Patch della libreria 'requests' per disabilitare la verifica SSL
original_session_request = requests.Session.request
def session_request_no_verify(self, *args, **kwargs):
    kwargs['verify'] = False
    return original_session_request(self, *args, **kwargs)
requests.Session.request = session_request_no_verify

# Configurazione logging
logging.basicConfig(level=logging.WARNING)

# Configurazione della pagina
st.set_page_config(
    page_title="RSS Feed Reader",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Tag noindex per evitare indicizzazione
st.markdown('<meta name="robots" content="noindex, nofollow">', unsafe_allow_html=True)

# CSS personalizzato con miglioramenti UX
st.markdown("""
<style>
    /* Margine zero per i tag hr */
    hr {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Scroll behavior smooth per migliorare UX */
    html {
        scroll-behavior: smooth;
    }
    
    /* Container per sezioni con ID per scroll */
    .section-container {
        scroll-margin-top: 100px;
        position: relative;
    }
    
    .article-card {
        border: 1px solid #e1e5e9;
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        background-color: #fafafa;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        scroll-margin-top: 100px;
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
        scroll-margin-top: 100px;
    }
    .keywords-section {
        background-color: #f0fdf4;
        border-left: 4px solid #10b981;
        padding: 15px;
        margin: 10px 0;
        border-radius: 8px;
        color: #065f46;
        scroll-margin-top: 100px;
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
        scroll-margin-top: 100px;
    }
    .keywords-approval-section {
        background-color: #f0fdf4;
        border: 2px dashed #10b981;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        margin: 10px 0;
        scroll-margin-top: 100px;
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
        scroll-margin-top: 100px;
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
        scroll-margin-top: 100px;
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
    
    /* Miglioramenti per la navigazione smooth */
    .stButton > button {
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Container per step sections con ID univoci */
    .step-section {
        scroll-margin-top: 100px;
        position: relative;
    }
    
    /* Indicatori visivi per sezioni attive */
    .active-step {
        box-shadow: 0 0 0 2px #3b82f6;
        border-radius: 8px;
    }
</style>

<script>
// JavaScript per gestire lo scroll smooth e prevenire jumps
function scrollToElement(elementId, offset = 100) {
    const element = document.getElementById(elementId);
    if (element) {
        const y = element.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({top: y, behavior: 'smooth'});
    }
}

// Previene il default scroll behavior di Streamlit
document.addEventListener('DOMContentLoaded', function() {
    // Intercetta i click sui bottoni per gestire lo scroll manualmente
    document.addEventListener('click', function(event) {
        const button = event.target.closest('button');
        if (button) {
            // Mantiene la posizione corrente per un breve momento
            setTimeout(() => {
                const activeElement = document.activeElement;
                if (activeElement) {
                    activeElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'center',
                        inline: 'nearest'
                    });
                }
            }, 100);
        }
    });
});
</script>
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
# SETUP INIZIALE ANALYTICS - Da mettere all'inizio del tuo main file
# ============================================================================

import uuid

def setup_analytics():
    """Configura Streamlit Analytics2 per il tracking degli eventi"""
    
    # Inizializza session_id se non presente
    if "session_id" not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())
    
    # Configura analytics
    streamlit_analytics.start_tracking()
    
    # Registra un evento di avvio sessione
    streamlit_analytics.track(
        "session_start",
        {
            "timestamp": datetime.now().isoformat(),
            "session_id": st.session_state.session_id,
            "app_version": "1.0.0"  # Personalizza con la tua versione
        }
    )

# ============================================================================
# FUNZIONI HELPER PER ANALYTICS
# ============================================================================

def track_user_interaction(interaction_type, details=None):
    """Helper function per tracciare interazioni generiche dell'utente"""
    if details is None:
        details = {}
    
    base_details = {
        "timestamp": datetime.now().isoformat(),
        "interaction_type": interaction_type
    }
    base_details.update(details)
    
    streamlit_analytics.track(interaction_type, base_details)

def track_api_usage(api_call_type, tokens_used=None, success=True):
    """Helper function per tracciare l'uso delle API"""
    streamlit_analytics.track(
        "api_usage",
        {
            "timestamp": datetime.now().isoformat(),
            "api_call_type": api_call_type,
            "tokens_used": tokens_used,
            "success": success
        }
    )

def get_analytics_summary():
    """Ottieni un riassunto delle analytics (se supportato dal tuo setup)"""
    try:
        # Questa funzione dipende da come hai configurato analytics
        # Puoi personalizzarla in base alle tue esigenze
        return streamlit_analytics.get_tracked_events()
    except:
        return "Analytics summary not available"

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
def generate_blog_structure(content: str, title: str, system_prompt: str = "") -> List[Dict[str, str]]:
    """Genera una struttura di titoli e paragrafi personalizzata basata sul system_prompt"""
    if not AZURE_AVAILABLE:
        return [{"tipo": "errore", "contenuto": "⚠️ Servizio AI non configurato."}]
    
    if not content or len(content.strip()) < 50:
        return [{"tipo": "errore", "contenuto": "Contenuto troppo breve per generare una struttura."}]
    
    content_truncated = content[:3000] if len(content) > 3000 else content
    
    # System prompt di default se non fornito
    default_system_prompt = """Sei un esperto di content marketing specializzato nel settore industriale e ferramenta.
    Analizza l'articolo fornito e crea una struttura ottimizzata per blog aziendale con titoli e sottotitoli accattivanti.
    Focus su: praticità, applicazioni concrete, vantaggi per professionisti del settore."""
    
    final_system_prompt = system_prompt.strip() if system_prompt.strip() else default_system_prompt
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": f"""{final_system_prompt}
                    
                    ###ISTRUZIONE###
                    Analizza il contenuto fornito e crea una struttura JSON per un articolo blog con titoli e paragrafi.
                    
                    ###STRUTTURA OBBLIGATORIA###
                    1. Titolo accattivante e SEO-friendly che comprende la keyword principale
                    2. Introduzione che descrive il tema e cattura l'attenzione (50-70 parole)
                    3. Corpo dell'articolo con sottotitoli H2/H3:
                       - H2 per trattare gli argomenti principali
                       - H3 SOLO SE NECESSARIO per trattare un sottoargomento specifico dell'H2 precedente
                       - Se ci sono più argomenti principali distinti, usa più H2
                       - EVITA H3 se non serve davvero per suddividere un H2 complesso
                    4. Ogni paragrafo deve essere conciso (50-100 parole) e focalizzato su un singolo punto
                    5. Conclusione con un riassunto che sottolinea le informazioni più importanti
                    
                    ###REGOLE PER H3###
                    ⚠️ USA H3 SOLO SE:
                    - L'argomento H2 è complesso e ha realmente bisogno di essere suddiviso
                    - Ci sono sottoargomenti distinti che meritano un titolo proprio
                    - Il contenuto sotto l'H2 sarebbe troppo lungo senza suddivisioni
                    
                    ❌ NON USARE H3 SE:
                    - L'H2 può essere trattato con un semplice paragrafo
                    - I sottoargomenti sono troppo brevi o superficiali
                    - Stai creando H3 solo per "riempire" la struttura
                    
                    ###VINCOLI###
                    - Lunghezza complessiva NON superiore a 1500 parole
                    - Massimo 3 paragrafi per eventuali sezioni FAQ
                    - Un paragrafo per l'introduzione e uno per la conclusione
                    
                    ###TESTI DI ESEMPIO###
                    I contenuti che generi devono essere SOLO UNA TRACCIA per l'utente, indicando:
                    - Cosa deve inserire in quel punto (titoli e paragrafi)
                    - Quali keyword inserire
                    - Che informazione si andrà a trattare nel caso dei paragrafi
                    
                    ###FORMATO OUTPUT###
                    Restituisci SOLO un JSON nel formato:
                    {{
                      "struttura": [
                        {{
                          "tipo": "titolo_principale",
                          "contenuto": "[TRACCIA TITOLO H1] - Inserisci qui la keyword principale + titolo accattivante che catturi l'attenzione"
                        }},
                        {{
                          "tipo": "introduzione", 
                          "contenuto": "[TRACCIA INTRODUZIONE] - Descrivi brevemente il tema principale e perché è importante per il lettore target. Includi keyword secondarie naturalmente (50-70 parole)"
                        }},
                        {{
                          "tipo": "sottotitolo",
                          "contenuto": "[TRACCIA H2] - Primo argomento principale con keyword correlata"
                        }},
                        {{
                          "tipo": "paragrafo",
                          "contenuto": "[TRACCIA PARAGRAFO] - Sviluppa il primo punto principale. Includi dettagli pratici e keyword. Focus su un singolo concetto (50-100 parole)"
                        }},
                        {{
                          "tipo": "sottotitolo",
                          "contenuto": "[TRACCIA H2] - Secondo argomento principale distinto"
                        }},
                        {{
                          "tipo": "paragrafo",
                          "contenuto": "[TRACCIA PARAGRAFO] - Sviluppa il secondo argomento principale (50-100 parole)"
                        }},
                        {{
                          "tipo": "conclusione",
                          "contenuto": "[TRACCIA CONCLUSIONE] - Riassumi i punti chiave e sottolinea le informazioni più importanti per il lettore"
                        }}
                      ]
                    }}
                    
                    ###ESEMPIO CON H3 GIUSTIFICATO###
                    Se l'H2 è "Tipologie di Utensili da Cantiere" e ci sono realmente 3-4 categorie diverse da spiegare:
                    - H2: "Tipologie di Utensili da Cantiere"
                    - H3: "Utensili Elettrici" (se merita approfondimento)
                    - H3: "Utensili Manuali" (se merita approfondimento)
                    - H3: "Utensili Pneumatici" (se merita approfondimento)
                    
                    ###ESEMPIO SENZA H3###
                    Se l'H2 è "Vantaggi degli Utensili Professionali":
                    - H2: "Vantaggi degli Utensili Professionali"
                    - Paragrafo diretto (NO H3, perché i vantaggi possono essere elencati in un paragrafo)
                    
                    ###TIPI DISPONIBILI###
                    - titolo_principale (H1) - UNO SOLO
                    - introduzione - UNA SOLA
                    - sottotitolo (H2) - Per argomenti principali
                    - sottotitolo_h3 (H3) - SOLO se necessario per sottoargomenti complessi
                    - paragrafo - Contenuto di sviluppo
                    - elenco_puntato - Liste quando appropriato
                    - conclusione - UNA SOLA
                    - call_to_action - Opzionale
                    
                    ###ESEMPIO PRATICO DI VALUTAZIONE H3###
                    
                    ✅ GIUSTO - H3 necessario:
                    H2: "Manutenzione degli Utensili Professionali"
                    - H3: "Pulizia e Conservazione" (argomento specifico)
                    - H3: "Calibrazione e Controlli" (argomento specifico) 
                    - H3: "Riparazione e Sostituzione Parti" (argomento specifico)
                    
                    ❌ SBAGLIATO - H3 non necessario:
                    H2: "Importanza della Sicurezza"
                    - NON serve H3, può essere trattato con un paragrafo diretto
                    """
                },
                {
                    "role": "user",
                    "content": f"""Crea una struttura ottimizzata per questo articolo seguendo ESATTAMENTE le specifiche richieste:
                    
                    TITOLO: {title}
                    CONTENUTO: {content_truncated}
                    
                    RICORDA:
                    - I contenuti devono essere TRACCE/GUIDE per l'utente
                    - Indica sempre quali keyword inserire
                    - Specifica che tipo di informazione trattare
                    - Rispetta i limiti di lunghezza (max 1500 parole totali)
                    - Struttura: H1 > Intro > H2 > H3 SOLO SE NECESSARIO > Conclusione
                    - VALUTA ATTENTAMENTE se serve davvero un H3 o se l'H2 può essere trattato con un paragrafo diretto
                    
                    Restituisci SOLO il JSON della struttura, senza spiegazioni aggiuntive."""
                }
            ],
            max_completion_tokens=1500  # Aumentato per contenere le tracce dettagliate
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        try:
            parsed_response = json.loads(ai_response)
            
            if "struttura" in parsed_response and isinstance(parsed_response["struttura"], list):
                return parsed_response["struttura"]
            else:
                return [{"tipo": "errore", "contenuto": "Formato JSON non valido"}]
                
        except json.JSONDecodeError:
            # Prova a estrarre struttura dal testo
            return extract_structure_from_text(ai_response)
        
    except Exception as e:
        logging.error(f"Errore Azure OpenAI per struttura: {e}")
        return [{"tipo": "errore", "contenuto": f"⚠️ Errore nella generazione: {str(e)}"}]

def extract_structure_from_text(text: str) -> List[Dict[str, str]]:
    """Estrae struttura da testo non-JSON con supporto per tracce"""
    lines = text.split('\n')
    structure = []
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('{') or line.startswith('}'):
            continue
            
        # Identifica il tipo basandosi su pattern comuni, incluse le tracce
        if any(marker in line.lower() for marker in ['titolo principale', 'h1', '# ', '[traccia titolo', '[traccia h1']):
            structure.append({"tipo": "titolo_principale", "contenuto": clean_structure_text(line)})
        elif any(marker in line.lower() for marker in ['sottotitolo', 'h2', '## ', '[traccia h2']):
            structure.append({"tipo": "sottotitolo", "contenuto": clean_structure_text(line)})
        elif any(marker in line.lower() for marker in ['h3', '### ', '[traccia h3']):
            structure.append({"tipo": "sottotitolo_h3", "contenuto": clean_structure_text(line)})
        elif any(marker in line.lower() for marker in ['introduzione', '[traccia introduzione']):
            structure.append({"tipo": "introduzione", "contenuto": clean_structure_text(line)})
        elif any(marker in line.lower() for marker in ['conclusione', '[traccia conclusione']):
            structure.append({"tipo": "conclusione", "contenuto": clean_structure_text(line)})
        elif any(marker in line.lower() for marker in ['call', 'azione']):
            structure.append({"tipo": "call_to_action", "contenuto": clean_structure_text(line)})
        elif line.startswith('- ') or line.startswith('* '):
            structure.append({"tipo": "elenco_puntato", "contenuto": clean_structure_text(line)})
        elif any(marker in line.lower() for marker in ['[traccia paragrafo', 'paragrafo']) or len(line) > 20:
            structure.append({"tipo": "paragrafo", "contenuto": clean_structure_text(line)})
    
    return structure if structure else [{"tipo": "errore", "contenuto": "Impossibile estrarre struttura dal testo"}]

def clean_structure_text(text: str) -> str:
    """Pulisce il testo della struttura preservando le indicazioni per tracce"""
    # Rimuove marker JSON ma preserva le tracce in parentesi quadre
    text = re.sub(r'^[\d\-\*\•\s"#]+', '', text.strip())
    text = re.sub(r'",?\s*$', '', text.strip())
    text = re.sub(r'^["\'\s]+|["\'\s]+$', '', text.strip())
    
    # Se il testo non contiene già tracce, non modificare ulteriormente
    if '[TRACCIA' not in text.upper() and len(text) > 100:
        # Accorcia solo se molto lungo e non contiene tracce
        text = text[:200] + "..." if len(text) > 200 else text
    
    return text.strip()

def clean_structure_text(text: str) -> str:
    """Pulisce il testo della struttura"""
    # Rimuove marker JSON e caratteri speciali
    text = re.sub(r'^[\d\-\*\•\s"#]+', '', text.strip())
    text = re.sub(r'",?\s*$', '', text.strip())
    text = re.sub(r'^["\'\s]+|["\'\s]+$', '', text.strip())
    return text.strip()

def create_section_anchor(tab_name: str, article_index: int, section_type: str) -> str:
    """Crea un anchor ID univoco per la sezione"""
    return f"section_{tab_name}_{article_index}_{section_type}_{hash(str(article_index))}"

def display_structure_section(article, tab_name, article_index, enable_structure):
    """Visualizza la sezione per generazione e modifica struttura articolo con scroll ottimizzato"""
    section_id = create_section_anchor(tab_name, article_index, "structure")
    
    if enable_structure:
        structure_key = f"structure_{tab_name}_{article_index}_{hash(article['link'])}"
        edited_structure_key = f"edited_structure_{tab_name}_{article_index}_{hash(article['link'])}"
        system_prompt_key = f"system_prompt_{tab_name}_{article_index}_{hash(article['link'])}"
        structure_approval_key = f"structure_approve_{tab_name}_{article_index}_{hash(article['link'])}"
        show_structure_editor_key = f"show_structure_editor_{tab_name}_{article_index}_{hash(article['link'])}"
        
        if structure_key not in st.session_state:
            st.session_state[structure_key] = None
        if show_structure_editor_key not in st.session_state:
            st.session_state[show_structure_editor_key] = False
        if system_prompt_key not in st.session_state:
            st.session_state[system_prompt_key] = ""
        
        # Container con ID per scroll
        st.markdown(f'<div id="{section_id}" class="step-section section-container">', unsafe_allow_html=True)
        
        if st.session_state[structure_key] is None:
            st.markdown(f"""
            <div class="approval-section" style="background-color: #f0f4ff; border: 2px dashed #6366f1;">
                <h4 style="color: #4f46e5; margin-bottom: 15px;">📋 Step 3: Struttura Personalizzata</h4>
                <p style="color: #4f46e5; margin-bottom: 15px;">
                    Genera una struttura di titoli e paragrafi personalizzata usando un system prompt specifico.<br>
                    <small>💰 <em>Questa operazione consumerà token API</em></small>
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Campo per system prompt personalizzato
            system_prompt = st.text_area(
                "System Prompt personalizzato (opzionale):",
                value=st.session_state[system_prompt_key],
                height=100,
                placeholder="es: Crea una struttura per un articolo tecnico destinato a ingegneri, con focus su specifiche tecniche e casi d'uso pratici...",
                help="Lascia vuoto per usare il prompt di default ottimizzato per il settore industriale",
                key=f"system_prompt_input_{tab_name}_{article_index}"
            )
            st.session_state[system_prompt_key] = system_prompt
            
            if st.button("📋 Genera Struttura Personalizzata", key=structure_approval_key, type="primary"):
                # Aggiungi tracking
                streamlit_analytics.track("genera_struttura_personalizzata", {
                    "tab_name": tab_name,
                    "article_index": article_index,
                    "article_title": article['title'][:50]  # Primi 50 caratteri del titolo
                })
                with st.spinner("🤖 Generazione struttura in corso..."):
                    structure = generate_blog_structure(
                        article['full_content'], 
                        article['title'],
                        system_prompt
                    )
                    st.session_state[structure_key] = structure
                
                # JavaScript per scroll smooth alla sezione corrente
                st.markdown(f"""
                <script>
                setTimeout(() => {{
                    const element = document.getElementById('{section_id}');
                    if (element) {{
                        element.scrollIntoView({{
                            behavior: 'smooth',
                            block: 'center'
                        }});
                    }}
                }}, 100);
                </script>
                """, unsafe_allow_html=True)
                st.rerun()

        else:
            original_structure = st.session_state[structure_key]
            
            if edited_structure_key in st.session_state:
                final_structure = st.session_state[edited_structure_key]
                structure_source = "personalizzata"
            else:
                st.session_state[edited_structure_key] = original_structure.copy()
                final_structure = original_structure
                structure_source = "AI originale"
            
            structure_header_color = "#f59e0b" if st.session_state[show_structure_editor_key] else "#4f46e5"
            structure_bg_color = "#fef7e0" if st.session_state[show_structure_editor_key] else "#f0f4ff"
            
            st.markdown(f"""
            <div style="background-color: {structure_bg_color}; border-left: 4px solid {structure_header_color}; 
                       padding: 15px; margin: 10px 0; border-radius: 8px;">
                <h4 style="color: {structure_header_color}; margin-bottom: 10px;">
                    📋 Struttura Articolo ({len(final_structure)} elementi {structure_source})
                </h4>
            </div>
            """, unsafe_allow_html=True)
            
            if final_structure:
                if not st.session_state[show_structure_editor_key]:
                    display_structure_preview(final_structure)
                else:
                    display_structure_editor(final_structure, edited_structure_key, tab_name, article_index, hash(article['link']))
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                editor_text = "🔧 Chiudi Editor" if st.session_state[show_structure_editor_key] else "✏️ Modifica struttura"
                editor_key = f"toggle_structure_editor_{tab_name}_{article_index}_{hash(article['link'])}"
                if st.button(editor_text, key=editor_key, type="secondary", 
                           disabled=len(final_structure) == 0):
                    st.session_state[show_structure_editor_key] = not st.session_state[show_structure_editor_key]
                    
                    # Scroll smooth dopo toggle
                    st.markdown(f"""
                    <script>
                    setTimeout(() => {{
                        const element = document.getElementById('{section_id}');
                        if (element) {{
                            element.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center'
                            }});
                        }}
                    }}, 100);
                    </script>
                    """, unsafe_allow_html=True)
            
            with col2:
                regen_key = f"regen_structure_{tab_name}_{article_index}_{hash(article['link'])}"
                if st.button("🔄 Rigenera", key=regen_key, type="secondary"):
                    system_prompt = st.session_state.get(system_prompt_key, "")
                    with st.spinner("🤖 Rigenerazione struttura..."):
                        structure = generate_blog_structure(
                            article['full_content'], 
                            article['title'],
                            system_prompt
                        )
                        st.session_state[structure_key] = structure
                        
                        if edited_structure_key in st.session_state:
                            del st.session_state[edited_structure_key]
                        st.session_state[show_structure_editor_key] = False
                    
                    # Scroll smooth dopo rigenerazione
                    st.markdown(f"""
                    <script>
                    setTimeout(() => {{
                        const element = document.getElementById('{section_id}');
                        if (element) {{
                            element.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center'
                            }});
                        }}
                    }}, 100);
                    </script>
                    """, unsafe_allow_html=True)
                    st.rerun()
            
            with col3:
                if st.button("📋 Export JSON", key=f"export_structure_{tab_name}_{article_index}", 
                           type="secondary", disabled=len(final_structure) == 0):
                    
                    export_data = {
                        "article_title": article['title'],
                        "extraction_timestamp": datetime.now().isoformat(),
                        "structure": final_structure,
                        "structure_source": structure_source,
"total_elements": len(final_structure),
                        "system_prompt_used": st.session_state.get(system_prompt_key, "default")
                    }
                    
                    json_output = json.dumps(export_data, ensure_ascii=False, indent=2)
                    st.text_area(
                        "Struttura JSON:", 
                        value=json_output, 
                        height=150,
                        key=f"structure_json_output_{tab_name}_{article_index}",
                        help="Seleziona tutto (Ctrl+A) e copia (Ctrl+C)"
                    )
        
        st.markdown('</div>', unsafe_allow_html=True)  # Chiudi container sezione
    
    else:
        st.markdown(f"""
        <div style="background-color: #f9fafb; border-left: 4px solid #9ca3af; 
                   padding: 15px; margin: 10px 0; border-radius: 8px;">
            <div style="font-weight: bold; color: #6b7280; margin-bottom: 8px;">📋 Struttura Personalizzata disabilitata</div>
            <em style="color: #9ca3af;">Abilita la generazione strutture dalla sidebar.</em>
        </div>
        """, unsafe_allow_html=True)

def display_structure_preview(structure_list):
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
            # Evidenzia le tracce con stile diverso
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

def display_structure_editor(structure_list, edited_structure_key, tab_name, article_index, article_hash):
    """Editor per la struttura dell'articolo"""
    current_structure = st.session_state.get(edited_structure_key, structure_list.copy())
    
    st.markdown("""
    <div style="background-color: #fef7e0; border: 1px dashed #f59e0b; border-radius: 8px; padding: 15px; margin: 10px 0;">
        <h4 style="color: #92400e; margin-bottom: 10px;">✏️ Editor Struttura</h4>
    </div>
    """, unsafe_allow_html=True)
    
    # Tipi disponibili per dropdown
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
                        key=f"edit_content_{i}_{article_hash}"
                    )
                    element["contenuto"] = new_content
                
                with col_type:
                    st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                    new_type = st.selectbox(
                        "Tipo:",
                        options=available_types,
                        index=available_types.index(element.get("tipo", "paragrafo")) if element.get("tipo", "paragrafo") in available_types else 0,
                        key=f"edit_type_{i}_{article_hash}"
                    )
                    element["tipo"] = new_type
                
                with col_actions:
                    st.markdown("<br><br>", unsafe_allow_html=True)  # More spacing
                    
                    # Pulsanti move up/down
                    col_up, col_down, col_del = st.columns(3)
                    with col_up:
                        if st.button("↑", key=f"move_up_{i}_{article_hash}", disabled=i==0, help="Sposta su"):
                            if i > 0:
                                current_structure[i], current_structure[i-1] = current_structure[i-1], current_structure[i]
                                st.session_state[edited_structure_key] = current_structure
                                st.rerun()
                    
                    with col_down:
                        if st.button("↓", key=f"move_down_{i}_{article_hash}", disabled=i==len(current_structure)-1, help="Sposta giù"):
                            if i < len(current_structure) - 1:
                                current_structure[i], current_structure[i+1] = current_structure[i+1], current_structure[i]
                                st.session_state[edited_structure_key] = current_structure
                                st.rerun()
                    
                    with col_del:
                        if st.button("✕", key=f"delete_element_{i}_{article_hash}", help="Elimina", type="secondary"):
                            elements_to_remove.append(element)
                
                st.markdown("<hr>", unsafe_allow_html=True)
        
        # Rimuovi elementi selezionati
        if elements_to_remove:
            for element in elements_to_remove:
                if element in current_structure:
                    current_structure.remove(element)
            st.session_state[edited_structure_key] = current_structure
            st.rerun()
    
    # Aggiungi nuovo elemento
    st.markdown("**➕ Aggiungi nuovo elemento:**")
    col_new_type, col_new_content, col_add = st.columns([1, 2, 1])
    
    with col_new_type:
        new_element_type = st.selectbox(
            "Tipo elemento:",
            options=available_types,
            key=f"new_element_type_{tab_name}_{article_index}_{article_hash}"
        )
    
    with col_new_content:
        new_element_content = st.text_area(
            "Contenuto elemento:",
            placeholder="Inserisci il contenuto per il nuovo elemento...",
            height=80,
            key=f"new_element_content_{tab_name}_{article_index}_{article_hash}"
        )
    
    with col_add:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        if st.button("➕ Aggiungi", key=f"add_element_{tab_name}_{article_index}_{article_hash}", 
                   type="primary", disabled=not new_element_content.strip()):
            if new_element_content.strip():
                new_element = {
                    "tipo": new_element_type,
                    "contenuto": new_element_content.strip()
                }
                current_structure.append(new_element)
                st.session_state[edited_structure_key] = current_structure
                st.success(f"✅ Aggiunto elemento '{new_element_type}'!")
                st.rerun()
    
    # Salva modifiche
    st.session_state[edited_structure_key] = current_structure
    
    st.markdown(f"**📊 Totale elementi:** {len(current_structure)}")

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
            max_completion_tokens=1000
        
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

            ### CRITERI PER L'ESTRAZIONE E SELEZIONE###

            Keyword primarie
            - Sono il focus principale del testo.
            - Corrispondono al tema centrale trattato.
            - Si trovano spesso nei titoli (H1, H2) e vengono ripetute all'inizio dei paragrafi.
            - Generalmente sono 1 o 2 per testo.

            Keyword secondarie / correlate strette
            - Espansioni semantiche della keyword primaria.
            - Comprendono la keyword primaria arricchita da ulteriori specifiche (es. categorie, caratteristiche, processi).
            - Si trovano di frequente nei sottoparagrafi e nelle frasi descrittive.
            - Servono per intercettare ricerche a lunga coda direttamente legate alla keyword primaria.

            Keyword correlate
            - Termini o frasi a lunga coda che non includono direttamente la keyword primaria ma appartengono alla sua stessa area semantica.
            - Possono includere sinonimi, concetti correlati, frasi usate in contesti vicini.
            - Hanno lo scopo di arricchire la copertura semantica, aumentando la rilevanza SEO.

            INDICAZIONI AGGIUNTIVE
            - Dai priorità a keyword tecniche e specifiche del settore.
            - Includi nomi di strumenti, tecnologie, processi, sistemi o applicazioni concrete.
            - Inserisci anche entità rilevanti (es. brand, tecnologie emergenti, normative, soluzioni software).
            - Evita parole troppo generiche, articoli, preposizioni e termini slegati dal contesto tecnico/logistico.
            - Massimo 10 keyword totali (suddivise tra primarie, secondarie e correlate).

            ##ESEMPI DI ESTRAZIONE###
            **individuare keyword primarie (focus del contenuto)**
            Per keyword primarie si intendono le keyword più importanti che che di solito corrispondono al tema principale del testo. 
            Di solito sono presenti nei titoli(H1) e sottotitoli (H2). Viene ripetuta anche all'inizio dei paragrafi.
            ###ESEMPIO PER LE KEYWORD PRIMARIE###

            **estrarre keyword secondarie / correlate (espansione semantica)**
            Per le keyword secondarie si tratta di keyword a lunga coda che comprendono la keyword primaria unita ad ulteriori informazioni/caratteristiche.
            Si possono trovare spesso nelle prime frasi dei paragrafi in quanto aiutano a fornire al lettore le informazioni specifiche del paragrafo
            ###ESEMPIO PER LE KEYWORD SECONDARIE###

            **estrarre keyword correlate**
            Per keyword correlate si intende keyword al lunga coda che non integrano direttamente la keyword primaria ma sinonimi o termini che le collegano alla semnatica della keyword primaria.
            Servono per rafforzare ulteriormente l'informazione fornita dalla keyword primaria e le secondarie. Lo scopo è fornire un quadro ancora più chiaro dell'argomento trattato.

            *Articolo di prova*
            Quante categorie di DPI esistono?
            I dpi si distinguono in tre categorie, ovvero prima, seconda e terza e sono utili per assicurare un grado di protezione adeguato in base al lavoro da svolgere e al contesto professionale.

            DPI di prima categoria
            Si definiscono dpi di prima categoria i dispositivi DPI per rischio minimo, che proteggono dai rischi di basso livello e per i quali i produttori sono autorizzati a testare e autocertificare i loro prodotti. Rientrano tra questi dpi di sicurezza, per esempio, i guanti monouso in nitrile blu.

            DPI di seconda categoria
            I dpi di seconda categoria sono destinati alla protezione da rischi diversi da quelli elencati nelle categorie I e III, ossia i rischi di livello intermedio. Su di essi devono essere effettuati dei test specifici e per la loro certificazione è necessario un organismo abilitato a rilasciare un marchio CE. Senza la marcatura CE, tali DPI di sicurezza non possono essere né commercializzati né utilizzati.

            DPI di terza categoria
            I dpi di terza categoria proteggono dai rischi che possono causare conseguenze molto gravi, quali morte o danni alla salute irreversibili. Sono dunque necessari per chi ha a che fare con prodotti chimici, agenti biologici, scosse elettriche e lavori sotto tensione.

            Gestione dei Dispositivi di Protezione Individuale (DPI)
            La gestione dei Dispositivi di Protezione Individuale (DPI) è un aspetto cruciale della sicurezza sul lavoro. Secondo il D.Lgs. 81/08, la responsabilità di fornire i DPI ricade interamente sul datore di lavoro. Questo include non solo l'acquisto, ma anche la selezione dei dispositivi più adatti in base ai rischi specifici del luogo di lavoro, la loro manutenzione e la garanzia del loro corretto utilizzo. Il datore di lavoro deve consultare il Responsabile del Servizio di Prevenzione e Protezione e, ove presente, il Medico Competente per scegliere i DPI più appropriati. È importante sottolineare che i lavoratori non devono sostenere alcun costo per l'acquisto dei DPI. Il datore di lavoro è anche responsabile di mantenere i dispositivi in efficienza, assicurarne l'igiene e provvedere alle necessarie riparazioni o sostituzioni. La consegna dei DPI ai lavoratori deve essere documentata, e i lavoratori devono essere adeguatamente formati sul loro corretto utilizzo. Questa responsabilità deldatore di lavoro si estende a tutti i settori, inclusi quelli pubblici come il MIUR, dove in alcuni casi specifici i dispositivi possono essere forniti dal Ministero. L'obiettivo finale è garantire la massima protezione dei lavoratori, creando un ambiente di lavoro sicuro e conforme alle normative vigenti.

            **KEYWORD PRIMARIA NELL'ESEMPIO**
            Nell'esempio la keyword primaria è senz'altro "DPI". Si trova in tutti i titoli ed è presente anche nella parte iniziale dei paragrafi.

            **KEYWORD SECONDARIE NELL'ESEMPIO**
            Nell'esempio le keyword secondarie sono:

            - DPI di seconda categoria
            - DPI di terza categoria
            - DPI di prima categoria
            - Dispositivi di Protezione Individuale
            - Dispositivi DPI per rischio minimo
            - DPI di sicurezza 

            Tutte queste forniscono ulteriori informazioni relative ai DPI ed in particolari le categorie e informazioni sulla protezione offerta.
            In quanto sigla tra le secondarie ce la secondaria estesa "Dispositivi di Protezione Individuale".

            **KEYWORD CORRELATE NELL'ESEMPIO**
            Nell'esempio le keyword correlate sono:

            - Quante categorie di DPI esistono
            - Consegna dei DPI ai lavoratori deve essere documentata
            - Costi per l'acquisto dei DPI
            - Protezione dei lavoratori
            - Ambiente di lavoro sicuro

            ### FORMATO OUTPUT:
            Restituisci SOLO le keyword separate da virgola, senza indicare la tipologia o spiegazioni aggiuntive.
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
            max_completion_tokens=200,
            
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
def generate_intelligent_blog_draft(content: str, title: str, structured_summary: str, keywords: List[str], questions: List[str], blog_structure: List[Dict[str, str]] = None) -> str:
    """Genera una bozza di articolo intelligente usando riassunto, keywords, domande e struttura personalizzata"""
    if not AZURE_AVAILABLE:
        return "⚠️ Servizio AI non configurato."
    
    if not content or len(content.strip()) < 50:
        return "Contenuto troppo breve per generare una bozza."
    
    content_truncated = content[:3500] if len(content) > 3500 else content
    keywords_text = ", ".join(keywords[:10]) if keywords else ""
    questions_text = "\n".join([f"- {q}" for q in questions[:8]]) if questions else ""
    summary_for_prompt = structured_summary if structured_summary else ""
    
    # Prepara la struttura personalizzata se fornita
    structure_prompt = ""
    if blog_structure and len(blog_structure) > 0:
        structure_prompt = "\n### STRUTTURA PERSONALIZZATA DA SEGUIRE ###\n"
        for i, element in enumerate(blog_structure, 1):
            tipo = element.get("tipo", "paragrafo")
            contenuto = element.get("contenuto", "")
            structure_prompt += f"{i}. {tipo.upper()}: {contenuto}\n"
        structure_prompt += "\nSEGUI QUESTA STRUTTURA il più fedelmente possibile, adattando e espandendo i contenuti.\n"
    
    try:
        response = client.chat.completions.create(
            model=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": f"""Sei un copywriter esperto specializzato nel settore industriale, ferramenta e utensili per cantieri.
                    
                    ###ISTRUZIONE###
                    Trasforma l'articolo fornito in una bozza ottimizzata per blog aziendale seguendo questi criteri:
                    
                    PRIORITÀ:
                    1. Se è fornita una STRUTTURA PERSONALIZZATA, seguila rigorosamente
                    2. Integra naturalmente le keyword fornite
                    3. Incorpora le domande fornite come sezioni o FAQ
                    4. Usa le informazioni del riassunto per arricchire il contenuto
                    
                    STRUTTURA (se non personalizzata):
                    1. Titolo accattivante e SEO-friendly che comprende la keyword principale
                    2. Introduzione, senza titolo o sottotitolo, descrive il tema e cattura l'attenzione con le informazioni/novità più importanti
                    3. Corpo dell'articolo con sottotitoli H2/H3. H2 per trattare uno degli argomenti principali, H3 per dettagli specifici
                       Se ci sono più argomenti principali, usa più H2.
                    4. Ogni paragrafo, che sia H2 o H3, deve essere conciso e focalizzato su un singolo punto. espandi con dettagli tecnici, esempi pratici, dati rilevanti.
                       Usa elenchi puntati per chiarezza quando appropriato.
                    5. Conclusione con un riassunto per sottolineare le informazioni più importanti. Evidenziare che è un riassunto con un titolo adeguato

                    TESTI DI ESEMPIO:
                    - I testi di esempio dei titoli e dei paragrafi saranno solo una traccia per l'utente. Dovranno solo indicare cosa deve inserire in quel punto (titoli e paragrafi).
                    Indicare quali cìkeyword inderire e che informazione si andrà a trattare nel caso dei paragrafi
                    
                    STILE:
                    - Tono professionale ma accessibile
                    - Integra naturalmente le keyword fornite
                    - Usa elenchi puntati quando appropriato
                    - Includi informazioni tecniche precise
                    - Aggiungi valore pratico per il lettore
                    
                    OTTIMIZZAZIONE SEO:
                    - Keyword density equilibrata
                    - Titoli dei paragrafi ottimizzati utilizzando le keyword fornite
                    
                    FORMATO OUTPUT:
                    Restituisci la bozza in formato Markdown con:
                    - # per il titolo principale
                    - ## per i sottotitoli
                    - ### per i sottotitoli H3
                    - **grassetto** per enfasi
                    - * per elenchi puntati
                    - Lunghezza complessiva non superirore a 1500 parole
                    - Massimo 3 paragrafi per la sezione FAQ, un paragrafo per l'introduzione e la conclusione

                    
                    {structure_prompt}"""
                },
                {
                    "role": "user",
                    "content": f"""Trasforma questo articolo in una bozza ottimizzata per il nostro blog aziendale:

                    TITOLO ORIGINALE: {title}

                    KEYWORDS DA INTEGRARE: {keywords_text}

                    RIASSUNTO STRUTTURATO (usa per arricchire il contenuto):
                    {summary_for_prompt}

                    DOMANDE DA INCORPORARE (massimo 3 domande, come sezioni o FAQ):
                    {questions_text}

                    CONTENUTO ORIGINALE: {content_truncated}

                    Crea una bozza della struttura, professionale e ottimizzata SEO mantenendo l'accuratezza tecnica.
                    I testi di esempio dei titoli e dei paragrafi saranno solo una traccia per l'utente. Dovranno solo indicare cosa deve inserire in quel punto (titoli e paragrafi).
                    Indicare quali cìkeyword inderire e che informazione si andrà a trattare nel caso dei paragrafi"""
                }
            ],
            max_completion_tokens=1800,
        
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
# FUNZIONI DI VISUALIZZAZIONE UI CON UX MIGLIORATA
# ============================================================================

def display_ai_summary_section(article, tab_name, article_index, enable_ai_summary):
    """Visualizza la sezione del riassunto AI con domande editabili e scroll ottimizzato"""
    section_id = create_section_anchor(tab_name, article_index, "summary")
    
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
        
        # Container con ID per scroll
        st.markdown(f'<div id="{section_id}" class="step-section section-container">', unsafe_allow_html=True)
        
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
                # Aggiungi tracking
                streamlit_analytics.track("genera_riassunto_domande", {
                    "tab_name": tab_name,
                    "article_index": article_index,
                    "article_title": article['title'][:50]
                })
                with st.spinner("🤖 Generazione riassunto e domande in corso..."):
                    ai_result = generate_summary_with_questions(article['full_content'], article['title'])
                    
                    summary = ai_result.get("summary", "")
                    questions = ai_result.get("questions", [])
                    
                    st.session_state[summary_key] = summary
                    st.session_state[questions_key] = questions
                
                # JavaScript per scroll smooth alla sezione corrente
                st.markdown(f"""
                <script>
                setTimeout(() => {{
                    const element = document.getElementById('{section_id}');
                    if (element) {{
                        element.scrollIntoView({{
                            behavior: 'smooth',
                            block: 'center'
                        }});
                    }}
                }}, 100);
                </script>
                """, unsafe_allow_html=True)
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
                    
                    # Scroll smooth dopo toggle
                    st.markdown(f"""
                    <script>
                    setTimeout(() => {{
                        const element = document.getElementById('{section_id}');
                        if (element) {{
                            element.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center'
                            }});
                        }}
                    }}, 100);
                    </script>
                    """, unsafe_allow_html=True)
            
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
                    
                    # Scroll smooth dopo rigenerazione
                    st.markdown(f"""
                    <script>
                    setTimeout(() => {{
                        const element = document.getElementById('{section_id}');
                        if (element) {{
                            element.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center'
                            }});
                        }}
                    }}, 100);
                    </script>
                    """, unsafe_allow_html=True)
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
        
        st.markdown('</div>', unsafe_allow_html=True)  # Chiudi container sezione
    
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
    """Visualizza la sezione delle keywords con editor e volumi Ahrefs con scroll ottimizzato"""
    section_id = create_section_anchor(tab_name, article_index, "keywords")
    
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
        
        # Container con ID per scroll
        st.markdown(f'<div id="{section_id}" class="step-section section-container">', unsafe_allow_html=True)
        
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
                # Aggiungi tracking
                streamlit_analytics.track("estrai_keywords_ai", {
                    "tab_name": tab_name,
                    "article_index": article_index,
                    "article_title": article['title'][:50]
                })
                with st.spinner("🤖 Estrazione keywords in corso..."):
                    keywords = extract_keywords(article['full_content'], article['title'])
                    st.session_state[keywords_key] = keywords
                    if edited_keywords_key in st.session_state:
                        del st.session_state[edited_keywords_key]
                    st.session_state[volumes_key] = {}
                
                # JavaScript per scroll smooth alla sezione corrente
                st.markdown(f"""
                <script>
                setTimeout(() => {{
                    const element = document.getElementById('{section_id}');
                    if (element) {{
                        element.scrollIntoView({{
                            behavior: 'smooth',
                            block: 'center'
                        }});
                    }}
                }}, 100);
                </script>
                """, unsafe_allow_html=True)
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
                    header_text = "🎯 Step 1: Personalizza Keywords (Editor Attivo)"
                    header_color = "#f59e0b"
                    bg_color = "#fef7e0"
                else:
                    header_text = f"🏷️ Step 1: Keywords {keywords_source.title()}"
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
                st.markdown("<hr>", unsafe_allow_html=True)
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
                        
                        # Scroll smooth dopo toggle
                        st.markdown(f"""
                        <script>
                        setTimeout(() => {{
                            const element = document.getElementById('{section_id}');
                            if (element) {{
                                element.scrollIntoView({{
                                    behavior: 'smooth',
                                    block: 'center'
                                }});
                            }}
                        }}, 100);
                        </script>
                        """, unsafe_allow_html=True)
                
                with col2:
                    volumes_button_key = f"get_volumes_{tab_name}_{article_index}_{hash(article['link'])}"
                    volumes_disabled = len(final_keywords) == 0 or not ahrefs_api_token
                    button_text = "📊 Ottieni Volumi" if ahrefs_api_token else "📊 API Non Config."
                    if st.button(button_text, key=volumes_button_key, type="primary", 
                            disabled=volumes_disabled,
                            help="Cerca volumi Ahrefs per le keywords selezionate" if ahrefs_api_token else "API Ahrefs non configurata"):
                        # Aggiungi tracking
                        streamlit_analytics.track("ottieni_volumi_keywords", {
                            "tab_name": tab_name,
                            "article_index": article_index,
                            "num_keywords": len(final_keywords)
                        })
                        if final_keywords and ahrefs_api_token:
                            with st.spinner(f"📊 Ricerca volumi per {len(final_keywords)} keywords..."):
                                batch_results = get_multiple_keywords_volumes(final_keywords, "it")
                                
                                new_volumes = {}
                                for keyword, result in batch_results.items():
                                    if result["status"] == "success":
                                        new_volumes[keyword] = result["volume"]
                                
                                st.session_state[volumes_key] = new_volumes
                                st.session_state[show_editor_key] = False
                            
                            # Scroll smooth dopo ricerca volumi
                            st.markdown(f"""
                            <script>
                            setTimeout(() => {{
                                const element = document.getElementById('{section_id}');
                                if (element) {{
                                    element.scrollIntoView({{
                                        behavior: 'smooth',
                                        block: 'center'
                                    }});
                                }}
                            }}, 100);
                            </script>
                            """, unsafe_allow_html=True)
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
                        
                        # Scroll smooth dopo rigenerazione
                        st.markdown(f"""
                        <script>
                        setTimeout(() => {{
                            const element = document.getElementById('{section_id}');
                            if (element) {{
                                element.scrollIntoView({{
                                    behavior: 'smooth',
                                    block: 'center'
                                }});
                            }}
                        }}, 100);
                        </script>
                        """, unsafe_allow_html=True)
                        st.rerun()
                        
            else:
                # Dopo aver ottenuto i volumi
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🎯 Modifica Keywords", key=f"edit_after_volumes_{tab_name}_{article_index}", 
                            type="secondary", help="Modifica keywords (resetterà volumi)"):
                        # Aggiungi tracking
                        streamlit_analytics.track("modifica_keywords_post_volumi", {
                            "tab_name": tab_name,
                            "article_index": article_index
                        })
                        st.session_state[volumes_key] = {}
                        st.session_state[show_editor_key] = True
                        
                        # Scroll smooth dopo reset volumi
                        st.markdown(f"""
                        <script>
                        setTimeout(() => {{
                            const element = document.getElementById('{section_id}');
                            if (element) {{
                                element.scrollIntoView({{
                                    behavior: 'smooth',
                                    block: 'center'
                                }});
                            }}
                        }}, 100);
                        </script>
                        """, unsafe_allow_html=True)
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
                            
                            # Scroll smooth dopo aggiornamento
                            st.markdown(f"""
                            <script>
                            setTimeout(() => {{
                                const element = document.getElementById('{section_id}');
                                if (element) {{
                                    element.scrollIntoView({{
                                        behavior: 'smooth',
                                        block: 'center'
                                    }});
                                }}
                            }}, 100);
                            </script>
                            """, unsafe_allow_html=True)
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
        
        st.markdown('</div>', unsafe_allow_html=True)  # Chiudi container sezione
    
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
    """Sezione per generazione bozza blog intelligente con editor integrato e scroll ottimizzato"""
    section_id = create_section_anchor(tab_name, article_index, "blog_draft")
    
    if enable_blog_draft:
        blog_draft_key = f"blog_draft_{tab_name}_{article_index}_{hash(article['link'])}"
        edited_blog_draft_key = f"edited_blog_draft_{tab_name}_{article_index}_{hash(article['link'])}"
        blog_approval_key = f"blog_approve_{tab_name}_{article_index}_{hash(article['link'])}"
        show_blog_editor_key = f"show_blog_editor_{tab_name}_{article_index}_{hash(article['link'])}"
        
        keywords_key = f"keywords_{tab_name}_{article_index}_{hash(article['link'])}"
        edited_keywords_key = f"edited_keywords_{tab_name}_{article_index}_{hash(article['link'])}"
        volumes_key = f"volumes_{tab_name}_{article_index}_{hash(article['link'])}"
        
        questions_key = f"questions_{tab_name}_{article_index}_{hash(article['link'])}"
        edited_questions_key = f"edited_questions_{tab_name}_{article_index}_{hash(article['link'])}"
        summary_key = f"summary_{tab_name}_{article_index}_{hash(article['link'])}"
        
        if blog_draft_key not in st.session_state:
            st.session_state[blog_draft_key] = None
        if show_blog_editor_key not in st.session_state:
            st.session_state[show_blog_editor_key] = False
        
        # Container con ID per scroll
        st.markdown(f'<div id="{section_id}" class="step-section section-container blog-draft-container">', unsafe_allow_html=True)
        
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
                <h4 style="color: #92400e; margin-bottom: 15px;text-align: center;">✍️ Step 4: Bozza Blog Intelligente</h4>
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
                
                # Ottieni la struttura personalizzata se disponibile PRIMA del tracking
                structure_key = f"structure_{tab_name}_{article_index}_{hash(article['link'])}"
                edited_structure_key = f"edited_structure_{tab_name}_{article_index}_{hash(article['link'])}"
                
                blog_structure = None
                if edited_structure_key in st.session_state and st.session_state[edited_structure_key]:
                    blog_structure = st.session_state[edited_structure_key]
                elif structure_key in st.session_state and st.session_state[structure_key]:
                    blog_structure = st.session_state[structure_key]
                
                # Aggiungi tracking - ORA blog_structure è definita
                streamlit_analytics.track("genera_bozza_blog", {
                    "tab_name": tab_name,
                    "article_index": article_index,
                    "article_title": article['title'][:50],
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
                    st.session_state[blog_draft_key] = blog_draft
                
                # JavaScript per scroll smooth alla sezione corrente
                st.markdown(f"""
                <script>
                setTimeout(() => {{
                    const element = document.getElementById('{section_id}');
                    if (element) {{
                        element.scrollIntoView({{
                            behavior: 'smooth',
                            block: 'center'
                        }});
                    }}
                }}, 100);
                </script>
                """, unsafe_allow_html=True)
                st.rerun()
            
            if not has_minimum_content:
                st.info("💡 **Suggerimento:** Genera prima il riassunto e/o estrai keywords/domande per una bozza completa e ottimizzata.")
        
        else:
            original_blog_draft = st.session_state[blog_draft_key]
            
            # Gestisci versione editata vs originale
            if edited_blog_draft_key in st.session_state:
                final_blog_draft = st.session_state[edited_blog_draft_key]
                blog_draft_source = "personalizzata"
            else:
                st.session_state[edited_blog_draft_key] = original_blog_draft
                final_blog_draft = original_blog_draft
                blog_draft_source = "AI originale"
            
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
            
            # Header dinamico basato su editor stato
            header_color = "#f59e0b" if st.session_state[show_blog_editor_key] else "#065f46"
            bg_color = "#fef7e0" if st.session_state[show_blog_editor_key] else "#ecfdf5"
            
            st.markdown(f"""
            <div style="background-color: {bg_color}; border-left: 4px solid {header_color}; 
                       padding: 15px; margin: 10px 0; border-radius: 8px;">
                <h4 style="color: {header_color}; margin-bottom: 10px;">
                    ✅ Bozza Blog ({blog_draft_source})
                </h4>
                <small style="color: {header_color};">🧠 Ottimizzata con: {optimization_text}</small>
            </div>
            """, unsafe_allow_html=True)
            
            # Mostra contenuto o editor
            if not st.session_state[show_blog_editor_key]:
                st.markdown("### 📖 Bozza Blog Generata")
                st.markdown(final_blog_draft)
            else:
                display_blog_draft_editor(final_blog_draft, edited_blog_draft_key, tab_name, article_index, hash(article['link']))
            
            # Pulsanti di controllo
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                editor_text = "🔧 Chiudi Editor" if st.session_state[show_blog_editor_key] else "✏️ Modifica bozza"
                editor_key = f"toggle_blog_editor_{tab_name}_{article_index}_{hash(article['link'])}"
                if st.button(editor_text, key=editor_key, type="secondary"):

                    st.session_state[show_blog_editor_key] = not st.session_state[show_blog_editor_key]
                    
                    # Scroll smooth dopo toggle
                    st.markdown(f"""
                    <script>
                    setTimeout(() => {{
                        const element = document.getElementById('{section_id}');
                        if (element) {{
                            element.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center'
                            }});
                        }}
                    }}, 100);
                    </script>
                    """, unsafe_allow_html=True)
            
            with col2:
                if st.button("📋 Copia Bozza", key=f"copy_blog_{tab_name}_{article_index}"):
                    st.text_area(
                        "Bozza per copia:",
                        value=final_blog_draft,
                        height=150,
                        key=f"copy_area_{tab_name}_{article_index}",
                        help="Seleziona tutto (Ctrl+A) e copia (Ctrl+C)"
                    )
            
            with col3:
                if st.button("🔄 Rigenera", key=f"regen_blog_{tab_name}_{article_index}", type="secondary"):
                    with st.spinner("🤖 Rigenerazione bozza intelligente..."):
                        # Ottieni la struttura personalizzata se disponibile
                        structure_key = f"structure_{tab_name}_{article_index}_{hash(article['link'])}"
                        edited_structure_key = f"edited_structure_{tab_name}_{article_index}_{hash(article['link'])}"
                        
                        blog_structure = None
                        if edited_structure_key in st.session_state and st.session_state[edited_structure_key]:
                            blog_structure = st.session_state[edited_structure_key]
                        elif structure_key in st.session_state and st.session_state[structure_key]:
                            blog_structure = st.session_state[structure_key]
                        
                        blog_draft = generate_intelligent_blog_draft(
                            content=article['full_content'],
                            title=article['title'], 
                            structured_summary=used_summary,
                            keywords=used_keywords,
                            questions=used_questions,
                            blog_structure=blog_structure
                        )
                        st.session_state[blog_draft_key] = blog_draft
                        
                        # Reset editor
                        if edited_blog_draft_key in st.session_state:
                            del st.session_state[edited_blog_draft_key]
                        st.session_state[show_blog_editor_key] = False
                    
                    # Scroll smooth dopo rigenerazione
                    st.markdown(f"""
                    <script>
                    setTimeout(() => {{
                        const element = document.getElementById('{section_id}');
                        if (element) {{
                            element.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center'
                            }});
                        }}
                    }}, 100);
                    </script>
                    """, unsafe_allow_html=True)
                    st.rerun()
            
            with col4:
                if st.button("🎯 Modifica Contenuti", key=f"change_content_blog_{tab_name}_{article_index}", type="secondary"):
                    # Aggiungi tracking
                    streamlit_analytics.track("modifica_contenuti_blog", {
                        "tab_name": tab_name,
                        "article_index": article_index
                    })
                    st.session_state[blog_draft_key] = None
                    if edited_blog_draft_key in st.session_state:
                        del st.session_state[edited_blog_draft_key]
                    st.session_state[show_blog_editor_key] = False
                    
                    # Scroll smooth dopo reset
                    st.markdown(f"""
                    <script>
                    setTimeout(() => {{
                        const element = document.getElementById('{section_id}');
                        if (element) {{
                            element.scrollIntoView({{
                                behavior: 'smooth',
                                block: 'center'
                            }});
                        }}
                    }}, 100);
                    </script>
                    """, unsafe_allow_html=True)
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)  # Chiudi container sezione
    
    else:
        st.markdown(f"""
        <div class="blog-draft-section" style="background-color: #f9fafb; border-left-color: #9ca3af;">
            <div class="blog-draft-header" style="color: #6b7280;">✍️ Bozze Blog disabilitate</div>
            <em style="color: #9ca3af;">Abilita le bozze blog dalla sidebar.</em>
        </div>
        """, unsafe_allow_html=True)

def display_blog_draft_editor(blog_draft_text, edited_blog_draft_key, tab_name, article_index, article_hash):
    """Editor per la bozza del blog"""
    current_draft = st.session_state.get(edited_blog_draft_key, blog_draft_text)
    
    st.markdown("""
    <div style="background-color: #fef7e0; border: 1px dashed #f59e0b; border-radius: 8px; padding: 15px; margin: 10px 0;">
        <h4 style="color: #92400e; margin-bottom: 10px;">✏️ Editor Bozza Blog</h4>
        <p style="color: #92400e; font-size: 12px; margin-bottom: 10px;">
            Modifica direttamente il contenuto della bozza. Le modifiche saranno salvate automaticamente.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Editor principale con text_area grande
    new_draft = st.text_area(
        "Contenuto bozza:",
        value=current_draft,
        height=400,
        key=f"blog_draft_editor_{tab_name}_{article_index}_{article_hash}",
        help="Modifica direttamente il contenuto della bozza blog. Supporta Markdown."
    )
    
    # Salva automaticamente le modifiche
    st.session_state[edited_blog_draft_key] = new_draft
    
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
    
    # Pulsanti di utility
    col_reset, col_preview = st.columns(2)
    
    with col_reset:
        if st.button("🔄 Ripristina Originale", 
                    key=f"reset_blog_draft_{tab_name}_{article_index}_{article_hash}", 
                    type="secondary",
                    help="Ripristina la bozza AI originale (perderà le modifiche)"):
            st.session_state[edited_blog_draft_key] = blog_draft_text
            st.rerun()
    
    with col_preview:
        if st.button("👁️ Anteprima Markdown", 
                    key=f"preview_blog_draft_{tab_name}_{article_index}_{article_hash}",
                    help="Mostra come apparirà il markdown formattato"):
            with st.expander("📖 Anteprima Formattata", expanded=True):
                st.markdown(new_draft)
    
    # Suggerimenti per l'editing
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

def display_articles(articles, tab_name="", enable_ai_summary=True, enable_keywords=True, enable_blog_draft=True):
    """Visualizza gli articoli in formato card con funzionalità AI con scroll ottimizzato per UX migliorata"""
    
    if not articles:
        st.info("Nessun articolo disponibile per questa categoria.")
        return
    
    try:
        articles.sort(key=lambda x: datetime.strptime(x['published'].split()[0], '%d/%m/%Y') if '/' in x['published'] else datetime.min, reverse=True)
    except:
        pass
    
    for i, article in enumerate(articles):
        # Crea un container con ID univoco per ogni articolo
        article_id = f"article_{tab_name}_{i}_{hash(article['link'])}"
        st.markdown(f'<div id="{article_id}" class="article-container">', unsafe_allow_html=True)
        
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
            
            # SEZIONI IN DUE COLONNE
            col1, col2 = st.columns([1, 1])
            
            with col1:
                display_keywords_section(article, tab_name, i, enable_keywords)
            
            with col2:
                display_ai_summary_section(article, tab_name, i, enable_ai_summary)
            
            # STRUTTURA PERSONALIZZATA A FULL WIDTH (Step 3)
            display_structure_section(article, tab_name, i, enable_ai_summary)
            
            # BOZZA BLOG A FULL WIDTH (Step 4)
            if enable_blog_draft:
                display_blog_draft_section_full_width(article, tab_name, i, enable_blog_draft)
            
            st.markdown("<hr>", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Chiudi container articolo

# ============================================================================
# FUNZIONE MAIN
# ============================================================================

# Sostituisci la sezione feeds nella funzione main() con questo codice

def main():
    with streamlit_analytics.track():
        # Inizializza analytics all'inizio
        streamlit_analytics.start_tracking()
        st.title("Articoli dei competitor utili - RSS Feed Reader")
        st.markdown("*Tool ideato per poter generare una bozza utile di articolo utilizzando i contenuti dei competitor*")
        
        # STRUTTURA FEEDS CORRETTA - Supporta multiple fonti per categoria
        feeds = {
            "Automotive": [
                {"url": "https://www.automotive-news.it/feed/", "source": "Automotive News"},
                {"url": "https://www.inforicambi.it/feed", "source": "Info Ricambi"}
            ],
            "Logistic": [
                {"url": "https://www.logisticanews.it/feed/", "source": "Logistica News"}
            ],
            "Sicurezza": [
                {"url": "https://www.puntosicuro.it/feed.rss", "source": "Punto Sicuro"},
                {"url": "https://rss.app/feeds/K7dowcZBM8RXbT0w.xml", "source": "RSS app"},
                {"url": "https://rss.app/feeds/lbhrQtpF3vPaalRl.xml", "source": "Certifico"},
                {"url": "https://rss.app/feeds/EUBx8RfnzG0NksVC.xml", "source": "PVS"}
            ],
            "Sostenibilità": [
                {"url": "https://rss.app/feeds/JSL6rhDcA8Xix702.xml", "source": "RSS app"}
            ],
            "Edilizia": [
                {"url": "https://rss.app/feeds/xaEyeqF8dPlqNBkC.xml", "source": "RSS app"},
                {"url": "https://rss.app/feeds/mcFgAYTettUbW4uL.xml", "source": "Teknoring"},
                {"url": "https://rss.app/feeds/4LtvXUj3HfZTGjp3.xml", "source": "Ingenio"},
                {"url": "https://rss.app/feeds/mIWnpHFRX9qdUk2T.xml", "source": "Ediltecnico"},
                {"url": "https://rss.app/feeds/5qjAycQkiLnx3J9Z.xml", "source": "Il giornale dell'ingeniere"},
                {"url": "https://rss.app/feeds/BslWyLg0K7w9l8JS.xml", "source": "Edilizia.com"},
                {"url": "https://rss.app/feeds/IKoHHF0URcI5uwEe.xml", "source": "Giuda edilizia"},
                {"url": "https://rss.app/feeds/LtaLGxSQkKp53n8P.xml", "source": "Ferrutensil"},
                {"url": "https://rss.app/feeds/9KhLOkevfMkm2NKu.xml", "source": "Istituto Giordano"}
            ],
            "Industria": [
                {"url": "https://rss.app/feeds/aTnohv8ofErEMSNm.xml", "source": "RSS app"}
            ],
            "Legno": [
                {"url": "https://rss.app/feeds/gynaWAjP6OwTxznl.xml", "source": "Infobuild"}
            ]
        }
        
        # Sidebar essenziale
        st.sidebar.header("🔍 Controlli")
        
        # Info API status Ahrefs
        # if ahrefs_api_token:
        #     st.sidebar.success("✅ API Ahrefs configurata")
        # else:
        #     st.sidebar.warning("⚠️ API Ahrefs non configurata")
        
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
        
        # Cache per i feed - AGGIORNATA per supportare multiple fonti
        @st.cache_data(ttl=300)  # Cache per 5 minuti
        def get_all_articles():
            all_articles = []
            feed_stats = {}
            
            for category, sources in feeds.items():
                if category in selected_categories:
                    category_articles = []
                    total_count = 0
                    
                    for source_info in sources:
                        url = source_info["url"]
                        source_name = source_info["source"]
                        
                        try:
                            articles, count = fetch_feed(url, f"{category} - {source_name}")
                            category_articles.extend(articles[:10])  # Max 10 per fonte
                            total_count += count
                            
                            # Log per debug delle fonti
                            # st.sidebar.text(f"✓ {source_name}: {count} articoli")
                            
                        except Exception as e:
                            st.sidebar.error(f"❌ {source_name}: Errore")
                            continue
                    
                    all_articles.extend(category_articles)
                    feed_stats[category] = total_count
            
            return all_articles, feed_stats
        
        # Recupera tutti gli articoli
        all_articles, feed_stats = get_all_articles()
        
        # Statistiche nella sidebar - AGGIORNATA
        st.sidebar.markdown("### 📊 Statistiche Feed")
        for category, total_count in feed_stats.items():
            articles_in_category = [a for a in all_articles if a['source_category'].startswith(category)]
            images_in_category = len([a for a in articles_in_category if a['has_image']])
            
            # Mostra dettaglio fonti per Automotive
            if category == "Automotive":
                automotive_news_count = len([a for a in articles_in_category if "Automotive News" in a['source_category']])
                inforicambi_count = len([a for a in articles_in_category if "Info Ricambi" in a['source_category']])
                detail_text = f"Auto News: {automotive_news_count}, Info Ricambi: {inforicambi_count}"
            else:
                detail_text = f"{images_in_category} con immagini"
            
            st.sidebar.metric(
                f"{category}", 
                f"{len(articles_in_category)}/{total_count}",
                delta=detail_text,
                help=f"Articoli mostrati/totali. {detail_text}"
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
        1. **Estrai le keyword con l'AI e personalizzale secondo le tue esigenze**
        2. **Genera riassunto + estrai le domande per ogni articolo che ti interessa**
        3. **Genera la struttura personalizzata della bozza del tuo articolo**
        4. **Genera la bozza del tuo articolo ottimizzata con tutti i tuoi contenuti personalizzati**
        """)
        
        # Tabs per le categorie - AGGIORNATA per gestire sottocategorie
        if len(selected_categories) > 1:
            tabs = st.tabs(["Tutti"] + selected_categories)
            
            with tabs[0]:
                display_articles([a for a in all_articles], "tutti", True, True, True)
            
            for i, category in enumerate(selected_categories, 1):
                with tabs[i]:
                    # Filtra articoli per categoria (include sottocategorie)
                    category_articles = [a for a in all_articles if a['source_category'].startswith(category)]
                    display_articles(category_articles, category.lower(), True, True, True)
        else:
            category_name = selected_categories[0] if selected_categories else "default"
            # Filtra per categoria principale
            filtered_articles = [a for a in all_articles if a['source_category'].startswith(category_name)]
            display_articles(filtered_articles, category_name.lower(), True, True, True)


# INOLTRE, aggiorna la funzione fetch_feed per gestire meglio il source naming:

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
                'source_category': category,  # Ora include il nome della fonte
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
# ESECUZIONE PRINCIPALE 
# ============================================================================

if __name__ == "__main__":
    main()
