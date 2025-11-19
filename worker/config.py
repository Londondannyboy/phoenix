"""
Phoenix Worker Configuration

Unified configuration for all Phoenix services.
"""

import os
from typing import Optional, List, Tuple
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Centralized configuration for Phoenix worker."""

    # ========== TEMPORAL ==========
    TEMPORAL_ADDRESS: str = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    TEMPORAL_NAMESPACE: str = os.getenv("TEMPORAL_NAMESPACE", "default")
    TEMPORAL_API_KEY: Optional[str] = os.getenv("TEMPORAL_API_KEY")
    TEMPORAL_TASK_QUEUE: str = os.getenv("TEMPORAL_TASK_QUEUE", "phoenix-queue")

    # ========== ENVIRONMENT ==========
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # ========== DATABASE ==========
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

    # ========== AI PROVIDERS ==========
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")

    # ========== RESEARCH ==========
    SERPER_API_KEY: Optional[str] = os.getenv("SERPER_API_KEY")
    EXA_API_KEY: Optional[str] = os.getenv("EXA_API_KEY")
    FIRECRAWL_API_KEY: Optional[str] = os.getenv("FIRECRAWL_API_KEY")
    LINKUP_API_KEY: Optional[str] = os.getenv("LINKUP_API_KEY")

    # ========== SERVICES ==========
    CRAWL_SERVICE_URL: Optional[str] = os.getenv("CRAWL_SERVICE_URL")

    # ========== MEDIA ==========
    CLOUDINARY_URL: Optional[str] = os.getenv("CLOUDINARY_URL")
    CLOUDINARY_CLOUD_NAME: Optional[str] = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY: Optional[str] = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET: Optional[str] = os.getenv("CLOUDINARY_API_SECRET")
    FLUX_API_KEY: Optional[str] = os.getenv("FLUX_API_KEY")
    REPLICATE_API_TOKEN: Optional[str] = os.getenv("REPLICATE_API_TOKEN")

    # ========== KNOWLEDGE GRAPH ==========
    ZEP_API_KEY: Optional[str] = os.getenv("ZEP_API_KEY")
    ZEP_API_URL: str = os.getenv("ZEP_API_URL", "https://api.getzep.com")

    @classmethod
    def get_ai_model(cls) -> Tuple[str, str]:
        """
        Get the preferred AI model based on available API keys.

        Returns:
            Tuple of (provider, model_id)

        Priority:
        1. Anthropic Claude Sonnet 4.5 (preferred for narrative generation)
        2. Google Gemini 2.5 Flash
        3. OpenAI GPT-4o Mini
        """
        if cls.ANTHROPIC_API_KEY:
            return ("anthropic", "claude-sonnet-4-5-20250929")
        elif cls.GOOGLE_API_KEY:
            return ("google", "gemini-2.5-flash")
        elif cls.OPENAI_API_KEY:
            return ("openai", "gpt-4o-mini")
        else:
            raise ValueError("No AI API key configured. Set ANTHROPIC_API_KEY, GOOGLE_API_KEY, or OPENAI_API_KEY")

    @classmethod
    def validate_required(cls) -> List[str]:
        """
        Validate required environment variables.

        Returns:
            List of missing required variables
        """
        required = [
            ("TEMPORAL_ADDRESS", cls.TEMPORAL_ADDRESS),
            ("TEMPORAL_NAMESPACE", cls.TEMPORAL_NAMESPACE),
            ("DATABASE_URL", cls.DATABASE_URL),
            ("ZEP_API_KEY", cls.ZEP_API_KEY),
            ("SERPER_API_KEY", cls.SERPER_API_KEY),
        ]

        missing = [name for name, value in required if not value]
        return missing

    @classmethod
    def validate_ai(cls) -> bool:
        """Check if at least one AI provider is configured."""
        return any([
            cls.ANTHROPIC_API_KEY,
            cls.GOOGLE_API_KEY,
            cls.OPENAI_API_KEY
        ])

    @classmethod
    def as_dict(cls) -> dict:
        """
        Get configuration as dictionary (for display).

        Returns:
            Dictionary of service availability
        """
        return {
            # Core
            "has_temporal": bool(cls.TEMPORAL_API_KEY),
            "has_database": bool(cls.DATABASE_URL),
            "has_zep": bool(cls.ZEP_API_KEY),

            # AI
            "has_anthropic": bool(cls.ANTHROPIC_API_KEY),
            "has_google": bool(cls.GOOGLE_API_KEY),
            "has_openai": bool(cls.OPENAI_API_KEY),

            # Research
            "has_serper": bool(cls.SERPER_API_KEY),
            "has_exa": bool(cls.EXA_API_KEY),
            "has_firecrawl": bool(cls.FIRECRAWL_API_KEY),
            "has_linkup": bool(cls.LINKUP_API_KEY),
            "has_crawl_service": bool(cls.CRAWL_SERVICE_URL),

            # Media
            "has_cloudinary": bool(cls.CLOUDINARY_URL or cls.CLOUDINARY_API_KEY),
            "has_flux": bool(cls.FLUX_API_KEY),
            "has_replicate": bool(cls.REPLICATE_API_TOKEN),
        }


# Singleton instance
config = Config()
