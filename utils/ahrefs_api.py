import http.client
import urllib.parse
import time
import json
from typing import Dict, Any, List
import streamlit as st

def get_keyword_volume_ahrefs(keyword: str, api_token: str, country: str = "it") -> Dict[str, Any]:
    """Ottiene il volume di ricerca per una singola keyword usando Ahrefs API"""
    if not api_token:
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
            'Authorization': f"Bearer {api_token}"
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


def get_multiple_keywords_volumes(keywords_list: List[str], api_token: str, country: str = "it") -> Dict[str, Dict[str, Any]]:
    """Ottiene i volumi per una lista di keywords con rate limiting"""
    results = {}
    total_keywords = len(keywords_list)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, keyword in enumerate(keywords_list):
        progress = (i + 1) / total_keywords
        progress_bar.progress(progress)
        status_text.text(f"Processando keyword {i+1}/{total_keywords}: {keyword}")
        
        result = get_keyword_volume_ahrefs(keyword, api_token, country)
        results[keyword] = result
        
        if i < total_keywords - 1:
            time.sleep(0.5)  # Rate limiting
    
    progress_bar.empty()
    status_text.empty()
    
    return results