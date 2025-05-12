import os
import logging
import time
import json
from flask import Flask, request, jsonify, render_template, Response
from flask_cors import CORS
from dotenv import load_dotenv
import server.llm_service as llm_service
import server.scraper_service as scraper_service

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder="../client", template_folder="../client", static_url_path='')
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Enable CORS
CORS(app)
sessions = {}

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')

@app.route('/api/scrape', methods=['POST'])
def scrape():
    """
    Endpoint to scrape a website and create a vector store from its content
    
    Expects JSON with:
    - url: the website URL to scrape
    
    Returns:
    - session_id: unique identifier for this chat session
    """
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
            
        logger.debug(f"Scraping URL: {url}")
        
        global sessions
        sessions = {}  # Clear all sessions before creating a new one
        
        # Create a unique session ID
        session_id = scraper_service.create_session_id()
        
        # Scrape website and create vector store 
        try:
            logger.debug(f"Starting to scrape website: {url}")
            vector_store, persist_dir = scraper_service.get_vectorstore_from_url(url)
            logger.debug(f"Successfully created vector store for URL: {url} in {persist_dir}")
        except Exception as scrape_error:
            logger.error(f"Error during scraping: {str(scrape_error)}")
            return jsonify({"error": f"Failed to scrape website: {str(scrape_error)}"}), 500
        
        # Store vector_store and initialize empty chat history
        sessions[session_id] = {
            "vector_store": vector_store,
            "chat_history": [],  # Start with empty chat history
            "url": url          # Store URL for reference
        }
        
        logger.debug(f"Created new session {session_id} for URL: {url}")
        
        return jsonify({
            "session_id": session_id,
            "message": "Website scraped successfully"
        })
        
    except Exception as e:
        logger.error(f"Error scraping website: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Endpoint to chat with a website
    
    Expects JSON with:
    - session_id: the session ID returned from /scrape
    - query: the user's question
    
    Returns:
    - response: the LLM's response
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        query = data.get('query')
        
        if not session_id or not query:
            return jsonify({"error": "Both session_id and query are required"}), 400
            
        if session_id not in sessions:
            return jsonify({"error": "Invalid or expired session ID. Please scrape the website again."}), 404
            
        session = sessions[session_id]
        vector_store = session["vector_store"]
        chat_history = session["chat_history"]
        url = session.get("url", "unknown")
        
        logger.debug(f"Processing query for URL '{url}': {query}")
        
        try:
            # Get response from LLM
            response = llm_service.get_response(query, vector_store, chat_history)
            logger.debug("Got response from LLM")
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            return jsonify({"error": f"Error processing query: {str(e)}"}), 500
        
        # Update chat history with new interaction
        updated_history = llm_service.update_chat_history(chat_history, query, response)
        session["chat_history"] = updated_history
        
        return jsonify({
            "response": response,
            "url": url
        })
        
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/check_api_key', methods=['GET'])
def check_api_key():
    """
    Check if the GROQ_API_KEY is set in environment variables
    """
    api_key = os.getenv("GROQ_API_KEY")
    return jsonify({"has_api_key": api_key is not None})

@app.route('/api/clear_sessions', methods=['POST'])
def clear_api_sessions():
    """
    Explicit endpoint to clear all sessions
    This can be called when loading the app to ensure a fresh state
    """
    global sessions
    session_count = len(sessions)
    sessions = {}  # Simply clear all sessions
    logger.debug(f"API endpoint cleared {session_count} sessions")
    return jsonify({"message": f"All sessions cleared successfully"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
