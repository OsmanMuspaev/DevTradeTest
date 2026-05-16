from typing import Iterable, Dict, Optional
from anthropic import Anthropic

from llm.base import BaseLLMProvider
from llm.utils import logger, safe_str

# Провайдер для Anthropic Claude API
class AnthropicProvider(BaseLLMProvider):
    def _init_client(self):
        self.client = Anthropic(api_key=self.api_key)
        self.default_model = self.config.get("default_model", "claude-3-sonnet-20240229")
        self.fast_model = self.config.get("fast_model", "claude-3-haiku-20240307")
    
    def _convert_messages(self, messages: Iterable[Dict[str, str]]) -> tuple:
        system = None
        converted = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system = content
            else:
                converted.append({"role": role, "content": content})
        
        return system, converted
    
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
            system, converted_messages = self._convert_messages(messages)
            
            logger.info(f"Claude: Sending request with model {model}")
            
            response = self.client.messages.create(
                model=model,
                messages=converted_messages,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            reply = response.content[0].text
            logger.info(f"Claude: Response received ({len(reply)} chars)")
            
            return safe_str(reply)
        
        except Exception as e:
            logger.error(f"Claude error: {e}")
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
            system, converted_messages = self._convert_messages(messages)
            
            stream = self.client.messages.create(
                model=model,
                messages=converted_messages,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.type == "content_block_delta":
                    yield safe_str(chunk.delta.text)
        
        except Exception as e:
            logger.error(f"Claude streaming error: {e}")
            yield self._handle_error(e)
    
    def _handle_error(self, e: Exception) -> str:
        error_msg = str(e).lower()
        if "rate_limit" in error_msg:
            return "⚠️ Превышен лимит запросов Claude. Подожди немного."
        elif "invalid_api_key" in error_msg:
            return "⚠️ Неверный API ключ Anthropic. Проверь ANTHROPIC_API_KEY."
        else:
            return f"⚠️ Ошибка Claude: {str(e)[:200]}"