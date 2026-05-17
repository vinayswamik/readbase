import unittest

from src.backend.infrastructure.retrieval.retriever import build_index, delete_index, search


# Tests are small examples of desired behavior. This one proves simple word
# normalization lets "sessions created" match create_session in code.
class RetrieverTests(unittest.TestCase):
    def tearDown(self):
        delete_index("repo")

    def test_search_prefers_matching_code_terms(self):
        # Two fake chunks are enough to check ranking without cloning a real repo.
        chunks = [
            {
                "id": "1",
                "path": "app/auth/session.py",
                "start_line": 1,
                "end_line": 10,
                "text": "def create_session(user_id):\n    return Session(user_id=user_id)",
            },
            {
                "id": "2",
                "path": "app/billing/invoice.py",
                "start_line": 1,
                "end_line": 10,
                "text": "def create_invoice(customer):\n    return Invoice(customer=customer)",
            },
        ]
        # Build the same kind of index the app saves under .readbase/indexes.
        index = build_index(
            chunks,
            repo_url="https://github.com/example/repo",
            repo_id="repo",
            file_count=2,
        )
        results = search(index, "how are sessions created?", top_k=1)

        # The auth/session chunk should beat billing/invoice for this question.
        self.assertEqual(results[0]["path"], "app/auth/session.py")


if __name__ == "__main__":
    # Allows `python tests/test_retriever.py` in addition to unittest discovery.
    unittest.main()
