import unittest
from agentsearchhelper.search import query_searxng

class TestSearxng(unittest.TestCase):
    def test_search_connectivity(self):
        """Test if SearXNG local server is reachable and returns structured results."""
        try:
            results = query_searxng("python language", max_results=2)
            print(f"\n[Test] SearXNG returned {len(results)} results.")
            for i, r in enumerate(results, 1):
                print(f"  Result {i}: {r['title']} - {r['url']}")
                self.assertIsNotNone(r['title'])
                self.assertIsNotNone(r['url'])
        except Exception as e:
            self.fail(f"SearXNG search failed: {e}. Ensure local SearXNG docker is running.")

if __name__ == "__main__":
    unittest.main()
