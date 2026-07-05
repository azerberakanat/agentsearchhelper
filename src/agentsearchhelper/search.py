import os
import requests
from typing import List, Dict, Any

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080").rstrip("/")

def query_searxng(
    query: str,
    max_results: int = 3,
    time_range: str = None,
    categories: str = None,
    engines: str = None,
    language: str = None,
) -> List[Dict[str, Any]]:
    """Query local SearXNG and return the top search results.

    Each result is a dictionary containing:
        - title: The page title
        - url: The page URL
        - snippet: Brief description snippet
    """
    url = f"{SEARXNG_URL}/search"
    params = {
        "q": query,
        "format": "json"
    }
    if time_range:
        params["time_range"] = time_range
    if categories:
        params["categories"] = categories
    if engines:
        params["engines"] = engines
    if language:
        params["language"] = language

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        formatted_results = []
        
        for r in results[:max_results]:
            formatted_results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")
            })
            
        return formatted_results
    except Exception as e:
        # Return empty list or raise depending on preferences. Let's raise with context.
        raise RuntimeError(f"Failed to query SearXNG at {url}. Is the service running? Details: {e}")
