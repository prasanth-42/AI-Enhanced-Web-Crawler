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

# Global registry for sessions
# Completely clear this on app initialization to solve the persistence issue across reloads
sessions = {}
latest_urls = {}

# Explicitly clear all sessions on module load to solve persistence issues
# This is necessary to ensure a clean start each time the app is reloaded
def clear_all_sessions():
    """Clear all sessions and URLs from global state"""
    global sessions, latest_urls
    old_session_count = len(sessions)
    if old_session_count > 0:
        logger.debug(f"Clearing {old_session_count} existing sessions on app initialization")
    sessions.clear()
    latest_urls.clear()
    
# Call this on module import to ensure a clean slate
clear_all_sessions()

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
        
        # CRITICAL FIX: Clean up ALL sessions before creating a new one
        # This ensures there's only ever one active session in the app, exactly like Streamlit
        clear_all_sessions()
        logger.debug("Cleared all existing sessions")
        
        # Create a unique session ID
        session_id = scraper_service.create_session_id()
        
        # Current time for session expiry tracking
        current_time = time.time()
        
        # Scrape website and create vector store following the Streamlit pattern exactly
        try:
            logger.debug(f"Starting to scrape website: {url}")
            # This method now uses WebBaseLoader like in the Streamlit app
            vector_store = scraper_service.get_vectorstore_from_url(url)
            logger.debug(f"Successfully created vector store for URL: {url}")
        except Exception as scrape_error:
            logger.error(f"Error during scraping: {str(scrape_error)}")
            return jsonify({"error": f"Failed to scrape website: {str(scrape_error)}"}), 500
        
        # Store vector_store and initialize empty chat history with timestamp
        # This follows the same pattern as Streamlit's session_state
        sessions[session_id] = {
            "vector_store": vector_store,
            "chat_history": [],  # Start with empty chat history like Streamlit's chat_history
            "url": url,          # Store URL for reference
            "timestamp": current_time
        }
        
        # Also track the latest URL for debugging
        latest_urls[session_id] = url
        
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
        
        # Update session timestamp to keep it active
        session["timestamp"] = time.time()
        
        try:
            # This matches the RAG pipeline logic in the Streamlit app
            logger.debug("Setting up RAG pipeline for query")
            
            # Get context retriever chain - similar to Streamlit app's get_context_retriever_chain function
            retriever_chain = llm_service.get_context_retriever_chain(vector_store)
            
            # Get conversational RAG chain - similar to Streamlit app's get_conversational_rag_chain function
            rag_chain = llm_service.get_conversational_rag_chain(retriever_chain)
            
            # Get response - invoke with chat history and user input, similar to Streamlit app's get_response function
            response_data = rag_chain.invoke({
                "chat_history": chat_history,
                "input": query
            })
            
            logger.debug("RAG pipeline completed successfully")
            
            # Extract answer from response
            if isinstance(response_data, dict) and "answer" in response_data:
                response = response_data["answer"]
            else:
                logger.warning(f"Unexpected response format: {type(response_data)}")
                response = str(response_data)  # Fallback to string representation
                
        except Exception as rag_error:
            logger.error(f"Error in RAG pipeline: {str(rag_error)}")
            # Fallback to simpler response method
            response = llm_service.get_response(query, vector_store, chat_history)
        
        # Update chat history with new interaction
        updated_history = llm_service.update_chat_history(chat_history, query, response)
        session["chat_history"] = updated_history
        
        return jsonify({
            "response": response,
            "url": url,
            "session_id": session_id  # Include session_id in response for validation
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
    global sessions, latest_urls
    session_count = len(sessions)
    sessions = {}
    latest_urls = {}
    logger.debug(f"API endpoint cleared {session_count} sessions")
    return jsonify({"message": f"All sessions cleared successfully ({session_count} sessions)"})

@app.route('/api/debug', methods=['GET'])
def debug_state():
    """
    Debug endpoint to see the current server state
    This helps diagnose session persistence issues
    """
    debug_info = {
        "session_count": len(sessions),
        "session_ids": list(sessions.keys()),
        "urls": latest_urls,
        "timestamp": time.time()
    }
    return Response(
        json.dumps(debug_info, indent=2),
        mimetype='application/json'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
