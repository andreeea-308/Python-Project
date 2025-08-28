import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock


# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules to test
try:
    from chatbot import BookRecommendationChatbot, APIKeyError, VectorStoreError, RateLimitError, ChatbotError
    from book_summaries import get_summary_by_title, book_summaries_dict, book_metadata
    from vector_store import BookVectorStore, setup_vector_store
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all project files are in the same directory as this test file")
    sys.exit(1)


class TestBookSummaries(unittest.TestCase):
    """Test the book_summaries module"""

    def test_book_summaries_dict_exists(self):
        """Test that book_summaries_dict is properly loaded"""
        self.assertIsInstance(book_summaries_dict, dict)
        self.assertGreater(len(book_summaries_dict), 0)

    def test_book_metadata_exists(self):
        """Test that book_metadata is properly loaded"""
        self.assertIsInstance(book_metadata, dict)
        self.assertEqual(len(book_metadata), len(book_summaries_dict))

    def test_get_summary_by_title_valid_book(self):
        """Test getting summary for a valid book"""
        # Get first book from dict
        first_book = list(book_summaries_dict.keys())[0]
        summary = get_summary_by_title(first_book)
        self.assertEqual(summary, book_summaries_dict[first_book])

    def test_get_summary_by_title_invalid_book(self):
        """Test getting summary for an invalid book"""
        result = get_summary_by_title("Nonexistent Book")
        self.assertIn("Sorry, I don't have a summary", result)

    def test_get_summary_by_title_case_insensitive(self):
        """Test case-insensitive book title matching"""
        first_book = list(book_summaries_dict.keys())[0]
        summary = get_summary_by_title(first_book.lower())
        self.assertEqual(summary, book_summaries_dict[first_book])

    def test_book_data_integrity(self):
        """Test that all books have required metadata"""
        for title, summary in book_summaries_dict.items():
            self.assertIsInstance(title, str)
            self.assertIsInstance(summary, str)
            self.assertGreater(len(title), 0)
            self.assertGreater(len(summary), 10)  # Summaries should be substantial

            # Check metadata exists
            self.assertIn(title, book_metadata)
            metadata = book_metadata[title]
            self.assertIn('author', metadata)
            self.assertIn('genre', metadata)
            self.assertIn('themes', metadata)


