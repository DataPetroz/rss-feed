import streamlit as st
import json
import re
import logging
from typing import List, Dict, Any
from openai import AzureOpenAI
from config.settings import (
    AZURE_ENDPOINT, 
    AZURE_API_KEY, 
    AZURE_DEPLOYMENT_NAME,
    AZURE_API_VERSION
)

logging.basicConfig(level=logging.WARNING)

# Inizializza client Azure OpenAI
try:
    client = AzureOpenAI(
        api_key=AZURE_API_KEY,
        api_version=AZURE_API_VERSION,
        azure_endpoint=AZURE_ENDPOINT
    )
    AZURE_AVAILABLE = True
except Exception as e:
    logging.error(f"Errore inizializzazione Azure OpenAI: {e}")
    AZURE_AVAILABLE = False


@st.cache_data(ttl=1800)
def extract_keywords(content: str, title: str) -> List[str]:
    """Estrae le keyword principali dell'articolo usando Azure OpenAI GPT-4o-mini"""
    if not AZURE_AVAILABLE:
        return ["⚠️ Servizio AI non configurato"]
    
    if not content or len(content.strip()) < 50:
        return ["Contenuto troppo breve"]
    
    content_truncated = content[:3000] if len(content) > 3000 else content
    
    try:
        response = client.chat.completions.create(
            model=AZURE_DEPLOYMENT_NAME,
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
        error_msg = str(e)
        
        # ✅ Gestione errore Content Filter
        if 'content_filter' in error_msg.lower() or 'content management policy' in error_msg.lower():
            logging.warning(f"Content filter triggered per keywords: {error_msg}")
            return ["⚠️ Elaborazione bloccata dal modello per violazioni delle policy"]
        
        logging.error(f"Errore Azure OpenAI per keywords: {e}")
        return ["⚠️ Errore nell'estrazione keywords"]
        
    except Exception as e:
        logging.error(f"Errore Azure OpenAI per keywords: {e}")
        return ["⚠️ Errore nell'estrazione keywords"]
# Continuazione di ai_services.py

@st.cache_data(ttl=1800)
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
            model=AZURE_DEPLOYMENT_NAME,
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
        error_msg = str(e)
        
        # ✅ Gestione errore Content Filter
        if 'content_filter' in error_msg.lower() or 'content management policy' in error_msg.lower():
            logging.warning(f"Content filter triggered per summary: {error_msg}")
            return {
                "summary": "⚠️ Elaborazione bloccata dal modello per violazioni delle policy. Il contenuto dell'articolo potrebbe contenere tematiche sensibili.",
                "questions": []
            }
        
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

# Continuazione di ai_services.py

@st.cache_data(ttl=1800)
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
            model=AZURE_DEPLOYMENT_NAME,
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
                    
                    ###TIPI DISPONIBILI###
                    - titolo_principale (H1) - UNO SOLO
                    - introduzione - UNA SOLA
                    - sottotitolo (H2) - Per argomenti principali
                    - sottotitolo_h3 (H3) - SOLO se necessario per sottoargomenti complessi
                    - paragrafo - Contenuto di sviluppo
                    - elenco_puntato - Liste quando appropriato
                    - conclusione - UNA SOLA
                    - call_to_action - Opzionale
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
            max_tokens=1500,
            temperature=0.3
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        try:
            parsed_response = json.loads(ai_response)
            
            if "struttura" in parsed_response and isinstance(parsed_response["struttura"], list):
                return parsed_response["struttura"]
            else:
                return [{"tipo": "errore", "contenuto": "Formato JSON non valido"}]
                
        except json.JSONDecodeError:
            return extract_structure_from_text(ai_response)
        
    except Exception as e:
        error_msg = str(e)
        
        # ✅ Gestione errore Content Filter
        if 'content_filter' in error_msg.lower() or 'content management policy' in error_msg.lower():
            logging.warning(f"Content filter triggered per struttura: {error_msg}")
            return [{"tipo": "errore", "contenuto": "⚠️ Elaborazione bloccata dal modello per violazioni delle policy"}]
        
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

# Continuazione e conclusione di ai_services.py

@st.cache_data(ttl=1800)
def generate_intelligent_blog_draft(
    content: str, 
    title: str, 
    structured_summary: str, 
    keywords: List[str], 
    questions: List[str], 
    blog_structure: List[Dict[str, str]] = None
) -> str:
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
            model=AZURE_DEPLOYMENT_NAME,
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
                    Indicare quali keyword inserire e che informazione si andrà a trattare nel caso dei paragrafi
                    
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
                    - Lunghezza complessiva non superiore a 1500 parole
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
                    Indicare quali keyword inserire e che informazione si andrà a trattare nel caso dei paragrafi"""
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
        error_msg = str(e)
        
        # ✅ Gestione errore Content Filter
        if 'content_filter' in error_msg.lower() or 'content management policy' in error_msg.lower():
            logging.warning(f"Content filter triggered per blog draft: {error_msg}")
            return "⚠️ Elaborazione bloccata dal modello per violazioni delle policy. Il contenuto potrebbe contenere tematiche sensibili o non conformi alle linee guida."
        
        logging.error(f"Errore Azure OpenAI per blog draft intelligente: {e}")
        return "⚠️ Errore nella generazione della bozza intelligente."