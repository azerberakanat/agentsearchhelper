# agentsearchhelper

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#)

A high-performance, private, and local CLI tool that queries a **SearXNG** metasearch instance, concurrently scrapes resulting web pages, and generates dense query-relevant summaries using a local **llama.cpp** OpenAI-compatible server.

`agentsearchhelper` acts as a cost-saving token filter. Instead of dumping massive raw webpage contents (often exceeding 100k tokens per search) into your agent's context window, it extracts clean body text and feeds it to a local LLM to generate precise, query-centric summaries.

---

## 🚀 Features & Talents

- **Local & Private Metasearch**: Seamless integration with a local SearXNG instance, aggregating search results from Google, Bing, DuckDuckGo, and other search engines without API key limits or IP blocks.
- **Boilerplate-Free Web Scraping**: Integrates `trafilatura` alongside a custom monkey patch for `lxml.html.clean` to guarantee text extraction is clean, stripping out navigation bars, ads, and page footers.
- **Fully Concurrent Pipeline**:
  - **Scraping**: Fetches target webpages concurrently using Python's `ThreadPoolExecutor`.
  - **Summarization**: Dispatches prompts to the LLM concurrently, leveraging the parallel slots and continuous batching of the local `llama.cpp` server (`-np 3 --cont-batching`).
- **Dense, Query-Centric Summaries**: Prompts are optimized to extract only query-relevant facts, code snippets, and explanations under 300 words, warning you explicitly if there is a content mismatch.
- **Performance Benchmarking**: The `--benchmark` flag breaks down the execution times for the search query, individual page scraping, and LLM summarization.

---

## 🛠️ Highs & Lows

### The Highs (Pros)
- **Zero API Cost**: Completely local pipeline. No external LLM token bills or Google Search API charges.
- **True Parallel Speedup**: Network scraping and local model inference run concurrently, preventing sequential request bottlenecks.
- **Absolute Privacy**: All searches, scraping, and summarizations occur locally or on your own local area network.
- **Context Protection**: Prevents context bloating and token dilution. It replaces massive raw HTML/text dumps with highly distilled summaries.

### The Lows (Cons)
- **Infrastructure Dependency**: Requires managing two background services (SearXNG in Docker and a `llama.cpp` model server).
- **Hardware Bound**: High-performance local inference is constrained by your local GPU VRAM (e.g. requiring ~6GB of VRAM for running parallel slots comfortably with a model like Qwen 3.5 4B).

---

## 📐 Architectural Justification

### Why SearXNG?
Commercial search engine APIs charge per query and are subject to strict rate limits. SearXNG is a self-hosted metasearch aggregator. Using SearXNG locally guarantees zero running costs, high availability, and allows custom search options.

---

## 📥 Installation

### 1. Run SearXNG
Deploy SearXNG using Docker, mounting the local `settings.yml` to enable the JSON search format:
```bash
docker run -d -p 8080:8080 -v "$(pwd)/settings.yml:/etc/searxng/settings.yml" searxng/searxng
```

### 2. Start the llama.cpp Server
Launch `llama-server` on your local network (e.g., on host `[IP_ADDRESS]` or `localhost`), configuring it with multiple parallel slots and continuous batching:
```bash
llama-server.exe \
  -m "/path/to/Qwen3.5-4B-UD-Q4_K_XL.gguf" \
  -c 32768 \
  -np 3 \
  --cont-batching \
  --port 8888 \
  --flash-attn on
```
> [!NOTE]
> `agentsearchhelper` targets the model's OpenAI-compatible endpoint at `/v1/chat/completions` and passes `"enable_thinking": False` in `chat_template_kwargs` to avoid wasting reasoning budget on summarization tasks, maximizing token generation speed.

### 3. Clone and Setup Environment
Install dependencies and the package locally in editable mode:
```bash
git clone https://github.com/your-username/agentsearchhelper.git
cd agentsearchhelper
pip install -e .
```

Configure your environment variables in a `.env` file at the project root:
```ini
LLM_BASE_URL=http://localhost:8888/v1
LLM_MODEL=unsloth/Qwen3.5-4B-MTP-GGUF:UD-Q4_K_XL
SEARXNG_URL=http://localhost:8080
```

---

## 📖 Usage

### 1. Search Flow (Only `--query`)
Queries local SearXNG, scrapes resulting pages, and summarizes relative to the query.
```bash
agentsearchhelper --query "<search_query>" [options]
```

### 2. Guided Direct Flow (Both `--url` and `--query`)
Scrapes the target URL directly and produces a query-focused summary, tracing internal links to find matching content.
```bash
agentsearchhelper --url "<target_url>" --query "<search_query>" [options]
```

### CLI Options

| Option | Shortcut | Description | Default |
| :--- | :--- | :--- | :--- |
| `--query` | `-q` | **Required**. The search query to execute (required for all flows). | N/A |
| `--url` | `-u` | Direct URL to scrape and summarize (combines with `--query` for Guided Flow). | None |
| `--depth` | `-d` | Maximum crawling depth for guided direct flow. | `6` |
| `--max-results` | `-m` | Maximum number of search results to crawl (Search Flow only). | `3` |
| `--model` | | Local LLM model identifier. | Loaded from `.env` |
| `--time-range` | `-t` | Filter results by time range (`day`, `week`, `month`, `year`) (Search Flow only). | None |
| `--category` | `-c` | Search category (e.g., `general`, `it`, `news`, `science`) (Search Flow only). | None |
| `--engines` | `-e` | Comma-separated list of engines to query (Search Flow only). | None |
| `--language` | `-l` | Language code (e.g., `en`, `fr`, `de`) (Search Flow only). | None |
| `--benchmark` | | Display detailed execution times for each phase. | Flag |

### Example Queries
```bash
# Query API changes for Next.js 15
agentsearchhelper --query "Next.js 15 app router API changes" --benchmark

# Scrape and summarize a webpage with a guided query
agentsearchhelper --url "https://github.com/DeusData/codebase-memory-mcp" --query "how semantic query is done" --benchmark
```

---

## 📊 Benchmark Evidence

Below is a typical benchmark run comparing sequential execution against `agentsearchhelper`'s concurrent architecture:

```text
🔍 Searching SearXNG for: 'Next.js 15 app router API changes'...
Found 3 results. Scraping pages in parallel...

[1/3] Scraping: Routing: API Routes - Next.js (https://nextjs.org/...)...
[2/3] Scraping: Next.js 15 (https://nextjs.org/blog/next-15)...
[3/3] Scraping: Next.js 15 App Router: Critical Changes Explained...

Summarizing pages in parallel using 'unsloth/Qwen3.5-4B-MTP-GGUF:UD-Q4_K_XL'...

[1/3] Summarizing content...
[2/3] Summarizing content...
[3/3] Summarizing content...

========================================
📝 WEB RESEARCH SUMMARY
... (Summarized content) ...

========================================
⏱️ BENCHMARK REPORT
SearXNG query: 0.920s
Source [1] (Routing: API Routes - Next.js):
  - Scraping:      5.496s
  - Summarization: 6.242s
Source [2] (Next.js 15):
  - Scraping:      5.482s
  - Summarization: 7.574s
Source [3] (Next.js 15 App Router):
  - Scraping:      5.335s
  - Summarization: 7.555s
Total time:    13.993s
========================================
```

> [!TIP]
> In a sequential setup, scraping and summarizing three pages sequentially would take upwards of **40 seconds**. By parallelizing both the HTTP network requests and the GPU generation slots, the total execution time is reduced to the duration of the slowest branch (**~13.9 seconds**).
