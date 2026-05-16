import os
from typing import Optional

# LLM Provider выбранный
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()  # groq, openai, anthropic

# Общие настройки
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
DEFAULT_FAST_MODEL = os.getenv("DEFAULT_FAST_MODEL", "llama-3.1-8b-instant")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "2000"))

# Настройки для каждого провайдера
PROVIDER_CONFIG = {
    "groq": {
        "api_key": os.getenv("GROQ_API_KEY"),
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "fast_model": "llama-3.1-8b-instant",
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": "https://api.openai.com/v1",
        "default_model": os.getenv("OPENAI_MODEL", "gpt-4"),
        "fast_model": os.getenv("OPENAI_FAST_MODEL", "gpt-3.5-turbo"),
    },
    "anthropic": {
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "default_model": os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229"),
        "fast_model": os.getenv("CLAUDE_FAST_MODEL", "claude-3-haiku-20240307"),
    },
    "deepseek": {
        "api_key": os.getenv("DEEPSEEK_API_KEY"),
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "fast_model": "deepseek-chat",
    },
    "together": {
        "api_key": os.getenv("TOGETHER_API_KEY"),
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "fast_model": "meta-llama/Llama-3.1-8B-Instruct-Turbo",
    },
}

# Библиотечный контекст
LIBRARY_CONTEXT_PATH = os.path.join(os.path.dirname(__file__), "context", "devtrade_library.md")

# Кодировка
DEFAULT_ENCODING = "utf-8"