# backend/keys_service.py
import secrets
from datetime import datetime
from backend.models import db, APIKey

class KeysService:
    @staticmethod
    def verify_key(auth_header):
        """Vérifie une clé API"""
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        api_key = auth_header.replace('Bearer ', '')
        key_record = APIKey.query.filter_by(key=api_key, is_active=True).first()
        
        if key_record:
            key_record.last_used = datetime.utcnow()
            db.session.commit()
            return key_record.user
        
        return None
    
    @staticmethod
    def generate_key():
        """Génère une nouvelle clé API"""
        return f"open_always_live_{secrets.token_urlsafe(32)}"
    
    @staticmethod
    def get_user_keys(user_id):
        """Récupère toutes les clés d'un utilisateur"""
        return APIKey.query.filter_by(user_id=user_id).order_by(APIKey.created_at.desc()).all()
    
    @staticmethod
    def create_key(user_id, key):
        """Crée une nouvelle clé API"""
        new_key = APIKey(
            user_id=user_id,
            key=key,
            is_active=True
        )
        db.session.add(new_key)
        return new_key
    
    @staticmethod
    def deactivate_key(key):
        """Désactive une clé API"""
        key.is_active = False
        return key
