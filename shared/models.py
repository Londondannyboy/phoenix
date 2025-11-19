"""
Phoenix Shared Models

Pydantic models used across all Phoenix services.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, HttpUrl, Field
from uuid import UUID


# ============================================================================
# INPUT MODELS
# ============================================================================

class CompanyInput(BaseModel):
    """Input for CompanyCreationWorkflow."""
    url: HttpUrl
    category: str = "placement_agent"
    jurisdiction: str = "UK"
    app: str = "placement"
    force_update: bool = False
    research_depth: str = "standard"
    max_crawl_urls: int = 15
    use_exa: bool = False


class ArticleInput(BaseModel):
    """Input for ArticleCreationWorkflow."""
    topic: str
    article_type: str = "news"
    app: str = "placement"
    research_depth: str = "deep"
    max_sources: int = 30
    priority_sources: List[str] = []
    exclude_paywalls: bool = True


# ============================================================================
# RESEARCH MODELS
# ============================================================================

class ResearchArticle(BaseModel):
    """Individual research article from crawling."""
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    published_date: Optional[str] = None
    source: Optional[str] = None
    crawler_used: str = "unknown"
    word_count: int = 0


class ResearchData(BaseModel):
    """Aggregated research data from all sources."""
    normalized_url: str
    domain: str
    company_name: str
    jurisdiction: str
    category: str

    # Research results
    news_articles: List[Dict[str, Any]] = []
    website_content: Dict[str, Any] = {}
    exa_research: Dict[str, Any] = {}
    logo_data: Dict[str, Any] = {}
    zep_context: Dict[str, Any] = {}

    # Metadata
    confidence_score: float = 1.0
    ambiguity_signals: List[str] = []
    is_ambiguous: bool = False
    recommendation: str = "proceed"
    total_cost: float = 0.0

    # Deep research stats
    total_sources: int = 0
    total_words: int = 0
    crawlers_used: Dict[str, int] = {}


# ============================================================================
# ZEP MODELS
# ============================================================================

class ZepEntity(BaseModel):
    """Entity for Zep knowledge graph."""
    type: str  # company, deal, person
    name: str
    attributes: Dict[str, Any] = {}


class ZepRelationship(BaseModel):
    """Relationship between Zep entities."""
    from_entity_id: str
    to_entity_id: str
    type: str  # works_at, advised_on, invested_in


class ZepContext(BaseModel):
    """Context retrieved from Zep graph."""
    exists: bool = False
    entity_id: Optional[str] = None
    relationships: List[Dict[str, Any]] = []
    deals: List[Dict[str, Any]] = []
    people: List[Dict[str, Any]] = []
    related_companies: List[Dict[str, Any]] = []


# ============================================================================
# PAYLOAD MODELS
# ============================================================================

class ProfileSection(BaseModel):
    """Individual section of a company profile."""
    title: str
    content: str
    sources: List[str] = []


class CompanyPayload(BaseModel):
    """Full company profile payload."""
    # Identity
    name: str
    slug: str
    domain: str
    category: str
    app: str

    # Narrative sections
    profile_sections: Dict[str, ProfileSection] = {}

    # Structured data
    headquarters_country: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[str] = None
    specializations: List[str] = []
    geographic_focus: List[str] = []

    # Entities for graph
    deals: List[Dict[str, Any]] = []
    key_people: List[Dict[str, Any]] = []
    related_companies: List[str] = []

    # Media
    logo_url: Optional[str] = None
    featured_image_url: Optional[str] = None
    hero_image_url: Optional[str] = None

    # Metadata
    data_completeness_score: float = 0.0
    data_sources: Dict[str, Any] = {}
    zep_graph_data: Optional[Dict[str, Any]] = None

    # SEO
    meta_description: Optional[str] = None


class ArticlePayload(BaseModel):
    """Full article payload."""
    # Identity
    title: str
    slug: str
    article_type: str
    app: str

    # Content
    summary: str
    content: str  # Full markdown content
    sections: List[Dict[str, Any]] = []

    # Media
    featured_image_url: Optional[str] = None
    images: List[Dict[str, Any]] = []

    # Entities
    companies_mentioned: List[str] = []
    people_mentioned: List[str] = []
    deals_mentioned: List[Dict[str, Any]] = []

    # Metadata
    sources: List[Dict[str, Any]] = []
    word_count: int = 0
    research_depth: str = "standard"
    data_completeness_score: float = 0.0

    # SEO
    meta_description: Optional[str] = None
    tags: List[str] = []


# ============================================================================
# DATABASE MODELS
# ============================================================================

class Company(BaseModel):
    """Company database record."""
    id: UUID
    slug: str
    name: str
    category: str
    app: str
    status: str = "draft"

    # Content
    description: Optional[str] = None
    website_url: Optional[str] = None
    logo_url: Optional[str] = None
    featured_image_url: Optional[str] = None

    # Payload
    payload: Dict[str, Any]

    # Timestamps
    created_at: datetime
    updated_at: datetime


class Article(BaseModel):
    """Article database record."""
    id: UUID
    slug: str
    title: str
    article_type: str
    app: str
    status: str = "draft"

    # Content
    summary: Optional[str] = None
    featured_image_url: Optional[str] = None

    # Payload
    payload: Dict[str, Any]

    # Timestamps
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
