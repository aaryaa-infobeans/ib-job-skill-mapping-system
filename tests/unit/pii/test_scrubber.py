"""Unit tests for PIIScrubber - FR-PII-001"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.pii.scrubber import PIIScrubber, ScrubRule, PIIType, ScrubResult
from app.pii.config import PIIConfig
from app.pii.ner_detector import PIIEntity


class TestPIIScrubber:
    """Test suite for PII scrubber core functionality."""
    
    @pytest.fixture
    def mock_config(self, monkeypatch):
        """Fixture providing mocked PIIConfig."""
        monkeypatch.setenv("PII_TOKENIZATION_SALT", "test_salt_" + "x" * 32)
        
        with patch('app.pii.config.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Tesla T4\n")
            
            with patch('app.pii.config.torch') as mock_torch:
                mock_torch.cuda.is_available.return_value = True
                mock_torch.version.cuda = "11.8"
                mock_torch.cuda.device_count.return_value = 1
                
                yield PIIConfig(use_gpu=False)  # Disable GPU for tests
    
    @pytest.fixture
    def scrubber(self, mock_config):
        """Fixture providing PIIScrubber instance with mocked NER."""
        with patch('app.pii.scrubber.NERDetector'):
            scrubber = PIIScrubber(config=mock_config, audit_logger=None)
            
            # Mock NER detector
            scrubber.ner_detector.detect_entities = Mock(return_value=[])
            
            yield scrubber
    
    def test_scrubber_initialization(self, scrubber):
        """Test scrubber initializes with default rules."""
        assert len(scrubber.rules) > 0
        assert scrubber.tokenizer is not None
        assert scrubber.ner_detector is not None
    
    def test_scrub_email_pattern(self, scrubber):
        """Test email pattern detection and redaction."""
        text = "Contact us at john.doe@example.com for more info"
        
        result = scrubber.scrub_text(text)
        
        assert "[EMAIL_REDACTED]" in result.scrubbed_text
        assert "john.doe@example.com" not in result.scrubbed_text
        assert len(result.detections) > 0
        assert any(d['pii_type'] == 'email' for d in result.detections)
    
    def test_scrub_phone_pattern(self, scrubber):
        """Test phone number detection and redaction."""
        text = "Call me at 555-123-4567 or (555) 987-6543"
        
        result = scrubber.scrub_text(text)
        
        assert "[PHONE_REDACTED]" in result.scrubbed_text
        assert "555-123-4567" not in result.scrubbed_text
        assert "555" not in result.scrubbed_text  # All instances redacted
    
    def test_scrub_ssn_pattern(self, scrubber):
        """Test SSN detection and redaction."""
        text = "SSN: 123-45-6789"
        
        result = scrubber.scrub_text(text)
        
        assert "[SSN_REDACTED]" in result.scrubbed_text
        assert "123-45-6789" not in result.scrubbed_text
    
    def test_scrub_postal_code_pattern(self, scrubber):
        """Test postal code detection and redaction."""
        text = "Address: 12345 or 12345-6789"
        
        result = scrubber.scrub_text(text)
        
        assert "[POSTAL_REDACTED]" in result.scrubbed_text
        assert "12345" not in result.scrubbed_text
    
    def test_scrub_empty_text(self, scrubber):
        """Test scrubbing empty text returns empty result."""
        result = scrubber.scrub_text("")
        
        assert result.original_text == ""
        assert result.scrubbed_text == ""
        assert len(result.detections) == 0
    
    def test_scrub_text_without_pii(self, scrubber):
        """Test text without PII passes through unchanged."""
        text = "This is a clean text about Python programming."
        
        result = scrubber.scrub_text(text)
        
        assert result.scrubbed_text == text
        assert result.is_scrubbed is True  # Marked as scrubbed even if no changes
    
    def test_scrub_with_person_name_via_ner(self, scrubber):
        """Test person name detection via NER."""
        text = "John Smith worked on the project"
        
        # Mock NER to return PERSON entity
        scrubber.ner_detector.detect_entities = Mock(return_value=[
            PIIEntity(text="John Smith", label="PERSON", start=0, end=10, confidence=0.95)
        ])
        
        result = scrubber.scrub_text(text)
        
        assert "[NAME_REDACTED]" in result.scrubbed_text
        assert "John Smith" not in result.scrubbed_text
    
    def test_scrub_with_organization_tokenization(self, scrubber):
        """Test organization name tokenization via NER."""
        text = "Acme Corporation hired us"
        
        # Mock NER to return ORG entity
        scrubber.ner_detector.detect_entities = Mock(return_value=[
            PIIEntity(text="Acme Corporation", label="ORG", start=0, end=16, confidence=0.92)
        ])
        
        result = scrubber.scrub_text(text)
        
        # Should be tokenized, not redacted
        assert "CLIENT_TOKEN_" in result.scrubbed_text
        assert "Acme Corporation" not in result.scrubbed_text
    
    def test_tech_whitelist_filtering(self, scrubber):
        """Test tech terms are whitelisted and not scrubbed."""
        text = "Experience with Python, Java, and React"
        
        # Mock NER to flag tech terms as entities (false positive scenario)
        scrubber.ner_detector.detect_entities = Mock(return_value=[
            PIIEntity(text="Python", label="PERSON", start=16, end=22, confidence=0.85),
            PIIEntity(text="Java", label="PERSON", start=24, end=28, confidence=0.83),
        ])
        
        result = scrubber.scrub_text(text)
        
        # Tech terms should NOT be scrubbed
        assert "Python" in result.scrubbed_text
        assert "Java" in result.scrubbed_text
        assert "[NAME_REDACTED]" not in result.scrubbed_text
    
    def test_scrub_profile_dictionary(self, scrubber):
        """Test scrubbing of profile dictionary."""
        profile = {
            "summary": "Contact john@example.com",
            "experience": "Worked at Acme Corp",
            "id": 123  # Non-string field
        }
        
        result = scrubber.scrub_profile(profile)
        
        assert "[EMAIL_REDACTED]" in result["summary"]
        assert result["id"] == 123  # Non-string unchanged
    
    def test_deterministic_scrubbing(self, scrubber):
        """Test scrubbing is deterministic (NFR-PII-004)."""
        text = "Contact john.doe@example.com"
        
        result1 = scrubber.scrub_text(text)
        result2 = scrubber.scrub_text(text)
        result3 = scrubber.scrub_text(text)
        
        assert result1.scrubbed_text == result2.scrubbed_text == result3.scrubbed_text
    
    def test_scrubber_with_audit_logging(self, mock_config):
        """Test scrubber logs to audit logger when provided."""
        mock_audit_logger = Mock()
        
        with patch('app.pii.scrubber.NERDetector'):
            scrubber = PIIScrubber(config=mock_config, audit_logger=mock_audit_logger)
            scrubber.ner_detector.detect_entities = Mock(return_value=[])
            
            text = "Email: test@example.com"
            scrubber.scrub_text(text, entity_type="test_entity", entity_id=1)
            
            # Verify audit logger was called
            assert mock_audit_logger.log_redaction.called
    
    def test_multiple_pii_types_in_same_text(self, scrubber):
        """Test multiple PII types detected in same text."""
        text = "John Doe (john@example.com, 555-1234) at Acme Corp"
        
        scrubber.ner_detector.detect_entities = Mock(return_value=[
            PIIEntity(text="John Doe", label="PERSON", start=0, end=8, confidence=0.95),
            PIIEntity(text="Acme Corp", label="ORG", start=43, end=52, confidence=0.92),
        ])
        
        result = scrubber.scrub_text(text)
        
        # Should detect: name (NER), email (regex), phone (regex), org (NER)
        assert len(result.detections) >= 3
        assert "[NAME_REDACTED]" in result.scrubbed_text
        assert "[EMAIL_REDACTED]" in result.scrubbed_text
        assert "CLIENT_TOKEN_" in result.scrubbed_text


class TestScrubRule:
    """Test suite for ScrubRule configuration."""
    
    def test_scrub_rule_creation(self):
        """Test scrub rule can be created."""
        rule = ScrubRule(
            pii_type=PIIType.EMAIL,
            detection_method='regex',
            action='redact',
            pattern=r'\b[\w\.-]+@[\w\.-]+\.\w+\b',
            replacement='[EMAIL]'
        )
        
        assert rule.pii_type == PIIType.EMAIL
        assert rule.action == 'redact'
        assert rule.pattern is not None
