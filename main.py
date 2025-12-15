import logging
import warnings
import streamlit as st
from config.settings import PAGE_TITLE, PAGE_ICON

# Silenzia i warning
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# DEFINIZIONE PAGINE
# ============================================================================

# Definisci le pagine disponibili
lista_page = st.Page("pages/lista_articoli.py", title="📰 Lista Articoli", icon="📰", default=True)
elabora_page = st.Page("pages/elaborazione.py", title="📊 Elaborazione", icon="📊")

# Crea navigazione
pg = st.navigation([lista_page, elabora_page])

# Esegui la pagina selezionata
pg.run()
