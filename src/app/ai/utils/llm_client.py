"""Unified LLM client utility to support multiple providers."""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from app.settings import settings

logger = logging.getLogger(__name__)

class LLMClient:
    """Unified client for multiple LLM providers."""
    
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.client = self._initialize_client()

    def _initialize_client(self) -> Any:
        """Initialize the specific provider client."""
        if self.provider == "openai":
            from openai import OpenAI
            api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                return OpenAI(api_key=api_key)
        
        elif self.provider == "groq":
            from groq import Groq
            api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY")
            if api_key:
                return Groq(api_key=api_key)
        
        elif self.provider == "google":
            from google import genai
            api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")
            if api_key:
                return genai.Client(api_key=api_key)
        
        return None

    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        response_format: Optional[Dict] = None
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Generic chat completion interface.
        
        Returns:
            Tuple[content, usage_metrics]
        """
        if not self.client:
            logger.error(f"LLM client for {self.provider} not initialized")
            return None, None

        if self.provider == "openai":
            return self._openai_completion(messages, model, temperature, max_tokens, response_format)
        elif self.provider == "groq":
            return self._groq_completion(messages, model, temperature, max_tokens, response_format)
        elif self.provider == "google":
            return self._google_completion(messages, model, temperature, max_tokens)
        
        return None, None

    def _openai_completion(self, messages, model, temperature, max_tokens, response_format):
        model = model or settings.openai_model
        try:
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
        except Exception as e:
            logger.error(f"OpenAI error: {str(e)}")
            return None, None

    def _groq_completion(self, messages, model, temperature, max_tokens, response_format):
        model = model or settings.groq_model
        try:
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
        except Exception as e:
            logger.error(f"Groq error: {str(e)}")
            return None, None

    def _google_completion(self, messages, model, temperature, max_tokens):
        # Fallback to gemini-2.5-flash if model is not provided or unavailable
        model = model or settings.google_model or "gemini-2.5-flash"
        try:
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
        except Exception as e:
            logger.error(f"Google Gemini error: {str(e)}")
            return None, None

# Singleton instance
llm_client = LLMClient()
