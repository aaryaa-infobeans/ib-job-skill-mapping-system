"""Centralized LLM factory for multi-provider support."""

import logging
import os
from typing import Optional, Any

from app.settings import settings

logger = logging.getLogger(__name__)

# Cache for LLM instances
_llm_cache = {}

def get_llm(temperature: float = 0.0, max_tokens: Optional[int] = None) -> Any:
    """
    Get a configured LLM instance (OpenAI or Gemini) based on application settings.
    
    Args:
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate (defaults to settings.max_tokens)
        
    Returns:
        A LangChain ChatModel instance (ChatOpenAI or ChatGoogleGenerativeAI)
    """
    provider = settings.llm_provider.lower()
    
    # Use global setting if not specified
    actual_max_tokens = max_tokens if max_tokens is not None else settings.max_tokens
    
    cache_key = f"{provider}_{temperature}_{actual_max_tokens}"
    
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]

    if provider == "google":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            api_key = settings.google_api_key or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.error("❌ GOOGLE_API_KEY not found in settings or environment")
                raise ValueError("Google API Key missing")

            model_name = settings.google_model
            if not model_name.startswith("models/"):
                model_name = f"models/{model_name}"

            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
                max_tokens=actual_max_tokens,
            )
            logger.info(f"✅ Initialized Gemini LLM: {model_name}")
            _llm_cache[cache_key] = llm
            return llm
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Gemini: {str(e)}")
            # Fallback to OpenAI if Gemini fails? Or just raise? 
            # Given the context, we'll raise to avoid silent failures with exhausted credits.
            raise

    # Default to OpenAI
    try:
        from langchain_openai import ChatOpenAI
        
        api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        llm = ChatOpenAI(
            model=settings.openai_model,
            openai_api_key=api_key,
            temperature=temperature,
            max_tokens=actual_max_tokens,
        )
        logger.info(f"✅ Initialized OpenAI LLM: {settings.openai_model}")
        _llm_cache[cache_key] = llm
        return llm
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenAI: {str(e)}")
        raise
