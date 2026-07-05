import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8888/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "unsloth/Qwen3.5-4B-MTP-GGUF:UD-Q4_K_XL")

# Initialize OpenAI client with local custom endpoint
client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key=os.getenv("OPENAI_API_KEY", "no-key-required"),
    timeout=60.0,  # Prevent hanging indefinitely
)

def chunk_text(text: str, max_chars: int = 28000) -> list[str]:
    """Split text into chunks of at most max_chars, preferably at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph) + 2  # including the \n\n
        if current_length + paragraph_len > max_chars:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            
            # If a single paragraph is larger than max_chars, split it by lines
            if paragraph_len > max_chars:
                lines = paragraph.split("\n")
                for line in lines:
                    line_len = len(line) + 1
                    if current_length + line_len > max_chars:
                        if current_chunk:
                            chunks.append("\n".join(current_chunk))
                            current_chunk = []
                            current_length = 0
                        
                        # If a single line is still too large, force split it
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
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=False,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            }
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error running local summarization via OpenAI client: {e}"

def _summarize_chunk(text: str, query: str, model: str) -> str:
    prompt = (
        f"You are a high-performance summarization assistant.\n"
        f"We are answering the user's search query: \"{query}\"\n\n"
        f"Based ONLY on the webpage content provided below, extract and summarize the key facts, "
        f"explanations, or code snippets that directly answer the query.\n"
        f"Follow these guidelines:\n"
        f"1. Do not include boilerplate introduction or conversational filler. Start directly with the summary.\n"
        f"2. Keep the output dense, precise, and concise.\n"
        f"3. Include critical code snippets if they exist in the text.\n"
        f"4. If the content does not contain facts that directly answer the query, explicitly state this mismatch as a note.\n\n"
        f"--- Webpage Content ---\n"
        f"{text}\n"
        f"--- End of Webpage Content ---"
    )
    return _call_llm(prompt, model)

def _summarize_combined(combined_summaries: str, query: str, model: str) -> str:
    prompt = (
        f"You are a high-performance summarization assistant.\n"
        f"We are answering the user's search query: \"{query}\"\n\n"
        f"We have summarized different sections of a webpage. Below are the individual section summaries.\n"
        f"Synthesize them into a single, cohesive, dense, and precise final summary (under 300 words) "
        f"that directly answers the query.\n"
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
    """Send clean webpage text to the custom local OpenAI-compatible endpoint

    and summarize it relative to the query.
    """
    if not text or not text.strip():
        return "No content extracted from this URL."

    # Max characters for a single request to fit within ~8000 token limit
    MAX_CHARS_PER_CHUNK = 28000
    
    chunks = chunk_text(text, MAX_CHARS_PER_CHUNK)
    
    # If there is only 1 chunk, summarize it normally
    if len(chunks) == 1:
        return _summarize_chunk(chunks[0], query, model)
        
    # If there are multiple chunks, summarize each and then combine the summaries
    chunk_summaries = []
    for idx, chunk in enumerate(chunks, 1):
        summary = _summarize_chunk(chunk, f"{query} (Part {idx} of {len(chunks)})", model)
        if not summary.startswith("Error running local summarization"):
            chunk_summaries.append(summary)
            
    if not chunk_summaries:
        return "Failed to summarize webpage content chunks."
        
    # Combine chunk summaries and run a final summarization pass
    combined_text = "\n\n".join(
        f"--- Chunk {idx} Summary ---\n{s}" for idx, s in enumerate(chunk_summaries, 1)
    )
    
    return _summarize_combined(combined_text, query, model)
