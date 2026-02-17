"""Unit tests for PIIConfig and GPU detection - TASK-PII-001"""

import pytest
import os
from unittest.mock import patch, MagicMock
from app.pii.config import PIIConfig


class TestPIIConfig:
    """Test suite for PII configuration and GPU detection."""
    
    def test_config_initialization_with_valid_salt(self, monkeypatch):
        """Test configuration initializes with valid tokenization salt."""
        # Set valid salt
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "a" * 32)
        
        with patch('app.pii.config.subprocess.run') as mock_run:
            # Mock nvidia-smi response
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Tesla T4, 510.47.03, 15360 MiB\n"
            )
            
            with patch('app.pii.config.torch') as mock_torch:
                mock_torch.cuda.is_available.return_value = True
                mock_torch.cuda.device_count.return_value = 1
                mock_torch.version.cuda = "11.8"
                
                config = PIIConfig()
                
                assert config.use_gpu is True
                assert config.tokenization_salt == b"a" * 32
                assert config.spacy_model == "en_core_web_trf"
    
    def test_config_fails_with_short_salt(self, monkeypatch):
        """Test configuration fails with salt < 32 characters."""
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "short")
        
        with pytest.raises(ValueError, match="must be ≥ 32 characters"):
            PIIConfig()
    
    def test_config_fails_with_missing_salt(self, monkeypatch):
        """Test configuration fails when salt not set."""
        monkeypatch.delenv("PII_TOKENIZATION_SALT", raising=False)
        
        with pytest.raises(ValueError, match="not set"):
            PIIConfig()
    
    def test_gpu_validation_success(self, monkeypatch):
        """Test GPU validation passes with nvidia-smi and CUDA."""
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "a" * 32)
        
        with patch('app.pii.config.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Tesla T4, 510.47.03, 15360 MiB\n"
            )
            
            with patch('app.pii.config.torch') as mock_torch:
                mock_torch.cuda.is_available.return_value = True
                mock_torch.version.cuda = "11.8"
                mock_torch.cuda.device_count.return_value = 1
                
                config = PIIConfig(use_gpu=True)
                
                # Should not raise
                assert config.use_gpu is True
                mock_run.assert_called_once()
    
    def test_gpu_validation_fails_without_nvidia_smi(self, monkeypatch):
        """Test GPU validation fails when nvidia-smi not found."""
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "a" * 32)
        
        with patch('app.pii.config.subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()
            
            with pytest.raises(RuntimeError, match="nvidia-smi not found"):
                PIIConfig(use_gpu=True)
    
    def test_gpu_validation_fails_with_old_cuda(self, monkeypatch):
        """Test GPU validation fails with CUDA < 11.0."""
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "a" * 32)
        
        with patch('app.pii.config.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Tesla T4, 510.47.03, 15360 MiB\n"
            )
            
            with patch('app.pii.config.torch') as mock_torch:
                mock_torch.cuda.is_available.return_value = True
                mock_torch.version.cuda = "10.2"  # Old CUDA version
                
                with pytest.raises(RuntimeError, match="CUDA version 10.2 < 11.0"):
                    PIIConfig(use_gpu=True)
    
    def test_config_from_env(self, monkeypatch):
        """Test configuration creation from environment variables."""
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "a" * 32)
        monkeypatch.setenv("PII_USE_GPU", "false")
        monkeypatch.setenv("PII_GPU_BATCH_SIZE", "64")
        monkeypatch.setenv("PII_ENABLE_AUDIT", "false")
        
        config = PIIConfig.from_env()
        
        assert config.use_gpu is False  # GPU validation skipped
        assert config.gpu_batch_size == 64
        assert config.enable_audit is False
    
    def test_config_skips_gpu_validation_when_disabled(self, monkeypatch):
        """Test GPU validation is skipped when use_gpu=False."""
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "a" * 32)
        
        # Should not call nvidia-smi
        config = PIIConfig(use_gpu=False)
        
        assert config.use_gpu is False


@pytest.fixture
def valid_config(monkeypatch):
    """Fixture providing valid PIIConfig for tests."""
    monkeypatch.setenv("PII_TOKENIZATION_SALT", "test_salt_" + "x" * 32)
    
    with patch('app.pii.config.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Tesla T4, 510.47.03, 15360 MiB\n"
        )
        
        with patch('app.pii.config.torch') as mock_torch:
            mock_torch.cuda.is_available.return_value = True
            mock_torch.version.cuda = "11.8"
            mock_torch.cuda.device_count.return_value = 1
            
            yield PIIConfig()
