"""
News Assessment with Pydantic AI

AI-powered relevance assessment for news stories using:
- Zep context (existing coverage)
- Neon context (recently published)
- Pydantic AI (structured outputs)
"""

from typing import Dict, Any, List, Literal, Optional
from pydantic import BaseModel, Field
from temporalio import activity
from pydantic_ai import Agent

from config import config


# ============================================================================
# PYDANTIC MODELS FOR AI OUTPUTS
# ============================================================================

class StoryRelevance(BaseModel):
    """AI assessment of story relevance for an app."""
    is_relevant: bool = Field(description="Is this story relevant for the app?")
    relevance_score: float = Field(ge=0, le=1, description="Relevance score 0-1")
    story_type: Literal["new", "update", "saga"] = Field(
        description="new=fresh story, update=new info on existing, saga=ongoing series"
    )
    priority: Literal["high", "medium", "low"] = Field(
        description="Publishing priority"
    )
    reasoning: str = Field(description="Why is this relevant/not relevant")
    suggested_angle: Optional[str] = Field(
        default=None,
        description="Suggested angle if we cover this story"
    )
    related_entities: List[str] = Field(
        default_factory=list,
        description="Companies, people, deals mentioned"
    )


class NewsAssessmentResult(BaseModel):
    """Result of assessing multiple news stories."""
    stories_assessed: int
    relevant_stories: List[Dict[str, Any]]
    skipped_stories: List[Dict[str, Any]]
    app: str
    total_high_priority: int
    total_medium_priority: int
    total_low_priority: int


# ============================================================================
# AI AGENT FOR NEWS ASSESSMENT
# ============================================================================

def get_news_assessment_agent():
    """Create Pydantic AI agent for news assessment."""
    provider, model = config.get_ai_model()

    return Agent(
        model=f"{provider}:{model}",
        result_type=StoryRelevance,
        system_prompt="""You are a news editor assessing stories for relevance to a specific industry app.

Your job is to:
1. Determine if a story is relevant for the given app and its audience
2. Check if we've already covered this (using Zep/Neon context)
3. Classify: new story, update to existing, or ongoing saga
4. Assess priority based on timeliness and importance
5. Suggest an angle if we should cover it

Be selective - only high-quality, relevant stories should be marked as relevant.
Consider the app's target audience and what they care about.

For story_type:
- "new": First time we're hearing about this
- "update": New information on something we've covered
- "saga": Part of an ongoing series (e.g., deal that's been developing)
"""
    )


# ============================================================================
# NEWS ASSESSMENT ACTIVITIES
# ============================================================================

