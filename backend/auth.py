from flask import Blueprint, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from datetime import datetime, timedelta
import secrets
import requests
from authlib.integrations.flask_client import OAuth

# ✅ IMPORTANT: Ajouter APIKey ici
from .models import db, User, OTPCode, APIKey
from .config import Config

auth_bp = Blueprint('auth', __name__)
mail = Mail()
oauth = OAuth()

# Configuration Google OAuth
google = oauth.register(
    name='google',
    client_id=Config.GOOGLE_CLIENT_ID,
    client_secret=Config.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

def verify_turnstile(token):
    """Vérifie le token Cloudflare Turnstile"""
    response = requests.post(
        'https://challenges.cloudflare.com/turnstile/v0/siteverify',
        data={
            'secret': Config.CLOUDFLARE_TURNSTILE_SECRET_KEY,
            'response': token
        }
    )
    return response.json().get('success', False)

def send_otp_email(email, code, purpose):
    """Envoie un email OTP"""
    msg = Message(
        subject=f"Open Always - {purpose}",
        recipients=[email]
    )
    if purpose == "verification":
        msg.body = f"Bienvenue sur Open Always ! Votre code de vérification est : {code}"
    elif purpose == "reset":
        msg.body = f"Pour réinitialiser votre mot de passe, utilisez ce code : {code}"
    mail.send(msg)

# ============================================
# INSCRIPTION (avec initialisation des clés)
# ============================================
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    
    # Vérifier captcha
    if not verify_turnstile(data.get('turnstile_token')):
        return jsonify({'error': 'Captcha invalide'}), 400
    
    # Vérifier si l'utilisateur existe
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email déjà utilisé'}), 400
    
    # Créer utilisateur
    user = User(
        email=data['email'],
        username=data['username'],
        password_hash=generate_password_hash(data['password'])
    )
    db.session.add(user)
    db.session.flush()  # Pour obtenir l'ID de l'utilisateur
    
    # ✅ AJOUT : Enregistrer la première clé dans l'historique
    first_key = APIKey(
        user_id=user.id,
        key=user.api_key,  # La clé générée automatiquement
        is_active=True
    )
    db.session.add(first_key)
    
    # Générer OTP
    otp = secrets.token_hex(4).upper()
    otp_code = OTPCode(
        user_id=user.id,
        code=otp,
        purpose='verification',
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.session.add(otp_code)
    
    db.session.commit()
    
    # Envoyer email
    send_otp_email(user.email, otp, "verification")
    
    return jsonify({
        'message': 'Inscription réussie. Vérifiez vos emails pour le code OTP.',
        'email': user.email
    })

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
    
    otp = OTPCode.query.filter_by(
        user_id=user.id,
        code=data['code'],
        purpose='verification',
        used=False
    ).first()
    
    if not otp or otp.expires_at < datetime.utcnow():
        return jsonify({'error': 'Code invalide ou expiré'}), 400
    
    user.is_verified = True
    otp.used = True
    db.session.commit()
    
    return jsonify({'message': 'Email vérifié avec succès'})

# ============================================
# CONNEXION
# ============================================
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Email ou mot de passe incorrect'}), 401
    
    if not user.is_verified:
        return jsonify({'error': 'Veuillez vérifier votre email'}), 401
    
    login_user(user)
    return jsonify({
        'message': 'Connexion réussie',
        'api_key': user.api_key,
        'username': user.username
    })

# ============================================
# CONNEXION GOOGLE (avec initialisation des clés)
# ============================================
@auth_bp.route('/google-login')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@auth_bp.route('/google-callback')
def google_callback():
    token = google.authorize_access_token()
    userinfo = google.parse_id_token(token)
    
    user = User.query.filter_by(google_id=userinfo['sub']).first()
    
    if not user:
        # ✅ Créer un nouvel utilisateur
        user = User(
            email=userinfo['email'],
            username=userinfo['email'].split('@')[0],
            google_id=userinfo['sub'],
            is_verified=True
        )
        db.session.add(user)
        db.session.flush()  # Pour obtenir l'ID
        
        # ✅ AJOUT : Enregistrer la première clé dans l'historique
        first_key = APIKey(
            user_id=user.id,
            key=user.api_key,
            is_active=True
        )
        db.session.add(first_key)
        db.session.commit()
    
    login_user(user)
    return redirect(url_for('dashboard'))

# ============================================
# MOT DE PASSE OUBLIÉ
# ============================================
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        return jsonify({'error': 'Email non trouvé'}), 404
    
    # Générer OTP reset
    otp = secrets.token_hex(4).upper()
    otp_code = OTPCode(
        user_id=user.id,
        code=otp,
        purpose='reset',
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.session.add(otp_code)
    db.session.commit()
    
    # Envoyer email
    send_otp_email(user.email, otp, "reset")
    
    return jsonify({'message': 'Code de réinitialisation envoyé'})

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
    
    otp = OTPCode.query.filter_by(
        user_id=user.id,
        code=data['code'],
        purpose='reset',
        used=False
    ).first()
    
    if not otp or otp.expires_at < datetime.utcnow():
        return jsonify({'error': 'Code invalide ou expiré'}), 400
    
    user.password_hash = generate_password_hash(data['new_password'])
    otp.used = True
    db.session.commit()
    
    return jsonify({'message': 'Mot de passe réinitialisé avec succès'})

# ============================================
# DÉCONNEXION
# ============================================
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Déconnexion réussie'})