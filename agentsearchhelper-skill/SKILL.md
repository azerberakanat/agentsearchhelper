---
name: agentsearchhelper-skill
description: This skill should be used when the user asks to "search the web", "search the internet", "run online research", "query search helper", or wants to search, scrape, and summarize web pages using a local SearXNG metasearch instance.
version: 0.1.0
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

Run the `agentsearchhelper` CLI command directly in bash:

```bash
agentsearchhelper --query "<search_query>" [options]
```

### Reference Options

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-q`, `--query` | The search query to execute (required). | None |
| `-m`, `--max-results` | Maximum number of search results to crawl. | 3 |
| `-t`, `--time-range` | Filter results by time range (`day`, `week`, `month`, `year`). | None |
| `-c`, `--category` | Search category (e.g., `general`, `it`, `news`, `science`). | None |
| `-e`, `--engines` | Comma-separated list of engines to query. | None |
| `-l`, `--language` | Language code (e.g., `en`, `fr`, `de`). | None |
| `--benchmark` | Display detailed execution times for each phase. | False |

### Execution Examples

```bash
# Query API changes for Next.js 15
agentsearchhelper --query "Next.js 15 app router API changes" --benchmark

# Find recent news about Python releases filtering by the last week
agentsearchhelper -q "Python 3.13 release notes" -t week -m 5
```

## Error Handling & Fallbacks
1. **Connection Error to SearXNG (Port 8080 default)**: Verify if the SearXNG Docker container is running (`docker ps`). If not, start it:
   ```bash
   docker run -d -p 8080:8080 searxng/searxng
   ```
2. **Connection Error to llama.cpp Server (Port 8888 default)**: Check if the local LLM server is running. If not, start it or fall back to standard web search tools if available.
3. **Environment Setup**: Ensure the environment variables in `.env` at the project root are loaded or configured correctly:
   - `LLM_BASE_URL` (default: http://127.0.0.1:8888/v1)
   - `LLM_MODEL` (default: unsloth/Qwen3.5-4B-MTP-GGUF:UD-Q4_K_XL)
   - `SEARXNG_URL` (default: http://localhost:8080)
   - `OPENAI_API_KEY` (optional, defaults to "no-key-required" for local server connections)
