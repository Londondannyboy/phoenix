"""
Phoenix App Configurations

Each app has specific:
- Keywords for news monitoring
- Exclusions (topics to avoid)
- Interests (what to prioritize)
- Target audience context
"""

from typing import Dict, List, Any
from pydantic import BaseModel


class AppConfig(BaseModel):
    """Configuration for a Phoenix app."""
    name: str
    display_name: str
    description: str

    # News monitoring
    keywords: List[str]
    exclusions: List[str]
    priority_sources: List[str]

    # Content focus
    interests: List[str]
    target_audience: str
    content_tone: str

    # Company categories for this app
    company_categories: List[str]

    # Geographic focus
    geographic_focus: List[str]


# ============================================================================
# APP CONFIGURATIONS
# ============================================================================

PLACEMENT_CONFIG = AppConfig(
    name="placement",
    display_name="Placement Agent Directory",
    description="Directory of placement agents for private equity fund managers",

    keywords=[
        "placement agent",
        "fund placement",
        "capital raising",
        "private equity fundraising",
        "LP commitment",
        "fund distribution",
        "GP stakes",
        "fund formation",
        "institutional investors",
        "limited partner"
    ],

    exclusions=[
        "job placement",
        "staffing agency",
        "recruitment",
        "employment agency",
        "real estate placement",
        "product placement",
        "advertising placement"
    ],

    priority_sources=[
        "Private Equity International",
        "PE Hub",
        "PitchBook",
        "Preqin",
        "Buyouts Insider",
        "Private Equity Wire",
        "Institutional Investor",
        "Bloomberg",
        "Reuters"
    ],

    interests=[
        "New fund launches",
        "Placement agent mandates",
        "LP commitments",
        "Fundraising milestones",
        "Team hires at placement agents",
        "New placement agent launches",
        "GP-LP relationships",
        "Fund performance",
        "Market trends in PE fundraising"
    ],

    target_audience="Private equity fund managers, GPs, institutional LPs, placement professionals",
    content_tone="Professional, data-driven, industry insider",

    company_categories=[
        "placement_agent",
        "fund_administrator",
        "investor_relations",
        "capital_advisory"
    ],

    geographic_focus=["US", "UK", "EU", "Asia"]
)


RELOCATION_CONFIG = AppConfig(
    name="relocation",
    display_name="Global Relocation Directory",
    description="Directory of corporate relocation and global mobility providers",

    keywords=[
        "corporate relocation",
        "employee mobility",
        "global mobility",
        "expat relocation",
        "talent mobility",
        "international assignment",
        "relocation management",
        "destination services",
        "immigration services",
        "assignment management"
    ],

    exclusions=[
        "moving company reviews",
        "DIY moving tips",
        "furniture moving",
        "residential moving",
        "local moving",
        "storage units",
        "packing tips"
    ],

    priority_sources=[
        "Mobility Magazine",
        "Forum for Expatriate Management",
        "Relocate Global",
        "Re:locate Magazine",
        "Global Mobility News",
        "HR Executive",
        "SHRM",
        "Bloomberg",
        "Reuters"
    ],

    interests=[
        "RMC acquisitions and mergers",
        "New mobility programs",
        "Immigration policy changes",
        "Remote work policies",
        "Hybrid work impact on mobility",
        "Tax and compliance changes",
        "Technology in mobility",
        "Sustainability in relocation",
        "DE&I in global mobility"
    ],

    target_audience="HR leaders, global mobility managers, talent acquisition, relocation professionals",
    content_tone="Practical, compliance-aware, HR-focused",

    company_categories=[
        "relocation_provider",
        "destination_services",
        "immigration_services",
        "corporate_housing"
    ],

    geographic_focus=["US", "UK", "EU", "Asia", "Global"]
)


RAINMAKER_CONFIG = AppConfig(
    name="rainmaker",
    display_name="Rainmaker Network",
    description="Network for dealmakers and business development professionals",

    keywords=[
        "rainmaker",
        "dealmaker",
        "investment banking",
        "M&A advisor",
        "deal origination",
        "client acquisition",
        "business development",
        "deal sourcing",
        "relationship capital",
        "revenue generation"
    ],

    exclusions=[
        "weather rainmaker",
        "cloud seeding",
        "irrigation",
        "gaming rainmaker",
        "music rainmaker"
    ],

    priority_sources=[
        "Bloomberg",
        "Reuters",
        "Financial Times",
        "Wall Street Journal",
        "Dealogic",
        "Mergermarket",
        "PE Hub",
        "Business Insider"
    ],

    interests=[
        "Major deal announcements",
        "Banker moves and hires",
        "League table changes",
        "New advisory mandates",
        "Cross-border deals",
        "Industry consolidation",
        "New fund launches",
        "IPO pipeline",
        "SPAC activity"
    ],

    target_audience="Investment bankers, M&A advisors, PE deal teams, corporate development",
    content_tone="Deal-focused, competitive intelligence, market-moving",

    company_categories=[
        "investment_bank",
        "advisory_firm",
        "boutique_bank",
        "deal_origination"
    ],

    geographic_focus=["US", "UK", "EU", "Asia"]
)


CHIEF_OF_STAFF_CONFIG = AppConfig(
    name="chief-of-staff",
    display_name="Chief of Staff Network",
    description="Community for Chiefs of Staff and executive operations professionals",

    keywords=[
        "chief of staff",
        "executive operations",
        "CEO office",
        "strategic operations",
        "executive assistant",
        "office of the CEO",
        "executive chief of staff",
        "business operations",
        "strategic initiatives"
    ],

    exclusions=[
        "military chief of staff",
        "White House chief of staff",
        "government chief of staff",
        "political appointments"
    ],

    priority_sources=[
        "Harvard Business Review",
        "McKinsey Insights",
        "Fast Company",
        "Forbes",
        "Inc Magazine",
        "Chief of Staff Network",
        "LinkedIn News"
    ],

    interests=[
        "CoS role evolution",
        "Executive leadership",
        "Organizational design",
        "Strategic planning",
        "Board relations",
        "Executive communication",
        "Crisis management",
        "Change management",
        "Career paths for CoS"
    ],

    target_audience="Chiefs of Staff, executive assistants, COOs, executive operations",
    content_tone="Strategic, leadership-focused, career-oriented",

    company_categories=[
        "executive_services",
        "consulting",
        "leadership_development"
    ],

    geographic_focus=["US", "UK", "EU", "Global"]
)


# ============================================================================
# APP REGISTRY
# ============================================================================

APP_CONFIGS: Dict[str, AppConfig] = {
    "placement": PLACEMENT_CONFIG,
    "relocation": RELOCATION_CONFIG,
    "rainmaker": RAINMAKER_CONFIG,
    "chief-of-staff": CHIEF_OF_STAFF_CONFIG,
}


def get_app_config(app_name: str) -> AppConfig:
    """Get configuration for an app."""
    if app_name not in APP_CONFIGS:
        raise ValueError(f"Unknown app: {app_name}. Available: {list(APP_CONFIGS.keys())}")
    return APP_CONFIGS[app_name]


def get_all_apps() -> List[str]:
    """Get list of all configured apps."""
    return list(APP_CONFIGS.keys())
