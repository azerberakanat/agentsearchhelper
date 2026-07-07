# summarizer.py
import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8888/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "unsloth/Qwen3.5-4B-MTP-GGUF:UD-Q4_K_XL")

client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key=os.getenv("OPENAI_API_KEY", "no-key-required"),
    timeout=60.0,
)

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "could",
    "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", "further", "had", "has",
    "have", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "itself", "me", "more", "most", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own",
    "same", "she", "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", "under",
    "until", "up", "very", "was", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "would", "you", "your", "yours", "yourself", "yourselves"
}

def chunk_text(text: str, max_chars: int = 28000) -> list[str]:
    """Split text into chunks of at most max_chars, preferably at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph) + 2
        if current_length + paragraph_len > max_chars:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            if paragraph_len > max_chars:
                lines = paragraph.split("\n")
                for line in lines:
                    line_len = len(line) + 1
                    if current_length + line_len > max_chars:
                        if current_chunk:
                            chunks.append("\n".join(current_chunk))
                            current_chunk = []
                            current_length = 0
                        if line_len > max_chars:
                            start = 0
                            while start < len(line):
                                chunks.append(line[start:start + max_chars])
                                start += max_chars
                        else:
                            current_chunk.append(line)
                            current_length += line_len
                    else:
                        current_chunk.append(line)
                        current_length += line_len
            else:
                current_chunk.append(paragraph)
                current_length += paragraph_len
        else:
            current_chunk.append(paragraph)
            current_length += paragraph_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks

def _call_llm(prompt: str, model: str) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}}
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error running local summarization via OpenAI client: {e}"

def _summarize_chunk(text: str, query: str, model: str) -> str:
    prompt = (
        f"You are a high-performance summarization assistant.\n"
        f"Based ONLY on the webpage content provided below, extract and summarize the key facts, "
        f"explanations, or code snippets to produce a comprehensive summary of its contents, "
        f"focusing especially on answering the query/objective: \"{query}\".\n"
        f"Do not ignore general parts of the webpage completely unless you are convinced they are irrelevant noise to the subject matter.\n"
        f"Follow these guidelines:\n"
        f"1. Do not include boilerplate introduction or conversational filler. Start directly with the summary.\n"
        f"2. Keep the output dense, precise, and concise.\n"
        f"3. Include critical code snippets if they exist in the text.\n"
        f"4. If the page content does not contain facts that address the query, explicitly state this mismatch as a note.\n\n"
        f"--- Webpage Content ---\n"
        f"{text}\n"
        f"--- End of Webpage Content ---"
    )
    return _call_llm(prompt, model)

def _summarize_combined(combined_summaries: str, query: str, model: str) -> str:
    prompt = (
        f"You are a high-performance summarization assistant.\n"
        f"We have summarized different sections of a webpage. Below are the individual section summaries.\n"
        f"Synthesize them into a single, cohesive, dense, and precise final summary (under 300 words) "
        f"of the webpage contents, prioritizing information and details that answer: \"{query}\".\n"
        f"Do not ignore general parts of the webpage completely unless you are convinced they are irrelevant noise to the subject matter.\n"
        f"Follow these guidelines:\n"
        f"1. Do not include boilerplate introduction or conversational filler. Start directly with the final summary.\n"
        f"2. Include critical code snippets if they were present in the section summaries and are relevant.\n"
        f"3. Maintain factual accuracy based only on the provided section summaries.\n\n"
        f"--- Section Summaries ---\n"
        f"{combined_summaries}\n"
        f"--- End of Section Summaries ---"
    )
    return _call_llm(prompt, model)

def summarize_text(text: str, query: str, model: str = LLM_MODEL) -> str:
    if not text or not text.strip():
        return "No content extracted from this URL."

    MAX_CHARS_PER_CHUNK = 28000
    chunks = chunk_text(text, MAX_CHARS_PER_CHUNK)
    
    if len(chunks) == 1:
        return _summarize_chunk(chunks[0], query, model)
        
    chunk_summaries = []
    for idx, chunk in enumerate(chunks, 1):
        chunk_query = f"{query} (Part {idx} of {len(chunks)})"
        summary = _summarize_chunk(chunk, chunk_query, model)
        if not summary.startswith("Error running local summarization"):
            chunk_summaries.append(summary)
            
    if not chunk_summaries:
        return "Failed to summarize webpage content chunks."
        
    combined_text = "\n\n".join(
        f"--- Chunk {idx} Summary ---\n{s}" for idx, s in enumerate(chunk_summaries, 1)
    )
    
    return _summarize_combined(combined_text, query, model)

def select_links_with_llm(links: list[dict], query: str, model: str) -> list[str]:
    """Select the top links most likely to contain documentation/relevant details."""
    seen_urls = set()
    unique_links = []
    for l in links:
        url_clean = l["url"].split("#")[0].rstrip("/")
        if url_clean not in seen_urls and l["text"]:
            seen_urls.add(url_clean)
            unique_links.append(l)
            
    if not unique_links:
        return []
        
    # Extract query terms, stripping punctuation
    query_words = [w.strip("?,.:;!") for w in query.lower().split()]
    query_words = [w for w in query_words if w]
    
    scored_links = []
    for l in unique_links:
        link_str = f"{l['text']} {l['url']}".lower()
        score = 0.0
        for w in query_words:
            if w in link_str:
                if w in STOPWORDS:
                    score += 0.1  # Low weight for grammatical stopwords as minor tiebreakers
                else:
                    score += len(w)  # Word length as generic IDF proxy
        scored_links.append((score, l))
        
    scored_links.sort(key=lambda x: x[0], reverse=True)
    top_candidates = [item[1] for item in scored_links[:12]]
    
    candidates_str = "\n".join(f"- {idx}: URL: {c['url']} | Anchor: {c['text']}" for idx, c in enumerate(top_candidates, 1))
    
    prompt = (
        f"You are a web routing assistant. We are answering the research query: \"{query}\"\n"
        f"Below is a list of candidate links from the current website:\n"
        f"{candidates_str}\n\n"
        f"Instructions:\n"
        f"1. In a single paragraph, think step-by-step about which 2-3 links are most likely to contain the actual answer, configuration instructions, or technical setup for the query: \"{query}\".\n"
        f"2. Conclude with a JSON list of the top 2-3 chosen URLs on a new line at the very end of your response, prefixed with 'CHOSEN_URLS: ', for example:\n"
        f"CHOSEN_URLS: [\"url1\", \"url2\"]"
    )
    
    try:
        response = _call_llm(prompt, model)
        # Parse output for the final CHOSEN_URLS line
        clean_response = ""
        for line in reversed(response.splitlines()):
            if "CHOSEN_URLS:" in line:
                clean_response = line.split("CHOSEN_URLS:", 1)[1].strip()
                break
                
        # Fallback if prefix not found
        if not clean_response:
            clean_response = response.strip()
            
        # Robust JSON extraction from LLM chatter
        start_idx = clean_response.find("[")
        end_idx = clean_response.rfind("]")
        if start_idx != -1 and end_idx != -1:
            clean_response = clean_response[start_idx:end_idx+1]
        
        urls = json.loads(clean_response)
        if isinstance(urls, list):
            candidate_urls = {c["url"] for c in top_candidates}
            valid_urls = [u for u in urls if u in candidate_urls]
            return valid_urls[:3]
    except Exception:
        pass
        
    return [c["url"] for c in top_candidates[:2]]

def check_satisfaction_with_llm(text: str, query: str, model: str = LLM_MODEL) -> bool:
    """Use step-by-step reasoning to evaluate if the content contains a detailed answer."""
    if not text or not text.strip():
        return False
        
    # Extract core query terms (non-stopwords)
    query_words = [w.strip("?,.:;!") for w in query.lower().split()]
    core_words = [w for w in query_words if w and w not in STOPWORDS]
    
    # Pre-check: if none of the core topic words are present in the text, it cannot satisfy the query
    if core_words and not any(cw in text.lower() for cw in core_words):
        return False
        
    prompt = (
        f"Analyze if the following webpage content contains a direct, specific, and detailed answer "
        f"to the user's research objective.\n\n"
        f"Research Objective: \"{query}\"\n\n"
        f"--- Webpage Content Snippet ---\n"
        f"{text[:6000]}\n"
        f"--- End of Snippet ---\n\n"
        f"Instructions:\n"
        f"1. Reason step-by-step: Is there configuration logic, specific setup instructions, "
        f"or technical guidelines directly fulfilling the objective?\n"
        f"2. Distinguish partial keyword matches from actual relevant instruction (e.g., if searching for 'adapter configuration', "
        f"does the page actually discuss configuring adapters? If it discusses unrelated components like proxies, do not accept it).\n"
        f"3. Conclude with either 'DECISION: YES' or 'DECISION: NO' on a new line at the very end. Be conservative."
    )
    
    try:
        response = _call_llm(prompt, model)
        # Parse output for the final decision line
        decision_line = ""
        for line in reversed(response.splitlines()):
            if "DECISION:" in line.upper():
                decision_line = line.upper()
                break
                
        return "YES" in decision_line
    except Exception:
        return False