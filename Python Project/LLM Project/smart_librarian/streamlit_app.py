import streamlit as st
import openai
import os
import re
import base64
from io import BytesIO
from chatbot import BookRecommendationChatbot
from book_summaries import book_summaries_dict, book_metadata

# Optional imports for advanced features
try:
    import pyttsx3

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import speech_recognition as sr

    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False

try:
    from PIL import Image
    import requests

    IMAGE_GEN_AVAILABLE = True
except ImportError:
    IMAGE_GEN_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="Book Recommendation Chatbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 30px;
    }
    .book-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 4px solid #1f77b4;
        color: #333333;
    }
    .book-card h4 {
        color: #1f77b4;
        margin-bottom: 10px;
    }
    .book-card p {
        color: #333333;
        margin: 5px 0;
    }
    .chat-message {
        padding: 10px;
        margin: 5px 0;
        border-radius: 10px;
    }
    .user-message {
        background-color: #e1f5fe;
        text-align: right;
        color: #0d47a1;
    }
    .assistant-message {
        background-color: #f5f5f5;
        color: #333333;
    }
    .feature-box {
        background-color: #fff3e0;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
        color: #333333;
    }
    /* Ensure all text in containers is dark */
    .stContainer {
        color: #333333;
    }
    /* Fix sidebar text */
    .css-1d391kg {
        color: #333333;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if 'chatbot' not in st.session_state:
        st.session_state.chatbot = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'api_key_set' not in st.session_state:
        st.session_state.api_key_set = False
    if 'selected_example' not in st.session_state:
        st.session_state.selected_example = ""


def setup_sidebar():
    """Setup sidebar with configuration and features"""
    with st.sidebar:
        st.header("🔧 Configuration")

        # API Key input
        api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Enter your OpenAI API key to start chatting"
        )

        if api_key and not st.session_state.api_key_set:
            try:
                with st.spinner("Initializing chatbot..."):
                    st.session_state.chatbot = BookRecommendationChatbot(api_key)
                    st.session_state.api_key_set = True
                st.success("✅ Chatbot initialized!")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

        st.divider()

        # Book database info
        st.header("📚 Book Database")
        st.metric("Total Books", len(book_summaries_dict))

        # Show available genres
        genres = set()
        for metadata in book_metadata.values():
            genres.add(metadata.get('genre', 'Unknown'))

        st.write("**Available Genres:**")
        for genre in sorted(genres):
            st.write(f"• {genre}")

        st.divider()

        # Advanced Features
        st.header("🚀 Advanced Features")

        # Text-to-Speech
        if TTS_AVAILABLE:
            st.session_state.tts_enabled = st.checkbox("🔊 Text-to-Speech", help="Convert responses to audio")
        else:
            st.info("📦 Install pyttsx3 for text-to-speech")

        # Speech-to-Text
        if STT_AVAILABLE:
            st.session_state.stt_enabled = st.checkbox("🎤 Voice Input", help="Use voice to ask questions")
        else:
            st.info("📦 Install SpeechRecognition for voice input")

        # Image Generation
        if IMAGE_GEN_AVAILABLE:
            st.session_state.image_gen_enabled = st.checkbox("🎨 Generate Book Images",
                                                             help="Create images for book recommendations")
        else:
            st.info("📦 Install Pillow and requests for image generation")

        # Content Filter
        st.session_state.content_filter = st.checkbox("🛡️ Content Filter", value=True,
                                                      help="Filter inappropriate content")

        st.divider()

        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.chat_history = []
            st.rerun()


def display_chat_history():
    """Display chat history with styling"""
    for message in st.session_state.chat_history:
        if message['role'] == 'user':
            st.markdown(f"""
            <div class="chat-message user-message">
                <strong>🧑 You:</strong> {message['content']}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-message assistant-message">
                <strong>🤖 Assistant:</strong> {message['content']}
            </div>
            """, unsafe_allow_html=True)


def display_book_showcase():
    """Display a showcase of available books"""
    st.header("📖 Book Showcase")

    # Create columns for book display
    cols = st.columns(3)

    for i, (title, summary) in enumerate(list(book_summaries_dict.items())[:6]):
        with cols[i % 3]:
            metadata = book_metadata.get(title, {})

            st.markdown(f"""
            <div class="book-card">
                <h4>{title}</h4>
                <p><strong>Author:</strong> {metadata.get('author', 'Unknown')}</p>
                <p><strong>Genre:</strong> {metadata.get('genre', 'Unknown')}</p>
                <p>{summary[:150]}...</p>
            </div>
            """, unsafe_allow_html=True)


