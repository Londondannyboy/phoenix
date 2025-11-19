#!/usr/bin/env python3
"""
Debug script to check Neon database for Phoenix articles and companies.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'worker'))

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in environment")
    sys.exit(1)


async def check_database():
    import psycopg

    print("=" * 60)
    print("Phoenix Database Debug")
    print("=" * 60)
    print(f"\nConnecting to: {DATABASE_URL[:50]}...")

    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        async with conn.cursor() as cur:
            # Check if tables exist
            print("\n1. Checking tables...")
            await cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('articles', 'companies')
            """)
            tables = await cur.fetchall()

            if not tables:
                print("   WARNING: No Phoenix tables found!")
                print("   Tables 'articles' and 'companies' do not exist.")
                print("\n   To create them, run:")
                print("   python scripts/init_db.py")
                return

            table_names = [t[0] for t in tables]
            print(f"   Found tables: {', '.join(table_names)}")

            # Check articles
            if 'articles' in table_names:
                print("\n2. Checking articles...")
                await cur.execute("SELECT COUNT(*) FROM articles")
                count = (await cur.fetchone())[0]
                print(f"   Total articles: {count}")

                if count > 0:
                    await cur.execute("""
                        SELECT id, slug, title, status, article_type,
                               published_at, created_at
                        FROM articles
                        ORDER BY created_at DESC
                        LIMIT 10
                    """)
                    articles = await cur.fetchall()

                    print("\n   Recent articles:")
                    for a in articles:
                        status = a[3] or 'unknown'
                        pub = a[5].strftime('%Y-%m-%d %H:%M') if a[5] else 'not published'
                        created = a[6].strftime('%Y-%m-%d %H:%M') if a[6] else 'unknown'
                        print(f"   - [{status}] {a[2][:50]}")
                        print(f"     ID: {a[0]}")
                        print(f"     Slug: {a[1]}")
                        print(f"     Type: {a[4]}, Published: {pub}, Created: {created}")
                        print()
                else:
                    print("   No articles found in database.")

            # Check companies
            if 'companies' in table_names:
                print("\n3. Checking companies...")
                await cur.execute("SELECT COUNT(*) FROM companies")
                count = (await cur.fetchone())[0]
                print(f"   Total companies: {count}")

                if count > 0:
                    await cur.execute("""
                        SELECT id, slug, name, status, app, created_at
                        FROM companies
                        ORDER BY created_at DESC
                        LIMIT 5
                    """)
                    companies = await cur.fetchall()

                    print("\n   Recent companies:")
                    for c in companies:
                        status = c[3] or 'unknown'
                        created = c[5].strftime('%Y-%m-%d %H:%M') if c[5] else 'unknown'
                        print(f"   - [{status}] {c[2]}")
                        print(f"     ID: {c[0]}, Slug: {c[1]}, App: {c[4]}")
                        print(f"     Created: {created}")
                        print()

    print("=" * 60)
    print("Debug complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(check_database())
