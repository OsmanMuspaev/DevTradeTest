from typing import Optional
from functools import lru_cache
from pathlib import Path

from llm.base import BaseLLMProvider
from llm.groq_provider import GroqProvider
from llm.openai_provider import OpenAIProvider
from llm.anthropic_provider import AnthropicProvider
from llm.utils import logger, safe_str
import config

# Фабрика для создания LLM провайдеров
class LLMFactory:
    _providers = {
        "groq": GroqProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }
    
    @classmethod
    def get_provider(cls, provider_name: Optional[str] = None) -> Optional[BaseLLMProvider]:
        provider_name = (provider_name or config.LLM_PROVIDER).lower()
        
        if provider_name not in cls._providers:
            logger.error(f"Unknown provider: {provider_name}")
            return None
        
        provider_config = config.PROVIDER_CONFIG.get(provider_name, {}).copy()
        
        api_key = provider_config.pop("api_key", None)
        
        if not api_key:
            logger.error(f"No API key for provider: {provider_name}")
            return None
        
        provider_class = cls._providers[provider_name]
        
        return provider_class(api_key=api_key, **provider_config)
    
    @classmethod
    def register_provider(cls, name: str, provider_class):
        cls._providers[name.lower()] = provider_class


# Глобальный экземпляр провайдера
_default_provider = None


def get_llm_provider() -> Optional[BaseLLMProvider]:
    global _default_provider
    if _default_provider is None:
        _default_provider = LLMFactory.get_provider()
    return _default_provider


@lru_cache(maxsize=1)
def load_library_context() -> str:
    path = Path(config.LIBRARY_CONTEXT_PATH)
    try:
        if path.exists():
            content = path.read_text(encoding=config.DEFAULT_ENCODING)
            logger.info(f"Loaded library context ({len(content)} chars)")
            return safe_str(content)
        else:
            logger.warning(f"Library context not found: {path}")
            return ""
    except Exception as e:
        logger.error(f"Error loading library context: {e}")
        return ""