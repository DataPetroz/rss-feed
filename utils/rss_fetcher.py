import feedparser
import requests
from datetime import datetime
import re
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Tuple

logging.basicConfig(level=logging.WARNING)

def extract_images_from_html(html_content: str) -> List[str]:
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


def extract_first_image_from_feed_entry(entry) -> str:
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


def clean_html_content(html_content: str) -> str:
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


def fetch_feed(url: str, category: str) -> Tuple[List[Dict], int]:
    """
    Recupera e processa un feed RSS con estrazione delle immagini
    
    Returns:
        Tuple[List[Dict], int]: (lista articoli, conteggio totale)
    """
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
        logging.error(f"Errore nel recuperare il feed da {url}: {str(e)}")
        return [], 0