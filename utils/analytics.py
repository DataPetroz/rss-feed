import json
import os
from datetime import datetime
from typing import Dict, Any

ANALYTICS_FILE = "analytics_events.json"

def track_event(button_name: str, page: str, extra_data: Dict[str, Any] = None):
    """
    Registra un evento di click su bottone in un file JSON
    
    Args:
        button_name: Nome del bottone cliccato
        page: Pagina in cui è avvenuto il click
        extra_data: Dati aggiuntivi opzionali (es. titolo articolo)
    """
    event = {
        "timestamp": datetime.now().isoformat(),
        "button": button_name,
        "page": page
    }
    
    if extra_data:
        event.update(extra_data)
    
    # Carica eventi esistenti
    if os.path.exists(ANALYTICS_FILE):
        try:
            with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            data = {"events": []}
    else:
        data = {"events": []}
    
    # Aggiungi nuovo evento
    data["events"].append(event)
    
    # Salva
    try:
        with open(ANALYTICS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # Failsafe: non bloccare l'app se il tracking fallisce
        pass

def get_analytics_summary() -> Dict[str, Any]:
    """Restituisce un sommario degli eventi tracciati"""
    if not os.path.exists(ANALYTICS_FILE):
        return {"total_events": 0, "events": []}
    
    try:
        with open(ANALYTICS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {
            "total_events": len(data.get("events", [])),
            "events": data.get("events", [])
        }
    except:
        return {"total_events": 0, "events": []}