"""Application settings with secrets management integration."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

# Determine the absolute path to the .env file (root directory)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    """Application settings with secure secrets handling."""

    # API Configuration
    api_v1_prefix: str = "/api/v1"
    project_name: str = "IB Job Skill Mapping System"

    
    # Logging
    log_level: str
    
    # Database Configuration
    database_url: Optional[str] = None
    
    # JWT/OAuth2 Configuration
    jwt_secret_key: Optional[str] = None
    jwt_algorithm: str = "HS256"
    
    # Secrets Manager Configuration
    # secrets_backend: str

    
    # LLM Configuration
    llm_provider: str = "openai"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-ada-002"
    openai_input_rate: Optional[float] = None
    openai_output_rate: Optional[float] = None
    
    groq_api_key: Optional[str] = None
    groq_model: str = "llama3-70b-8192"
    input_cost_groq: Optional[float] = None
    output_cost_groq: Optional[float] = None
    
    google_api_key: Optional[str] = None
    google_model: str = "gemini-2.5-flash"
    input_cost_google: Optional[float] = None
    output_cost_google: Optional[float] = None
    
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1
 
    
    # --- GLOBAL WEIGHTS (Fallback) ---
    weight_mandatory_skills: float = 0.30
    weight_preferred_skills: float = 0.20
    weight_semantic_fit: float = 0.25
    weight_experience: float = 0.10
    weight_certification: float = 0.10
    weight_location: float = 0.10
    weight_work_mode: float = 0.10
    weight_jd_text: float = 0.05  # Title match
    
    # --- ROLE-SPECIFIC WEIGHTS (Phase 1) ---
    # SENIOR
    weight_mandatory_senior: float = 0.50
    weight_preferred_senior: float = 0.20
    weight_semantic_senior: float = 0.20
    weight_context_senior: float = 0.05
    weight_availability_senior: float = 0.05

    # MID
    weight_mandatory_mid: float = 0.40
    weight_preferred_mid: float = 0.20
    weight_semantic_mid: float = 0.20
    weight_context_mid: float = 0.15
    weight_availability_mid: float = 0.05

    # JUNIOR
    weight_mandatory_junior: float = 0.30
    weight_preferred_junior: float = 0.30
    weight_semantic_junior: float = 0.20
    weight_context_junior: float = 0.15
    weight_availability_junior: float = 0.05
    
    # Seniority Experience Thresholds (Months)
    senior_exp_threshold: int = 96  # 8 years
    junior_exp_threshold: int = 24  # 2 years
    
    # Gate Barrier Thresholds (Qualified/Disqualified)
    min_skill_weighted_senior: float = 0.20  # 40% of (M+P) weight
    min_semantic_senior: float = 0.30
    fit_threshold_senior: float = 0.75
    
    # Lowered mid-level skill gate to avoid excluding near-fit candidates
    min_skill_weighted_mid: float = 0.08
    min_semantic_mid: float = 0.20
    fit_threshold_mid: float = 0.70
    
    min_skill_weighted_junior: float = 0.15
    min_semantic_junior: float = 0.15
    fit_threshold_junior: float = 0.60
    
    # AI Factor Configs
    ai_boost_senior: float = 0.08
    ai_boost_mid: float = 0.05
    ai_override_threshold_senior: float = 0.75
    ai_confidence_threshold_boost: float = 0.70
    
    # Context Boost Cap (Optional safety)
    context_boost_cap: float = 0.08

    # Skill Family Mappings
    frontend_keywords: str = "react,angular,vue,html,css,javascript,js,frontend,ui,ux"
    backend_keywords: str = "python,java,scala,sql,node,backend,api,spark,snowflake,kafka,ai,ml"
    backend_ai_indicators: str = "backend,ai,ml,data,python,spark,sql,snowflake"
    
    # Skill Groupings (as comma-separated groups)
    skill_group_python: str = "python,django,flask,fastapi,pandas,numpy,scikit-learn,pytorch,tensorflow"
    skill_group_javascript: str = "javascript,js,typescript,ts,react,node,next.js,angular,vue,html,css"
    skill_group_sql: str = "sql,postgresql,postgres,mysql,sql server,snowflake,oracle,db2"
    skill_group_big_data: str = "spark,pyspark,hadoop,kafka,databricks"
    skill_group_ai_ml: str = "machine learning,ai,ml,nlp,llm,genai,deep learning,computer vision"
    skill_group_cloud: str = "aws,azure,gcp,docker,kubernetes,terraform"
    
    # Hybrid Search Ratios
    hybrid_ratio_bm25: float = 0.7
    hybrid_ratio_vector: float = 0.3
    
    # Penalties
    skill_family_penalty: float = -0.10
    max_llm_explanations: int = 10
    
    # Thresholds
    fit_score_threshold: float = 0.5
    rag_similarity_threshold: float = 0.40

    # RAG retrieval pool sizes
    rag_sql_limit: int = 100            # SQL LIMIT — candidate pool before Python filtering
    rag_keyword_fetch_limit: int = 100  # BM25 keyword SQL cap — matches rag_sql_limit
    rag_final_candidates: int = 40      # cap on candidates passed to Node 5

    # Multi-vector composite weights (rag_weight_* must sum to 1.0)
    rag_weight_full_jd: float = 0.25
    rag_weight_level: float = 0.35
    rag_weight_skills_mandatory: float = 0.20
    rag_weight_skills_preferred: float = 0.10
    rag_weight_cert: float = 0.10

    # Blend weight for full_jd_similarity in Node 5 s_score
    # s_score = jd_level_similarity * (1 - weight) + full_jd_similarity * weight
    scoring_blend_full_jd_weight: float = 0.30

    # Per-skill contribution blend (rating + experience → single scalar passed to scorer)
    skill_rating_weight: float = 0.6       # weight of normalised rating (rating/5) in contribution
    skill_exp_weight: float = 0.4          # weight of normalised experience in contribution
    skill_exp_months_cap: int = 48         # experience months at which norm_exp reaches 1.0
    profile_text_match_weight: float = 0.6 # contribution for text-only (no skill ID) matches

    # Feature flag: use jd_level_vector <-> resume_embedding for jd_level_similarity
    # Set RAG_USE_LEVEL_VECTOR=false in .env to revert to old full_jd_vector behavior
    rag_use_level_vector: bool = True
    
    # Retry Configuration
    max_retry_attempts: int = 3
    retry_backoff_factor: float = 2.0

    # LLM rate-limit retry (separate from general infra retry)
    llm_max_retries: int = 5
    llm_retry_base_delay: float = 2.0

    # Availability threshold: candidate is "available" if total allocation < this %
    availability_threshold_percentage: float = 80.0

    # RAG experience sanity bound: values beyond this are treated as no constraint
    exp_max_plausible_months: int = 600  # 50 years
    
    # pgvector Configuration
    pgvector_dimension: int = 768

    # CR-EMB-002: Embedding model settings
    embedding_model_name: str = "google/embeddinggemma-300m"
    embedding_model: Optional[str] = None  # Alias for EMBEDDING_MODEL in .env
    gemma_model_path: Optional[str] = None
    embedding_device: str = "cpu"
    mcp_gdrive_server_path: str = "src/mcp_servers/gdrive/server.py"
    google_service_account_file: Optional[str] = None
    
    # Application Configuration
    app_env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    
    # Security Configuration
    secret_key: Optional[str] = None
    access_token_expire_minutes: int = 1440
    
    model_config = ConfigDict(
        extra="ignore",
        env_file=ENV_PATH,
        case_sensitive=False
    )

    
    def get_database_url(self) -> str:
        """
        Get database URL from secrets manager or fallback to settings.
        """
        from app.app_secrets import get_secret
        
        # Try secrets manager first
        db_url = get_secret("DB_URL") or get_secret("DATABASE_URL")
        
        # Fall back to config (loaded from .env)
        return db_url or self.database_url
    
    def get_jwt_secret_key(self) -> Optional[str]:
        """
        Get JWT secret key from secrets manager or fallback to settings.
        """
        from app.app_secrets import get_secret
        
        # Try secrets manager
        secret = get_secret("JWT_SECRET_KEY") or get_secret("SECRET_KEY")
        
        # Fall back to config (loaded from .env)
        return secret or self.jwt_secret_key



settings = Settings()
