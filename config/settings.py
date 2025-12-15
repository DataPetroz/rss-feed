import os
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv("secure.env")

# Azure OpenAI
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT_NAME = 'gpt-4o-mini'
AZURE_API_VERSION = "2024-10-01-preview"

# Ahrefs
AHREFS_API_TOKEN = os.getenv("AHREFS_API_KEY")

# Feed RSS Configuration
RSS_FEEDS = {

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

# Cache TTL (secondi)
FEED_CACHE_TTL = 1800  # 30 minuti
AI_CACHE_TTL = 1800    # 30 minuti
AHREFS_CACHE_TTL = 3600  # 1 ora

# UI Configuration
PAGE_TITLE = "RSS Feed Reader"
PAGE_ICON = "📰"
DETAIL_PAGE_TITLE = "Elaborazione Articolo"
DETAIL_PAGE_ICON = "✍️"