"""
Phoenix Streamlit Dashboard

Dual-mode interface for content creation:
- Companies: URL-focused profile generation
- Articles: Topic-focused research and writing
- News Monitor: Scheduled news monitoring status
"""

import os
import streamlit as st
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

# Page config
st.set_page_config(
    page_title="Phoenix Content Engine",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# API HELPERS
# ============================================================================

def make_api_request(method: str, endpoint: str, **kwargs):
    """Make authenticated API request to gateway."""
    headers = kwargs.pop("headers", {})
    if API_KEY:
        headers["X-API-Key"] = API_KEY

    url = f"{GATEWAY_URL}{endpoint}"

    try:
        response = requests.request(method, url, headers=headers, **kwargs)
        return response
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return None


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Header
    st.title("🔥 Phoenix Content Engine")
    st.markdown("AI-powered content generation with Zep-first architecture")

    # Sidebar
    with st.sidebar:
        st.header("Configuration")

        # Gateway URL
        gateway_url = st.text_input(
            "Gateway URL",
            value=GATEWAY_URL,
            help="Phoenix Gateway API URL"
        )

        # API Key
        api_key = st.text_input(
            "API Key",
            value=API_KEY,
            type="password",
            help="Gateway API key"
        )

        # Health check
        if st.button("Check Connection"):
            try:
                response = requests.get(f"{gateway_url}/health", timeout=5)
                if response.status_code == 200:
                    st.success("Connected!")
                else:
                    st.error(f"Error: {response.status_code}")
            except Exception as e:
                st.error(f"Failed: {str(e)}")

        st.divider()

        st.markdown("### Quick Links")
        st.markdown(f"[API Docs]({gateway_url}/docs)")
        st.markdown("[Temporal Cloud](https://cloud.temporal.io)")

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🏢 Companies", "📰 Articles", "📡 News Monitor"])

    # ========================================================================
    # TAB 1: COMPANIES
    # ========================================================================
    with tab1:
        st.header("Create Company Profile")
        st.markdown("Generate comprehensive company profiles by crawling websites and researching activities")

        col1, col2 = st.columns([2, 1])

        with col1:
            company_url = st.text_input(
                "Company Website URL",
                placeholder="https://evercore.com",
                help="Main website URL of the company"
            )

        with col2:
            company_category = st.selectbox(
                "Category",
                [
                    "placement_agent",
                    "relocation_provider",
                    "chief_of_staff",
                    "investment_bank",
                    "other"
                ],
                help="Company type"
            )

        col3, col4, col5 = st.columns(3)

        with col3:
            company_jurisdiction = st.selectbox(
                "Jurisdiction",
                ["UK", "US", "EU", "Global"],
                help="Primary jurisdiction"
            )

        with col4:
            company_app = st.selectbox(
                "App",
                ["placement", "relocation", "chief-of-staff", "rainmaker"],
                help="Which app is this for?"
            )

        with col5:
            company_force = st.checkbox(
                "Force Update",
                help="Re-generate even if company exists"
            )

        # Advanced options
        with st.expander("⚙️ Advanced Research Options"):
            col_a, col_b = st.columns(2)

            with col_a:
                company_max_urls = st.slider(
                    "Max URLs to Crawl",
                    min_value=5,
                    max_value=30,
                    value=15,
                    help="Maximum articles to crawl from Serper"
                )

            with col_b:
                company_use_exa = st.checkbox(
                    "Use Exa (optional)",
                    value=False,
                    help="Enable Exa for additional research (+$0.04)"
                )

        if st.button("🚀 Create Company Profile", type="primary", key="company_btn"):
            if not company_url:
                st.error("Please enter a company URL")
            else:
                with st.spinner("Creating company profile... (90-150 seconds)"):
                    response = make_api_request(
                        "POST",
                        "/api/v1/workflows/companies",
                        json={
                            "url": company_url,
                            "category": company_category,
                            "jurisdiction": company_jurisdiction,
                            "app": company_app,
                            "force_update": company_force,
                            "max_crawl_urls": company_max_urls,
                            "use_exa": company_use_exa
                        },
                        timeout=180
                    )

                    if response and response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Workflow started: {result.get('workflow_id')}")
                        st.info(f"Task Queue: {result.get('task_queue')}")

                        # Show link to Temporal
                        st.markdown(
                            f"[View in Temporal Cloud]"
                            f"(https://cloud.temporal.io/namespaces/quickstart-quest.zivkb/"
                            f"workflows/{result.get('workflow_id')})"
                        )
                    elif response:
                        st.error(f"Error: {response.text}")

    # ========================================================================
    # TAB 2: ARTICLES
    # ========================================================================
    with tab2:
        st.header("Create Article")
        st.markdown("Generate comprehensive articles through deep research (no URL required)")

        article_topic = st.text_area(
            "Article Topic / Title",
            placeholder="Vista Equity Partners acquires Plural Platform for $90M",
            help="Describe what the article should be about",
            height=100
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            article_type = st.selectbox(
                "Article Type",
                ["news", "analysis", "deep_dive", "profile"],
                help="What kind of article?"
            )

        with col2:
            article_app = st.selectbox(
                "App",
                ["placement", "relocation", "chief-of-staff", "rainmaker"],
                help="Which app is this for?",
                key="article_app"
            )

        with col3:
            article_depth = st.select_slider(
                "Research Depth",
                options=["quick", "standard", "deep"],
                value="deep",
                help="Deep research recommended for articles"
            )

        # Advanced options
        with st.expander("⚙️ Advanced Research Options"):
            article_max_sources = st.slider(
                "Max Sources to Research",
                min_value=10,
                max_value=50,
                value=30,
                help="Maximum sources to crawl"
            )

            article_priority = st.multiselect(
                "Priority Sources (optional)",
                ["Reuters", "Bloomberg", "TechCrunch", "CNBC", "Forbes", "PE Hub", "PitchBook"],
                help="Prioritize these sources if found"
            )

            article_exclude_paywalls = st.checkbox(
                "Exclude Paywalled Content",
                value=True,
                help="Skip WSJ, FT, Economist, etc."
            )

        if st.button("📰 Create Article", type="primary", key="article_btn"):
            if not article_topic:
                st.error("Please enter an article topic")
            else:
                with st.spinner("Creating article... (5-12 minutes)"):
                    response = make_api_request(
                        "POST",
                        "/api/v1/workflows/articles",
                        json={
                            "topic": article_topic,
                            "article_type": article_type,
                            "app": article_app,
                            "research_depth": article_depth,
                            "max_sources": article_max_sources,
                            "priority_sources": article_priority,
                            "exclude_paywalls": article_exclude_paywalls
                        },
                        timeout=180
                    )

                    if response and response.status_code == 200:
                        result = response.json()
                        st.success(f"✅ Workflow started: {result.get('workflow_id')}")
                        st.info("Article generation takes 5-12 minutes")

                        st.markdown(
                            f"[View in Temporal Cloud]"
                            f"(https://cloud.temporal.io/namespaces/quickstart-quest.zivkb/"
                            f"workflows/{result.get('workflow_id')})"
                        )
                    elif response:
                        st.error(f"Error: {response.text}")

    # ========================================================================
    # TAB 3: NEWS MONITOR
    # ========================================================================
    with tab3:
        st.header("News Monitor")
        st.markdown("AI-powered news monitoring that automatically creates articles")

        st.info(
            "News Monitor workflows are typically scheduled in Temporal Cloud. "
            "Use this tab to manually trigger monitoring or view status."
        )

        # Manual trigger
        st.subheader("Manual Trigger")

        col1, col2 = st.columns(2)

        with col1:
            monitor_app = st.selectbox(
                "App to Monitor",
                ["placement", "relocation", "chief-of-staff", "rainmaker"],
                key="monitor_app"
            )

        with col2:
            monitor_max = st.slider(
                "Max Articles to Create",
                min_value=1,
                max_value=10,
                value=3,
                help="Maximum articles to auto-create"
            )

        monitor_relevance = st.slider(
            "Minimum Relevance Score",
            min_value=0.5,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="Only create articles above this relevance threshold"
        )

        if st.button("🔍 Run News Monitor", type="primary", key="monitor_btn"):
            st.warning("News Monitor endpoint not yet implemented in Gateway")
            st.info(
                "To run manually, use Temporal Cloud UI to start:\n"
                f"- Workflow: NewsMonitorWorkflow\n"
                f"- Input: {{\"app\": \"{monitor_app}\", \"max_articles_to_create\": {monitor_max}}}"
            )

        st.divider()

        # App keywords reference
        st.subheader("App Keywords Reference")

        keywords_data = {
            "placement": ["placement agent", "fund placement", "capital raising", "LP commitment"],
            "relocation": ["corporate relocation", "employee mobility", "global mobility", "expat"],
            "rainmaker": ["rainmaker", "dealmaker", "investment banking", "M&A advisor"],
            "chief-of-staff": ["chief of staff", "executive operations", "CEO office"]
        }

        for app, keywords in keywords_data.items():
            with st.expander(f"📋 {app.title()} Keywords"):
                for kw in keywords:
                    st.markdown(f"- {kw}")

        st.divider()

        # Scheduling info
        st.subheader("Scheduling in Temporal Cloud")
        st.markdown("""
        To schedule automatic daily monitoring:

        1. Go to [Temporal Cloud](https://cloud.temporal.io)
        2. Navigate to your namespace
        3. Create a Schedule:
           - Workflow: `NewsMonitorAllAppsWorkflow`
           - Cron: `0 8 * * *` (8 AM daily)
           - Input: `{"apps": ["placement", "relocation"], "max_articles_per_app": 3}`

        This will automatically:
        - Check news for all specified apps
        - Use AI to assess relevance
        - Create articles for high-priority stories
        """)


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    main()
