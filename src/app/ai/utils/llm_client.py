"""Unified LLM client utility to support multiple providers."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.settings import settings

logger = logging.getLogger(__name__)

from trulens_eval.tru_custom_app import instrument

class LLMClient:
    """Unified client for multiple LLM providers."""
    
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.client = self._initialize_client()

    def _initialize_client(self) -> Any:
        """Initialize the specific provider client."""
        if self.provider == "openai":
            from openai import OpenAI
            if settings.openai_api_key:
                return OpenAI(api_key=settings.openai_api_key)

        elif self.provider == "groq":
            from groq import Groq
            if settings.groq_api_key:
                return Groq(api_key=settings.groq_api_key)

        elif self.provider == "google":
            from google import genai
            if settings.google_api_key:
                return genai.Client(api_key=settings.google_api_key)

        return None

    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Generic chat completion interface with retry logic for rate limits.
        
        Returns:
            Tuple[content, usage_metrics]
        """
        # Use global defaults if not provided
        temperature = temperature if temperature is not None else settings.llm_temperature
        max_tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens

        if not self.client:
            logger.error(f"LLM client for {self.provider} not initialized")
            return None, None

        import time
        max_retries = settings.llm_max_retries
        base_delay = settings.llm_retry_base_delay

        for attempt in range(max_retries):
            try:
                if self.provider == "openai":
                    return self._openai_completion(messages, model, temperature, max_tokens, response_format)
                elif self.provider == "groq":
                    return self._groq_completion(messages, model, temperature, max_tokens, response_format)
                elif self.provider == "google":
                    return self._google_completion(messages, model, temperature, max_tokens)
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(f"Rate limit hit (429). Retrying in {delay}s... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue

                logger.error(f"LLM call failed on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:
                    return None, None

        return None, None


    @instrument
    def _openai_completion(self, messages, model, temperature, max_tokens, response_format):
        model = model or settings.openai_model
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "model": model
        }
        return content, usage


    @instrument
    def _groq_completion(self, messages, model, temperature, max_tokens, response_format):
        model = model or settings.groq_model
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        if response_format:
             kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "model": model
        }
        return content, usage


    @instrument
    def _google_completion(self, messages, model, temperature, max_tokens):
        # Fallback to gemini-2.5-flash if model is not provided or unavailable
        model = model or settings.google_model or "gemini-2.5-flash"
        # Reformat messages for new GenAI SDK
        system_instruction = ""
        gemini_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                gemini_messages.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                gemini_messages.append({"role": "model", "parts": [{"text": msg["content"]}]})

        # New google.genai client syntax
        response = self.client.models.generate_content(
            model=model,
            contents=gemini_messages,
            config={
                "system_instruction": system_instruction,
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
        )
        
        content = response.text
        usage = {
            "prompt_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
            "completion_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
            "total_tokens": response.usage_metadata.total_token_count if response.usage_metadata else 0,
            "model": model
        }
        return content, usage

    def get_completion_cost(self, usage: Dict) -> float:
        """
        Calculate the cost of a completion based on usage metrics and provider.
        """
        if not usage:
            return 0.0
            
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        input_rate = 0.0
        output_rate = 0.0
        
        if self.provider == "openai":
            input_rate = settings.openai_input_rate or 0.0
            output_rate = settings.openai_output_rate or 0.0
        elif self.provider == "google":
            input_rate = settings.input_cost_google or 0.0
            output_rate = settings.output_cost_google or 0.0
        elif self.provider == "groq":
            input_rate = settings.input_cost_groq or 0.0
            output_rate = settings.output_cost_groq or 0.0
            
        cost = (prompt_tokens / 1_000_000 * input_rate) + (completion_tokens / 1_000_000 * output_rate)
        return cost



# Singleton instance
llm_client = LLMClient()
