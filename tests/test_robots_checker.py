import unittest

from app.services.robots_checker import analyze_robots


class RobotsCheckerTests(unittest.TestCase):
    def test_analyze_robots_preserves_raw_content(self):
        robots_txt = """# As a condition of accessing this website, you agree to abide by the following
# content signals:

# search: building a search index and providing search results.
# ai-input: inputting content into one or more AI models.
# ai-train: training or fine-tuning AI models.
"""

        result = analyze_robots(robots_txt)

        self.assertTrue(result["exists"])
        self.assertTrue(result["default_ua_allowed"])
        self.assertEqual(result["raw_content"], robots_txt)
        self.assertIsNotNone(result["note"])
        self.assertIn("content signals", result["note"].lower())


if __name__ == "__main__":
    unittest.main()