class TestChatbotInitialization(unittest.TestCase):
    """Test chatbot initialization and error handling"""

    def test_initialization_with_invalid_api_key(self):
        """Test that invalid API keys raise proper errors"""
        with self.assertRaises(APIKeyError):
            BookRecommendationChatbot("")

        with self.assertRaises(APIKeyError):
            BookRecommendationChatbot("invalid-key")

        with self.assertRaises(APIKeyError):
            BookRecommendationChatbot("   ")

    @patch('chatbot.setup_vector_store')
    @patch('openai.OpenAI')
    def test_initialization_with_valid_api_key(self, mock_openai, mock_vector_store):
        """Test successful initialization with mocked dependencies"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_models_response = Mock()
        mock_models_response.data = [Mock()]
        mock_client.models.list.return_value = mock_models_response
        mock_openai.return_value = mock_client

        # Mock vector store
        mock_vector_store.return_value = Mock()

        try:
            chatbot = BookRecommendationChatbot("sk-test-key")
            self.assertIsNotNone(chatbot.openai_client)
            self.assertIsNotNone(chatbot.vector_store)
        except Exception as e:
            self.fail(f"Valid initialization failed: {e}")

    @patch('chatbot.setup_vector_store')
    @patch('openai.OpenAI')
    def test_initialization_vector_store_failure(self, mock_openai, mock_vector_store):
        """Test handling of vector store initialization failure"""
        # Mock OpenAI client success
        mock_client = Mock()
        mock_models_response = Mock()
        mock_models_response.data = [Mock()]
        mock_client.models.list.return_value = mock_models_response
        mock_openai.return_value = mock_client

        # Mock vector store failure
        mock_vector_store.side_effect = Exception("Vector store failed")

        with self.assertRaises(VectorStoreError):
            BookRecommendationChatbot("sk-test-key")


class TestChatbotFiltering(unittest.TestCase):
    """Test chatbot filtering functionality"""

    def setUp(self):
        """Set up test chatbot with mocked dependencies"""
        with patch('chatbot.setup_vector_store'), \
                patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_models_response = Mock()
            mock_models_response.data = [Mock()]
            mock_client.models.list.return_value = mock_models_response
            mock_openai.return_value = mock_client

            self.chatbot = BookRecommendationChatbot("sk-test-key")

    def test_inappropriate_content_filter(self):
        """Test inappropriate content filtering"""
        # Test clean content
        self.assertTrue(self.chatbot.filter_inappropriate_content("I love reading books"))

        # Test inappropriate content
        self.assertFalse(self.chatbot.filter_inappropriate_content("This fucking book sucks"))

        # Test edge cases
        self.assertTrue(self.chatbot.filter_inappropriate_content(""))
        self.assertTrue(self.chatbot.filter_inappropriate_content(None))

    def test_book_related_query_detection(self):
        """Test book-related query detection"""
        # Book-related queries
        book_queries = [
            "I want a book about romance",
            "Tell me about Red Rising",
            "What do you recommend for fiction?",
            "Books about dragons",
            "I love reading fantasy novels"
        ]

        for query in book_queries:
            with self.subTest(query=query):
                self.assertTrue(self.chatbot.is_book_related_query(query))

        # Non book-related queries
        non_book_queries = [
            "What's the weather like?",
            "How do I cook pasta?",
            "Tell me about politics",
            "What movies should I watch?",
            "Help me with math homework"
        ]

        for query in non_book_queries:
            with self.subTest(query=query):
                self.assertFalse(self.chatbot.is_book_related_query(query))

    def test_book_query_edge_cases(self):
        """Test edge cases for book query detection"""
        # Edge cases
        self.assertFalse(self.chatbot.is_book_related_query(""))
        self.assertFalse(self.chatbot.is_book_related_query(None))
        self.assertTrue(self.chatbot.is_book_related_query("book"))  # Single keyword


class TestChatbotResponseGeneration(unittest.TestCase):
    """Test chatbot response generation"""

    def setUp(self):
        """Set up test chatbot with mocked dependencies"""
        with patch('chatbot.setup_vector_store'), \
                patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_models_response = Mock()
            mock_models_response.data = [Mock()]
            mock_client.models.list.return_value = mock_models_response
            mock_openai.return_value = mock_client

            self.chatbot = BookRecommendationChatbot("sk-test-key")
            self.chatbot.vector_store = Mock()

    def test_empty_input_handling(self):
        """Test handling of empty or invalid input"""
        # Empty input
        response = self.chatbot.generate_response("")
        self.assertIn("didn't receive any input", response)

        # None input
        response = self.chatbot.generate_response(None)
        self.assertIn("can only process text input", response)

        # Whitespace only
        response = self.chatbot.generate_response("   ")
        self.assertIn("ask me a question", response)

    def test_long_input_handling(self):
        """Test handling of excessively long input"""
        long_input = "book " * 300  # Create a very long string
        response = self.chatbot.generate_response(long_input)
        self.assertIn("too long", response)

    def test_non_book_query_rejection(self):
        """Test rejection of non-book related queries"""
        non_book_query = "What's the weather like today?"
        response = self.chatbot.generate_response(non_book_query)
        self.assertIn("only help with book recommendations", response)

    def test_inappropriate_content_rejection(self):
        """Test rejection of inappropriate content"""
        inappropriate_query = "Recommend some fucking good books"
        response = self.chatbot.generate_response(inappropriate_query)
        self.assertIn("focused on book recommendations", response)

    @patch('chatbot.BookRecommendationChatbot._make_openai_request_with_retry')
    def test_successful_book_query(self, mock_request):
        """Test successful processing of book-related query"""
        # Mock vector store search
        self.chatbot.vector_store.search_books.return_value = [
            {
                'title': 'Red Rising',
                'author': 'Pierce Brown',
                'genre': 'Science Fiction',
                'themes': 'revolution, dystopia',
                'summary_preview': 'A dystopian story...'
            }
        ]

        # Mock OpenAI response
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "I recommend Red Rising because it's a great dystopian novel."
        mock_message.tool_calls = None
        mock_response.choices = [Mock(message=mock_message)]
        mock_request.return_value = mock_response

        response = self.chatbot.generate_response("I want a book about dystopia")
        self.assertIn("Red Rising", response)


class TestFunctionCalling(unittest.TestCase):
    """Test function calling functionality"""

    def setUp(self):
        """Set up test chatbot"""
        with patch('chatbot.setup_vector_store'), \
                patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_models_response = Mock()
            mock_models_response.data = [Mock()]
            mock_client.models.list.return_value = mock_models_response
            mock_openai.return_value = mock_client

            self.chatbot = BookRecommendationChatbot("sk-test-key")

    def test_get_summary_function_call(self):
        """Test get_summary_by_title function call"""
        # Valid book
        first_book = list(book_summaries_dict.keys())[0]
        result = self.chatbot.call_function("get_summary_by_title", {"title": first_book})
        self.assertEqual(result, book_summaries_dict[first_book])

        # Invalid book
        result = self.chatbot.call_function("get_summary_by_title", {"title": "Nonexistent Book"})
        self.assertIn("Sorry, I don't have a summary", result)

        # No title provided
        result = self.chatbot.call_function("get_summary_by_title", {})
        self.assertIn("No book title provided", result)

    def test_unknown_function_call(self):
        """Test handling of unknown function calls"""
        result = self.chatbot.call_function("unknown_function", {})
        self.assertIn("Unknown function", result)

    def test_invalid_function_parameters(self):
        """Test handling of invalid function parameters"""
        result = self.chatbot.call_function("", {"title": "test"})
        self.assertIn("Invalid function call", result)

        result = self.chatbot.call_function("get_summary_by_title", None)
        self.assertIn("Invalid function call", result)


class TestErrorHandling(unittest.TestCase):
    """Test comprehensive error handling"""

    def setUp(self):
        """Set up test chatbot"""
        with patch('chatbot.setup_vector_store'), \
                patch('openai.OpenAI') as mock_openai:
            mock_client = Mock()
            mock_models_response = Mock()
            mock_models_response.data = [Mock()]
            mock_client.models.list.return_value = mock_models_response
            mock_openai.return_value = mock_client

            self.chatbot = BookRecommendationChatbot("sk-test-key")
            self.chatbot.vector_store = Mock()

    @patch('openai.OpenAI')
    def test_api_rate_limit_handling(self, mock_openai_class):
        """Test handling of API rate limits"""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        mock_openai_class.return_value = mock_client

        # Mock other required methods
        mock_models_response = Mock()
        mock_models_response.data = [Mock()]
        mock_client.models.list.return_value = mock_models_response

        self.chatbot.openai_client = mock_client
        self.chatbot.vector_store.search_books.return_value = []

        response = self.chatbot.generate_response("Tell me about books")
        self.assertIn("unexpected error", response.lower())

    def test_vector_store_failure_handling(self):
        """Test handling of vector store failures"""
        self.chatbot.vector_store.search_books.side_effect = Exception("Vector store failed")

        # Should not crash, should return graceful error message
        response = self.chatbot.generate_response("Tell me about fantasy books")
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)


class TestVectorStore(unittest.TestCase):
    """Test vector store functionality (mocked)"""

    def setUp(self):
        """Set up temporary directory for testing"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory"""
        shutil.rmtree(self.temp_dir)

    @patch('openai.OpenAI')
    @patch('chromadb.PersistentClient')
    def test_vector_store_initialization(self, mock_chroma, mock_openai):
        """Test vector store initialization"""
        # Mock ChromaDB
        mock_collection = Mock()
        mock_client = Mock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection.return_value = mock_collection
        mock_chroma.return_value = mock_client

        # Mock OpenAI
        mock_openai.return_value = Mock()

        try:
            vector_store = BookVectorStore("sk-test-key", self.temp_dir)
            self.assertIsNotNone(vector_store.collection)
        except Exception as e:
            self.fail(f"Vector store initialization failed: {e}")


