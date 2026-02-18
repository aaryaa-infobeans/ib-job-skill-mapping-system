import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Add src to path so we can import app
sys.path.append(os.path.abspath("src"))

from app.ai.llm_factory import get_llm
from app.settings import settings

# Initialize LLM via our Factory with a LOW max_tokens to test "Thinking" consumption
llm = get_llm(temperature=0.0, max_tokens=200)

print(f"Testing LLM Factory integration with LOW max_tokens...")
print(f"  - Provider: {settings.llm_provider}")
print(f"  - Model: {settings.google_model}")
print(f"  - Max Tokens (Settings): {settings.max_tokens}")

# Check the instance attributes if possible
if hasattr(llm, 'max_tokens'):
    print(f"  - Max Tokens (LLM Instance): {llm.max_tokens}")
elif hasattr(llm, 'max_output_tokens'):
    print(f"  - Max Tokens (LLM Instance): {llm.max_output_tokens}")

from langchain_core.messages import SystemMessage, HumanMessage

messages = [
    SystemMessage(content="You are an expert HR recruitment assistant. Provide professional, evidence-based candidate evaluations."),
    HumanMessage(content="Explain how AI works in a few words")
]

response = llm.invoke(messages)
print(f"\nResponse Metadata:\n{json.dumps(response.response_metadata, indent=2)}")
if hasattr(response, 'usage_metadata'):
    print(f"\nUsage Metadata:\n{json.dumps(response.usage_metadata, indent=2)}")
print(f"\nResponse:\n{response.content}")
