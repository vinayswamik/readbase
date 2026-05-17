import unittest
from unittest.mock import patch

from src.backend.infrastructure.generation.answerer import (
    MIN_RELEVANCE_SCORE,
    OUT_OF_SCOPE_MESSAGE,
    answer_question,
    parse_anthropic_text,
)


# Anthropic returns a list of content blocks. The app needs to flatten text
# blocks into the single answer string shown in the chat UI.
class AnswererTests(unittest.TestCase):
    def test_parse_anthropic_text_blocks(self):
        data = {
            "content": [
                {"type": "text", "text": "First part."},
                {"type": "text", "text": "Second part."},
            ]
        }

        self.assertEqual(parse_anthropic_text(data), "First part.\nSecond part.")

    def test_answer_question_rejects_low_retrieval_score(self):
        matches = [{"score": MIN_RELEVANCE_SCORE - 0.01, "path": "a.py", "text": "x"}]
        result = answer_question("weather in Paris", matches)
        self.assertEqual(result["mode"], "out_of_scope")
        self.assertEqual(result["answer"], OUT_OF_SCOPE_MESSAGE)
        self.assertEqual(result["sources"], [])

    def test_answer_question_rejects_empty_matches(self):
        result = answer_question("how does auth work?", [])
        self.assertEqual(result["mode"], "out_of_scope")
        self.assertEqual(result["answer"], OUT_OF_SCOPE_MESSAGE)
        self.assertEqual(result["sources"], [])

    def test_answer_question_filters_low_scoring_sources(self):
        matches = [
            {
                "score": MIN_RELEVANCE_SCORE,
                "path": "src/auth.py",
                "start_line": 1,
                "end_line": 10,
                "text": "def login(): ...",
            },
            {
                "score": MIN_RELEVANCE_SCORE - 0.1,
                "path": "noise.py",
                "start_line": 1,
                "end_line": 5,
                "text": "unrelated",
            },
        ]
        with patch(
            "src.backend.infrastructure.generation.answerer.load_llm_settings",
            return_value=(None, None),
        ):
            result = answer_question("how does login work?", matches)
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["path"], "src/auth.py")

    @patch(
        "src.backend.infrastructure.generation.answerer.load_llm_settings",
        return_value=(None, None),
    )
    def test_answer_question_allows_strong_retrieval_without_llm(self, _mock_llm):
        matches = [
            {
                "score": MIN_RELEVANCE_SCORE,
                "path": "src/auth.py",
                "start_line": 1,
                "end_line": 10,
                "text": "def login(): ...",
            }
        ]
        result = answer_question("how does login work?", matches)
        self.assertEqual(result["mode"], "retrieval")
        self.assertIn("src/auth.py", result["answer"])


if __name__ == "__main__":
    # Allows direct execution while keeping standard unittest discovery working.
    unittest.main()
