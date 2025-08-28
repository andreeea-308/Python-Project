import openai
import json
import os
import re
import time
import logging
from typing import List, Dict, Any
from vector_store import setup_vector_store
from book_summaries import get_summary_by_title, book_summaries_dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ChatbotError(Exception):
    """Base exception class for chatbot errors"""
    pass


class APIKeyError(ChatbotError):
    """Raised when API key is invalid or missing"""
    pass


class VectorStoreError(ChatbotError):
    """Raised when vector store operations fail"""
    pass


class RateLimitError(ChatbotError):
    """Raised when API rate limits are exceeded"""
    pass


class BookRecommendationChatbot:
    def __init__(self, openai_api_key: str, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the chatbot with OpenAI client and vector store

        Args:
            openai_api_key: Your OpenAI API key
            max_retries: Maximum number of retries for API calls
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Validate API key
        if not openai_api_key or not openai_api_key.strip():
            raise APIKeyError("OpenAI API key is required and cannot be empty")

        if not openai_api_key.startswith('sk-'):
            raise APIKeyError("Invalid OpenAI API key format. Key should start with 'sk-'")

        try:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
            # Test API key validity
            self._test_api_connection()
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise APIKeyError(f"Failed to initialize OpenAI client: {str(e)}")

        try:
            logger.info("Setting up vector store...")
            self.vector_store = setup_vector_store(openai_api_key, force_reload=False)
            logger.info("Vector store setup complete")
        except Exception as e:
            logger.error(f"Failed to setup vector store: {e}")
            raise VectorStoreError(f"Failed to initialize vector store: {str(e)}")

        # Initialize other components
        self._initialize_filters_and_data()
        logger.info("Chatbot initialization complete!")

    def _test_api_connection(self):
        """Test if the API key is valid by making a simple request"""
        try:
            response = self.openai_client.models.list()
            if not response.data:
                raise APIKeyError("API key is valid but no models accessible")
        except openai.AuthenticationError:
            raise APIKeyError("Invalid API key - authentication failed")
        except openai.RateLimitError:
            raise RateLimitError("Rate limit exceeded during API key validation")
        except Exception as e:
            raise APIKeyError(f"API connection test failed: {str(e)}")

    def _initialize_filters_and_data(self):
        """Initialize filters, keywords, and other data structures"""
        try:
            # Inappropriate language filter
            self.inappropriate_words = {
                'fuck', 'shit', 'damn', 'bitch', 'asshole'
            }

            # Book-related keywords for topic detection
            self.book_keywords = {
                'book', 'books', 'read', 'reading', 'novel', 'story', 'author', 'writer',
                'fiction', 'nonfiction', 'genre', 'chapter', 'plot', 'character', 'protagonist',
                'recommend', 'recommendation', 'suggest', 'literature', 'biography', 'memoir',
                'fantasy', 'romance', 'mystery', 'thriller', 'horror', 'science fiction',
                'historical', 'contemporary', 'classic', 'bestseller', 'review', 'summary'
            }

            # Validate book database
            if not book_summaries_dict:
                raise ChatbotError("Book database is empty")

            # Get list of available book titles for validation
            self.available_books = set(book_summaries_dict.keys())
            self.available_books_lower = {title.lower() for title in book_summaries_dict.keys()}

            # Function definition for OpenAI
            self.tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_summary_by_title",
                        "description": "Get the full detailed summary for a specific book by its exact title. Only works for books in our database.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "The exact title of the book to get summary for"
                                }
                            },
                            "required": ["title"]
                        }
                    }
                }
            ]

            # System prompt
            self.system_prompt = f"""You are a specialized book recommendation assistant. You have access to a curated database of exactly {len(book_summaries_dict)} books. Your strict guidelines are:

IMPORTANT RESTRICTIONS:
1. ONLY recommend books from your database: {', '.join(list(book_summaries_dict.keys()))}
2. ONLY answer questions related to books, reading, and literature
3. If asked about topics unrelated to books, respond with: "I'm sorry, but I can only help with book recommendations and questions about literature. How can I assist you in finding your next great read?"

YOUR CAPABILITIES:
- Recommend books from your database based on user preferences
- Provide detailed summaries using the get_summary_by_title function
- Discuss themes, genres, and authors from your collection
- Help users find books similar to ones they've enjoyed
- Answer general questions about reading and literature

WHEN MAKING RECOMMENDATIONS:
- Always explain WHY you're recommending a specific book
- Only suggest books from your available database
- After recommending a book, automatically call get_summary_by_title to provide the full summary
- Include the author's name in recommendations
- If a user asks about a book not in your database, say you don't have information about it and suggest similar books from your collection

Available books in your database: {', '.join(sorted(book_summaries_dict.keys()))}

Remember: Stay focused on books and literature only. Be helpful, but maintain these boundaries."""

        except Exception as e:
            logger.error(f"Failed to initialize filters and data: {e}")
            raise ChatbotError(f"Failed to initialize chatbot components: {str(e)}")

    def is_book_related_query(self, text: str) -> bool:
        """
        Check if the query is related to books or literature

        Args:
            text: User input text

        Returns:
            True if query is book-related, False otherwise
        """
        try:
            if not text or not isinstance(text, str):
                return False

            text_lower = text.lower().strip()

            if not text_lower:
                return False

            # Check for book-related keywords
            for keyword in self.book_keywords:
                if keyword in text_lower:
                    return True

            # Check if any book title is mentioned
            for book_title in self.available_books_lower:
                if book_title in text_lower:
                    return True

            # Check for author names or book-specific terms
            book_related_patterns = [
                r'\bread\b', r'\breading\b', r'\bnovel\b', r'\bstory\b',
                r'\bfiction\b', r'\bnonfiction\b', r'\bauthor\b', r'\bwriter\b',
                r'\bgenre\b', r'\bplot\b', r'\bcharacter\b', r'\brecommend\b'
            ]

            for pattern in book_related_patterns:
                if re.search(pattern, text_lower):
                    return True

            return False

        except Exception as e:
            logger.error(f"Error in book-related query detection: {e}")
            # Default to True to avoid blocking legitimate requests
            return True

    def filter_inappropriate_content(self, text: str) -> bool:
        """
        Simple inappropriate content filter

        Args:
            text: Input text to check

        Returns:
            True if content is appropriate, False if inappropriate
        """
        try:
            if not text or not isinstance(text, str):
                return True

            text_lower = text.lower().strip()

            # Check for inappropriate words
            for word in self.inappropriate_words:
                if word in text_lower:
                    logger.warning(f"Inappropriate content detected in user input")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error in content filtering: {e}")
            # Default to True (appropriate) if filtering fails
            return True

    def search_relevant_books(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search for relevant books based on user query with error handling

        Args:
            query: User's search query
            n_results: Number of results to return

        Returns:
            List of relevant books
        """
        try:
            if not query or not isinstance(query, str):
                logger.warning("Invalid query provided to search_relevant_books")
                return []

            if not self.vector_store:
                raise VectorStoreError("Vector store not initialized")

            return self.vector_store.search_books(query, n_results=n_results)

        except Exception as e:
            logger.error(f"Error searching books: {e}")
            # Return empty list to allow graceful degradation
            return []

    def call_function(self, function_name: str, arguments: Dict[str, Any]) -> str:
        """
        Handle function calls from OpenAI with error handling

        Args:
            function_name: Name of function to call
            arguments: Function arguments

        Returns:
            Function result as string
        """
        try:
            if not function_name or not isinstance(arguments, dict):
                return "Invalid function call parameters"

            if function_name == "get_summary_by_title":
                title = arguments.get("title", "")
                if not title:
                    return "No book title provided"

                result = get_summary_by_title(title)
                logger.info(f"Retrieved summary for book: {title}")
                return result
            else:
                logger.warning(f"Unknown function called: {function_name}")
                return f"Unknown function: {function_name}"

        except Exception as e:
            logger.error(f"Error in function call {function_name}: {e}")
            return f"Error retrieving information: {str(e)}"

    def _make_openai_request_with_retry(self, messages: List[Dict], **kwargs) -> Any:
        """
        Make OpenAI API request with retry logic

        Args:
            messages: Messages for the API call
            **kwargs: Additional arguments for the API call

        Returns:
            API response
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    **kwargs
                )
                logger.info(f"OpenAI API request successful on attempt {attempt + 1}")
                return response

            except openai.RateLimitError as e:
                last_exception = e
                logger.warning(f"Rate limit error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    raise RateLimitError("Rate limit exceeded after all retries")

            except openai.AuthenticationError as e:
                logger.error(f"Authentication error: {e}")
                raise APIKeyError(f"API authentication failed: {str(e)}")

            except openai.APIError as e:
                last_exception = e
                logger.warning(f"API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise ChatbotError(f"API error after all retries: {str(e)}")

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)

        # If all retries failed
        raise ChatbotError(f"All API request attempts failed. Last error: {str(last_exception)}")

    def generate_response(self, user_query: str) -> str:
        """
        Generate chatbot response with comprehensive error handling

        Args:
            user_query: User's question or request

        Returns:
            Chatbot response
        """
        try:
            # Input validation
            if user_query is None:
                return "I can only process text input. Please ask me about books in text format."

            if not isinstance(user_query, str):
                return "I can only process text input. Please ask me about books in text format."

            if not user_query:
                return "I didn't receive any input. How can I help you find a great book?"

            user_query = user_query.strip()
            if not user_query:
                return "Please ask me a question about books or literature."

            if len(user_query) > 1000:
                return "Your message is too long. Please ask a shorter question about books."

            # Filter inappropriate content
            if not self.filter_inappropriate_content(user_query):
                return ("I appreciate your message, but I'd prefer to keep our conversation "
                        "focused on book recommendations. How can I help you find a great book to read?")

            # Check if query is book-related
            if not self.is_book_related_query(user_query):
                return ("I'm sorry, but I can only help with book recommendations and questions about literature. "
                        "How can I assist you in finding your next great read?")

            # Search for relevant books
            relevant_books = self.search_relevant_books(user_query, n_results=3)

            # Create context from search results
            if relevant_books:
                context = "Here are the most relevant books from your available database:\n\n"
                for i, book in enumerate(relevant_books):
                    context += f"{i + 1}. **{book['title']}** by {book['author']}\n"
                    context += f"   Genre: {book['genre']} | Themes: {book['themes']}\n"
                    context += f"   Preview: {book['summary_preview']}\n\n"
            else:
                context = "No specific books found in search, but I can recommend from my available collection.\n"

            # Create messages for OpenAI API
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Available books from database:\n{context}\n\nUser question: {user_query}"}
            ]

            # Make initial API request
            response = self._make_openai_request_with_retry(
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )

            message = response.choices[0].message

            # Check if the model wants to call a function
            if message.tool_calls:
                try:
                    # Execute function calls
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name

                        try:
                            function_args = json.loads(tool_call.function.arguments)
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON in function arguments: {e}")
                            continue

                        # Call the function
                        function_result = self.call_function(function_name, function_args)

                        # Add function call and response to conversation
                        messages.append({
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [tool_call]
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": function_result
                        })

                    # Get final response with function results
                    final_response = self._make_openai_request_with_retry(
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1500
                    )

                    return final_response.choices[
                        0].message.content or "I couldn't generate a proper response. Please try asking again."

                except Exception as e:
                    logger.error(f"Error in function calling: {e}")
                    return "I encountered an issue while processing your request. Please try asking about books again."
            else:
                return message.content or "I couldn't generate a response. Please try asking about books again."

        except RateLimitError:
            return ("I'm currently experiencing high demand. Please wait a moment and try again. "
                    "You can also try asking about a specific book from my collection.")

        except APIKeyError:
            logger.error("API key error in generate_response")
            return ("I'm experiencing authentication issues. Please contact support if this continues. "
                    "In the meantime, I can tell you about books in my database if you ask about specific titles.")

        except VectorStoreError:
            logger.error("Vector store error in generate_response")
            return ("I'm having trouble accessing my book database. I can still help with specific book titles "
                    "if you mention them directly.")

        except Exception as e:
            logger.error(f"Unexpected error in generate_response: {e}")
            return ("I apologize, but I encountered an unexpected error. Please try asking about books again, "
                    "or mention a specific book title from my collection.")


