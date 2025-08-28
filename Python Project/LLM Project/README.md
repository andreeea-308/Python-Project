# Smart Librarian AI - RAG Book Recommendation Chatbot

An intelligent AI-powered chatbot that recommends books using **Retrieval Augmented Generation (RAG)** with **ChromaDB vector database**, **OpenAI embeddings**, and **function calling**.

---

## Project Overview

This project implements a complete RAG (Retrieval Augmented Generation) pipeline that:

* Uses **ChromaDB** as a vector database with **OpenAI embeddings** (`text-embedding-3-small`)
* Implements **semantic search** to find relevant books based on themes, moods, and topics
* Uses **OpenAI GPT** with **function calling** for detailed book summaries
* Provides both **CLI** and **modern Streamlit web interfaces**
* Includes **reading progress tracking** and **advanced search features**

---

## Features

### Core Functionality
* **AI-Powered Recommendations**: Personalized book suggestions using GPT-4 and semantic search
* **Smart Search**: Find books by themes, moods, or specific topics with vector search
* **Reading Tracker**: Track reading progress, ratings, and personal notes
* **Interactive Chat**: Natural language conversations about books
* **Detailed Summaries**: Comprehensive book summaries with automatic function calling
* **Curated Database**: 20+ carefully selected books across multiple genres

### Advanced Features (Optional)
* **Text-to-Speech**: Convert recommendations to audio
* **Voice Input**: Ask questions using speech recognition
* **Image Generation**: Create book cover visualizations (DALL-E integration)
* **Content Filtering**: Basic inappropriate content detection
* **Analytics**: Reading statistics and progress tracking

---

## Book Collection

The chatbot includes **20 curated books** across various genres:

**Science Fiction**
* Red Rising (Pierce Brown)
* Neuromancer (William Gibson)
* Life 3.0 (Max Tegmark)

**Fantasy/Romance**
* Fourth Wing (Rebecca Yarros)
* Keeping 13 (Chloe Walsh)

**Mystery/Thriller**
* The Naturals (Jennifer Lynn Barnes)
* The Housemaid (Freida McFadden)

**Self-Help/Business**
* Atomic Habits (James Clear)
* The Lean Startup (Eric Ries)

**Literary Fiction**
* The Vanishing Half (Brit Bennett)
* Wolf Hall (Hilary Mantel)

**Psychology/Science**
* Thinking, Fast and Slow (Daniel Kahneman)
* Braiding Sweetgrass (Robin Wall Kimmerer)

---

## Quick Start

### Prerequisites
* Python 3.8+
* OpenAI API key
* Windows/Mac/Linux

### Installation

**1. Clone or download the project**
```bash
git clone <repository-url>
cd smart_librarian
```

**2. Create virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set OpenAI API key**
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="your_openai_api_key_here"

# Mac/Linux
export OPENAI_API_KEY="your_openai_api_key_here"
```

**5. Run the application**

**Option A: Modern Web Interface (Recommended)**
```bash
streamlit run modern_streamlit_app.py
```

**Option B: Standard Web Interface**
```bash
streamlit run streamlit_app.py
```

**Option C: Command Line Interface**
```bash
python chatbot.py
```

---

## Project Structure

```
smart_librarian/
├── book_summaries.py          # Book dataset and retrieval function
├── vector_store.py            # ChromaDB setup with OpenAI embeddings
├── chatbot.py                # Main chatbot with CLI interface
├── streamlit_app.py          # Standard Streamlit web interface
├── modern_streamlit_app.py   # Modern dark-themed web interface
├── requirements.txt          # Python dependencies
├── chroma_book_db/           # ChromaDB database (auto-created)
├── .env                      # Environment variables (create manually)
└── README.md                # This file
```

---

## Technical Architecture

### RAG Pipeline
```
User Query → OpenAI Embedding → ChromaDB Search → Context + Query → GPT Response
```

### Key Components

**1. BookVectorStore Class** (`vector_store.py`)
* ChromaDB integration with persistence
* OpenAI embedding generation (`text-embedding-3-small`)
* Semantic search functionality
* Batch processing for efficient loading

**2. BookRecommendationChatbot Class** (`chatbot.py`)
* OpenAI GPT integration with function calling
* RAG workflow implementation
* Content filtering and response generation
* Error handling and retry logic

**3. Function Calling Tool**
```python
def get_summary_by_title(title: str) -> str:
    """Returns complete book summary by exact title match"""
