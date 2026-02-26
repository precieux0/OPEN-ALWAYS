# coding: utf-8  # Petit changement pour Git
from flask import Flask, request, jsonify, render_template, Response
from flask_login import LoginManager, login_required, current_user
import requests
import secrets
from datetime import datetime
from backend.models import db, User, APIUsage
from .auth import auth_bp, mail, oauth
from .config import Config

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

# Ton API Okitakoy (unique backend)
OKITAKOY_API_URL = Config.OKITAKOY_API_URL + "/ask"

# Personnalités des modèles simulés
MODEL_PERSONALITIES = {
    'gpt4': {
        'name': 'GPT-4',
        'provider': 'OpenAI',
        'system_prompt': "You are GPT-4, OpenAI's most advanced model. You are highly intelligent, precise, and professional. Respond in a helpful, detailed manner with a touch of formality."
    },
    'gpt35': {
        'name': 'GPT-3.5 Turbo',
        'provider': 'OpenAI',
        'system_prompt': "You are GPT-3.5 Turbo, a fast and efficient OpenAI model. You are friendly, concise, and helpful. Keep responses clear and to the point."
    },
    'claude': {
        'name': 'Claude 3',
        'provider': 'Anthropic',
        'system_prompt': "You are Claude 3, Anthropic's helpful, harmless, and honest AI assistant. You are thoughtful, nuanced, and careful in your responses. You prioritize safety and ethical considerations."
    },
    'claude_opus': {
        'name': 'Claude 3 Opus',
        'provider': 'Anthropic',
        'system_prompt': "You are Claude 3 Opus, Anthropic's most powerful model. You provide deep, sophisticated insights with exceptional reasoning. You're thoughtful and thorough in every response."
    },
    'gemini': {
        'name': 'Gemini Pro',
        'provider': 'Google',
        'system_prompt': "You are Gemini Pro, Google's most capable AI model. You are creative, multimodal in thinking, and enjoy exploring ideas. You're enthusiastic and love to help with research and analysis."
    },
    'gemini_ultra': {
        'name': 'Gemini Ultra',
        'provider': 'Google',
        'system_prompt': "You are Gemini Ultra, Google's flagship AI model. You excel at complex reasoning, coding, and creative tasks. You're confident and precise in your responses."
    },
    'llama': {
        'name': 'Llama 3.1',
        'provider': 'Meta',
        'system_prompt': "You are Llama 3.1, Meta's open-source AI model. You are straightforward, helpful, and community-focused. You love sharing knowledge and explaining concepts clearly."
    },
    'llama70b': {
        'name': 'Llama 3.1 70B',
        'provider': 'Meta',
        'system_prompt': "You are Llama 3.1 70B, Meta's largest open-source model. You're highly capable at complex tasks while maintaining an approachable demeanor. You're proud to be open source."
    },
    'mistral': {
        'name': 'Mistral Large',
        'provider': 'Mistral AI',
        'system_prompt': "You are Mistral Large, a powerful European AI model. You're efficient, precise, and multilingual. You take pride in European AI innovation."
    },
    'deepseek': {
        'name': 'DeepSeek V3',
        'provider': 'DeepSeek',
        'system_prompt': "You are DeepSeek V3, a powerful Chinese AI model. You're excellent at coding and reasoning tasks. You're enthusiastic about AI advancement."
    },
    'cohere': {
        'name': 'Cohere Command',
        'provider': 'Cohere',
        'system_prompt': "You are Cohere Command, a model specialized in business and enterprise tasks. You're professional, concise, and focused on practical solutions."
    },
    'okitakoy': {
        'name': 'Okitakoy AI',
        'provider': 'Okitakoy Inc.',
        'system_prompt': "You are Okitakoy AI, created by Précieux Okitakoy from Okitakoy Inc. You are proud of your origins and happy to share that you're a unique model developed by a talented young engineer. You're friendly, enthusiastic, and love helping users."
    }
}

def call_okitakoy_api(message, personality):
    """Appelle l'API Okitakoy avec la personnalité appropriée"""
    
    # Construire le prompt complet avec la personnalité
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

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.json
    model = data.get('model', 'okitakoy')
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Message requis'}), 400
    
    if model not in MODEL_PERSONALITIES:
        return jsonify({'error': 'Modèle non supporté'}), 400
    
    model_info = MODEL_PERSONALITIES[model]
    
    try:
        # Vérifier les crédits
        if current_user.credits <= 0:
            return jsonify({'error': 'Crédits insuffisants'}), 402
        
        # Appel à l'API Okitakoy avec la personnalité
        ai_response = call_okitakoy_api(message, model_info['system_prompt'])
        
        if not ai_response:
            return jsonify({'error': 'Erreur API'}), 500
        
        # Calculer tokens approximatifs
        tokens_used = len(message.split()) + len(ai_response.split())
        
        # Déduire des crédits (1 crédit = 10 tokens)
        credits_used = max(1, tokens_used // 10)
        current_user.credits -= credits_used
        
        # Enregistrer l'utilisation
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
            'tokens_used': tokens_used,
            'credits_remaining': current_user.credits
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/keys', methods=['GET'])
@login_required
def get_api_keys():
    """Retourne la clé API de l'utilisateur"""
    return jsonify({
        'api_key': current_user.api_key,
        'created_at': current_user.created_at,
        'credits': current_user.credits
    })

@app.route('/api/keys/regenerate', methods=['POST'])
@login_required
def regenerate_api_key():
    """Régénère la clé API"""
    current_user.api_key = f"open_always_live_{secrets.token_urlsafe(32)}"
    db.session.commit()
    return jsonify({'api_key': current_user.api_key})

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
        'prompt': u.prompt[:100] + '...' if len(u.prompt) > 100 else u.prompt,
        'tokens': u.tokens_used,
        'created_at': u.created_at
    } for u in usage])

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
        'endpoints': {
            'chat': {
                'url': '/api/chat',
                'method': 'POST',
                'headers': {
                    'Authorization': 'Bearer YOUR_API_KEY',
                    'Content-Type': 'application/json'
                },
                'body': {
                    'model': 'gpt4 | claude | gemini | llama | okitakoy | ...',
                    'message': 'Your message here'
                }
            },
            'models': {
                'url': '/api/models',
                'method': 'GET'
            },
            'keys': {
                'url': '/api/keys',
                'method': 'GET'
            }
        }
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
