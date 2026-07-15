"""Unified LLM client utility to support multiple providers."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.settings import settings

logger = logging.getLogger(__name__)

import contextlib as _contextlib
import io as _io
import logging as _logging

# llm_client is imported before feedback.py (which contains the usual TruLens
# noise suppressor). Set up suppression here — this is the first TruLens import.
# Silence both logger.warning() calls AND raw print() calls that TruLens emits
# for optional integrations (llama_index, providers-google, templates, etc.).
_trulens_noisy_loggers = [
    "trulens",                     # parent — covers all trulens.* children
    "trulens.core.utils.imports",
    "trulens_eval.utils.imports",
]
_saved_levels = {_n: _logging.getLogger(_n).level for _n in _trulens_noisy_loggers}
for _n in _trulens_noisy_loggers:
    _logging.getLogger(_n).setLevel(_logging.CRITICAL)

with _contextlib.redirect_stdout(_io.StringIO()), _contextlib.redirect_stderr(_io.StringIO()):
    from trulens.apps.app import instrument

for _n, _lvl in _saved_levels.items():
    _logging.getLogger(_n).setLevel(_lvl)

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

        elif self.provider in ("local", "ollama"):
            from openai import OpenAI
            return OpenAI(
                api_key=settings.llm_local_api_key or "ollama",
                base_url=settings.llm_local_base_url,
                timeout=900.0,
                max_retries=0,
            )

        elif self.provider == "anthropic":
            from anthropic import Anthropic
            if not settings.ib_anthropic_auth_token:
                logger.error("IB_ANTHROPIC_AUTH_TOKEN is not set for provider 'anthropic'")
                return None
            return Anthropic(
                api_key=settings.ib_anthropic_auth_token,
                base_url=settings.ib_anthropic_base_url,
            )

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
                elif self.provider in ("local", "ollama"):
                    return self._local_completion(messages, model, temperature, max_tokens, response_format)
                elif self.provider == "anthropic":
                    return self._anthropic_completion(messages, model, temperature, max_tokens, response_format)
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
    def _local_completion(self, messages, model, temperature, max_tokens, response_format):
        """OpenAI-compatible completion against a local Ollama endpoint."""
        model = model or settings.llm_local_model
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        usage_obj = getattr(response, "usage", None)
        usage = {
            "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0) or 0,
            "completion_tokens": getattr(usage_obj, "completion_tokens", 0) or 0,
            "total_tokens": getattr(usage_obj, "total_tokens", 0) or 0,
            "model": model,
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

    @instrument
    def _anthropic_completion(self, messages, model, temperature, max_tokens, response_format):
        """Completion via the InfoBeans Anthropic (Claude) gateway."""
        model = model or settings.ib_anthropic_model

        # Anthropic API requires system prompt as a separate kwarg, not in messages.
        system = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        # JSON mode: inject instruction into system prompt (no native response_format param).
        # Must be explicit about no markdown fences — Claude wraps output in ```json by default.
        if response_format and response_format.get("type") == "json_object":
            system = (system + "\n\nOutput ONLY a raw JSON object. No markdown, no code fences, no explanation — just the JSON.").strip()

        kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": anthropic_messages,
        }
        if system:
            kwargs["system"] = system

        try:
            response = self.client.messages.create(**kwargs)
        except Exception as exc:
            # Some Claude models reject the temperature parameter — retry without it.
            if "temperature" in str(exc).lower():
                kwargs.pop("temperature", None)
                response = self.client.messages.create(**kwargs)
            else:
                raise

        content = "".join(
            block.text for block in response.content
            if getattr(block, "type", "") == "text"
        )
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            "model": model,
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
        elif self.provider == "anthropic":
            input_rate = settings.input_cost_anthropic or 0.0
            output_rate = settings.output_cost_anthropic or 0.0
            
        cost = (prompt_tokens / 1_000_000 * input_rate) + (completion_tokens / 1_000_000 * output_rate)
        return cost



# Singleton instance
llm_client = LLMClient()
