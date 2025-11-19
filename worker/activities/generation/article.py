"""
Article Content Generation with Pydantic AI

Generate comprehensive articles using Claude Sonnet 4.5.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from temporalio import activity
from pydantic_ai import Agent
from slugify import slugify

from config import config


# ============================================================================
# PYDANTIC MODELS FOR AI OUTPUTS
# ============================================================================

class ArticleSection(BaseModel):
    """Section of an article."""
    heading: str = Field(description="Section heading")
    content: str = Field(description="Section content in markdown")
    image_prompt: Optional[str] = Field(
        default=None,
        description="Prompt for generating an image for this section"
    )


class ExtractedEntity(BaseModel):
    """Entity extracted from article content."""
    name: str
    type: Literal["company", "person", "deal"]
    context: Optional[str] = Field(default=None, description="How they're mentioned")


class ArticleContentOutput(BaseModel):
    """Complete AI-generated article."""
    # Core content
    title: str = Field(description="Compelling article headline")
    summary: str = Field(description="Article summary/lead paragraph (2-3 sentences)")
    sections: List[ArticleSection] = Field(description="Article sections with content")

    # Entities mentioned
    companies_mentioned: List[str] = Field(
        default_factory=list,
        description="Company names mentioned in the article"
    )
    people_mentioned: List[str] = Field(
        default_factory=list,
        description="People mentioned in the article"
    )
    deals_mentioned: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Deals with name, amount, parties"
    )

    # SEO and metadata
    meta_description: str = Field(description="SEO meta description (150-160 chars)")
    tags: List[str] = Field(default_factory=list, description="Article tags/keywords")

    # Quality
    data_completeness_score: float = Field(
        ge=0, le=1,
        description="Score indicating article quality and completeness"
    )

    # Image generation
    featured_image_prompt: str = Field(
        description="Prompt for generating the featured/hero image"
    )


# ============================================================================
# AI AGENT FOR ARTICLE GENERATION
# ============================================================================

def get_article_generation_agent(article_type: str):
    """Create Pydantic AI agent for article generation."""
    provider, model = config.get_ai_model()

    # Adjust system prompt based on article type
    type_guidance = {
        "news": "Write a timely news article with the most important information first (inverted pyramid). Keep it factual and cite sources.",
        "analysis": "Write an analytical piece that examines trends, causes, and implications. Include expert perspectives and data points.",
        "deep_dive": "Write a comprehensive deep-dive exploring all aspects of the topic. Use multiple sections with detailed coverage.",
        "profile": "Write a profile piece focusing on a company or person. Include background, achievements, and future outlook.",
        "market_update": "Write a market update covering recent developments and their significance. Include relevant data and quotes."
    }

    guidance = type_guidance.get(article_type, type_guidance["news"])

    return Agent(
        model=f"{provider}:{model}",
        result_type=ArticleContentOutput,
        system_prompt=f"""You are an expert business journalist writing for a professional audience in private equity, fund placement, and corporate advisory.

Article Type: {article_type.upper()}
Guidance: {guidance}

Your job is to:
1. Create a compelling, well-structured article from the research provided
2. Extract all companies, people, and deals mentioned
3. Write in a professional, authoritative tone
4. Create sections that flow logically
5. Generate image prompts for visual content

Guidelines:
- Write in third person, professional journalistic tone
- Lead with the most newsworthy/important information
- Include specific numbers, dates, and names when available
- Attribute information to sources
- Each section should be 150-300 words
- Create 4-7 sections depending on content depth
- Extract ALL mentioned entities accurately

For the featured_image_prompt:
- Describe a professional, abstract image that represents the article theme
- Avoid specific people or logos
- Focus on concepts like "business growth", "global markets", "deal-making"

For section image_prompts:
- Create prompts relevant to that section's content
- Keep them professional and abstract

