import logging
import warnings
import streamlit as st
from config.settings import RSS_FEEDS, PAGE_TITLE, PAGE_ICON, FEED_CACHE_TTL
from utils.rss_fetcher import fetch_feed
from utils.ui_components import inject_custom_css
from utils.analytics import track_event
from datetime import datetime, timedelta
import hashlib

# Silenzia i warning di ScriptRunContext
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inietta CSS
inject_custom_css()

# Tag noindex
st.markdown('<meta name="robots" content="noindex, nofollow">', unsafe_allow_html=True)

def generate_article_id(article: dict) -> str:
    """Genera ID univoco per articolo basato sul link"""
    return hashlib.md5(article['link'].encode()).hexdigest()


def display_article_card(article: dict, index: int):
    """Visualizza card articolo con pulsante che naviga alla pagina elaborazione"""
    article_id = generate_article_id(article)
    
    # Immagine o placeholder
    if article['has_image'] and article['image_url']:
        image_html = f'<img src="{article["image_url"]}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 8px;">'
    else:
        image_html = '<div style="width: 100%; height: 150px; display: flex; align-items: center; justify-content: center; background-color: #f3f4f6; border-radius: 8px; font-size: 48px; color: #9ca3af;">📄</div>'
    
    card_html = f"""
    <div class="article-card">
        <div style="margin-bottom: 15px;">
            {image_html}
        </div>
        <div class="article-title">{article['title']}</div>
        <div class="article-meta">
            <span class="category-tag">{article['source_category']}</span>
            📅 {article['published']}
        </div>
        <div class="article-content">{article['preview']}</div>
    </div>
    """
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        st.markdown(card_html, unsafe_allow_html=True)
    
    with col2:
        # ✅ CORRETTO: Usa bottone Streamlit nativo con switch_page
        if st.button("📊 Elabora", key=f"elabora_{article_id}_{index}", use_container_width=True, type="primary"):
            # Salva articolo in session_state
            st.session_state['current_article'] = article
            st.session_state['current_article_id'] = article_id
            
            # Reset degli step di elaborazione
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
            
            # Track evento
            track_event("elabora_articolo", "lista_articoli", {
                "article_id": article_id,
                "category": article['source_category']
            })
            
            # ✅ Naviga alla pagina di elaborazione
            st.switch_page("pages/01_Elaborazione_Articolo.py")
        
        st.link_button("🔗 Leggi", article['link'], use_container_width=True)


