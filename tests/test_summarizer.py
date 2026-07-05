import unittest
from agentsearchhelper.summarizer import summarize_text

class TestSummarizer(unittest.TestCase):
    def test_summarization(self):
        """Test if local custom llama.cpp LLM endpoint is reachable and can summarize a short passage."""
        sample_text = (
            "Python is a high-level, general-purpose programming language. "
            "Its design philosophy emphasizes code readability with the use of significant indentation."
        )
        query = "what is python's design philosophy"
        
        try:
            summary = summarize_text(sample_text, query)
            print(f"\n[Test] llama.cpp summary output:\n{summary}")
            self.assertIsNotNone(summary)
            self.assertNotIn("Error running local summarization via OpenAI client", summary)
        except Exception as e:
            self.fail(f"llama.cpp summarization failed: {e}. Ensure the llama-server is running.")

if __name__ == "__main__":
    unittest.main()
