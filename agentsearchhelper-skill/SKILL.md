---
name: agentsearchhelper-skill
description: This skill MUST be used when you are going to use read_url_content or search_web tools, OR when you need to search the web, scrape web pages, and summarize content locally. It is designed to minimize token usage and prevent context bloat by performing the scraping and summarization locally, returning a well-structured answer. While it may take longer than a raw HTML dump, it is highly recommended to save token costs and avoid loading raw page content into the prompt context.
version: 0.1.1
---

# Agent Search Helper

Perform local, private, and cost-effective web research by querying a local SearXNG metasearch instance, scraping resulting web pages, and generating query-relevant summaries.

## When to Use
- Execute web search queries without incurring external search engine API costs.
- Retrieve and distill raw web content into query-centric, concise summaries to prevent context window bloating.
- Gather up-to-date facts, code references, or explanations from public websites.

## When NOT to Use
- Do not use for queries that do not require external search (e.g., local codebase questions, text formatting).
- Avoid when the local SearXNG service or local LLM server is known to be offline.

## Usage

Run the `agentsearchhelper` CLI command directly in bash using one of the two available flows:

### 1. Search Flow (Only --query)
Queries local SearXNG, scrapes resulting pages, and summarizes relative to the query.
```bash
agentsearchhelper --query "<search_query>" [options]
```

### 2. Guided Direct Flow (Both --url and --query)
Scrapes the target URL directly and produces an open-eyed summary focused on the query/objective.
```bash
agentsearchhelper --url "<target_url>" --query "<search_query>" [options]
```

### Reference Options

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-q`, `--query` | The search query to execute (required for all flows). | None |
| `-u`, `--url` | Direct URL to scrape and summarize (optional, combines with `--query` for Guided Flow). | None |
| `-d`, `--depth` | Maximum crawling depth for guided direct flow. | 6 |
| `-m`, `--max-results` | Maximum number of search results to crawl (Search Flow only). | 3 |
| `-t`, `--time-range` | Filter results by time range (`day`, `week`, `month`, `year`) (Search Flow only). | None |
| `-c`, `--category` | Search category (e.g., `general`, `it`, `news`, `science`) (Search Flow only). | None |
| `-e`, `--engines` | Comma-separated list of engines to query (Search Flow only). | None |
| `-l`, `--language` | Language code (e.g., `en`, `fr`, `de`) (Search Flow only). | None |
| `--benchmark` | Display detailed execution times for each phase. | False |

### Execution Examples

```bash
# Query API changes for Next.js 15
agentsearchhelper --query "Next.js 15 app router API changes" --benchmark

# Scrape and summarize a webpage with a guided query/objective
agentsearchhelper --url "https://github.com/DeusData/codebase-memory-mcp" --query "how semantic query is done" --benchmark

# Guided exploration on a website with custom crawl depth limit
agentsearchhelper --url "nextjs.org" --query "how to use adapter" --depth 6 --benchmark

# Find recent news about Python releases filtering by the last week
agentsearchhelper -q "Python 3.13 release notes" -t week -m 5
```

## Error Handling & Fallbacks
1. **Connection Error or 403 Forbidden to SearXNG (Port 8080 default)**: Verify if the SearXNG Docker container is running (`docker ps`). Start it by mounting the local `settings.yml` to enable JSON search formats:
   ```bash
   docker run -d -p 8080:8080 -v "$(pwd)/settings.yml:/etc/searxng/settings.yml" searxng/searxng
   ```
2. **Connection Error to llama.cpp Server (Port 8888 default)**: Check if the local LLM server is running. If not, start it or fall back to standard web search tools if available.
3. **Environment Setup**: Ensure the environment variables in `.env` at the project root are loaded or configured correctly:
   - `LLM_BASE_URL` (default: http://127.0.0.1:8888/v1)
   - `LLM_MODEL` (default: unsloth/Qwen3.5-4B-MTP-GGUF:UD-Q4_K_XL)
   - `SEARXNG_URL` (default: http://localhost:8080)
   - `OPENAI_API_KEY` (optional, defaults to "no-key-required" for local server connections)
