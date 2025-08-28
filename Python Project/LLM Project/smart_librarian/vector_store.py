import chromadb
import openai
import os
import time
from typing import List, Dict, Any
from book_summaries import get_all_books_data, book_summaries_dict
import pandas as pd


class BookVectorStore:
    def __init__(self, openai_api_key: str, persist_directory: str = "./chroma_book_db"):
        """
        Initialize the vector store with OpenAI embeddings

        Args:
            openai_api_key: Your OpenAI API key
            persist_directory: Directory to persist the ChromaDB
        """
        # Set up OpenAI client
        self.openai_client = openai.OpenAI(api_key=openai_api_key)

        # Initialize ChromaDB with persistence
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)

        # Create or get collection
        try:
            self.collection = self.chroma_client.get_collection("book_summaries")
            print("Connected to existing book_summaries collection")
        except:
            self.collection = self.chroma_client.create_collection(
                name="book_summaries",
                metadata={"description": "Book summaries with OpenAI embeddings"}
            )
            print("Created new book_summaries collection")

    def get_openai_embedding(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """
        Get embedding from OpenAI API

        Args:
            text: Text to embed
            model: OpenAI embedding model to use

        Returns:
            List of embedding values
        """
        try:
            # Replace newlines for better embedding quality
            text = text.replace("\n", " ")

            response = self.openai_client.embeddings.create(
                input=[text],
                model=model
            )

            return response.data[0].embedding
        except Exception as e:
            print(f"Error getting embedding for text: {e}")
            raise

    def load_books_to_vector_store(self, force_reload: bool = False):
        """
        Load all books into the vector store with OpenAI embeddings

        Args:
            force_reload: If True, clear existing data and reload
        """
        if force_reload:
            # Clear existing collection
            try:
                self.chroma_client.delete_collection("book_summaries")
                self.collection = self.chroma_client.create_collection(
                    name="book_summaries",
                    metadata={"description": "Book summaries with OpenAI embeddings"}
                )
                print("Cleared existing collection for reload")
            except:
                pass

        # Check if collection already has data
        existing_count = self.collection.count()
        if existing_count > 0 and not force_reload:
            print(f"Collection already contains {existing_count} books. Use force_reload=True to reload.")
            return

        # Get all book data
        books_data = get_all_books_data()
        print(f"Loading {len(books_data)} books into vector store...")

        # Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []
        embeddings = []

        for i, book in enumerate(books_data):
            # Combine summary with themes for better search
            searchable_text = f"{book['summary']} Themes: {book['themes']}"

            print(f"Processing book {i + 1}/{len(books_data)}: {book['title']}")

            # Get OpenAI embedding
            try:
                embedding = self.get_openai_embedding(searchable_text)

                documents.append(book['summary'])  # Store original summary

                # Store metadata
                metadata = {
                    "title": book['title'],
                    "author": book['author'],
                    "genre": book['genre'],
                    "themes": book['themes'],
                    "target_audience": book['target_audience']
                }
                metadatas.append(metadata)

                # Create ID
                book_id = f"book_{i}_{book['title'].replace(' ', '_').lower()}"
                ids.append(book_id)

                embeddings.append(embedding)

                # Small delay to respect rate limits
                time.sleep(0.1)

            except Exception as e:
                print(f"Error processing {book['title']}: {e}")
                continue

        if embeddings:
            # Add to ChromaDB
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            print(f"Successfully loaded {len(embeddings)} books into vector store!")
        else:
            print("No books were successfully processed")

    def search_books(self, query: str, n_results: int = 3, genre_filter: str = None) -> List[Dict[str, Any]]:
        """
        Search for books using semantic similarity

        Args:
            query: Search query
            n_results: Number of results to return
            genre_filter: Optional genre filter

        Returns:
            List of matching books with metadata
        """
        try:
            # Get query embedding
            query_embedding = self.get_openai_embedding(query)

            # Prepare where clause for filtering
            where_clause = None
            if genre_filter:
                where_clause = {"genre": genre_filter}

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause
            )

            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        "title": results['metadatas'][0][i]['title'],
                        "author": results['metadatas'][0][i]['author'],
                        "genre": results['metadatas'][0][i]['genre'],
                        "themes": results['metadatas'][0][i]['themes'],
                        "summary_preview": results['documents'][0][i][:200] + "...",
                        "similarity_score": 1 - results['distances'][0][i] if 'distances' in results else None
                    }
                    formatted_results.append(result)

            return formatted_results

        except Exception as e:
            print(f"Error searching books: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection"""
        count = self.collection.count()

        # Get sample of metadata to show available genres
        if count > 0:
            sample = self.collection.get(limit=count)
            genres = set()
            authors = set()

            for metadata in sample['metadatas']:
                genres.add(metadata.get('genre', 'Unknown'))
                authors.add(metadata.get('author', 'Unknown'))

            return {
                "total_books": count,
                "available_genres": sorted(list(genres)),
                "available_authors": sorted(list(authors))
            }
        else:
            return {"total_books": 0, "available_genres": [], "available_authors": []}


# Utility function for easy setup
def setup_vector_store(openai_api_key: str, force_reload: bool = False) -> BookVectorStore:
    """
    Convenience function to set up the vector store

    Args:
        openai_api_key: Your OpenAI API key
        force_reload: Whether to force reload all data

    Returns:
        Configured BookVectorStore instance
    """
    print("Setting up Book Vector Store with OpenAI embeddings...")

    # Create vector store
    vector_store = BookVectorStore(openai_api_key)

    # Load books
    vector_store.load_books_to_vector_store(force_reload=force_reload)

    # Show stats
    stats = vector_store.get_collection_stats()
    print(f"\nVector Store Stats:")
    print(f"  Total books: {stats['total_books']}")
    print(
        f"   Genres: {', '.join(stats['available_genres'][:5])}{'...' if len(stats['available_genres']) > 5 else ''}")
    print(
        f"   Authors: {', '.join(stats['available_authors'][:3])}{'...' if len(stats['available_authors']) > 3 else ''}")

    return vector_store


if __name__ == "__main__":
    # Test the vector store setup
    import os

    # Get API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        print("   Example: export OPENAI_API_KEY='your-api-key-here'")
        exit(1)

    # Setup vector store
    vector_store = setup_vector_store(api_key, force_reload=False)

    # Test search
    print("\nTesting search functionality:")

    test_queries = [
        "books about friendship and magic",
        "war stories and conflict",
        "dystopian society and control",
        "coming of age and growing up"
    ]

    for query in test_queries:
        print(f"\n--- Search: '{query}' ---")
        results = vector_store.search_books(query, n_results=2)

        for i, book in enumerate(results):
            print(f"{i + 1}. {book['title']} by {book['author']}")
            print(f"   Genre: {book['genre']} | Themes: {book['themes']}")
            if book['similarity_score']:
                print(f"   Similarity: {book['similarity_score']:.3f}")