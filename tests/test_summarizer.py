import unittest
from click.testing import CliRunner
from unittest.mock import patch
from agentsearchhelper.summarizer import summarize_text, LLM_MODEL
from agentsearchhelper.cli import main

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

class TestCLI(unittest.TestCase):
    def test_cli_missing_query_error(self):
        """Test click validation when required --query option is missing."""
        runner = CliRunner()
        result = runner.invoke(main, [])
        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Error: Missing option '--query'", result.output)

        result_with_url = runner.invoke(main, ["--url", "https://example.com"])
        self.assertNotEqual(result_with_url.exit_code, 0)
        self.assertIn("Error: Missing option '--query'", result_with_url.output)

    @patch("agentsearchhelper.cli.scrape_url_with_links")
    @patch("agentsearchhelper.cli.check_satisfaction_with_llm")
    @patch("agentsearchhelper.cli.summarize_text")
    def test_cli_guided_url_flow(self, mock_summarize, mock_satisfied, mock_scrape_with_links):
        """Test that passing both --url and --query triggers scrape_url_with_links and summarize."""
        mock_scrape_with_links.return_value = ("Mocked webpage content", [])
        mock_satisfied.return_value = True
        mock_summarize.return_value = "Mocked summary"
        
        runner = CliRunner()
        result = runner.invoke(main, ["--url", "https://github.com/DeusData/codebase-memory-mcp", "--query", "type resolution"])
        
        self.assertEqual(result.exit_code, 0)
        mock_scrape_with_links.assert_called_once_with("https://github.com/DeusData/codebase-memory-mcp")
        mock_summarize.assert_called_once_with("Mocked webpage content", "type resolution", model=LLM_MODEL)

    @patch("agentsearchhelper.cli.scrape_url_with_links")
    @patch("agentsearchhelper.cli.check_satisfaction_with_llm")
    @patch("agentsearchhelper.cli.summarize_text")
    def test_cli_url_normalization(self, mock_summarize, mock_satisfied, mock_scrape_with_links):
        """Test that --url nextjs.org (without scheme) is normalized to https://nextjs.org."""
        mock_scrape_with_links.return_value = ("Mocked webpage content", [])
        mock_satisfied.return_value = True
        mock_summarize.return_value = "Mocked summary"
        
        runner = CliRunner()
        result = runner.invoke(main, ["--url", "nextjs.org", "--query", "how to use adapter"])
        
        self.assertEqual(result.exit_code, 0)
        mock_scrape_with_links.assert_called_once_with("https://nextjs.org")
        mock_summarize.assert_called_once_with("Mocked webpage content", "how to use adapter", model=LLM_MODEL)

    @patch("agentsearchhelper.cli.scrape_url_with_links")
    @patch("agentsearchhelper.cli.check_satisfaction_with_llm")
    @patch("agentsearchhelper.cli.select_links_with_llm")
    @patch("agentsearchhelper.cli.summarize_text")
    def test_cli_deep_crawling_loop(self, mock_summarize, mock_select, mock_satisfied, mock_scrape_with_links):
        """Test that the CLI crawling loops to next depth if objective is not satisfied."""
        mock_scrape_with_links.side_effect = [
            ("Root page content", [{"url": "https://nextjs.org/docs", "text": "Docs"}]),
            ("Docs page content", [])
        ]
        mock_satisfied.side_effect = [False, True]
        mock_select.return_value = ["https://nextjs.org/docs"]
        mock_summarize.return_value = "Mocked summary"
        
        runner = CliRunner()
        result = runner.invoke(main, ["--url", "https://nextjs.org", "--query", "how to use adapter", "--depth", "3"])
        
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(mock_scrape_with_links.call_count, 2)
        self.assertEqual(mock_summarize.call_count, 2)

class TestScraperLinkExtraction(unittest.TestCase):
    @patch("agentsearchhelper.scraper.session.get")
    @patch("trafilatura.extract")
    def test_extract_links(self, mock_extract, mock_get):
        """Test internal link extraction and base URL joining."""
        mock_extract.return_value = "Clean text content"
        mock_html = """
        <html>
            <body>
                <a href="/docs/routing">Docs Routing</a>
                <a href="https://github.com/DeusData/codebase-memory-mcp">External GitHub</a>
                <a href="https://nextjs.org/blog/15">Internal Blog</a>
            </body>
        </html>
        """
        class MockResponse:
            status_code = 200
            text = mock_html
            content = mock_html.encode('utf-8')
            
        mock_get.return_value = MockResponse()
        
        from agentsearchhelper.scraper import scrape_url_with_links
        text, links = scrape_url_with_links("https://nextjs.org")
        
        self.assertEqual(text, "Clean text content")
        self.assertEqual(len(links), 2)
        urls = {l["url"] for l in links}
        self.assertIn("https://nextjs.org/docs/routing", urls)
        self.assertIn("https://nextjs.org/blog/15", urls)
        self.assertNotIn("https://github.com/DeusData/codebase-memory-mcp", urls)

class TestLinkSelection(unittest.TestCase):
    @patch("agentsearchhelper.summarizer._call_llm")
    def test_select_links_with_llm(self, mock_call_llm):
        """Test that LLM guided link selection parses output correctly and falls back if needed."""
        from agentsearchhelper.summarizer import select_links_with_llm
        # JSON response containing the selected URLs
        mock_call_llm.return_value = '["https://nextjs.org/docs/adapters", "https://nextjs.org/docs/config"]'
        
        links = [
            {"url": "https://nextjs.org/docs/adapters", "text": "Adapters Documentation"},
            {"url": "https://nextjs.org/docs/config", "text": "Configuration Settings"},
            {"url": "https://nextjs.org/enterprise", "text": "Enterprise Support"}
        ]
        
        selected = select_links_with_llm(links, "how to use adapter", model=LLM_MODEL)
        
        self.assertEqual(len(selected), 2)
        self.assertIn("https://nextjs.org/docs/adapters", selected)
        self.assertIn("https://nextjs.org/docs/config", selected)
        self.assertNotIn("https://nextjs.org/enterprise", selected)

    @patch("agentsearchhelper.summarizer._call_llm")
    def test_check_satisfaction_with_llm(self, mock_call_llm):
        """Test that check_satisfaction_with_llm returns True on YES and False on NO."""
        from agentsearchhelper.summarizer import check_satisfaction_with_llm
        mock_call_llm.side_effect = ["DECISION: YES", "DECISION: NO"]
        
        self.assertTrue(check_satisfaction_with_llm("Some query text", "query", model=LLM_MODEL))
        self.assertFalse(check_satisfaction_with_llm("Some query text", "query", model=LLM_MODEL))

if __name__ == "__main__":
    unittest.main()
