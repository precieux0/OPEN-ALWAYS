#!/usr/bin/env python
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user, login_user
import logging

from backend.models import db, User, APIUsage, APIKey
from backend.auth import auth_bp, email_service
from backend.chat_service import ChatService
from backend.keys_service import KeysService
from backend.google_service import init_google, get_google_client, google_client
from backend.config import Config
from backend.ads_config import get_active_ads

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation des services
chat_service = ChatService()

app = Flask(__name__, 
            static_folder='../frontend/static',
            template_folder='../frontend/templates')
app.config.from_object(Config)

# ============================================
# OPTIMISATION MÉMOIRE
# ============================================
app.config['SQLALCHEMY_POOL_SIZE'] = 2
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 3
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 180,
    'pool_timeout': 10,
}

# ============================================
# INITIALISATIONS
# ============================================
logger.info("=" * 50)
logger.info("DÉMARRAGE DE L'APPLICATION")
logger.info("=" * 50)

db.init_app(app)
logger.info("✅ Base de données initialisée")

email_service.init_app(app)
logger.info("✅ Service email initialisé")

logger.info("Initialisation de Google OAuth...")
init_google(app)
logger.info(f"google_client global après init: {google_client}")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # ← CORRIGÉ : utilise le blueprint
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.session_protection = 'basic'
logger.info("✅ Login manager initialisé")

app.register_blueprint(auth_bp, url_prefix='/auth')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ============================================
# ROUTES PRINCIPALES
# ============================================

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html', models=chat_service.get_models())

@app.route('/faq')
def faq():
    """Page FAQ"""
    return render_template('faq.html', creator='Precieux Okitakoy')

@app.route('/docs')
def documentation():
    """Page documentation"""
    return render_template('docs.html')

@app.route('/chat', methods=['GET'])
def chat_page():
    """Page de chat avec vérification session ET token"""
    
    if current_user and current_user.is_authenticated:
        logger.info(f"Accès chat par session: {current_user.username}")
        return render_template('chat.html')
    
    token = request.args.get('token')
    if token:
        user = KeysService.verify_key(f"Bearer {token}")
        if user:
            login_user(user, remember=True)
            logger.info(f"Accès chat par token URL: {user.username}")
            return render_template('chat.html')
    
    logger.warning("Accès chat non autorisé, redirection vers login")
    return redirect(url_for('auth.login'))  # ← Utilise le blueprint

@app.route('/auth/login', methods=['GET'])
def login_page():
    """Affiche la page de connexion"""
    return render_template('login.html')

@app.route('/auth/register', methods=['GET'])
def register_page():
    """Affiche la page d'inscription"""
    return render_template('login.html')

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Tableau de bord utilisateur"""
    logger.info(f"Accès dashboard: {current_user.username}")
    return render_template('dashboard.html', user=current_user)

# ============================================
# API MODÈLES
# ============================================

@app.route('/api/models', methods=['GET'])
def get_models():
    return jsonify(chat_service.get_models())

# ============================================
# API CHAT
# ============================================

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat avec authentification par API Key"""
    
    user = None
    
    if current_user and current_user.is_authenticated:
        user = current_user
    else:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            user = KeysService.verify_key(auth_header)
    
    if not user:
        return jsonify({'error': 'Authentification requise'}), 401
    
    data = request.json
    if not data or not data.get('message'):
        return jsonify({'error': 'Message requis'}), 400
    
    response, error = chat_service.process_message(
        data.get('model', 'okitakoy'), 
        data.get('message')
    )
    
    if error:
        return jsonify({'error': error}), 400 if error == "Modele non supporte" else 500
    
    try:
        usage = APIUsage(
            user_id=user.id,
            model=data.get('model', 'okitakoy'),
            prompt=data.get('message'),
            response=response['response'],
            tokens_used=response['tokens_used']
        )
        db.session.add(usage)
        db.session.commit()
    except Exception as e:
        logger.error(f"Erreur sauvegarde usage: {e}")
        db.session.rollback()
    
    return jsonify(response)

# ============================================
# API CHECK AUTH (for frontend)
# ============================================

@app.route('/api/me', methods=['GET'])
def check_auth():
    """Vérifie l'authentification de l'utilisateur"""
    if current_user and current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'username': current_user.username,
            'email': current_user.email,
            'api_key': current_user.api_key
        })
    
    auth_header = request.headers.get('Authorization')
    if auth_header:
        user = KeysService.verify_key(auth_header)
        if user:
            return jsonify({
                'authenticated': True,
                'username': user.username,
                'email': user.email,
                'api_key': user.api_key
            })
    
    return jsonify({'authenticated': False}), 401

# ============================================
# API CLÉS
# ============================================

@app.route('/api/keys', methods=['GET'])
def get_api_keys():
    """Retourne la clé API active et les stats"""
    user = None
    if current_user and current_user.is_authenticated:
        user = current_user
    else:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            user = KeysService.verify_key(auth_header)
    
    if not user:
        return jsonify({'error': 'Non autorise'}), 401
    
    return jsonify({
        'api_key': user.api_key,
        'created_at': str(user.created_at),
        'keys_generated': getattr(user, 'api_keys_generated', 1),
        'max_keys': getattr(user, 'max_api_keys', 5),
        'keys_remaining': getattr(user, 'max_api_keys', 5) - getattr(user, 'api_keys_generated', 1),
        'username': user.username,
        'email': user.email
    })

