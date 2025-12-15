import sqlite3
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any

DB_PATH = Path(__file__).parent.parent / "temp_articles.db"

def init_temp_db():
    """Inizializza database temporaneo per articoli"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS temp_articles
                 (id TEXT PRIMARY KEY, 
                  data TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def save_article(article: Dict[str, Any]) -> str:
    """Salva articolo e restituisce ID univoco"""
    article_id = hashlib.md5(article['link'].encode()).hexdigest()
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    
    article_json = json.dumps(article, ensure_ascii=False)
    
    c.execute('''INSERT OR REPLACE INTO temp_articles (id, data)
                 VALUES (?, ?)''', (article_id, article_json))
    conn.commit()
    conn.close()
    
    return article_id

def get_article(article_id: str) -> Optional[Dict[str, Any]]:
    """Recupera articolo dal database tramite ID"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('SELECT data FROM temp_articles WHERE id = ?', (article_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return json.loads(row[0])

def cleanup_old_articles(days: int = 7):
    """Pulisce articoli più vecchi di N giorni"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''DELETE FROM temp_articles 
                 WHERE created_at < datetime('now', '-' || ? || ' days')''', (days,))
    conn.commit()
    conn.close()
