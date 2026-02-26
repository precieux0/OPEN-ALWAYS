// Configuration frontend (clés PUBLIQUES uniquement !)
const CONFIG = {
    API_URL: window.location.origin,
    
    // Cloudflare Turnstile - Clé PUBLIQUE (peut être exposée)
    TURNSTILE_SITE_KEY: 'VOTRE_CLE_PUBLIQUE_TURNSTILE',
    
    // Google OAuth - Client ID PUBLIC (peut être exposé)
    GOOGLE_CLIENT_ID: 'VOTRE_GOOGLE_CLIENT_ID.apps.googleusercontent.com',
    
    // Modèles disponibles
    MODELS: {
        'gpt4': { name: 'GPT-4', provider: 'OpenAI' },
        'gpt35': { name: 'GPT-3.5 Turbo', provider: 'OpenAI' },
        'claude': { name: 'Claude 3', provider: 'Anthropic' },
        'claude_opus': { name: 'Claude 3 Opus', provider: 'Anthropic' },
        'gemini': { name: 'Gemini Pro', provider: 'Google' },
        'gemini_ultra': { name: 'Gemini Ultra', provider: 'Google' },
        'llama': { name: 'Llama 3.1', provider: 'Meta' },
        'llama70b': { name: 'Llama 3.1 70B', provider: 'Meta' },
        'mistral': { name: 'Mistral Large', provider: 'Mistral AI' },
        'deepseek': { name: 'DeepSeek V3', provider: 'DeepSeek' },
        'cohere': { name: 'Cohere Command', provider: 'Cohere' },
        'okitakoy': { name: 'Okitakoy AI', provider: 'Okitakoy Inc.' }
    }
};
