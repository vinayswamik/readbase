import unittest

from readbase.answering.answerer import parse_anthropic_text


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


if __name__ == "__main__":
    # Allows direct execution while keeping standard unittest discovery working.
    unittest.main()
