# ============================================
# Configuration des publicités
# ============================================

ADS_DATABASE = [
    {
        "id": 1,
        "title": "Okitakoy Inc.",
        "description": "Solutions IA innovantes - Gagnez +1 clé API",
        "image_url": "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=400&h=250&fit=crop",
        "reward": 1,
        "sponsor": "Okitakoy Inc.",
        "button_text": "Regarder",
        "active": True
    },
    {
        "id": 2,
        "title": "Python Academy",
        "description": "Maîtrisez Python - Gagnez +1 clé API",
        "image_url": "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=400&h=250&fit=crop",
        "reward": 1,
        "sponsor": "Python Academy",
        "button_text": "Regarder",
        "active": True
    },
    {
        "id": 3,
        "title": "WebHost Pro",
        "description": "Hébergement cloud - Gagnez +1 clé API",
        "image_url": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400&h=250&fit=crop",
        "reward": 1,
        "sponsor": "WebHost Pro",
        "button_text": "Regarder",
        "active": True
    },
    {
        "id": 4,
        "title": "Café Dev",
        "description": "Communauté de développeurs - Gagnez +1 clé API",
        "image_url": "https://images.unsplash.com/photo-1510915361894-db8b60106cb1?w=400&h=250&fit=crop",
        "reward": 1,
        "sponsor": "Café Dev",
        "button_text": "Regarder",
        "active": True
    }
]

ADS_CONFIG = {
    "watch_duration": 5,        # 5 secondes par pub
    "default_reward": 1,         # +1 clé par pub
    "max_ads_per_day": 10,       # Maximum 10 pubs par jour
    "messages": {
        "watch_prompt": "Regardez cette publicité pour gagner +1 clé API",
        "watch_complete": "✅ +1 clé API maximum !",
        "watch_error": "❌ Erreur lors du visionnage",
        "daily_limit": "⚠️ Limite de 10 pubs par jour atteinte"
    }
}

def get_active_ads():
    """Retourne les publicités actives"""
    return [ad for ad in ADS_DATABASE if ad.get("active", True)]

def get_ad_by_id(ad_id):
    """Retourne une publicité par son ID"""
    for ad in ADS_DATABASE:
        if ad["id"] == ad_id:
            return ad
    return None