```

**4. Streamlit Interfaces**
* Modern dark-themed UI with glassmorphism effects
* Interactive chat with message history
* Book browsing and filtering
* Reading progress tracking

---

## Usage Examples

### Chat Queries
```
"I want a book about friendship and magic"
"What do you recommend for someone who loves war stories?"
"Books about artificial intelligence and the future"
"Tell me about Red Rising"
"I need something for personal development"
```

### Search Filters
* **By Genre**: Science Fiction, Fantasy, Mystery, Self-Help, etc.
* **By Themes**: friendship, AI, war, dystopia, personal growth
* **By Author**: Pierce Brown, James Clear, Rebecca Yarros, etc.
* **By Audience**: Young Adult, Adult, New Adult

---

## Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Customization Options

**Add New Books** (in `book_summaries.py`):
```
book_summaries_dict["New Book Title"] = "Detailed summary here..."

book_metadata["New Book Title"] = {
    "author": "Author Name",
    "genre": "Genre", 
    "themes": ["theme1", "theme2"],
    "target_audience": "Adult"
}
```

**Modify Search Parameters**:
```
# In vector_store.py
vector_store.search_books(query, n_results=5)  # Adjust result count
```

**Content Filter**:
```
# In chatbot.py - add words to filter
self.inappropriate_words = {'word1', 'word2', 'word3'}
```

---

## Performance & Costs

### Setup Performance
* **Initial embedding generation**: ~30 seconds (one-time)
* **Database size**: ~2MB for 20 books
* **Search speed**: <1 second for semantic queries
* **Response time**: 2-5 seconds (OpenAI API dependent)

### OpenAI API Usage
* **Setup cost**: ~$0.01 (embedding generation)
* **Per conversation**: ~$0.01-0.05 depending on length
* **Monthly usage** (100 queries): ~$1-5
* **Function calls**: +1 API call when detailed summaries requested

### Scalability
* **Books supported**: Easily scalable to 1000+ books
* **Concurrent users**: Limited by Streamlit (1 user per instance)
* **Memory usage**: ~50MB base + ~1MB per 100 books

---

## Troubleshooting

### Common Issues

**1. API Key Error**
```bash
# Set environment variable
export OPENAI_API_KEY="your_key_here"

# Verify it's set
echo $OPENAI_API_KEY
```

**2. ChromaDB Database Issues**
```bash
# Delete and recreate database
rm -rf chroma_book_db/
python vector_store.py
```

**3. Package Installation Errors**
```bash
# Upgrade pip and reinstall
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**4. Streamlit Session State Errors**
```bash
# Use the modern app instead
streamlit run modern_streamlit_app.py
```

**5. Empty Search Results**
* Check if vector store is populated: `python vector_store.py`
* Verify API key has sufficient quota
* Try different search terms or themes

### Dependencies for Optional Features
```bash
# Text-to-Speech
pip install pyttsx3

# Speech-to-Text
pip install SpeechRecognition pyaudio

# Image Processing
pip install pillow requests

# Environment variables
pip install python-dotenv
```

---

## Testing

### Manual Testing Checklist

**Setup Verification**:
- [ ] Virtual environment activated
- [ ] All packages installed successfully
- [ ] API key set and valid
- [ ] Vector database created and populated

**Core Functionality**:
- [ ] CLI chatbot responds to queries
- [ ] Streamlit interface loads without errors
- [ ] Book search returns relevant results
- [ ] Function calling retrieves summaries
- [ ] Reading tracker saves progress

**Sample Test Queries**:
```python
test_queries = [
    "I want a book about friendship and magic",
    "Recommend something for personal development",
    "Tell me about Red Rising",
    "Books similar to 1984",
    "What's good for someone who loves romance?"
]
```
