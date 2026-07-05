import sys
import click
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load env variables before importing modules
load_dotenv()

# Monkey-patch lxml.html.clean for third-party libraries (like justext/trafilatura)
try:
    import lxml_html_clean
    sys.modules['lxml.html.clean'] = lxml_html_clean
except ImportError:
    pass

from agentsearchhelper.search import query_searxng
from agentsearchhelper.scraper import scrape_url
from agentsearchhelper.summarizer import summarize_text, LLM_MODEL

print_lock = threading.Lock()

def safe_echo(message, **kwargs):
    with print_lock:
        click.echo(message, **kwargs)

def scrape_source(i, total, title, url, snippet):
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
@click.option("--max-results", "-m", default=3, help="Maximum number of search results to crawl.")
@click.option("--model", default=LLM_MODEL, help="Local LLM model to use for summarization.")
@click.option("--time-range", "-t", type=click.Choice(["day", "week", "month", "year"]), help="Filter results by time range.")
@click.option("--category", "-c", help="Search category (e.g. general, it, news, science).")
@click.option("--engines", "-e", help="Comma-separated list of engines to query.")
@click.option("--language", "-l", help="Language code (e.g. en, fr, de).")
@click.option("--benchmark", is_flag=True, help="Show elapsed time for each phase of execution.")
def main(query: str, max_results: int, model: str, time_range: str, category: str, engines: str, language: str, benchmark: bool):
    """agentsearchhelper: A local CLI tool to query SearXNG and summarize web results using a local LLM."""
    total_start = time.perf_counter()
    
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
    
    # Step 1: Run scraping in parallel (network-bound)
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

    # Sort results by original search order (index) to preserve ranking order
    scraped_data.sort(key=lambda x: x[0])

    click.echo(f"\nSummarizing pages in parallel using '{model}'...\n")

    summaries = []
    citations = []
    benchmarks = []
    
    # Step 2: Run summarization in parallel (leveraging parallel slot execution on local LLM)
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

    # Sort results by original search order to preserve ranking
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
        click.echo(f"SearXNG query: {search_time:.3f}s")
        for b in benchmarks:
            click.echo(f"Source [{b['source']}] ({b['title'][:30]}...):")
            click.echo(f"  - Scraping:      {b['scrape_time']:.3f}s")
            click.echo(f"  - Summarization: {b['summary_time']:.3f}s")
        click.echo(f"Total time:    {total_time:.3f}s")
        
    click.echo("\n" + "="*40)

if __name__ == "__main__":
    main()
