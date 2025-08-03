"""jobs.search_api
Utility functions for job searches (Google Jobs via SerpAPI and fallback sources).
All external API logic is kept here to keep app.py focused on UI/orchestration.
"""
from __future__ import annotations

import datetime
import os
from typing import List, Dict

import feedparser
import httpx
from serpapi.google_search import GoogleSearch

__all__ = [
    "fetch_google_jobs_serpapi",
    "enhanced_jobicy_search",
]

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _get_serpapi_key() -> str | None:
    """Return SerpAPI key from Streamlit secrets or environment.
    Kept internal so Streamlit isn't a hard dependency for downstream callers.
    """
    # Late import to avoid unnecessary dependency for callers that don't use Streamlit
    try:
        import streamlit as st  # type: ignore

        key = st.secrets.get("SERPAPI_KEY", os.getenv("SERPAPI_KEY"))  # noqa: SLF001
    except Exception:
        key = os.getenv("SERPAPI_KEY")
    return key

# ---------------------------------------------------------------------------
# Google Jobs – SerpAPI implementation
# ---------------------------------------------------------------------------

def fetch_google_jobs_serpapi(
    detected_roles: Dict[str, list | str],
    location: str = "Remote",
    limit: int = 15,
) -> List[Dict[str, str]]:
    """Fetch job listings from Google Jobs using SerpAPI.

    Parameters
    ----------
    detected_roles : dict
        Output from detect_suitable_job_roles (primary_role, alternative_roles, career_level, …)
    location : str, optional
        Location query (default "Remote").
    limit : int, optional
        Max number of jobs to return.
    """
    api_key = _get_serpapi_key()
    if not api_key:
        return []

    # Build list of queries
    queries: list[str] = [
        str(detected_roles.get("primary_role", "")),
        f"{detected_roles.get('primary_role', '')} {str(detected_roles.get('career_level', '')).lower()}",
    ]
    queries.extend(detected_roles.get("alternative_roles", [])[:2])
    queries.extend(detected_roles.get("recommended_keywords", [])[:2])

    all_jobs: list[Dict[str, str]] = []

    for query in filter(None, queries):
        if len(all_jobs) >= limit:
            break

        params = {
            "engine": "google_jobs",
            "q": f"{query} remote",
            "hl": "en",
            "gl": "us",
            "api_key": api_key,
            "no_cache": False,
        }
        # Only include location if not set to 'Remote' to avoid unsupported error
        if location.strip().lower() != "remote":
            params["location"] = location
        try:
            res = GoogleSearch(params).get_dict()
            if "error" in res:  # quota errors, etc.
                continue
            for job in res.get("jobs_results", []):
                if len(all_jobs) >= limit:
                    break
                                # Prefer original listing link; fall back to any available URL so the UI always has something clickable.
                link = (
                    (job.get("related_links") or [{}])[0].get("link")
                    or job.get("apply_options", [{}])[0].get("link")
                    or job.get("search_link")
                    or job.get("apply_link")
                    or job.get("link")
                )

                jd = {
                    "title": job.get("title"),
                    "company": job.get("company_name"),
                    "location": job.get("location"),
                    "link": link,
                    "posted": job.get("detected_extensions", {}).get("posted_at"),
                    "schedule_type": job.get("detected_extensions", {}).get("schedule_type"),
                    "via": job.get("via"),
                    "match_reason": f"Matches: {query}",
                }
                if not any(
                    jd["title"] == e["title"] and jd["company"] == e["company"] for e in all_jobs
                ):
                    all_jobs.append(jd)
        except Exception:
            continue

    return all_jobs[:limit]

# ---------------------------------------------------------------------------
# Jobicy fallback search (no API key)
# ---------------------------------------------------------------------------

_RSS_FEEDS = [
    "https://weworkremotely.com/remote-programming-jobs.rss",
    "https://himalayas.app/jobs.rss",
]


def enhanced_jobicy_search(detected_roles: Dict[str, list | str], limit: int = 10):
    """Search Jobicy and RSS feeds using AI-recommended keywords."""

    search_terms: list[str] = [str(detected_roles.get("primary_role", ""))]
    search_terms.extend(detected_roles.get("recommended_keywords", []) or [])

    matched: list[Dict[str, str]] = []

    # Jobicy API
    try:
        data = (
            httpx.get("https://jobs.jobicy.com/api/v2/remote-jobs", timeout=15)
            .json()
            .get("jobs", [])
        )
        cutoff = datetime.date.today() - datetime.timedelta(days=30)
        for job in data:
            pub = datetime.date.fromisoformat(job["published_at"][:10])
            if pub < cutoff:
                continue
            content = (job.get("title", "") + " " + job.get("description", "")).lower()
            for term in search_terms:
                if term.lower() in content:
                    matched.append(
                        {
                            "url": job["url"],
                            "title": job["title"],
                            "company": job.get("company_name", "Unknown"),
                            "match_reason": f"Matches: {term}",
                        }
                    )
                    break
    except Exception:
        pass

    # RSS feeds fallback
    try:
        cutoff = datetime.date.today() - datetime.timedelta(days=30)
        for rss in _RSS_FEEDS:
            feed = feedparser.parse(rss)
            for entry in feed.entries:
                pub_dt = datetime.datetime.strptime(entry.published, "%a, %d %b %Y %H:%M:%S %z").date()
                if pub_dt < cutoff:
                    continue
                title_lower = entry.title.lower()
                for term in search_terms:
                    if term.lower() in title_lower:
                        matched.append({"url": entry.link, "title": entry.title, "company": "Remote", "match_reason": f"Matches: {term}"})
                        break
    except Exception:
        pass

    return matched[:limit]
