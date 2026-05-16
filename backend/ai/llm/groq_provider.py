from typing import Iterable, Dict, Optional
from groq import Groq

from llm.base import BaseLLMProvider
from llm.utils import logger, safe_str

# Провайдер для Groq API
class GroqProvider(BaseLLMProvider):
    def _init_client(self):
        self.client = Groq(api_key=self.api_key)
        self.default_model = self.config.get("default_model", "llama-3.3-70b-versatile")
        self.fast_model = self.config.get("fast_model", "llama-3.1-8b-instant")
    
    def generate(
        self,
        messages: Iterable[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> str:
        try:
            model = model or self.default_model
            
            logger.info(f"Groq: Sending request with model {model}")
            
            response = self.client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=kwargs.get("top_p", 0.95),
            )
            
            reply = response.choices[0].message.content
            logger.info(f"Groq: Response received ({len(reply)} chars)")
            
            return safe_str(reply)
        
        except Exception as e:
            logger.error(f"Groq error: {e}")
            return self._handle_error(e)
    
    def generate_streaming(
        self,
        messages: Iterable[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ):
        try:
            model = model or self.default_model
            
            stream = self.client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield safe_str(chunk.choices[0].delta.content)
        
        except Exception as e:
            logger.error(f"Groq streaming error: {e}")
            yield self._handle_error(e)
    
    def _handle_error(self, e: Exception) -> str:
        error_msg = str(e).lower()
        if "rate_limit" in error_msg:
            return "⚠️ Превышен лимит запросов Groq. Подожди немного."
        elif "invalid_api_key" in error_msg:
            return "⚠️ Неверный API ключ Groq. Проверь GROQ_API_KEY."
        else:
            return f"⚠️ Ошибка Groq: {str(e)[:200]}"