class TestIntegration(unittest.TestCase):
    """Integration tests"""

    @patch('chatbot.setup_vector_store')
    @patch('openai.OpenAI')
    def test_full_workflow_mock(self, mock_openai, mock_vector_store):
        """Test full workflow with mocked dependencies"""
        # Mock OpenAI client
        mock_client = Mock()
        mock_models_response = Mock()
        mock_models_response.data = [Mock()]
        mock_client.models.list.return_value = mock_models_response

        # Mock chat completion response
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "I recommend Red Rising for dystopian fiction."
        mock_message.tool_calls = None
        mock_response.choices = [Mock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Mock vector store
        mock_vs = Mock()
        mock_vs.search_books.return_value = [
            {
                'title': 'Red Rising',
                'author': 'Pierce Brown',
                'genre': 'Science Fiction',
                'themes': 'revolution, dystopia',
                'summary_preview': 'A dystopian story...'
            }
        ]
        mock_vector_store.return_value = mock_vs

        # Test workflow
        chatbot = BookRecommendationChatbot("sk-test-key")
        response = chatbot.generate_response("I want a dystopian book")

        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        self.assertIn("Red Rising", response)


def run_all_tests():
    """Run all tests and generate report"""
    # Create test suite
    test_suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestBookSummaries,
        TestChatbotInitialization,
        TestChatbotFiltering,
        TestChatbotResponseGeneration,
        TestFunctionCalling,
        TestErrorHandling,
        TestVectorStore,
        TestIntegration
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(test_suite)

    # Print summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {(result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100:.1f}%")

    if result.failures:
        print("\nFAILURES:")
        for test, error in result.failures:
            print(f"- {test}: {error.strip().split('AssertionError:')[-1].strip()}")

    if result.errors:
        print("\nERRORS:")
        for test, error in result.errors:
            print(f"- {test}: {error.strip().split('Exception:')[-1].strip()}")

    return result.wasSuccessful()


if __name__ == "__main__":
    print("Running comprehensive test suite for Book Recommendation Chatbot...")
    print("Note: Some tests use mocked dependencies to avoid requiring actual API keys")
    print("=" * 70)

    success = run_all_tests()

    if success:
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed. Check the output above for details.")

    sys.exit(0 if success else 1)