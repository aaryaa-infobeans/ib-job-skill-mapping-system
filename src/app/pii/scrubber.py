"""
Core PII Scrubber - FR-PII-001

Main scrubbing engine implementing deterministic, idempotent PII scrubbing.

Key Features:
- Multi-method detection: NER + Regex + Whitelist
- Configurable scrubbing rules (FR-PII-003)
- Hash-based tokenization (irreversible)
- Immutable audit logging
- GPU-accelerated NER processing
- Idempotent operation (safe to re-run)

Linked Specs:
- FR-PII-001: Core PII scrubbing requirements
- FR-PII-002: NER integration
- FR-PII-003: Configurable rule engine
- NFR-PII-001: Performance (p95 ≤ 50ms)
- NFR-PII-003: Audit logging
- NFR-PII-004: Determinism
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .config import PIIConfig
from .tokenizer import PIITokenizer
from .ner_detector import NERDetector, PIIEntity
from .audit_logger import PIIAuditLogger

logger = logging.getLogger(__name__)


class PIIType(Enum):
    """PII types detected by scrubber."""
    PERSON_NAME = "person_name"
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    POSTAL_CODE = "postal_code"
    CLIENT_NAME = "client_name"
    PROJECT_NAME = "project_name"
    ORGANIZATION = "organization"


@dataclass
class ScrubRule:
    """Scrubbing rule configuration."""
    pii_type: PIIType
    detection_method: str  # 'ner', 'regex', 'whitelist'
    action: str  # 'redact', 'tokenize', 'keep'
    pattern: Optional[str] = None  # Regex pattern (if detection_method='regex')
    replacement: str = "[REDACTED]"  # Replacement text (if action='redact')


@dataclass
class ScrubResult:
    """Result of scrubbing operation."""
    original_text: str
    scrubbed_text: str
    detections: List[Dict]
    is_scrubbed: bool = True
    deterministic: bool = True


class PIIScrubber:
    """
    Core PII scrubber with multi-method detection.
    
    Detection Methods:
    1. NER (SpaCy): PERSON, ORG entities
    2. Regex: Email, phone, SSN, postal code patterns
    3. Whitelist: Known safe terms (tech skills)
    
    Scrubbing Actions:
    - Redact: Replace with [REDACTED]
    - Tokenize: Replace with deterministic hash token
    - Keep: No modification (whitelisted)
    """
    
    def __init__(
        self,
        config: Optional[PIIConfig] = None,
        audit_logger: Optional[PIIAuditLogger] = None
    ):
        """
        Initialize PII scrubber.
        
        Args:
            config: PIIConfig instance (uses from_env() if None)
            audit_logger: PIIAuditLogger instance (optional)
        """
        self.config = config or PIIConfig.from_env()
        self.audit_logger = audit_logger
        
        # Initialize tokenizer
        self.tokenizer = PIITokenizer(salt=self.config.tokenization_salt)
        
        # Log the model being used
        logger.info(f"Initializing NERDetector with model={self.config.spacy_model}, gpu={self.config.use_gpu}, threshold={self.config.ner_confidence_threshold}")
        
        # Initialize NER detector
        self.ner_detector = NERDetector(
            model_name=self.config.spacy_model,
            use_gpu=self.config.use_gpu,
            confidence_threshold=self.config.ner_confidence_threshold
        )
        
        # Load scrubbing rules
        self.rules = self._load_default_rules()
        
        # Whitelist (tech terms that shouldn't be flagged as names)
        self.tech_whitelist = self._load_tech_whitelist()
        
        logger.info("PIIScrubber initialized with %d rules", len(self.rules))
    
    def _load_default_rules(self) -> List[ScrubRule]:
        """
        Load default scrubbing rules (FR-PII-003).
        
        Returns:
            List of scrubbing rules
        """
        return [
            # Email detection (regex)
            ScrubRule(
                pii_type=PIIType.EMAIL,
                detection_method='regex',
                action='redact',
                pattern=r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                replacement='[EMAIL_REDACTED]'
            ),
            
            # Phone numbers (regex) - US/Canada format
            ScrubRule(
                pii_type=PIIType.PHONE,
                detection_method='regex',
                action='redact',
                pattern=r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                replacement='[PHONE_REDACTED]'
            ),
            
            # SSN (regex) - XXX-XX-XXXX format
            ScrubRule(
                pii_type=PIIType.SSN,
                detection_method='regex',
                action='redact',
                pattern=r'\b\d{3}-\d{2}-\d{4}\b',
                replacement='[SSN_REDACTED]'
            ),
            
            # Postal codes (regex) - US ZIP codes
            ScrubRule(
                pii_type=PIIType.POSTAL_CODE,
                detection_method='regex',
                action='redact',
                pattern=r'\b\d{5}(?:-\d{4})?\b',
                replacement='[POSTAL_REDACTED]'
            ),
            
            # Person names (NER)
            ScrubRule(
                pii_type=PIIType.PERSON_NAME,
                detection_method='ner',
                action='redact',
                replacement='[NAME_REDACTED]'
            ),
            
            # Client names (NER + tokenization)
            ScrubRule(
                pii_type=PIIType.CLIENT_NAME,
                detection_method='ner',
                action='redact',
                replacement='[CLIENT_REDACTED]'
                # action='tokenize',  # Tokenize for business context preservation
            ),
            
            # Organizations (NER)
            ScrubRule(
                pii_type=PIIType.ORGANIZATION,
                detection_method='ner',
                # action='tokenize',
                action='redact',
                replacement='[ORG_REDACTED]'
            ),
        ]
    
    def _load_tech_whitelist(self) -> Set[str]:
        """
        Load whitelist of tech terms (NFR False Positive Prevention).
        
        These terms are commonly flagged as names by NER but are actually
        programming languages, frameworks, or tech terminology.
        
        Returns:
            Set of whitelisted terms (lowercase)
        """
        return {
            # Programming languages
            'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby',
            'go', 'rust', 'swift', 'kotlin', 'scala', 'r', 'julia', 'matlab',
            
            # Frameworks
            'react', 'angular', 'vue', 'django', 'flask', 'spring', 'rails',
            'express', 'fastapi', 'nest', 'next', 'svelte',
            
            # Tools
            'docker', 'kubernetes', 'jenkins', 'git', 'jira', 'confluence',
            'terraform', 'ansible', 'maven', 'gradle',
            
            # Databases
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'oracle', 'sqlserver','mssql', 'cassandra', 'dynamodb', 'bigquery', 'snowflake',
            
            # Cloud
            'aws', 'azure', 'gcp', 'heroku', 'vercel', 'netlify',
            
            # Common false positives
            'agile', 'scrum', 'kanban', 'devops', 'cicd', 'ci/cd',

            # Add more as needed based on false positive analysis
            'athena', 'cloudwatch', 'emr', 'glue', 'jwt', 'lambda', 'redshift', 'activemq',
            'agile', 'ai', 'aiflow', 'alteryx', 'android', 'androidx', 'angular', 'angularjs', 
            'ant design', 'artificial intelligence', 'asana', 'asp.net', 'attention mechanism', 
            'autoencoders', 'aws', 'aws cloudformation', 'aws cloudfront', 'aws cloudwatch', 
            'aws dynamodb', 'aws ec2', 'aws lambda', 'aws rds', 'aws redshift', 'aws s3', 'azure', 
            'azure app service', 'azure blob storage', 'azure cosmos', 'azure devops', 
            'azure functions', 'azure ml', 'azure sql database', 'azure virtual machines', 
            'backbone', 'backlog', 'behat', 'big data', 'bigcommerce', 'bigquery', 'birst', 
            'blazor', 'blob','bootstrap', 'bulma', 'burndown chart', 'burnup chart', 'c#', 'c++', 
            'capybara', 'cassandra', 'cd', 'centos', 'chartio', 'ci', 'ci/cd', 'ci/cd pipelines', 
            'cicd', 'classification', 'clickhouse', 'clickup', 'clustering', 'cloud','coda', 'codeception', 
            'codeigniter', 'computer vision', 'confluence', 'convolutional neural networks', 
            'cordova', 'css3', 'cypress', 'data', 'data modeling', 'data science', 'databricks', 
            'dataops', 'db', 'debian', 'deep learning', 'devops', 'dimensionality reduction', 
            'discord', 'django', 'docker', 'domo', 'dropbox paper', 'druid', 'drupal', 'dynamodb', 
            'e2e testing', 'elasticsearch', 'electron', 'ember', 'epic', 'evernote', 'express', 
            'fastapi', 'fedora', 'few-shot learning', 'flask', 'fleep', 'flutter', 'foundation', 
            'freshdesk', 'gcp', 'gcp ai platform', 'gcp app engine', 'gcp bigquery', 
            'gcp cloud functions', 'gcp cloud pub/sub', 'gcp cloud run', 'gcp cloud storage', 
            'gcp compute engine', 'gcp sql', 'generative adversarial networks', 'git', 'glip', 
            'go', 'gooddata', 'google docs', 'google meet', 'graphql', 'grpc', 'h2o.ai', 
            'hadoop', 'heroku', 'hive', 'html5', 'hubbspot', 'hubspot', 'impala', 'insightly', 
            'integration testing', 'intercom', 'ionic', 'ios', 'iosx', 'java', 'javascript', 
            'jenkins', 'jest', 'jira', 'joomla', 'julia', 'junit', 'kafka', 'kanban', 'kotlin', 
            'kubeflow', 'kubernetes', 'laravel', 'lightgbm', 'linux', 'looker', 'machine learning', 
            'macos', 'magento', 'mailchimp', 'marketo', 'material-ui', 'matlab', 'mattermost', 
            'metabase', 'meteor', 'microsoft onenote', 'microsoft teams', 'microsoft word', 'ml', 
            'mlflow', 'mlops', 'mlops & ci/cd', 'mocha', 'mode analytics', 'monday.com', 'mongodb', 
            'mssql', 'mstest', 'mysql', 'natural language processing', 'nest', 'netlify', 
            'neural networks', 'next', 'nlp', 'notion', 'nuclino', 'nunit', 'oauth2', 'onlyoffice', 
            'oracle', 'pardot', 'periscope data', 'phpunit', 'pig', 'pipedrive', 'playwright', 
            'postgresql', 'power bi', 'prestashop', 'presto', 'project', 'prompt', 
            'prompt engineering', 'pytest', 'python', 'pytorch', 'qlik', 'quip', 'r', 'rbac','rabbitmq', 
            'rag pipelines', 'rails', 'rapidminer', 'react', 'react native', 
            'recurrent neural networks', 'red hat', 'redash', 'redis', 'redis streams', 
            'regression', 'reinforcement learning', 'rest', 'retrospective', 'rocket.chat', 
            'rspec', 'ruby', 'rust', 'ryver', 'sagemaker', 'salesforce', 'scala', 'scikit-learn', 
            'scrum', 'selenium', 'self-supervised learning', 'semantic ui', 
            'semi-supervised learning', 'shopify', 'sisense', 'skype', 'slack', 'slack notes', 
            'slack wiki', 'slite', 'snowflake', 'socket.io', 'spark', 'spring', 'sprint', 
            'sprint planning', 'sprint retrospective', 'sprint review', 'sqlserver', 
            'squarespace', 'standup', 'story points', 'superset', 'supervised learning', 'svelte', 
            'swift', 'symfony', 'tableau', 'tailwind', 'tensorflow', 'testcafe', 'testing', 
            'testng', 'transfer learning', 'transformers', 'trello', 'twist', 'typescript', 
            'ubuntu', 'uikit', 'unit', 'unittest', 'unsupervised learning', 'user story', 
            'velocity', 'vercel', 'vue', 'vue.js', 'webex', 'websocket', 'windows', 'wix', 
            'woocommerce', 'wordpress', 'xgboost', 'xunit', 'yammer', 'yellowfin', 'zendesk', 
            'zero-shot learning', 'zoho', 'zoho docs', 'zoom'            
        }
    
    def scrub_text(
        self,
        text: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        field_name: Optional[str] = None
    ) -> ScrubResult:
        """
        Scrub PII from text using multi-method detection.
        
        Algorithm:
        1. Detect entities via NER (PERSON, ORG)
        2. Detect patterns via regex (email, phone, SSN)
        3. Apply whitelist filtering (tech terms)
        4. Execute scrubbing rules (redact/tokenize)
        5. Log to immutable audit trail
        
        Args:
            text: Input text to scrub
            entity_type: Entity type for audit logging
            entity_id: Entity ID for audit logging
            field_name: Field name for audit logging
        
        Returns:
            ScrubResult with scrubbed text and detection metadata
        
        Properties:
        - Deterministic: Same input → same output
        - Idempotent: Safe to run multiple times
        - Audited: All operations logged
        
        Performance (NFR-PII-001):
        - p95 latency ≤ 50ms
        - GPU acceleration for NER (5x speedup)
        """
        if not text or not text.strip():
            return ScrubResult(
                original_text=text,
                scrubbed_text=text,
                detections=[],
                is_scrubbed=True
            )
        
        scrubbed = text
        detections = []
        
        # Step 1: NER detection
        ner_entities = self.ner_detector.detect_entities(text)
        
        for entity in ner_entities:
            # Filter whitelist: exact phrase match OR any individual word is a known tech term
            entity_lower = entity.text.lower()
            if entity_lower in self.tech_whitelist or any(
                word in self.tech_whitelist for word in entity_lower.split()
            ):
                logger.debug("Whitelisted: %s (tech term)", entity.text)
                continue
            
            # Find applicable rule
            rule = self._find_rule_for_entity(entity)
            if not rule:
                continue
            
            # Apply scrubbing action
            if rule.action == 'redact':
                scrubbed = scrubbed.replace(entity.text, rule.replacement)
                
                if self.audit_logger:
                    self.audit_logger.log_redaction(
                        original_value=entity.text,
                        redacted_value=rule.replacement,
                        pii_type=rule.pii_type.value,
                        detection_method='ner',
                        confidence_score=entity.confidence,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        field_name=field_name
                    )
            
            elif rule.action == 'tokenize':
                # Determine token type based on entity label
                token_type = 'CLIENT' if entity.label == 'ORG' else 'PROJECT'
                token = self.tokenizer.tokenize(entity.text, token_type)
                scrubbed = scrubbed.replace(entity.text, token)
                
                if self.audit_logger:
                    self.audit_logger.log_tokenization(
                        original_value=entity.text,
                        token=token,
                        token_type=token_type,
                        entity_type=entity_type,
                        entity_id=entity_id
                    )
            
            detections.append({
                'text': entity.text,
                'pii_type': rule.pii_type.value,
                'method': 'ner',
                'action': rule.action,
                'confidence': entity.confidence
            })
        
        # Step 2: Regex pattern detection
        for rule in self.rules:
            if rule.detection_method == 'regex' and rule.pattern:
                matches = re.finditer(rule.pattern, scrubbed)
                
                for match in matches:
                    matched_text = match.group(0)
                    
                    if rule.action == 'redact':
                        scrubbed = scrubbed.replace(matched_text, rule.replacement)
                        
                        if self.audit_logger:
                            self.audit_logger.log_redaction(
                                original_value=matched_text,
                                redacted_value=rule.replacement,
                                pii_type=rule.pii_type.value,
                                detection_method='regex',
                                confidence_score=1.0,
                                entity_type=entity_type,
                                entity_id=entity_id,
                                field_name=field_name
                            )
                    
                    detections.append({
                        'text': matched_text,
                        'pii_type': rule.pii_type.value,
                        'method': 'regex',
                        'action': rule.action,
                        'confidence': 1.0
                    })
        
        return ScrubResult(
            original_text=text,
            scrubbed_text=scrubbed,
            detections=detections,
            is_scrubbed=len(detections) > 0 or text == scrubbed,
            deterministic=True
        )
    
    def _find_rule_for_entity(self, entity: PIIEntity) -> Optional[ScrubRule]:
        """
        Find applicable scrubbing rule for NER entity.
        
        Args:
            entity: Detected PIIEntity
        
        Returns:
            Matching ScrubRule or None
        """
        for rule in self.rules:
            if rule.detection_method == 'ner':
                if entity.label == 'PERSON' and rule.pii_type == PIIType.PERSON_NAME:
                    return rule
                elif entity.label == 'ORG' and rule.pii_type in (PIIType.CLIENT_NAME, PIIType.ORGANIZATION):
                    return rule
        
        return None
    
    def scrub_profile(self, profile: Dict[str, str]) -> Dict[str, str]:
        """
        Scrub PII from team member profile dictionary.
        
        Args:
            profile: Profile dictionary with fields like 'summary', 'experience'
        
        Returns:
            Scrubbed profile dictionary
        """
        scrubbed_profile = {}
        
        for field, value in profile.items():
            if isinstance(value, str):
                result = self.scrub_text(value, field_name=field)
                scrubbed_profile[field] = result.scrubbed_text
            else:
                scrubbed_profile[field] = value
        
        return scrubbed_profile
