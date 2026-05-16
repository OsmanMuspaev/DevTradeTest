from typing import Iterable, Dict, Optional
from openai import OpenAI

from llm.base import BaseLLMProvider
from llm.utils import logger, safe_str

# Провайдер для OpenAI API
class OpenAIProvider(BaseLLMProvider):
    def _init_client(self):
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.config.get("base_url", "https://api.openai.com/v1")
        )
        self.default_model = self.config.get("default_model", "gpt-4")
        self.fast_model = self.config.get("fast_model", "gpt-3.5-turbo")
    
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
            
            logger.info(f"OpenAI: Sending request with model {model}")
            
            response = self.client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            reply = response.choices[0].message.content
            logger.info(f"OpenAI: Response received ({len(reply)} chars)")
            
            return safe_str(reply)
        
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
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
            logger.error(f"OpenAI streaming error: {e}")
            yield self._handle_error(e)
    
    def _handle_error(self, e: Exception) -> str:
        error_msg = str(e).lower()
        if "rate_limit" in error_msg:
            return "⚠️ Превышен лимит запросов OpenAI. Подожди немного."
        elif "invalid_api_key" in error_msg:
            return "⚠️ Неверный API ключ OpenAI. Проверь OPENAI_API_KEY."
        elif "insufficient_quota" in error_msg:
            return "⚠️ Закончилась квота OpenAI. Пополни баланс."
        else:
            return f"⚠️ Ошибка OpenAI: {str(e)[:200]}"