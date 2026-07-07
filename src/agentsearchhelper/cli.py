# cli.py
import sys
import click
import time
import threading
import heapq
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

load_dotenv()

try:
    import lxml_html_clean
    sys.modules['lxml.html.clean'] = lxml_html_clean
except ImportError:
    pass

from agentsearchhelper.search import query_searxng
from agentsearchhelper.scraper import scrape_url, scrape_url_with_links
from agentsearchhelper.summarizer import summarize_text, LLM_MODEL, select_links_with_llm, check_satisfaction_with_llm

print_lock = threading.Lock()
scraped_cache = {}

def safe_echo(message, **kwargs):
    with print_lock:
        click.echo(message, **kwargs)

def scrape_source(i, total, title, url, snippet):
    if url in scraped_cache:
        return i, title, url, scraped_cache[url], 0.0

    safe_echo(f"[{i}/{total}] Scraping: {title} ({url})...")
    scrape_start = time.perf_counter()
    content = scrape_url(url)
    scrape_time = time.perf_counter() - scrape_start
    
    if not content:
        safe_echo(f"  ⚠️ [{i}/{total}] Scraping failed. Falling back to snippet.")
        content = snippet
        
    return i, title, url, content, scrape_time

@click.command()
@click.option("--query", "-q", required=True, help="The search query to execute.")
@click.option("--url", "-u", help="Direct URL to scrape and summarize.")
@click.option("--max-results", "-m", default=3, help="Maximum number of search results to crawl.")
@click.option("--model", default=LLM_MODEL, help="Local LLM model to use for summarization.")
@click.option("--time-range", "-t", type=click.Choice(["day", "week", "month", "year"]), help="Filter results by time range.")
@click.option("--category", "-c", help="Search category (e.g. general, it, news, science).")
@click.option("--engines", "-e", help="Comma-separated list of engines to query.")
@click.option("--language", "-l", help="Language code (e.g. en, fr, de).")
@click.option("--benchmark", is_flag=True, help="Show elapsed time for each phase of execution.")
@click.option("--depth", "-d", default=6, help="Maximum crawling depth for guided direct flow.")
def main(query: str, url: str, max_results: int, model: str, time_range: str, category: str, engines: str, language: str, benchmark: bool, depth: int):
    """agentsearchhelper: A local CLI tool to query SearXNG and summarize web results using a local LLM."""
    total_start = time.perf_counter()
    
    if url:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        click.echo(f"🌐 Starting Guided Link Exploration (max depth: {depth}) on URL: {url} guided by query: '{query}'...")
        
        visited = set()
        scraped_pages = []
        
        # Priority Queue for Best-First Search
        # Tuple format: (priority_score, current_depth, current_url)
        queue = []
        heapq.heappush(queue, (0, 0, url))
        
        while queue and len(scraped_pages) < depth:
            priority, current_depth, current_url = heapq.heappop(queue)
            
            if current_url in visited:
                continue
            visited.add(current_url)
            
            click.echo(f"🌐 [Depth {current_depth}/{depth}][Priority Cost {priority}] Scraping: {current_url}...")
            text, links = scrape_url_with_links(current_url)
            if not text:
                click.echo(f"  ⚠️ Scraping failed for {current_url}")
                continue
                
            scraped_cache[current_url] = text
            scraped_pages.append({
                "url": current_url,
                "text": text,
                "depth": current_depth
            })
            
            click.echo("🤔 Checking if content satisfies the query objective...")
            if check_satisfaction_with_llm(text, query, model):
                click.echo("✅ Detailed answer found! Stopping exploration loop.\n")
                break
                
            if current_depth >= depth - 1:
                click.echo(f"Reached max depth limit for branch starting at {current_url}.\n")
                continue
                
            if not links:
                click.echo(f"No more links to follow from {current_url}.\n")
                continue
                
            click.echo("🔎 Extracting and scoring internal links for next transition...")
            next_urls = select_links_with_llm(links, query, model)
            
            unvisited_next = [u for u in next_urls if u not in visited]
            for idx, next_url in enumerate(unvisited_next):
                # Backtracking Priority: Boost based on index rank
                new_priority = priority + idx + 1
                heapq.heappush(queue, (new_priority, current_depth + 1, next_url))
                
            if unvisited_next:
                click.echo(f"🔗 Guided path routing (best option added to priority queue): {unvisited_next[0]}\n")
            else:
                click.echo("No unvisited candidate links found on this page.\n")
            
        from urllib.parse import urlparse
        results = []
        for idx, page in enumerate(scraped_pages):
            path = urlparse(page["url"]).path or "/"
            depth_val = page.get("depth", idx)
            title = "Direct Webpage" if idx == 0 else f"Crawl Page (Depth {depth_val}): {path}"
            results.append({"title": title, "url": page["url"], "snippet": ""})
            
        search_time = None
    else:
        click.echo(f"🔍 Searching SearXNG for: '{query}'...")
        
        search_start = time.perf_counter()
        try:
            results = query_searxng(
                query,
                max_results=max_results,
                time_range=time_range,
                categories=category,
                engines=engines,
                language=language
            )
        except Exception as e:
            click.secho(f"Error: {e}", fg="red", err=True)
            sys.exit(1)
        search_time = time.perf_counter() - search_start
        
    if not results:
        click.echo("No search results found.")
        sys.exit(0)
        
    click.echo(f"Found {len(results)} results. Scraping pages in parallel...\n")
    
    scraped_data = []
    with ThreadPoolExecutor(max_workers=len(results)) as executor:
        futures = [
            executor.submit(scrape_source, i, len(results), res["title"], res["url"], res["snippet"])
            for i, res in enumerate(results, 1)
        ]
        for future in futures:
            try:
                scraped_data.append(future.result())
            except Exception as e:
                click.secho(f"Error scraping a source thread: {e}", fg="red", err=True)

    scraped_data.sort(key=lambda x: x[0])

    click.echo(f"\nSummarizing pages in parallel using '{model}'...\n")

    summaries = []
    citations = []
    benchmarks = []
    
    def summarize_source(i, title, url, content, scrape_time):
        safe_echo(f"[{i}/{len(results)}] Summarizing content...")
        summary_start = time.perf_counter()
        summary = summarize_text(content, query, model=model)
        summary_time = time.perf_counter() - summary_start
        return i, title, url, summary, scrape_time, summary_time

    summarized_data = []
    with ThreadPoolExecutor(max_workers=len(scraped_data)) as executor:
        futures = [
            executor.submit(summarize_source, i, title, url, content, scrape_time)
            for i, title, url, content, scrape_time in scraped_data
        ]
        for future in futures:
            try:
                summarized_data.append(future.result())
            except Exception as e:
                click.secho(f"Error summarizing a source thread: {e}", fg="red", err=True)

    summarized_data.sort(key=lambda x: x[0])

    for i, title, url, summary, scrape_time, summary_time in summarized_data:
        summaries.append((title, url, summary))
        citations.append(f"[{i}] {title} - {url}")
        benchmarks.append({
            "source": i,
            "title": title,
            "scrape_time": scrape_time,
            "summary_time": summary_time
        })
        
    click.echo("\n" + "="*40 + "\n")
    click.secho("📝 WEB RESEARCH SUMMARY\n", fg="green", bold=True)
    
    for i, (title, url, summary) in enumerate(summaries, 1):
        click.secho(f"### Source [{i}]: {title}", bold=True)
        click.echo(f"URL: {url}\n")
        click.echo(summary)
        click.echo("\n" + "-"*30 + "\n")
        
    click.secho("🔗 CITATIONS", bold=True)
    for cite in citations:
        click.echo(cite)
        
    total_time = time.perf_counter() - total_start
    
    if benchmark:
        click.echo("\n" + "="*40 + "\n")
        click.secho("⏱️ BENCHMARK REPORT", fg="yellow", bold=True)
        if search_time is not None:
            click.echo(f"SearXNG query: {search_time:.3f}s")
        for b in benchmarks:
            click.echo(f"Source [{b['source']}] ({b['title'][:30]}...):")
            click.echo(f"  - Scraping:      {b['scrape_time']:.3f}s")
            click.echo(f"  - Summarization: {b['summary_time']:.3f}s")
        click.echo(f"Total time:    {total_time:.3f}s")
        
    click.echo("\n" + "="*40)

if __name__ == "__main__":
    main()