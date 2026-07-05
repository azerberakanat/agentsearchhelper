import requests
import trafilatura
from typing import Optional

# Initialize a thread-safe Session with connection pooling
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
session.mount("http://", adapter)
session.mount("https://", adapter)

def scrape_url(url: str) -> Optional[str]:
    """Download a webpage and extract its clean main text.

    Returns the clean text content as a string, or None if download/extraction fails.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    try:
        response = session.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
            
        # extract text using trafilatura
        text = trafilatura.extract(response.text, include_comments=False, include_tables=True)
        return text
    except Exception:
        return None
