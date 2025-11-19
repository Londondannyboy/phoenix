"""
Company Profile Generation with Pydantic AI

Generate comprehensive company profiles using Claude Sonnet 4.5.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from temporalio import activity
from pydantic_ai import Agent

from config import config


# ============================================================================
# PYDANTIC MODELS FOR AI OUTPUTS
# ============================================================================

class ProfileSection(BaseModel):
    """Individual section of a company profile."""
    title: str = Field(description="Section title")
    content: str = Field(description="Section content in markdown format")
    sources: List[str] = Field(default_factory=list, description="Source URLs used")


class ExtractedDeal(BaseModel):
    """Deal extracted from research."""
    name: str = Field(description="Deal or fund name")
    amount: Optional[str] = Field(default=None, description="Deal size/amount if known")
    date: Optional[str] = Field(default=None, description="Deal date if known")
    parties: List[str] = Field(default_factory=list, description="Companies involved")
    sector: Optional[str] = Field(default=None, description="Industry sector")


class ExtractedPerson(BaseModel):
    """Person extracted from research."""
    name: str = Field(description="Person's full name")
    role: Optional[str] = Field(default=None, description="Job title or role")
    company: Optional[str] = Field(default=None, description="Company they work for")


class CompanyProfileOutput(BaseModel):
    """Complete AI-generated company profile."""
    # Basic info
    company_name: str = Field(description="Official company name")
    tagline: str = Field(description="One-sentence company description")

    # Profile sections
    overview: str = Field(description="Company overview paragraph")
    services: str = Field(description="Key services and offerings")
    track_record: str = Field(description="Notable deals and achievements")
    team: str = Field(description="Key team members and leadership")
    market_position: str = Field(description="Market position and competitive advantages")

    # Structured data
    headquarters_country: Optional[str] = Field(default=None, description="HQ country")
    founded_year: Optional[int] = Field(default=None, description="Year founded")
    employee_count: Optional[str] = Field(default=None, description="Employee count range")
    specializations: List[str] = Field(default_factory=list, description="Key specializations")
    geographic_focus: List[str] = Field(default_factory=list, description="Geographic markets")

    # Extracted entities
    deals: List[ExtractedDeal] = Field(default_factory=list, description="Deals mentioned")
    key_people: List[ExtractedPerson] = Field(default_factory=list, description="Key people")
    related_companies: List[str] = Field(default_factory=list, description="Related companies")

    # Quality metrics
    data_completeness_score: float = Field(
        ge=0, le=1,
        description="Score 0-1 indicating how complete the profile is"
    )

    # SEO
    meta_description: str = Field(description="SEO meta description (150-160 chars)")


# ============================================================================
# AI AGENT FOR PROFILE GENERATION
# ============================================================================

def get_profile_generation_agent():
    """Create Pydantic AI agent for company profile generation."""
    provider, model = config.get_ai_model()

    return Agent(
        model=f"{provider}:{model}",
        result_type=CompanyProfileOutput,
        system_prompt="""You are an expert business analyst creating comprehensive company profiles for a professional audience in private equity and fund placement.

Your job is to:
1. Synthesize research data into a clear, authoritative company profile
2. Extract key deals, people, and relationships from the research
3. Identify the company's market position and competitive advantages
4. Create SEO-friendly content that reads professionally

Guidelines:
- Write in third person, professional tone
- Be factual and cite specific deals/numbers when available
- If information is missing or unclear, note it but don't fabricate
- Focus on what makes this company unique in their market
- Extract ALL mentioned deals with as much detail as available
- Extract ALL mentioned people with their roles
- Identify geographic markets they operate in

For the data_completeness_score:
- 1.0 = All sections have substantial, sourced information
- 0.7-0.9 = Most sections complete, some gaps
- 0.5-0.7 = Basic profile possible but missing key details
- Below 0.5 = Insufficient data for quality profile

