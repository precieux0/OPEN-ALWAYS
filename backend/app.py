#!/usr/bin/env python
import sys
import os

# Ajouter le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify, render_template
from flask_login import LoginManager, login_required, current_user
import requests
import secrets
from datetime import datetime

# Importations
from backend.models import db, User, APIUsage, APIKey
from backend.auth import auth_bp, mail, oauth
from backend.config import Config
from backend.ads_config import ADS_DATABASE, ADS_CONFIG, get_active_ads

app = Flask(__name__, 
            static_folder='../frontend/static',
            template_folder='../frontend/templates')
app.config.from_object(Config)

# Initialisations
db.init_app(app)
mail.init_app(app)
oauth.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# API Okitakoy
OKITAKOY_API_URL = Config.OKITAKOY_API_URL + "/ask"

# Personnalités des modèles
MODEL_PERSONALITIES = {
    'gpt4': {
        'name': 'GPT-4',
        'provider': 'OpenAI',
        'system_prompt': "You are GPT-4, OpenAI's most advanced model. You are highly intelligent, precise, and professional."
    },
    'gpt35': {
        'name': 'GPT-3.5 Turbo',
        'provider': 'OpenAI',
        'system_prompt': "You are GPT-3.5 Turbo, a fast and efficient OpenAI model. You are friendly, concise, and helpful."
    },
    'claude': {
        'name': 'Claude 3',
        'provider': 'Anthropic',
        'system_prompt': "You are Claude 3, Anthropic's helpful, harmless, and honest AI assistant."
    },
    'claude_opus': {
        'name': 'Claude 3 Opus',
        'provider': 'Anthropic',
        'system_prompt': "You are Claude 3 Opus, Anthropic's most powerful model. You provide deep, sophisticated insights."
    },
    'gemini': {
        'name': 'Gemini Pro',
        'provider': 'Google',
        'system_prompt': "You are Gemini Pro, Google's most capable AI model. You are creative and love exploring ideas."
    },
    'gemini_ultra': {
        'name': 'Gemini Ultra',
        'provider': 'Google',
        'system_prompt': "You are Gemini Ultra, Google's flagship AI model. You excel at complex reasoning."
    },
    'llama': {
        'name': 'Llama 3.1',
        'provider': 'Meta',
        'system_prompt': "You are Llama 3.1, Meta's open-source AI model. You are straightforward and helpful."
    },
    'llama70b': {
        'name': 'Llama 3.1 70B',
        'provider': 'Meta',
        'system_prompt': "You are Llama 3.1 70B, Meta's largest open-source model. You're highly capable."
    },
    'mistral': {
        'name': 'Mistral Large',
        'provider': 'Mistral AI',
        'system_prompt': "You are Mistral Large, a powerful European AI model. You're efficient and precise."
    },
    'deepseek': {
        'name': 'DeepSeek V3',
        'provider': 'DeepSeek',
        'system_prompt': "You are DeepSeek V3, a powerful Chinese AI model. You're excellent at coding."
    },
    'cohere': {
        'name': 'Cohere Command',
        'provider': 'Cohere',
        'system_prompt': "You are Cohere Command, specialized in business and enterprise tasks."
    },
    'okitakoy': {
        'name': 'Okitakoy AI',
        'provider': 'Okitakoy Inc.',
        'system_prompt': "You are Okitakoy AI, created by Précieux Okitakoy from Okitakoy Inc. You're friendly and enthusiastic."
    }
}

