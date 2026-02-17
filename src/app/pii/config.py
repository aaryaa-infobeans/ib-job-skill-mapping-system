"""
PII Configuration and GPU Detection - TASK-PII-001

Implements:
- GPU detection and validation (NVIDIA T4)
- CUDA availability checks
- Environment configuration
- Performance optimization settings

Linked Specs:
- NFR-PII-001: Performance requirements
- TASK-PII-001: GPU provisioning validation
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional
import subprocess

logger = logging.getLogger(__name__)


@dataclass
class PIIConfig:
    """PII Scrubber configuration with GPU detection."""
    
    # GPU Configuration
    use_gpu: bool = True
    cuda_device: int = 0
    gpu_batch_size: int = 32
    
    # SpaCy Model
    spacy_model: str = "en_core_web_trf"
    ner_confidence_threshold: float = 0.90
    
    # Tokenization
    tokenization_salt_env_var: str = "PII_TOKENIZATION_SALT"
    token_hash_length: int = 8
    
    # Performance
    max_workers: int = 4
    batch_timeout_seconds: int = 30
    
    # Audit Logging
    audit_table_name: str = "pii_scrub_audit"
    enable_audit: bool = True
    
    def __post_init__(self):
        """Validate GPU availability and configuration."""
        if self.use_gpu:
            self._validate_gpu()
        self._validate_tokenization_salt()
    
    def _validate_gpu(self) -> None:
        """
        Validate GPU availability and CUDA support.
        
        DoD Criteria (TASK-PII-001):
        - GPU detected via nvidia-smi
        - CUDA 11+ installed
        - Device accessible
        
        Raises:
            RuntimeError: If GPU validation fails
        """
        try:
            # Check nvidia-smi
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"nvidia-smi failed: {result.stderr}")
            
            gpu_info = result.stdout.strip()
            logger.info(f"GPU detected: {gpu_info}")
            
            # Validate CUDA availability (will be checked by SpaCy/PyTorch)
            try:
                import torch
                if not torch.cuda.is_available():
                    raise RuntimeError("CUDA not available in PyTorch")
                
                cuda_version = torch.version.cuda
                if cuda_version and float(cuda_version.split('.')[0]) < 11:
                    raise RuntimeError(f"CUDA version {cuda_version} < 11.0")
                
                logger.info(f"CUDA {cuda_version} available, device count: {torch.cuda.device_count()}")
                
            except ImportError:
                logger.warning("PyTorch not installed, skipping CUDA version check")
            
        except FileNotFoundError:
            raise RuntimeError(
                "nvidia-smi not found. GPU instance not properly configured. "
                "See TASK-PII-001 DoD requirements."
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("nvidia-smi timeout - GPU driver issue")
        except Exception as e:
            raise RuntimeError(f"GPU validation failed: {str(e)}")
    
    def _validate_tokenization_salt(self) -> None:
        """
        Validate tokenization salt is configured.
        
        Security requirement: Salt must be from environment variable,
        not hardcoded (prevents token prediction attacks).
        
        Raises:
            ValueError: If salt not configured
        """
        salt = os.getenv(self.tokenization_salt_env_var)
        if not salt:
            raise ValueError(
                f"Environment variable {self.tokenization_salt_env_var} not set. "
                "Required for deterministic tokenization (FR-PII-003). "
                "Set with minimum 32 characters for security."
            )
        
        if len(salt) < 32:
            raise ValueError(
                f"Tokenization salt must be ≥ 32 characters (current: {len(salt)}). "
                "Security requirement for HMAC-SHA256."
            )
        
        logger.info("Tokenization salt validated from environment")
    
    @property
    def tokenization_salt(self) -> bytes:
        """Get tokenization salt as bytes."""
        return os.getenv(self.tokenization_salt_env_var, "").encode('utf-8')
    
    @classmethod
    def from_env(cls) -> "PIIConfig":
        """
        Create configuration from environment variables.
        
        Environment Variables:
        - PII_USE_GPU: Enable GPU acceleration (default: true)
        - PII_CUDA_DEVICE: CUDA device index (default: 0)
        - PII_GPU_BATCH_SIZE: Batch size for GPU processing (default: 32)
        - PII_TOKENIZATION_SALT: Secret salt for tokenization (required)
        - PII_ENABLE_AUDIT: Enable audit logging (default: true)
        
        Returns:
            PIIConfig: Validated configuration
        """
        return cls(
            use_gpu=os.getenv("PII_USE_GPU", "true").lower() == "true",
            cuda_device=int(os.getenv("PII_CUDA_DEVICE", "0")),
            gpu_batch_size=int(os.getenv("PII_GPU_BATCH_SIZE", "32")),
            enable_audit=os.getenv("PII_ENABLE_AUDIT", "true").lower() == "true",
        )
