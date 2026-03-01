from flask import Blueprint, request, jsonify, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import requests
import logging

from backend.models import db, User, OTPCode, APIKey
from backend.config import Config
from backend.email_service import EmailService
from backend.keys_service import KeysService
from backend.google_service import get_google_client

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)
email_service = EmailService()

def verify_turnstile(token):
    if not token:
        logger.warning("Turnstile token manquant")
        return False
    
    if not Config.TURNSTILE_SECRET_KEY:
        logger.warning("TURNSTILE_SECRET_KEY non configure - skip verification")
        return True
    
    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': Config.TURNSTILE_SECRET_KEY,
                'response': token
            },
            timeout=10
        )
        result = response.json()
        return result.get('success', False)
    except Exception as e:
        logger.error(f"Erreur Turnstile: {e}")
        return False

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    logger.info(f"Tentative inscription: {data.get('email')}")
    
    if not data.get('email') or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Tous les champs sont requis'}), 400
    
    if not verify_turnstile(data.get('turnstile_token')):
        return jsonify({'error': 'Verification captcha echouee'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email deja utilise'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': "Nom d'utilisateur deja pris"}), 400
    
    try:
        user = User(
            email=data['email'],
            username=data['username'],
            password_hash=generate_password_hash(data['password'])
        )
        db.session.add(user)
        db.session.flush()
        
        KeysService.create_key(user.id, user.api_key)
        
        otp = secrets.token_hex(3).upper()
        otp_code = OTPCode(
            user_id=user.id,
            code=otp,
            purpose='verification',
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(otp_code)
        db.session.commit()
        
        email_sent = email_service.send_otp(user.email, otp, "verification")
        
        if not email_sent:
            logger.warning(f"Email non envoye a {user.email} - verification manuelle requise")
        
        return jsonify({
            'success': True,
            'message': 'Inscription reussie. Verifiez vos emails.',
            'email': user.email,
            'email_sent': email_sent,
            'otp_code': otp if not email_sent else None
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur inscription: {e}")
        return jsonify({'error': "Erreur lors de l'inscription"}), 500

@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user:
        return jsonify({'error': 'Utilisateur non trouve'}), 404
    
    otp = OTPCode.query.filter_by(
        user_id=user.id,
        code=data.get('code', '').upper().strip(),
        purpose='verification',
        used=False
    ).first()
    
    if not otp:
        return jsonify({'error': 'Code invalide'}), 400
    
    if otp.expires_at < datetime.utcnow():
        return jsonify({'error': 'Code expire'}), 400
    
    user.is_verified = True
    otp.used = True
    db.session.commit()
    
    login_user(user)
    
    return jsonify({
        'success': True,
        'message': 'Email verifie !',
        'api_key': user.api_key,
        'username': user.username
    })

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return redirect(url_for('login_page'))
    
    data = request.json
    logger.info(f"Tentative connexion: {data.get('email')}")
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email et mot de passe requis'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.password_hash or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Email ou mot de passe incorrect'}), 401
    
    if not user.is_verified:
        otp = secrets.token_hex(3).upper()
        otp_code = OTPCode(
            user_id=user.id,
            code=otp,
            purpose='verification',
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(otp_code)
        db.session.commit()
        
        email_sent = email_service.send_otp(user.email, otp, "verification")
        
        return jsonify({
            'error': 'Email non verifie',
            'needs_verification': True,
            'email': user.email,
            'email_sent': email_sent,
            'otp_code': otp if not email_sent else None
        }), 401
    
    login_user(user, remember=True)
    logger.info(f"Connexion reussie: {user.email}")
    
    return jsonify({
        'success': True,
        'message': 'Connexion reussie',
        'api_key': user.api_key,
        'username': user.username
    })

@auth_bp.route('/google-login')
def google_login():
    logger.info("Route /google-login appelee")
    google = get_google_client()
    
    if not google:
        logger.error("Service Google non disponible")
        return jsonify({'error': 'Service Google temporairement indisponible'}), 503
    
    redirect_uri = url_for('auth.google_callback', _external=True)
    logger.info(f"Redirect URI: {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@auth_bp.route('/google-callback')
def google_callback():
    logger.info("Route /google-callback appelee")
    google = get_google_client()
    
    if not google:
        return redirect('/auth/login?error=google_unavailable')
    
    try:
        token = google.authorize_access_token()
        userinfo = google.parse_id_token(token, nonce=None)
        logger.info(f"Utilisateur Google: {userinfo.get('email')}")
        
        user = User.query.filter_by(google_id=userinfo['sub']).first()
        
        if not user:
            existing_user = User.query.filter_by(email=userinfo['email']).first()
            if existing_user:
                existing_user.google_id = userinfo['sub']
                if not existing_user.is_verified:
                    existing_user.is_verified = True
                user = existing_user
                db.session.commit()
            else:
                username_base = userinfo['email'].split('@')[0]
                username = username_base
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f"{username_base}{counter}"
                    counter += 1
                
                user = User(
                    email=userinfo['email'],
                    username=username,
                    google_id=userinfo['sub'],
                    is_verified=True
                )
                db.session.add(user)
                db.session.flush()
                
                KeysService.create_key(user.id, user.api_key)
                db.session.commit()
        
        login_user(user, remember=True)
        return redirect(f'/dashboard?api_key={user.api_key}&username={user.username}')
        
    except Exception as e:
        logger.error(f"Erreur Google OAuth: {e}")
        return redirect('/auth/login?error=google_failed')

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user:
        return jsonify({'error': 'Email non trouve'}), 404
    
    try:
        otp = secrets.token_hex(3).upper()
        otp_code = OTPCode(
            user_id=user.id,
            code=otp,
            purpose='reset',
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.session.add(otp_code)
        db.session.commit()
        
        email_sent = email_service.send_otp(user.email, otp, "reset")
        
        return jsonify({
            'success': True,
            'message': 'Code envoye',
            'email_sent': email_sent,
            'otp_code': otp if not email_sent else None
        })
        
    except Exception as e:
        logger.error(f"Erreur forgot password: {e}")
        return jsonify({'error': "Erreur lors de l'envoi"}), 500

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user:
        return jsonify({'error': 'Utilisateur non trouve'}), 404
    
    otp = OTPCode.query.filter_by(
        user_id=user.id,
        code=data.get('code', '').upper().strip(),
        purpose='reset',
        used=False
    ).first()
    
    if not otp:
        return jsonify({'error': 'Code invalide'}), 400
    
    if otp.expires_at < datetime.utcnow():
        return jsonify({'error': 'Code expire'}), 400
    
    user.password_hash = generate_password_hash(data['new_password'])
    otp.used = True
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Mot de passe reinitialise'})

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@auth_bp.route('/test-email')
def test_email():
    success, message = email_service.send_test("test@freeinternet.io")
    if success:
        return jsonify({'success': True, 'message': 'Email de test envoye'})
    return jsonify({'error': message}), 500

@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    data = request.json
    user = User.query.filter_by(email=data.get('email')).first()
    
    if not user:
        return jsonify({'error': 'Utilisateur non trouve'}), 404
    
    otp = secrets.token_hex(3).upper()
    otp_code = OTPCode(
        user_id=user.id,
        code=otp,
        purpose=data.get('purpose', 'verification'),
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.session.add(otp_code)
    db.session.commit()
    
    email_sent = email_service.send_otp(user.email, otp, data.get('purpose', 'verification'))
    
    return jsonify({
        'success': True,
        'message': 'Code renvoye',
        'email_sent': email_sent,
        'otp_code': otp if not email_sent else None
    })
