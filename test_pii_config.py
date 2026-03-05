#!/usr/bin/env python
"""Test PII configuration to verify model name"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Set required environment variable
os.environ["PII_TOKENIZATION_SALT"] = "test_salt_" + "x" * 32

from app.pii.config import PIIConfig

# Test 1: Default config with GPU disabled (no nvidia-smi on this machine)
print("=== Test 1: PIIConfig(use_gpu=False) ===")
config1 = PIIConfig(use_gpu=False)
print(f"spacy_model: {config1.spacy_model}")
print(f"use_gpu: {config1.use_gpu}")
print(f"ner_confidence_threshold: {config1.ner_confidence_threshold}")

# Test 2: Config with use_gpu=False
print("\n=== Test 2: PIIConfig(use_gpu=False) ===")
config2 = PIIConfig(use_gpu=False)
print(f"spacy_model: {config2.spacy_model}")
print(f"use_gpu: {config2.use_gpu}")
print(f"ner_confidence_threshold: {config2.ner_confidence_threshold}")

# Test 3: from_env()
print("\n=== Test 3: PIIConfig.from_env() ===")
os.environ["PII_TOKENIZATION_SALT"] = "test_salt_" + "x" * 32
try:
    config3 = PIIConfig.from_env()
    print(f"spacy_model: {config3.spacy_model}")
    print(f"use_gpu: {config3.use_gpu}")
    print(f"ner_confidence_threshold: {config3.ner_confidence_threshold}")
except Exception as e:
    print(f"Error: {e}")
