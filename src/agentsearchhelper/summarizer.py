import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8888/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-unsloth-YOUR_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "unsloth/Qwen3.5-4B-MTP-GGUF:UD-Q4_K_XL")

# Initialize OpenAI client with local custom endpoint
client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
    timeout=60.0,  # Prevent hanging indefinitely
)

def summarize_text(text: str, query: str, model: str = LLM_MODEL) -> str:
    """Send clean webpage text to the custom local OpenAI-compatible endpoint

    and summarize it relative to the query.
    """
    if not text or not text.strip():
        return "No content extracted from this URL."

    prompt = (
        f"You are a high-performance summarization assistant.\n"
        f"We are answering the user's search query: \"{query}\"\n\n"
        f"Based ONLY on the webpage content provided below, extract and summarize the key facts, "
        f"explanations, or code snippets that directly answer the query.\n"
        f"Follow these guidelines:\n"
        f"1. Do not include boilerplate introduction or conversational filler. Start directly with the summary.\n"
        f"2. Keep the output dense, precise, and concise (under 300 words).\n"
        f"3. Include critical code snippets if they exist in the text and help explain the changes.\n"
        f"4. If the content does not contain facts that directly answer the query (e.g., it discusses a different version or is high-level/marketing-focused without technical details), explicitly state this mismatch as a note at the very beginning.\n\n"
        f"--- Webpage Content ---\n"
        f"{text}\n"
        f"--- End of Webpage Content ---"
    )


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