@app.route('/api/keys/list', methods=['GET'])
@login_required
def list_api_keys():
    """Liste toutes les clés API de l'utilisateur"""
    keys = KeysService.get_user_keys(current_user.id)
    return jsonify([{
        'key': k.key,
        'is_active': k.is_active,
        'created_at': str(k.created_at)
    } for k in keys])

@app.route('/api/keys/regenerate', methods=['POST'])
@login_required
def regenerate_api_key():
    """Génère une nouvelle clé API (si dans la limite)"""
    if not hasattr(current_user, 'api_keys_generated'):
        current_user.api_keys_generated = 1
    if not hasattr(current_user, 'max_api_keys'):
        current_user.max_api_keys = 5
    
    if current_user.api_keys_generated >= current_user.max_api_keys:
        return jsonify({'error': 'Limite atteinte'}), 403
    
    old_key = APIKey.query.filter_by(key=current_user.api_key).first()
    if old_key:
        old_key.is_active = False
    
    new_key = KeysService.generate_key()
    current_user.api_key = new_key
    current_user.api_keys_generated += 1
    
    KeysService.create_key(current_user.id, new_key)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'api_key': new_key,
        'keys_generated': current_user.api_keys_generated,
        'max_keys': current_user.max_api_keys
    })

# ============================================
# API USAGE
# ============================================

@app.route('/api/usage', methods=['GET'])
@login_required
def get_usage():
    """Historique d'utilisation"""
    usage = APIUsage.query.filter_by(user_id=current_user.id)\
        .order_by(APIUsage.created_at.desc())\
        .limit(100).all()
    
    return jsonify([{
        'id': u.id,
        'model': u.model,
        'prompt': u.prompt[:50] if u.prompt else '',
        'tokens': u.tokens_used,
        'created_at': str(u.created_at)
    } for u in usage])

# ============================================
# API PUBLICITÉS
# ============================================

user_ad_views = {}

@app.route('/api/ads', methods=['GET'])
def get_ads():
    """Retourne la liste des publicités disponibles"""
    return jsonify({
        'ads': get_active_ads(),
        'config': {'watch_duration': 5, 'default_reward': 1}
    })

@app.route('/api/ads/reward', methods=['POST'])
@login_required
def claim_ad_reward():
    """Réclamer une récompense après avoir regardé une pub"""
    from datetime import date
    
    data = request.json
    ad_id = data.get('adId')
    
    if not ad_id:
        return jsonify({"error": "ID requis"}), 400
    
    today = date.today().isoformat()
    user_key = f"{current_user.id}_{ad_id}_{today}"
    
    if user_key in user_ad_views:
        return jsonify({"error": "Deja vu aujourd'hui"}), 400
    
    try:
        if not hasattr(current_user, 'max_api_keys'):
            current_user.max_api_keys = 5
        current_user.max_api_keys += 1
        db.session.commit()
        user_ad_views[user_key] = True
        logger.info(f"✅ +1 clé max pour {current_user.username}")
        return jsonify({'success': True, 'new_max_keys': current_user.max_api_keys})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur pub: {e}")
        return jsonify({"error": str(e)}), 500

# ============================================
# API DOCS
# ============================================

@app.route('/api/docs')
def api_docs():
    return jsonify({
        'name': 'Open Always API',
        'version': '1.0',
        'base_url': request.host_url.rstrip('/'),
        'authentication': {'type': 'Bearer Token', 'header': 'Authorization: Bearer YOUR_API_KEY'},
        'endpoints': {
            'chat': {'method': 'POST', 'url': '/api/chat', 'description': 'Envoyer un message à l\'IA'},
            'models': {'method': 'GET', 'url': '/api/models', 'description': 'Liste des modèles disponibles'},
            'keys': {'method': 'GET', 'url': '/api/keys', 'description': 'Obtenir sa clé API'},
            'regenerate': {'method': 'POST', 'url': '/api/keys/regenerate', 'description': 'Générer une nouvelle clé'},
            'usage': {'method': 'GET', 'url': '/api/usage', 'description': 'Historique d\'utilisation'},
            'ads': {'method': 'GET', 'url': '/api/ads', 'description': 'Publicités disponibles'}
        }
    })

# ============================================
# ROUTES DE DEBUG
# ============================================

@app.route('/debug/login-view')
def debug_login_view():
    """Affiche la configuration de login_view"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debug Login View</title>
        <style>
            body {{ font-family: Arial; padding: 2rem; background: #f0f2f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; padding: 2rem; }}
            .success {{ color: #10b981; }}
            .info {{ background: #f8fafc; padding: 1rem; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Debug Login View</h1>
            <div class="info">
                <p><strong>login_manager.login_view =</strong> {login_manager.login_view}</p>
                <p><strong>Route pour auth.login:</strong> {url_for('auth.login')}</p>
                <p><strong>Route pour login_page:</strong> {url_for('login_page') if has_url_for('login_page') else 'N/A'}</p>
            </div>
            <p class="success">✅ Configuration correcte !</p>
            <a href="/" class="btn">Retour</a>
        </div>
    </body>
    </html>
    """

def has_url_for(endpoint):
    """Vérifie si un endpoint existe"""
    try:
        url_for(endpoint)
        return True
    except:
        return False

# ============================================
# DÉMARRAGE
# ============================================
if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
            print("✅ Tables créées/vérifiées")
        except Exception as e:
            print(f"⚠️ Erreur: {e}")
    
    print("🚀 Démarrage de l'application...")
    app.run(debug=False, host='0.0.0.0', port=5000)

# Pour Gunicorn
application = app
