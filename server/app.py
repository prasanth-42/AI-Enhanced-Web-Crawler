import os
import logging
import time
from flask import Flask, request, jsonify, render_template
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

# In-memory storage for chat sessions
# We'll use a global sessions dictionary with a cleanup mechanism
sessions = {}

# Also track the latest URL for each session to help with debugging
latest_urls = {}

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
        
        # Create a unique session ID
        session_id = scraper_service.create_session_id()
        
        # Before creating new sessions, clean up old ones and any session with the same URL
        current_time = time.time()
        sessions_to_remove = []
        
        # Clean old sessions and sessions with the same URL
        for sid, session_data in sessions.items():
            # Remove sessions that are old (older than 1 hour)
            if 'timestamp' in session_data and (current_time - session_data['timestamp']) > 3600:
                sessions_to_remove.append(sid)
            # Also remove any session that was created for the same URL
            elif 'url' in session_data and session_data['url'] == url:
                logger.debug(f"Found existing session for URL {url}, will replace it")
                sessions_to_remove.append(sid)
                
        # Remove flagged sessions
        for sid in sessions_to_remove:
            logger.debug(f"Removing session: {sid}")
            del sessions[sid]
            if sid in latest_urls:
                del latest_urls[sid]
        
        # Scrape website and create vector store following the Streamlit pattern
        try:
            # This method is now using WebBaseLoader like in the Streamlit app
            vector_store = scraper_service.get_vectorstore_from_url(url)
            logger.debug(f"Successfully created vector store for URL: {url}")
        except Exception as scrape_error:
            logger.error(f"Error during scraping: {str(scrape_error)}")
            return jsonify({"error": f"Failed to scrape website: {str(scrape_error)}"}), 500
        
        # Store vector_store and initialize empty chat history with timestamp
        sessions[session_id] = {
            "vector_store": vector_store,
            "chat_history": [],  # Start with empty chat history
            "url": url,          # Store URL for reference
            "timestamp": current_time
        }
        
        # Also track the latest URL
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
