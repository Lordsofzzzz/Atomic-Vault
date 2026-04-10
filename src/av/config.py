PROVIDERS = {
    "openai": {
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "env_key": "OPENAI_API_KEY"
    },
    "anthropic": {
        "models": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"],
        "env_key": "ANTHROPIC_API_KEY"
    },
    "openrouter": {
        "models": ["google/gemini-pro-1.5", "meta-llama/llama-3-70b-instruct"],
        "env_key": "OPENROUTER_API_KEY"
    },
    "github_copilot": {
        "models": ["gemini-3-flash-preview", "gpt-4o", "gpt-4"],
        "env_key": "GITHUB_COPILOT_TOKEN"
    },
    "ollama": {
        "models": ["llama3", "mistral", "phi3"],
        "env_key": None
    }
}