Profile should be suitable for publication on a professional industry website."""
    )


# ============================================================================
# PROFILE GENERATION ACTIVITY
# ============================================================================

@activity.defn
async def generate_company_profile(
    research_data: Dict[str, Any],
    context_prompt: str,
    app: str = "placement"
) -> Dict[str, Any]:
    """
    Generate company profile using Pydantic AI.

    Args:
        research_data: ResearchData as dict from deep_research_company
        context_prompt: Zep context formatted as prompt
        app: App name for context

    Returns:
        CompanyPayload as dict
    """
    company_name = research_data.get("company_name", "Unknown Company")
    domain = research_data.get("domain", "")

    activity.logger.info(f"Generating profile for: {company_name}")

    # Build comprehensive prompt from research
    prompt_parts = []

    # Company basics
    prompt_parts.append(f"COMPANY TO PROFILE: {company_name}")
    prompt_parts.append(f"Domain: {domain}")
    prompt_parts.append(f"Category: {research_data.get('category', 'general')}")
    prompt_parts.append(f"Jurisdiction: {research_data.get('jurisdiction', 'Unknown')}")

    # Zep context (existing knowledge)
    if context_prompt:
        prompt_parts.append(f"\nEXISTING KNOWLEDGE (from Zep):\n{context_prompt}")

    # Research results - news articles
    news_articles = research_data.get("news_articles", [])
    if news_articles:
        prompt_parts.append(f"\nNEWS ARTICLES ({len(news_articles)} sources):")
        for i, article in enumerate(news_articles[:15], 1):
            prompt_parts.append(f"\n--- Source {i} ---")
            prompt_parts.append(f"Title: {article.get('title', 'N/A')}")
            prompt_parts.append(f"Source: {article.get('source', 'N/A')}")
            prompt_parts.append(f"Date: {article.get('published_date', 'N/A')}")
            content = article.get("content", "")
            if content:
                # Truncate very long content
                if len(content) > 3000:
                    content = content[:3000] + "..."
                prompt_parts.append(f"Content:\n{content}")

    # Website content
    website_content = research_data.get("website_content", {})
    if website_content and website_content.get("content"):
        prompt_parts.append(f"\nWEBSITE CONTENT:")
        content = website_content.get("content", "")
        if len(content) > 5000:
            content = content[:5000] + "..."
        prompt_parts.append(content)

    # Additional research stats
    prompt_parts.append(f"\nRESEARCH STATS:")
    prompt_parts.append(f"Total sources: {research_data.get('total_sources', 0)}")
    prompt_parts.append(f"Total words: {research_data.get('total_words', 0):,}")

    prompt = "\n".join(prompt_parts)

    try:
        # Run AI generation
        agent = get_profile_generation_agent()
        result = await agent.run(prompt)

        profile_output = result.data

        activity.logger.info(
            f"Profile generated: completeness={profile_output.data_completeness_score:.2f}, "
            f"deals={len(profile_output.deals)}, people={len(profile_output.key_people)}"
        )

        # Convert to CompanyPayload format
        payload = {
            # Identity
            "name": profile_output.company_name,
            "slug": domain.replace(".", "-") if domain else company_name.lower().replace(" ", "-"),
            "domain": domain,
            "category": research_data.get("category", "general"),
            "app": app,

            # Narrative sections
            "profile_sections": {
                "overview": {
                    "title": "Overview",
                    "content": profile_output.overview,
                    "sources": []
                },
                "services": {
                    "title": "Services",
                    "content": profile_output.services,
                    "sources": []
                },
                "track_record": {
                    "title": "Track Record",
                    "content": profile_output.track_record,
                    "sources": []
                },
                "team": {
                    "title": "Team",
                    "content": profile_output.team,
                    "sources": []
                },
                "market_position": {
                    "title": "Market Position",
                    "content": profile_output.market_position,
                    "sources": []
                }
            },

            # Structured data
            "headquarters_country": profile_output.headquarters_country,
            "founded_year": profile_output.founded_year,
            "employee_count": profile_output.employee_count,
            "specializations": profile_output.specializations,
            "geographic_focus": profile_output.geographic_focus,

            # Entities for graph
            "deals": [deal.model_dump() for deal in profile_output.deals],
            "key_people": [person.model_dump() for person in profile_output.key_people],
            "related_companies": profile_output.related_companies,

            # Media placeholders
            "logo_url": None,
            "featured_image_url": None,
            "hero_image_url": None,

            # Metadata
            "data_completeness_score": profile_output.data_completeness_score,
            "data_sources": {
                "news_count": len(news_articles),
                "has_website": bool(website_content),
                "total_sources": research_data.get("total_sources", 0),
                "total_words": research_data.get("total_words", 0)
            },
            "tagline": profile_output.tagline,

            # SEO
            "meta_description": profile_output.meta_description
        }

        return payload

    except Exception as e:
        activity.logger.error(f"Profile generation failed: {str(e)}")

        # Return minimal placeholder on failure
        return {
            "name": company_name,
            "slug": domain.replace(".", "-") if domain else company_name.lower().replace(" ", "-"),
            "domain": domain,
            "category": research_data.get("category", "general"),
            "app": app,
            "profile_sections": {
                "overview": {
                    "title": "Overview",
                    "content": f"Profile generation failed for {company_name}: {str(e)}",
                    "sources": []
                }
            },
            "deals": [],
            "key_people": [],
            "related_companies": [],
            "data_completeness_score": 0.0,
            "meta_description": f"{company_name} company profile",
            "error": str(e)
        }
