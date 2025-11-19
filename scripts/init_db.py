#!/usr/bin/env python3
"""
Initialize Phoenix database schema in Neon.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in environment")
    sys.exit(1)

SCHEMA = """
-- Companies table
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

-- Articles table
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


async def init_database():
    import psycopg

    print("Initializing Phoenix database schema...")
    print(f"Database: {DATABASE_URL[:50]}...")

    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            await cur.execute(SCHEMA)
            await conn.commit()

    print("Schema initialized successfully!")
    print("Tables created: companies, articles")


if __name__ == "__main__":
    asyncio.run(init_database())
