"""
Neon Database Storage Activities

Save companies and articles to Neon PostgreSQL database.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import psycopg
from temporalio import activity

from config import config


# ============================================================================
# DATABASE SCHEMA SETUP
# ============================================================================

COMPANIES_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    domain TEXT,
    category TEXT,
    app TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    description TEXT,
    website_url TEXT,
    logo_url TEXT,
    featured_image_url TEXT,
    hero_image_url TEXT,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_companies_app ON companies(app);
CREATE INDEX IF NOT EXISTS idx_companies_slug ON companies(slug);
CREATE INDEX IF NOT EXISTS idx_companies_domain ON companies(domain);
CREATE INDEX IF NOT EXISTS idx_companies_created ON companies(created_at DESC);
"""

ARTICLES_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    article_type TEXT,
    app TEXT NOT NULL,
    status TEXT DEFAULT 'draft',
    summary TEXT,
    featured_image_url TEXT,
    payload JSONB,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_app_published ON articles(app, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_slug ON articles(slug);
CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_type ON articles(article_type);
"""


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

@activity.defn
async def init_database_schema() -> Dict[str, Any]:
    """
    Initialize database schema with companies and articles tables.

    This should be run once during setup.

    Returns:
        Dict with status and tables created
    """
    activity.logger.info("Initializing database schema")

    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")

    try:
        async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                # Create companies table
                await cur.execute(COMPANIES_TABLE_SCHEMA)
                activity.logger.info("Companies table created/verified")

                # Create articles table
                await cur.execute(ARTICLES_TABLE_SCHEMA)
                activity.logger.info("Articles table created/verified")

                await conn.commit()

        activity.logger.info("Database schema initialized successfully")
        return {
            "status": "success",
            "tables_created": ["companies", "articles"]
        }

    except Exception as e:
        activity.logger.error(f"Failed to initialize database: {str(e)}")
        raise


# ============================================================================
# COMPANY STORAGE
# ============================================================================

@activity.defn
async def save_company_to_neon(
    company_payload: Dict[str, Any],
    status: str = "draft"
) -> Dict[str, Any]:
    """
    Save company profile to Neon database.

    Args:
        company_payload: CompanyPayload as dict
        status: Company status (draft, published, archived)

    Returns:
        Dict with company_id, slug, status
    """
    activity.logger.info(f"Saving company: {company_payload.get('name')}")

    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")

    # Generate UUID if not present
    company_id = company_payload.get("id") or str(uuid.uuid4())

    # Extract fields from payload
    name = company_payload.get("name", "Unknown")
    slug = company_payload.get("slug", name.lower().replace(" ", "-"))
    domain = company_payload.get("domain")
    category = company_payload.get("category", "general")
    app = company_payload.get("app", "placement")
    description = company_payload.get("meta_description")
    website_url = company_payload.get("domain")
    if website_url and not website_url.startswith("http"):
        website_url = f"https://{website_url}"
    logo_url = company_payload.get("logo_url")
    featured_image_url = company_payload.get("featured_image_url")
    hero_image_url = company_payload.get("hero_image_url")

    try:
        async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                # Check if company with this slug already exists
                await cur.execute(
                    "SELECT id FROM companies WHERE slug = %s",
                    (slug,)
                )
                existing = await cur.fetchone()

                if existing:
                    # Update existing company
                    await cur.execute(
                        """
                        UPDATE companies SET
                            name = %s,
                            domain = %s,
                            category = %s,
                            app = %s,
                            status = %s,
                            description = %s,
                            website_url = %s,
                            logo_url = %s,
                            featured_image_url = %s,
                            hero_image_url = %s,
                            payload = %s,
                            updated_at = NOW()
                        WHERE slug = %s
                        RETURNING id
                        """,
                        (
                            name, domain, category, app, status,
                            description, website_url, logo_url,
                            featured_image_url, hero_image_url,
                            json.dumps(company_payload), slug
                        )
                    )
                    company_id = str((await cur.fetchone())[0])
                    operation = "updated"

                else:
                    # Insert new company
                    await cur.execute(
                        """
                        INSERT INTO companies (
                            id, slug, name, domain, category, app, status,
                            description, website_url, logo_url,
                            featured_image_url, hero_image_url, payload
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        RETURNING id
                        """,
                        (
                            company_id, slug, name, domain, category, app, status,
                            description, website_url, logo_url,
                            featured_image_url, hero_image_url,
                            json.dumps(company_payload)
                        )
                    )
                    company_id = str((await cur.fetchone())[0])
                    operation = "created"

                await conn.commit()

        activity.logger.info(f"Company {operation}: {slug} (id: {company_id})")

        return {
            "company_id": company_id,
            "slug": slug,
            "name": name,
            "operation": operation,
            "status": status
        }

    except Exception as e:
        activity.logger.error(f"Failed to save company: {str(e)}")
        raise


@activity.defn
async def get_company_from_neon(
    identifier: str,
    by: str = "slug"
) -> Optional[Dict[str, Any]]:
    """
    Get company from Neon database.

    Args:
        identifier: Company slug, ID, or domain
        by: Field to search by (slug, id, domain)

    Returns:
        Company record or None
    """
    activity.logger.info(f"Getting company by {by}: {identifier}")

    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")

    try:
        async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                if by == "slug":
                    await cur.execute(
                        "SELECT * FROM companies WHERE slug = %s",
                        (identifier,)
                    )
                elif by == "id":
                    await cur.execute(
                        "SELECT * FROM companies WHERE id = %s::uuid",
                        (identifier,)
                    )
                elif by == "domain":
                    await cur.execute(
                        "SELECT * FROM companies WHERE domain = %s",
                        (identifier,)
                    )
                else:
                    raise ValueError(f"Invalid search field: {by}")

                row = await cur.fetchone()

                if row:
                    # Get column names
                    columns = [desc[0] for desc in cur.description]
                    company = dict(zip(columns, row))

                    # Convert UUID and datetime to strings
                    company["id"] = str(company["id"])
                    if company.get("created_at"):
                        company["created_at"] = company["created_at"].isoformat()
                    if company.get("updated_at"):
                        company["updated_at"] = company["updated_at"].isoformat()

                    return company

                return None

    except Exception as e:
        activity.logger.error(f"Failed to get company: {str(e)}")
        raise


# ============================================================================
# ARTICLE STORAGE
# ============================================================================

@activity.defn
async def save_article_to_neon(
    article_payload: Dict[str, Any],
    status: str = "draft",
    publish: bool = False
) -> Dict[str, Any]:
    """
    Save article to Neon database.

    Uses Quest's existing schema with columns:
    - id (serial), slug, title, content, status, app
    - excerpt, article_angle, word_count, meta_description
    - featured_image_url, payload, published_at, etc.

    Args:
        article_payload: ArticlePayload as dict
        status: Article status (draft, published, archived)
        publish: Whether to set published_at timestamp

    Returns:
        Dict with article_id, slug, status
    """
    activity.logger.info(f"Saving article: {article_payload.get('title')}")

    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")

    # Extract fields from payload - map to Quest schema
    title = article_payload.get("title", "Untitled")
    slug = article_payload.get("slug", title.lower().replace(" ", "-")[:100])
    content = article_payload.get("content", "")
    app = article_payload.get("app", "placement")

    # Map Phoenix fields to Quest schema
    excerpt = article_payload.get("summary") or article_payload.get("meta_description", "")
    article_angle = article_payload.get("article_type", "news")  # Quest uses article_angle
    word_count = article_payload.get("word_count", len(content.split()) if content else 0)
    meta_description = article_payload.get("meta_description", "")
    featured_image_url = article_payload.get("featured_image_url")

    # Set published_at if publishing
    published_at = None
    if publish or status == "published":
        published_at = datetime.utcnow()
        status = "published"

    try:
        async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                # Check if article with this slug already exists
                await cur.execute(
                    "SELECT id FROM articles WHERE slug = %s",
                    (slug,)
                )
                existing = await cur.fetchone()

                if existing:
                    # Update existing article
                    await cur.execute(
                        """
                        UPDATE articles SET
                            title = %s,
                            content = %s,
                            app = %s,
                            status = %s,
                            excerpt = %s,
                            article_angle = %s,
                            word_count = %s,
                            meta_description = %s,
                            featured_image_url = %s,
                            payload = %s,
                            published_at = COALESCE(%s, published_at),
                            updated_at = NOW()
                        WHERE slug = %s
                        RETURNING id
                        """,
                        (
                            title, content, app, status,
                            excerpt, article_angle, word_count,
                            meta_description, featured_image_url,
                            json.dumps(article_payload),
                            published_at, slug
                        )
                    )
                    article_id = str((await cur.fetchone())[0])
                    operation = "updated"

                else:
                    # Insert new article - let PostgreSQL auto-generate id
                    await cur.execute(
                        """
                        INSERT INTO articles (
                            slug, title, content, app, status,
                            excerpt, article_angle, word_count,
                            meta_description, featured_image_url,
                            payload, published_at, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
                        )
                        RETURNING id
                        """,
                        (
                            slug, title, content, app, status,
                            excerpt, article_angle, word_count,
                            meta_description, featured_image_url,
                            json.dumps(article_payload), published_at
                        )
                    )
                    article_id = str((await cur.fetchone())[0])
                    operation = "created"

                await conn.commit()

        activity.logger.info(f"Article {operation}: {slug} (id: {article_id})")

        return {
            "article_id": article_id,
            "slug": slug,
            "title": title,
            "operation": operation,
            "status": status,
            "published_at": published_at.isoformat() if published_at else None
        }

    except Exception as e:
        activity.logger.error(f"Failed to save article: {str(e)}")
        raise


@activity.defn
async def get_article_from_neon(
    identifier: str,
    by: str = "slug"
) -> Optional[Dict[str, Any]]:
    """
    Get article from Neon database.

    Args:
        identifier: Article slug or ID
        by: Field to search by (slug, id)

    Returns:
        Article record or None
    """
    activity.logger.info(f"Getting article by {by}: {identifier}")

    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")

    try:
        async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                if by == "slug":
                    await cur.execute(
                        "SELECT * FROM articles WHERE slug = %s",
                        (identifier,)
                    )
                elif by == "id":
                    await cur.execute(
                        "SELECT * FROM articles WHERE id = %s::uuid",
                        (identifier,)
                    )
                else:
                    raise ValueError(f"Invalid search field: {by}")

                row = await cur.fetchone()

                if row:
                    # Get column names
                    columns = [desc[0] for desc in cur.description]
                    article = dict(zip(columns, row))

                    # Convert UUID and datetime to strings
                    article["id"] = str(article["id"])
                    if article.get("created_at"):
                        article["created_at"] = article["created_at"].isoformat()
                    if article.get("updated_at"):
                        article["updated_at"] = article["updated_at"].isoformat()
                    if article.get("published_at"):
                        article["published_at"] = article["published_at"].isoformat()

                    return article

                return None

    except Exception as e:
        activity.logger.error(f"Failed to get article: {str(e)}")
        raise


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

@activity.defn
async def list_companies_from_neon(
    app: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List companies from Neon database.

    Args:
        app: Filter by app
        status: Filter by status
        limit: Maximum records
        offset: Offset for pagination

    Returns:
        Dict with companies and total count
    """
    activity.logger.info(f"Listing companies (app={app}, status={status})")

    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")

    try:
        async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                # Build query
                query = "SELECT id, slug, name, domain, app, status, created_at FROM companies"
                params = []
                conditions = []

                if app:
                    conditions.append("app = %s")
                    params.append(app)

                if status:
                    conditions.append("status = %s")
                    params.append(status)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                await cur.execute(query, params)
                rows = await cur.fetchall()

                companies = []
                for row in rows:
                    companies.append({
                        "id": str(row[0]),
                        "slug": row[1],
                        "name": row[2],
                        "domain": row[3],
                        "app": row[4],
                        "status": row[5],
                        "created_at": row[6].isoformat() if row[6] else None
                    })

                # Get total count
                count_query = "SELECT COUNT(*) FROM companies"
                if conditions:
                    count_query += " WHERE " + " AND ".join(conditions)

                await cur.execute(count_query, params[:-2] if conditions else [])
                total = (await cur.fetchone())[0]

                return {
                    "companies": companies,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }

    except Exception as e:
        activity.logger.error(f"Failed to list companies: {str(e)}")
        raise


@activity.defn
async def list_articles_from_neon(
    app: str = None,
    status: str = None,
    article_type: str = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List articles from Neon database.

    Args:
        app: Filter by app
        status: Filter by status
        article_type: Filter by type
        limit: Maximum records
        offset: Offset for pagination

    Returns:
        Dict with articles and total count
    """
    activity.logger.info(f"Listing articles (app={app}, status={status}, type={article_type})")

    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL not configured")

    try:
        async with await psycopg.AsyncConnection.connect(config.DATABASE_URL) as conn:
            async with conn.cursor() as cur:
                # Build query
                query = """
                    SELECT id, slug, title, article_type, app, status,
                           published_at, created_at
                    FROM articles
                """
                params = []
                conditions = []

                if app:
                    conditions.append("app = %s")
                    params.append(app)

                if status:
                    conditions.append("status = %s")
                    params.append(status)

                if article_type:
                    conditions.append("article_type = %s")
                    params.append(article_type)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                await cur.execute(query, params)
                rows = await cur.fetchall()

                articles = []
                for row in rows:
                    articles.append({
                        "id": str(row[0]),
                        "slug": row[1],
                        "title": row[2],
                        "article_type": row[3],
                        "app": row[4],
                        "status": row[5],
                        "published_at": row[6].isoformat() if row[6] else None,
                        "created_at": row[7].isoformat() if row[7] else None
                    })

                # Get total count
                count_query = "SELECT COUNT(*) FROM articles"
                if conditions:
                    count_query += " WHERE " + " AND ".join(conditions)

                await cur.execute(count_query, params[:-2] if conditions else [])
                total = (await cur.fetchone())[0]

                return {
                    "articles": articles,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                }

    except Exception as e:
        activity.logger.error(f"Failed to list articles: {str(e)}")
        raise
