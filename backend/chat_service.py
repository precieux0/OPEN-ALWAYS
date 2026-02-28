import requests
import logging
from backend.config import Config

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.api_url = Config.OKITAKOY_API_URL + "/ask"
        self.models = self._init_models()
    
    def _init_models(self):
        return {
            'gpt4': {'name': 'GPT-4', 'provider': 'OpenAI', 'system_prompt': "You are GPT-4, OpenAI's most advanced model. You are highly intelligent, precise, and professional. Always respond in the same language as the user's message."},
            'gpt35': {'name': 'GPT-3.5 Turbo', 'provider': 'OpenAI', 'system_prompt': "You are GPT-3.5 Turbo, a fast and efficient OpenAI model. You are friendly, concise, and helpful. Always respond in the same language as the user's message."},
            'claude': {'name': 'Claude 3', 'provider': 'Anthropic', 'system_prompt': "You are Claude 3, Anthropic's helpful, harmless, and honest AI assistant. Always respond in the same language as the user's message."},
            'claude_opus': {'name': 'Claude 3 Opus', 'provider': 'Anthropic', 'system_prompt': "You are Claude 3 Opus, Anthropic's most powerful model. You provide deep, sophisticated insights. Always respond in the same language as the user's message."},
            'gemini': {'name': 'Gemini Pro', 'provider': 'Google', 'system_prompt': "You are Gemini Pro, Google's most capable AI model. You are creative and love exploring ideas. Always respond in the same language as the user's message."},
            'gemini_ultra': {'name': 'Gemini Ultra', 'provider': 'Google', 'system_prompt': "You are Gemini Ultra, Google's flagship AI model. You excel at complex reasoning. Always respond in the same language as the user's message."},
            'llama': {'name': 'Llama 3.1', 'provider': 'Meta', 'system_prompt': "You are Llama 3.1, Meta's open-source AI model. You are straightforward and helpful. Always respond in the same language as the user's message."},
            'llama70b': {'name': 'Llama 3.1 70B', 'provider': 'Meta', 'system_prompt': "You are Llama 3.1 70B, Meta's largest open-source model. Always respond in the same language as the user's message."},
            'mistral': {'name': 'Mistral Large', 'provider': 'Mistral AI', 'system_prompt': "You are Mistral Large, a powerful European AI model. You're efficient and precise. Always respond in the same language as the user's message."},
            'deepseek': {'name': 'DeepSeek V3', 'provider': 'DeepSeek', 'system_prompt': "You are DeepSeek V3, a powerful AI model. You're excellent at coding and reasoning. Always respond in the same language as the user's message."},
            'cohere': {'name': 'Cohere Command', 'provider': 'Cohere', 'system_prompt': "You are Cohere Command, specialized in business and enterprise tasks. Always respond in the same language as the user's message."},
            'okitakoy': {'name': 'Okitakoy AI', 'provider': 'Okitakoy Inc.', 'system_prompt': "You are Okitakoy AI, created by Precieux Okitakoy from Okitakoy Inc. You're friendly and enthusiastic. Always respond in the same language as the user's message."}
        }
    
    def get_models(self):
        return {k: {'name': v['name'], 'provider': v['provider']} for k, v in self.models.items()}
    
    def call_api(self, message, personality):
        full_prompt = f"[SYSTEM]\n{personality}\n\n[USER]\n{message}\n\n[ASSISTANT]"
        
        try:
            response = requests.get(
                self.api_url,
                params={'text': full_prompt},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('response', data.get('text', ''))
            logger.error(f"API returned status {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Erreur API Okitakoy: {e}")
            return None
    
    def process_message(self, model_id, message):
        if model_id not in self.models:
            return None, "Modele non supporte"
        
        if not message or not message.strip():
            return None, "Message vide"
        
        model = self.models[model_id]
        response = self.call_api(message, model['system_prompt'])
        
        if not response:
            return None, "Erreur API - reessayez"
        
        return {
            'success': True,
            'model': model['name'],
            'provider': model['provider'],
            'response': response,
            'tokens_used': len(message.split()) + len(response.split())
        }, None
