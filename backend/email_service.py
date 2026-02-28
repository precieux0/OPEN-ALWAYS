from flask_mail import Mail, Message
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, app=None):
        self.mail = None
        self._app = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self._app = app
        self.mail = Mail(app)
        logger.info("Service email initialise")
    
    def send_otp(self, email, code, purpose):
        try:
            if not self.mail:
                logger.error("Service email non initialise")
                return False
            
            if purpose == "verification":
                subject = "Open Always - Code de verification"
                html_body = f"""
                <div style="font-family: 'Segoe UI', sans-serif; max-width: 500px; margin: 0 auto; padding: 2rem;">
                    <div style="text-align: center; margin-bottom: 2rem;">
                        <h1 style="color: #0ea5e9; font-size: 1.5rem;">Open Always</h1>
                    </div>
                    <h2 style="color: #1e293b;">Verification de votre email</h2>
                    <p style="color: #475569;">Bienvenue ! Utilisez le code ci-dessous pour verifier votre compte :</p>
                    <div style="text-align: center; margin: 2rem 0;">
                        <span style="background: #f0f9ff; border: 2px solid #0ea5e9; color: #0369a1; padding: 1rem 2rem; font-size: 2rem; font-weight: bold; letter-spacing: 0.3em; border-radius: 12px; display: inline-block;">{code}</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.875rem;">Ce code expire dans 10 minutes.</p>
                </div>
                """
            elif purpose == "reset":
                subject = "Open Always - Reinitialisation mot de passe"
                html_body = f"""
                <div style="font-family: 'Segoe UI', sans-serif; max-width: 500px; margin: 0 auto; padding: 2rem;">
                    <div style="text-align: center; margin-bottom: 2rem;">
                        <h1 style="color: #0ea5e9; font-size: 1.5rem;">Open Always</h1>
                    </div>
                    <h2 style="color: #1e293b;">Reinitialisation du mot de passe</h2>
                    <p style="color: #475569;">Voici votre code de reinitialisation :</p>
                    <div style="text-align: center; margin: 2rem 0;">
                        <span style="background: #fff7ed; border: 2px solid #f97316; color: #c2410c; padding: 1rem 2rem; font-size: 2rem; font-weight: bold; letter-spacing: 0.3em; border-radius: 12px; display: inline-block;">{code}</span>
                    </div>
                    <p style="color: #94a3b8; font-size: 0.875rem;">Ce code expire dans 10 minutes. Si vous n'avez pas demande cette reinitialisation, ignorez cet email.</p>
                </div>
                """
            else:
                return False
            
            msg = Message(
                subject=subject,
                recipients=[email],
                html=html_body,
                body=f"Votre code : {code} (expire dans 10 minutes)"
            )
            
            self.mail.send(msg)
            logger.info(f"Email envoye a {email}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email a {email}: {e}")
            return False
    
    def send_test(self, recipient):
        try:
            if not self.mail:
                return False, "Service email non initialise"
            msg = Message(
                subject="Test Email - Open Always",
                recipients=[recipient],
                body="Ceci est un email de test. Si vous recevez cet email, tout fonctionne !"
            )
            self.mail.send(msg)
            return True, "Email de test envoye"
        except Exception as e:
            return False, str(e)