def main():
    st.title("📰 RSS Feed Reader")
    st.markdown("*Tool per analizzare e elaborare articoli dai competitor del settore industriale*")
    
    # Sidebar
    st.sidebar.header("🔍 Controlli")
    
    # Filtro categorie
    selected_categories = st.sidebar.multiselect(
        "Seleziona categorie:",
        options=list(RSS_FEEDS.keys()),
        default=list(RSS_FEEDS.keys())
    )
    
    # Filtro range date
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Filtro Date")
    
    enable_date_filter = st.sidebar.checkbox("Abilita filtro date", value=False)
    
    date_from = None
    date_to = None
    
    if enable_date_filter:
        col_from, col_to = st.sidebar.columns(2)
        
        with col_from:
            date_from = st.date_input(
                "Da:",
                value=datetime.now() - timedelta(days=30),
                max_value=datetime.now(),
                key="date_from"
            )
        
        with col_to:
            date_to = st.date_input(
                "A:",
                value=datetime.now(),
                max_value=datetime.now(),
                key="date_to"
            )
        
        # Validazione
        if date_from > date_to:
            st.sidebar.error("⚠️ La data 'Da' deve essere precedente alla data 'A'")
            date_from = None
            date_to = None
    
    st.sidebar.markdown("---")
    
    # Pulsante refresh
    if st.sidebar.button("🔄 Aggiorna Feed", type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # Cache feed
    @st.cache_data(ttl=FEED_CACHE_TTL)
    def get_all_articles():
        all_articles = []
        feed_stats = {}
        
        for category, sources in RSS_FEEDS.items():
            if category in selected_categories:
                category_articles = []
                total_count = 0
                
                for source_info in sources:
                    url = source_info["url"]
                    source_name = source_info["source"]
                    
                    try:
                        articles, count = fetch_feed(url, f"{category} - {source_name}")
                        category_articles.extend(articles[:10])
                        total_count += count
                    except Exception as e:
                        continue
                
                all_articles.extend(category_articles)
                feed_stats[category] = total_count
        
        return all_articles, feed_stats
    
    # Recupera articoli
    all_articles, feed_stats = get_all_articles()
    
    # APPLICA FILTRO DATE
    if enable_date_filter and date_from and date_to:
        filtered_by_date = []
        
        for article in all_articles:
            try:
                date_str = article['published'].split()[0]
                if '/' in date_str:
                    article_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                    
                    if date_from <= article_date <= date_to:
                        filtered_by_date.append(article)
            except:
                filtered_by_date.append(article)
        
        all_articles = filtered_by_date
        
        st.info(f"📅 **Filtro date attivo:** {date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')} | {len(all_articles)} articoli trovati")
    
    # Statistiche sidebar
    st.sidebar.markdown("### 📊 Statistiche Feed")
    for category, total_count in feed_stats.items():
        articles_in_category = [a for a in all_articles if a['source_category'].startswith(category)]
        images_in_category = len([a for a in articles_in_category if a['has_image']])
        
        st.sidebar.metric(
            f"{category}", 
            f"{len(articles_in_category)}",
            delta=f"{images_in_category} con immagini"
        )
    
    total_with_images = len([a for a in all_articles if a['has_image']])
    st.sidebar.markdown(f"**Articoli totali:** {len(all_articles)}")
    if len(all_articles) > 0:
        st.sidebar.markdown(f"**Con immagini:** {total_with_images} ({total_with_images/len(all_articles)*100:.1f}%)")
    
    # Contenuto principale
    if not all_articles:
        st.warning("Nessun articolo trovato con i filtri selezionati.")
        return
    
    st.info("""
    **Come usare l'app:**
    1. Clicca su **📊 Elabora** per aprire la pagina di elaborazione
    2. Nella pagina elaborazione potrai generare riassunto, keywords, struttura e bozza blog
    3. Ogni step può essere personalizzato e modificato
    """)
    
    st.markdown("---")
    
    # TAB PER CATEGORIE
    if len(selected_categories) > 1:
        tab_names = ["Tutti"] + selected_categories
        tabs = st.tabs(tab_names)
        
        # Tab "Tutti" - ORDINATO PER DATA
        with tabs[0]:
            st.markdown(f"### 📰 Tutti gli articoli ({len(all_articles)})")
            
            # Ordina per data (più recente prima)
            try:
                sorted_articles = sorted(
                    all_articles, 
                    key=lambda x: datetime.strptime(x['published'].split()[0], '%d/%m/%Y') if '/' in x['published'] else datetime.min,
                    reverse=True
                )
            except:
                sorted_articles = all_articles
            
            for i, article in enumerate(sorted_articles):
                display_article_card(article, i)
        
        # Tab per ogni categoria
        for idx, category in enumerate(selected_categories, start=1):
            with tabs[idx]:
                category_articles = [a for a in all_articles if a['source_category'].startswith(category)]
                st.markdown(f"### 📰 {category} ({len(category_articles)} articoli)")
                
                if category_articles:
                    for i, article in enumerate(category_articles):
                        display_article_card(article, f"{category}_{i}")
                else:
                    st.info(f"Nessun articolo disponibile per {category}")
    
    else:
        category_name = selected_categories[0] if selected_categories else "default"
        filtered_articles = [a for a in all_articles if a['source_category'].startswith(category_name)]
        
        st.markdown(f"### 📰 {category_name} ({len(filtered_articles)} articoli)")
        for i, article in enumerate(filtered_articles):
            display_article_card(article, i)


if __name__ == "__main__":
    main()
