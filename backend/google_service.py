from authlib.integrations.flask_client import OAuth
import logging
import traceback

logger = logging.getLogger(__name__)

oauth = OAuth()
google_client = None

def init_google_app(app):
    try:
        client_id = app.config.get('GOOGLE_CLIENT_ID')
        client_secret = app.config.get('GOOGLE_CLIENT_SECRET')
        
        logger.info("Initialisation Google OAuth...")
        logger.info(f"Client ID present: {'OUI' if client_id else 'NON'}")
        logger.info(f"Client Secret present: {'OUI' if client_secret else 'NON'}")
        
        if not client_id or not client_secret:
            logger.error("GOOGLE_CLIENT_ID ou GOOGLE_CLIENT_SECRET manquant")
            return None
        
        oauth.init_app(app)
        
        google = oauth.register(
            name='google',
            client_id=client_id,
            client_secret=client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
        
        logger.info("Service Google OAuth enregistre avec succes")
        return google
        
    except Exception as e:
        logger.error(f"Erreur initialisation Google: {e}")
        logger.error(traceback.format_exc())
        return None

def init_google(app):
    global google_client
    google_client = init_google_app(app)
    return google_client

def get_google_client():
    global google_client
    return google_client