def main():
    """Main Streamlit application"""
    initialize_session_state()

    # Header
    st.markdown("<h1 class='main-header'>📚 AI Book Recommendation Chatbot</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # Setup sidebar
    setup_sidebar()

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("💬 Chat Interface")

        # Check if chatbot is initialized
        if not st.session_state.api_key_set:
            st.warning("⚠️ Please enter your OpenAI API key in the sidebar to start chatting!")
            return

        # Voice input button
        if STT_AVAILABLE and st.session_state.get('stt_enabled', False):
            if st.button("🎤 Voice Input"):
                try:
                    r = sr.Recognizer()
                    with sr.Microphone() as source:
                        st.info("🎤 Listening... Speak now!")
                        audio = r.listen(source, timeout=5)
                        voice_text = r.recognize_google(audio)
                        st.session_state.selected_example = voice_text
                        st.success(f"Heard: {voice_text}")
                except Exception as e:
                    st.error(f"Voice recognition error: {e}")

        # Chat input - Use a different approach to avoid session state conflicts
        user_input = st.text_input(
            "Ask me about books!",
            placeholder="e.g., 'I want a book about friendship and magic'",
            value=st.session_state.selected_example,
            key="chat_input_field"
        )

        # Clear the selected example after it's been used
        if st.session_state.selected_example and user_input == st.session_state.selected_example:
            st.session_state.selected_example = ""

        # Send button
        col_send1, col_send2 = st.columns([4, 1])
        with col_send2:
            send_button = st.button("🚀 Send")

        # Example questions
        st.markdown("**💡 Try these example questions:**")
        example_questions = [
            "I want a book about friendship and magic",
            "What do you recommend for someone who loves war stories?",
            "Books about artificial intelligence",
            "Tell me about Red Rising",
            "I need something for personal development"
        ]

        cols = st.columns(2)
        for i, question in enumerate(example_questions):
            with cols[i % 2]:
                if st.button(question, key=f"example_{i}"):
                    # Instead of modifying session state, directly process the input
                    process_user_input(question)

        # Process user input from text field
        if user_input and send_button:
            process_user_input(user_input)

        # Display chat history
        if st.session_state.chat_history:
            st.markdown("---")
            display_chat_history()

    with col2:
        st.header("📊 Statistics")

        if st.session_state.chat_history:
            total_messages = len(st.session_state.chat_history)
            user_messages = len([m for m in st.session_state.chat_history if m['role'] == 'user'])

            st.metric("Total Messages", total_messages)
            st.metric("Your Questions", user_messages)

        st.markdown("---")

        # Quick book lookup
        st.header("🔍 Quick Book Lookup")

        selected_book = st.selectbox(
            "Select a book for details:",
            [""] + list(book_summaries_dict.keys())
        )

        if selected_book:
            metadata = book_metadata.get(selected_book, {})
            st.markdown(f"""
            <div class="book-card">
                <h4>{selected_book}</h4>
                <p><strong>Author:</strong> {metadata.get('author', 'Unknown')}</p>
                <p><strong>Genre:</strong> {metadata.get('genre', 'Unknown')}</p>
                <p><strong>Summary:</strong></p>
                <p>{book_summaries_dict[selected_book]}</p>
            </div>
            """, unsafe_allow_html=True)

    # Book showcase section
    display_book_showcase()


def process_user_input(user_input):
    """Process user input and get chatbot response"""
    # Add user message to history
    st.session_state.chat_history.append({
        'role': 'user',
        'content': user_input
    })

    # Get chatbot response
    with st.spinner("🤔 Thinking..."):
        try:
            response = st.session_state.chatbot.generate_response(user_input)

            # Add assistant response to history
            st.session_state.chat_history.append({
                'role': 'assistant',
                'content': response
            })

            # Text-to-speech
            if TTS_AVAILABLE and st.session_state.get('tts_enabled', False):
                try:
                    engine = pyttsx3.init()
                    engine.say(response)
                    engine.runAndWait()
                except Exception as e:
                    st.error(f"TTS Error: {e}")

        except Exception as e:
            st.error(f"Error: {str(e)}")

    # Rerun to update the display
    st.rerun()


if __name__ == "__main__":
    main()