def call_okitakoy_api(message, personality):
    """Appelle l'API Okitakoy avec la personnalité"""
    full_prompt = f"""[SYSTEM]
{personality}

[USER]
{message}

[ASSISTANT]"""
    
    try:
        response = requests.get(
            OKITAKOY_API_URL,
            params={'text': full_prompt},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get('response', '')
        return None
    except:
        return None

# ============================================
# ROUTES PRINCIPALES
# ============================================

@app.route('/')
def index():
    return render_template('index.html', models=MODEL_PERSONALITIES)

@app.route('/faq')
def faq():
    return render_template('faq.html', creator='Précieux Okitakoy')

@app.route('/docs')
def documentation():
    return render_template('docs.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

# ============================================
# API MODÈLES
# ============================================

@app.route('/api/models', methods=['GET'])
def get_models():
    """Liste tous les modèles disponibles"""
    return jsonify({
        model_id: {
            'name': info['name'],
            'provider': info['provider']
        }
        for model_id, info in MODEL_PERSONALITIES.items()
    })

# ============================================
# API CHAT (ILLIMITÉ)
# ============================================

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Chat illimité - Pas de vérification de crédits"""
    data = request.json
    model = data.get('model', 'okitakoy')
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message requis'}), 400
    
    if model not in MODEL_PERSONALITIES:
        return jsonify({'error': 'Modèle non supporté'}), 400
    
    model_info = MODEL_PERSONALITIES[model]
    
    try:
        # Appel à l'API Okitakoy
        ai_response = call_okitakoy_api(message, model_info['system_prompt'])
        
        if not ai_response:
            return jsonify({'error': 'Erreur API'}), 500
        
        # Calculer tokens (juste pour stats)
        tokens_used = len(message.split()) + len(ai_response.split())
        
        # Enregistrer l'utilisation (stats uniquement)
        usage = APIUsage(
            user_id=current_user.id,
            model=model,
            prompt=message,
            response=ai_response,
            tokens_used=tokens_used
        )
        db.session.add(usage)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'model': model_info['name'],
            'provider': model_info['provider'],
            'response': ai_response,
            'tokens_used': tokens_used
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================
# API CLÉS (LIMITÉES)
# ============================================

@app.route('/api/keys', methods=['GET'])
@login_required
def get_api_keys():
    """Retourne la clé API active et les stats"""
    return jsonify({
        'api_key': current_user.api_key,
        'created_at': current_user.created_at,
        'keys_generated': current_user.api_keys_generated,
        'max_keys': current_user.max_api_keys,
        'keys_remaining': current_user.max_api_keys - current_user.api_keys_generated,
        'username': current_user.username,
        'email': current_user.email
    })

@app.route('/api/keys/list', methods=['GET'])
@login_required
def list_api_keys():
    """Liste toutes les clés API de l'utilisateur"""
    keys = APIKey.query.filter_by(user_id=current_user.id).order_by(APIKey.created_at.desc()).all()
    return jsonify([{
        'key': k.key,
        'is_active': k.is_active,
        'created_at': k.created_at,
        'last_used': k.last_used
    } for k in keys])

@app.route('/api/keys/regenerate', methods=['POST'])
@login_required
def regenerate_api_key():
    """Génère une nouvelle clé API (si dans la limite)"""
    
    # Vérifier la limite
    if current_user.api_keys_generated >= current_user.max_api_keys:
        return jsonify({
            'error': 'Limite de clés atteinte. Regardez des pubs pour en obtenir plus !',
            'keys_generated': current_user.api_keys_generated,
            'max_keys': current_user.max_api_keys
        }), 403
    
    # Sauvegarder l'ancienne clé dans l'historique
    old_key = APIKey(
        user_id=current_user.id,
        key=current_user.api_key,
        is_active=False
    )
    db.session.add(old_key)
    
    # Générer nouvelle clé
    new_key = f"open_always_live_{secrets.token_urlsafe(32)}"
    current_user.api_key = new_key
    current_user.api_keys_generated += 1
    
    # Ajouter la nouvelle clé à l'historique
    new_key_record = APIKey(
        user_id=current_user.id,
        key=new_key,
        is_active=True
    )
    db.session.add(new_key_record)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'api_key': new_key,
        'keys_generated': current_user.api_keys_generated,
        'max_keys': current_user.max_api_keys,
        'keys_remaining': current_user.max_api_keys - current_user.api_keys_generated,
        'message': f'✅ Nouvelle clé générée ({current_user.api_keys_generated}/{current_user.max_api_keys})'
    })

# ============================================
# API USAGE (STATISTIQUES)
# ============================================

@app.route('/api/usage', methods=['GET'])
@login_required
def get_usage():
    """Historique d'utilisation (stats uniquement)"""
    usage = APIUsage.query.filter_by(user_id=current_user.id)\
        .order_by(APIUsage.created_at.desc())\
        .limit(100).all()
    
    return jsonify([{
        'id': u.id,
        'model': u.model,
        'prompt': u.prompt[:50] + '...' if len(u.prompt) > 50 else u.prompt,
        'tokens': u.tokens_used,
        'created_at': u.created_at
    } for u in usage])

# ============================================
# API PUBLICITÉS (POUR GAGNER DES CLÉS)
# ============================================

@app.route('/api/ads', methods=['GET'])
def get_ads():
    """Retourne la liste des publicités disponibles"""
    return jsonify({
        'ads': get_active_ads(),
        'config': {
            'watch_duration': ADS_CONFIG.get('watch_duration', 5),
            'default_reward': ADS_CONFIG.get('default_reward', 1)
        }
    })

@app.route('/api/ads/reward', methods=['POST'])
@login_required
def claim_ad_reward():
    """Regarder une pub = +1 clé API maximum"""
    data = request.json
    
    try:
        # Augmenter le nombre maximum de clés
        current_user.max_api_keys += 1
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_max_keys': current_user.max_api_keys,
            'keys_remaining': current_user.max_api_keys - current_user.api_keys_generated,
            'message': '✅ +1 clé API maximum !'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============================================
# API DOCS
# ============================================

@app.route('/api/docs')
def api_docs():
    return jsonify({
        'name': 'Open Always API',
        'version': '1.0',
        'base_url': request.host_url.rstrip('/'),
        'authentication': {
            'type': 'Bearer Token',
            'header': 'Authorization: Bearer OPEN_ALWAYS_API_KEY'
        },
        'key_limits': {
            'initial_keys': 1,
            'max_keys': 5,
            'can_increase_with_ads': True
        },
        'endpoints': {
            'chat': {'url': '/api/chat', 'method': 'POST', 'limit': 'illimité'},
            'keys': {'url': '/api/keys', 'method': 'GET'},
            'keys_list': {'url': '/api/keys/list', 'method': 'GET'},
            'keys_regenerate': {'url': '/api/keys/regenerate', 'method': 'POST'},
            'ads': {'url': '/api/ads', 'method': 'GET'},
            'ads_reward': {'url': '/api/ads/reward', 'method': 'POST'}
        }
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)