For data_completeness_score:
- 1.0 = Comprehensive article with multiple sources and perspectives
- 0.7-0.9 = Good article with solid coverage
- 0.5-0.7 = Basic article, some gaps in information
- Below 0.5 = Insufficient information for quality article"""
    )


# ============================================================================
# ARTICLE GENERATION ACTIVITY
# ============================================================================

@activity.defn
async def generate_article_content(
    topic: str,
    article_type: str,
    research_data: Dict[str, Any],
    context_prompt: str,
    app: str = "placement"
) -> Dict[str, Any]:
    """
    Generate article content using Pydantic AI.

    Args:
        topic: Article topic
        article_type: Type of article (news, analysis, deep_dive, profile, market_update)
        research_data: Research results from deep_research_article
        context_prompt: Zep context formatted as prompt
        app: App name for context

    Returns:
        ArticlePayload as dict
    """
    activity.logger.info(f"Generating {article_type} article: {topic}")

    # Build comprehensive prompt from research
    prompt_parts = []

    # Article basics
    prompt_parts.append(f"ARTICLE TOPIC: {topic}")
    prompt_parts.append(f"ARTICLE TYPE: {article_type}")
    prompt_parts.append(f"TARGET APP: {app}")

    # Zep context (existing knowledge)
    if context_prompt:
        prompt_parts.append(f"\nEXISTING KNOWLEDGE (from Zep):\n{context_prompt}")

    # Research results
    sources = research_data.get("sources", [])
    if not sources:
        # Fallback to news_articles if sources not present
        sources = research_data.get("news_articles", [])

    if sources:
        prompt_parts.append(f"\nRESEARCH SOURCES ({len(sources)} total):")

        for i, source in enumerate(sources[:20], 1):
            prompt_parts.append(f"\n--- Source {i} ---")
            prompt_parts.append(f"Title: {source.get('title', 'N/A')}")
            prompt_parts.append(f"URL: {source.get('url', 'N/A')}")
            prompt_parts.append(f"Source: {source.get('source', 'N/A')}")
            prompt_parts.append(f"Date: {source.get('published_date', source.get('date', 'N/A'))}")

            content = source.get("content", "")
            if content:
                # Truncate very long content
                if len(content) > 2500:
                    content = content[:2500] + "..."
                prompt_parts.append(f"Content:\n{content}")

    # Research stats
    prompt_parts.append(f"\nRESEARCH STATS:")
    prompt_parts.append(f"Total sources: {research_data.get('total_sources', len(sources))}")
    prompt_parts.append(f"Total words: {research_data.get('total_words', 0):,}")

    prompt = "\n".join(prompt_parts)

    try:
        # Run AI generation
        agent = get_article_generation_agent(article_type)
        result = await agent.run(prompt)

        article_output = result.data

        activity.logger.info(
            f"Article generated: '{article_output.title}', "
            f"sections={len(article_output.sections)}, "
            f"completeness={article_output.data_completeness_score:.2f}"
        )

        # Generate slug from title
        slug = slugify(article_output.title, max_length=100)

        # Compile full markdown content
        content_parts = [article_output.summary, ""]

        for section in article_output.sections:
            content_parts.append(f"## {section.heading}")
            content_parts.append("")
            content_parts.append(section.content)
            content_parts.append("")

        full_content = "\n".join(content_parts)
        word_count = len(full_content.split())

        # Convert to ArticlePayload format
        payload = {
            # Identity
            "title": article_output.title,
            "slug": slug,
            "article_type": article_type,
            "app": app,

            # Content
            "summary": article_output.summary,
            "content": full_content,
            "sections": [
                {
                    "heading": section.heading,
                    "content": section.content,
                    "image_prompt": section.image_prompt
                }
                for section in article_output.sections
            ],

            # Media
            "featured_image_url": None,
            "featured_image_prompt": article_output.featured_image_prompt,
            "images": [],

            # Entities
            "companies_mentioned": article_output.companies_mentioned,
            "people_mentioned": article_output.people_mentioned,
            "deals_mentioned": article_output.deals_mentioned,

            # Metadata
            "sources": [
                {
                    "url": s.get("url", ""),
                    "title": s.get("title", ""),
                    "source": s.get("source", "")
                }
                for s in sources[:20]
            ],
            "word_count": word_count,
            "research_depth": research_data.get("research_depth", "standard"),
            "data_completeness_score": article_output.data_completeness_score,

            # SEO
            "meta_description": article_output.meta_description,
            "tags": article_output.tags
        }

        return payload

    except Exception as e:
        activity.logger.error(f"Article generation failed: {str(e)}")

        # Return minimal placeholder on failure
        slug = slugify(topic, max_length=100)

        return {
            "title": topic,
            "slug": slug,
            "article_type": article_type,
            "app": app,
            "summary": f"Article generation failed: {str(e)}",
            "content": f"# {topic}\n\nArticle generation failed: {str(e)}",
            "sections": [],
            "featured_image_url": None,
            "images": [],
            "companies_mentioned": [],
            "people_mentioned": [],
            "deals_mentioned": [],
            "sources": [],
            "word_count": 0,
            "research_depth": "standard",
            "data_completeness_score": 0.0,
            "meta_description": topic,
            "tags": [],
            "error": str(e)
        }


# ============================================================================
# ENTITY EXTRACTION ACTIVITY
# ============================================================================

class ExtractedEntities(BaseModel):
    """All entities extracted from content."""
    deals: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Deals with name, amount, date, parties, sector"
    )
    people: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="People with name, role, company"
    )
    companies: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Companies with name, type, relationships"
    )


def get_entity_extraction_agent():
    """Create Pydantic AI agent for entity extraction."""
    provider, model = config.get_ai_model()

    return Agent(
        model=f"{provider}:{model}",
        result_type=ExtractedEntities,
        system_prompt="""You are an expert at extracting structured entities from business content.

Extract ALL mentions of:

1. DEALS:
   - Fund placements and capital raises
   - M&A transactions
   - Investments and funding rounds
   Include: name, amount (if mentioned), date (if mentioned), parties involved, sector

2. PEOPLE:
   - Executives and founders
   - Advisors and board members
   - Key personnel mentioned
   Include: full name, role/title, company

3. COMPANIES:
   - Investment firms and funds
   - Corporates and targets
   - Advisors and service providers
   Include: name, type (fund, corporate, advisor), any relationships mentioned

Be thorough - extract every entity mentioned, even if information is partial.
If information is not explicitly stated, leave that field empty rather than guessing."""
    )


@activity.defn
async def extract_entities_from_content(
    content: str,
    title: str = ""
) -> Dict[str, Any]:
    """
    Extract entities from content using Pydantic AI.

    Args:
        content: Text content to extract from
        title: Optional title for context

    Returns:
        Dict with deals, people, companies lists
    """
    activity.logger.info(f"Extracting entities from: {title[:50] if title else 'content'}")

    prompt = f"""CONTENT TO ANALYZE:

Title: {title}

{content[:10000]}  # Limit to avoid token issues

Extract all entities mentioned in this content."""

    try:
        agent = get_entity_extraction_agent()
        result = await agent.run(prompt)

        entities = result.data

        activity.logger.info(
            f"Extracted: {len(entities.deals)} deals, "
            f"{len(entities.people)} people, "
            f"{len(entities.companies)} companies"
        )

        return {
            "deals": entities.deals,
            "people": entities.people,
            "companies": entities.companies
        }

    except Exception as e:
        activity.logger.error(f"Entity extraction failed: {str(e)}")
        return {
            "deals": [],
            "people": [],
            "companies": [],
            "error": str(e)
        }
