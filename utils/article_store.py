"""
Store globale per gli articoli - accessibile da tutte le pagine
"""
import streamlit as st
from typing import Dict, Optional
import hashlib

def init_article_store():
    """Inizializza lo store degli articoli in session_state"""
    if 'articles_store' not in st.session_state:
        st.session_state.articles_store = {}

def store_article(article: Dict) -> str:
    """
    Salva un articolo nello store e restituisce il suo ID
    
    Args:
        article: Dictionary con i dati dell'articolo
        
    Returns:
        str: ID univoco dell'articolo
    """
    init_article_store()
    
    # Genera ID univoco
    article_id = hashlib.md5(article['link'].encode()).hexdigest()
    
    # Salva nello store
    st.session_state.articles_store[article_id] = article
    
    return article_id

def get_article(article_id: str) -> Optional[Dict]:
    """
    Recupera un articolo dallo store tramite ID
    
    Args:
        article_id: ID univoco dell'articolo
        
    Returns:
        Dict | None: Dati articolo o None se non trovato
    """
    init_article_store()
    return st.session_state.articles_store.get(article_id, None)

def store_all_articles(articles_list: list):
    """
    Salva tutti gli articoli nello store
    
    Args:
        articles_list: Lista di articoli
    """
    init_article_store()
    
    for article in articles_list:
        article_id = hashlib.md5(article['link'].encode()).hexdigest()
        st.session_state.articles_store[article_id] = article