@activity.defn
async def assess_story_relevance(
    story: Dict[str, Any],
    app: str,
    app_keywords: List[str],
    zep_context: Dict[str, Any],
    neon_recent: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Assess a single story's relevance using Pydantic AI.

    Args:
        story: News story with title, snippet, url, source, date
        app: App name (placement, relocation, rainmaker)
        app_keywords: Keywords relevant to this app
        zep_context: Existing coverage from Zep
        neon_recent: Recently published articles from Neon

    Returns:
        StoryRelevance assessment
    """
    activity.logger.info(f"Assessing story: {story.get('title', '')[:50]}...")

    # Build context for AI
    context_parts = []

    # Story info
    context_parts.append(f"STORY TO ASSESS:")
    context_parts.append(f"Title: {story.get('title', '')}")
    context_parts.append(f"Source: {story.get('source', '')}")
    context_parts.append(f"Date: {story.get('date', '')}")
    context_parts.append(f"Snippet: {story.get('snippet', '')}")
    context_parts.append(f"URL: {story.get('url', '')}")

    # App context
    context_parts.append(f"\nAPP: {app}")
    context_parts.append(f"Keywords: {', '.join(app_keywords)}")

    # Zep context (existing coverage)
    if zep_context.get("articles"):
        context_parts.append(f"\nEXISTING COVERAGE IN ZEP ({len(zep_context['articles'])} articles):")
        for article in zep_context["articles"][:5]:
            context_parts.append(f"- {article.get('title', '')}")

    # Neon context (recently published)
    if neon_recent:
        context_parts.append(f"\nRECENTLY PUBLISHED ({len(neon_recent)} articles):")
        for article in neon_recent[:5]:
            context_parts.append(f"- {article.get('title', '')} ({article.get('published_at', '')})")

    # Related entities from Zep
    if zep_context.get("companies"):
        context_parts.append(f"\nKNOWN COMPANIES: {', '.join([c.get('name', '') for c in zep_context['companies'][:10]])}")

    if zep_context.get("deals"):
        context_parts.append(f"\nKNOWN DEALS: {', '.join([d.get('name', '') for d in zep_context['deals'][:10]])}")

    prompt = "\n".join(context_parts)

    try:
        # Run AI assessment
        agent = get_news_assessment_agent()
        result = await agent.run(prompt)

        assessment = result.data.model_dump()
        assessment["story"] = story

        activity.logger.info(
            f"Assessment: relevant={assessment['is_relevant']}, "
            f"type={assessment['story_type']}, "
            f"priority={assessment['priority']}"
        )

        return assessment

    except Exception as e:
        activity.logger.error(f"Assessment failed: {str(e)}")
        return {
            "is_relevant": False,
            "relevance_score": 0.0,
            "story_type": "new",
            "priority": "low",
            "reasoning": f"Assessment failed: {str(e)}",
            "story": story,
            "error": str(e)
        }


@activity.defn
async def assess_news_batch(
    stories: List[Dict[str, Any]],
    app: str,
    app_keywords: List[str],
    zep_context: Dict[str, Any],
    neon_recent: List[Dict[str, Any]],
    min_relevance_score: float = 0.6
) -> Dict[str, Any]:
    """
    Assess a batch of news stories for relevance.

    Args:
        stories: List of news stories
        app: App name
        app_keywords: Keywords for this app
        zep_context: Existing Zep context
        neon_recent: Recently published articles
        min_relevance_score: Minimum score to be considered relevant

    Returns:
        NewsAssessmentResult with relevant and skipped stories
    """
    activity.logger.info(f"Assessing {len(stories)} stories for app: {app}")

    relevant_stories = []
    skipped_stories = []

    high_priority = 0
    medium_priority = 0
    low_priority = 0

    for story in stories:
        assessment = await assess_story_relevance(
            story=story,
            app=app,
            app_keywords=app_keywords,
            zep_context=zep_context,
            neon_recent=neon_recent
        )

        if assessment.get("is_relevant") and assessment.get("relevance_score", 0) >= min_relevance_score:
            relevant_stories.append(assessment)

            priority = assessment.get("priority", "low")
            if priority == "high":
                high_priority += 1
            elif priority == "medium":
                medium_priority += 1
            else:
                low_priority += 1
        else:
            skipped_stories.append(assessment)

    activity.logger.info(
        f"Assessment complete: {len(relevant_stories)} relevant, "
        f"{len(skipped_stories)} skipped "
        f"(high={high_priority}, medium={medium_priority}, low={low_priority})"
    )

    return {
        "stories_assessed": len(stories),
        "relevant_stories": relevant_stories,
        "skipped_stories": skipped_stories,
        "app": app,
        "total_high_priority": high_priority,
        "total_medium_priority": medium_priority,
        "total_low_priority": low_priority
    }


# ============================================================================
# CHECK NEON FOR RECENT ARTICLES
# ============================================================================

@activity.defn
async def get_recent_articles_from_neon(
    app: str,
    days: int = 7,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get recently published articles from Neon database.

    Used to avoid duplicate coverage.

    Args:
        app: App name
        days: How many days back to check
        limit: Maximum articles to return

    Returns:
        List of recent articles
    """
    import psycopg
    from datetime import datetime, timedelta

    activity.logger.info(f"Fetching recent articles for {app} (last {days} days)")

    if not config.DATABASE_URL:
        activity.logger.warning("DATABASE_URL not configured")
        return []

    try:
        async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                cutoff = datetime.utcnow() - timedelta(days=days)

                await cur.execute(
                    """
                    SELECT id, title, slug, article_type, published_at
                    FROM articles
                    WHERE app = %s
                    AND published_at >= %s
                    ORDER BY published_at DESC
                    LIMIT %s
                    """,
                    (app, cutoff, limit)
                )

                rows = await cur.fetchall()

                articles = []
                for row in rows:
                    articles.append({
                        "id": str(row[0]),
                        "title": row[1],
                        "slug": row[2],
                        "article_type": row[3],
                        "published_at": row[4].isoformat() if row[4] else None
                    })

                activity.logger.info(f"Found {len(articles)} recent articles")
                return articles

    except Exception as e:
        activity.logger.error(f"Failed to fetch recent articles: {str(e)}")
        return []
