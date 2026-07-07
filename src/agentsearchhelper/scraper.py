# scraper.py
import requests
import trafilatura
from typing import Optional
from urllib.parse import urljoin, urlparse

# Initialize a thread-safe Session with connection pooling
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10)
session.mount("http://", adapter)
session.mount("https://", adapter)

def clean_and_validate_url(base_url: str, href: str) -> Optional[str]:
    """Resolve, strip fragments, and filter invalid URLs/assets."""
    try:
        # Resolve relative links
        resolved_url = urljoin(base_url, href)
        parsed = urlparse(resolved_url)
        
        # Strip trailing slashes and normalize path
        clean_path = parsed.path
        if clean_path.endswith("/"):
            clean_path = clean_path.rstrip("/")
            
        # Ignore non-HTML static files and raw documentation assets
        ignored_extensions = (
            ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", 
            ".tar", ".gz", ".md", ".json", ".css", ".js", ".svg"
        )
        if clean_path.lower().endswith(ignored_extensions):
            return None
            
        # Reconstruct without any fragment/hash
        reconstructed = f"{parsed.scheme}://{parsed.netloc}{clean_path}"
        if parsed.query:
            reconstructed += f"?{parsed.query}"
            
        return reconstructed
    except Exception:
        return None

def scrape_url(url: str) -> Optional[str]:
    """Download a webpage and extract its clean main text."""
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
            
        text = trafilatura.extract(response.text, include_comments=False, include_tables=True)
        return text
    except Exception:
        return None

def scrape_url_with_links(url: str) -> tuple[Optional[str], list[dict]]:
    """Download a webpage, extract its clean main text and resolve internal links cleanly."""
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
            return None, []
            
        text = trafilatura.extract(response.text, include_comments=False, include_tables=True)
        
        from lxml import html
        links = []
        base_domain = urlparse(url).netloc
        
        try:
            tree = html.fromstring(response.content)
            seen_urls = set()
            for a in tree.xpath("//a[@href]"):
                href = a.get("href")
                link_text = (a.text_content() or "").strip()
                
                # Filter out empty text or structural utility/accessibility layout links
                if not link_text or len(link_text) < 2:
                    continue
                if any(skip in link_text.lower() for skip in ["skip to", "skip navigation", "geist-skip"]):
                    continue
                
                resolved_url = clean_and_validate_url(url, href)
                if not resolved_url:
                    continue
                    
                # Ensure same-domain navigation
                resolved_domain = urlparse(resolved_url).netloc
                if resolved_domain == base_domain:
                    if resolved_url not in seen_urls:
                        seen_urls.add(resolved_url)
                        links.append({
                            "url": resolved_url,
                            "text": link_text
                        })
        except Exception:
            pass
            
        return text, links
    except Exception:
        return None, []