def run_cli_chatbot():
    """
    Run the chatbot in CLI mode with error handling
    """
    print("Welcome to the Book Recommendation Chatbot!")
    print("=" * 50)

    try:
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: Please set your OPENAI_API_KEY environment variable")
            print("   Example: export OPENAI_API_KEY='your-api-key-here'")
            return

        # Initialize chatbot
        print("\nInitializing chatbot and vector store...")
        chatbot = BookRecommendationChatbot(api_key)
        print("Chatbot ready!")

        print(f"\nI can help you find great books from my curated database!")
        print("Available books include:")
        for i, title in enumerate(list(book_summaries_dict.keys())[:5]):
            print(f"  • {title}")
        print(f"  ... and {len(book_summaries_dict) - 5} more!")

        print("\nTry asking things like:")
        print("  • 'I want a book about friendship and magic'")
        print("  • 'What do you recommend for someone who loves war stories?'")
        print("  • 'Tell me about Red Rising'")
        print("  • 'Books about artificial intelligence'")
        print("\nType 'quit' to exit.")
        print("=" * 50)

    except APIKeyError as e:
        print(f"API Key Error: {e}")
        print("Please check your OpenAI API key and try again.")
        return
    except VectorStoreError as e:
        print(f"Vector Store Error: {e}")
        print("Please check your setup and try again.")
        return
    except Exception as e:
        print(f"Initialization Error: {e}")
        print("Please check your setup and try again.")
        return

    # Chat loop
    while True:
        try:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nThanks for using the Book Recommendation Chatbot! Happy reading!")
                break

            if not user_input:
                continue

            print("\nAssistant: ", end="")
            response = chatbot.generate_response(user_input)
            print(response)

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error in chat loop: {e}")
            print(f"\nUnexpected error occurred. Please try again.")


if __name__ == "__main__":
    run_cli_chatbot()