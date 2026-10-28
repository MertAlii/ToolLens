export const providerNames:Record<string,string>={codex:'Codex',antigravity:'Antigravity',claude:'Claude Code',cursor:'Cursor CLI',ollama:'Ollama',openai:'OpenAI API',gemini:'Gemini API',anthropic:'Claude API',openrouter:'OpenRouter',groq:'Groq',api:'Diğer API'};
export const cliProviders=['codex','antigravity','claude','cursor'];
export const apiPresets:Record<string,{base_url:string;api_format:string;api_key_env:string}>={
 openai:{base_url:'https://api.openai.com/v1',api_format:'responses',api_key_env:'OPENAI_API_KEY'},
 gemini:{base_url:'https://generativelanguage.googleapis.com/v1beta/openai',api_format:'chat_completions',api_key_env:'GEMINI_API_KEY'},
 anthropic:{base_url:'https://api.anthropic.com/v1',api_format:'anthropic',api_key_env:'ANTHROPIC_API_KEY'},
 openrouter:{base_url:'https://openrouter.ai/api/v1',api_format:'chat_completions',api_key_env:'OPENROUTER_API_KEY'},
 groq:{base_url:'https://api.groq.com/openai/v1',api_format:'chat_completions',api_key_env:'GROQ_API_KEY'},
};
export const isAPI=(id:string)=>id==='api'||id in apiPresets;
