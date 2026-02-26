import os
from dotenv import load_dotenv

# Charge les variables d'environnement depuis .env
load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-12345'
    
    # Base de données
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@open-always.com')
    
    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    # Cloudflare Turnstile
    TURNSTILE_SITE_KEY = os.environ.get('TURNSTILE_SITE_KEY')
    TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY')
    
    # API Okitakoy
    OKITAKOY_API_URL = os.environ.get('OKITAKOY_API_URL', 'https://llm-chat-app-template.deltaprecieux851.workers.dev')
