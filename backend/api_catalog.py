"""Official API presets. No default model is invented; catalogs are fetched."""
PRESETS={
 'openai':{'name':'OpenAI API','base_url':'https://api.openai.com/v1','api_format':'responses','api_key_env':'OPENAI_API_KEY'},
 'gemini':{'name':'Gemini API','base_url':'https://generativelanguage.googleapis.com/v1beta/openai','api_format':'chat_completions','api_key_env':'GEMINI_API_KEY'},
 'anthropic':{'name':'Claude API','base_url':'https://api.anthropic.com/v1','api_format':'anthropic','api_key_env':'ANTHROPIC_API_KEY'},
 'openrouter':{'name':'OpenRouter','base_url':'https://openrouter.ai/api/v1','api_format':'chat_completions','api_key_env':'OPENROUTER_API_KEY'},
 'groq':{'name':'Groq','base_url':'https://api.groq.com/openai/v1','api_format':'chat_completions','api_key_env':'GROQ_API_KEY'},
}

def prepare(provider,config):
    value={**PRESETS.get(provider,{}),**(config or {}),'_provider_id':provider}
    if provider in PRESETS:
        # Saved keys cannot silently be sent to a different host or endpoint.
        value['base_url']=PRESETS[provider]['base_url']
        value['api_format']=PRESETS[provider]['api_format']
    return value
