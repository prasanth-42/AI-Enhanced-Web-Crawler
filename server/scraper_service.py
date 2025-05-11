import uuid
import logging
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Configure logging
logger = logging.getLogger(__name__)

def create_session_id():
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def get_vectorstore_from_url(url):
    """
    Scrape a website and create a vector store from its content
    
    This implementation follows the same pattern as the Streamlit version:
    1. Use WebBaseLoader to load the website
    2. Split the document into chunks
    3. Create embeddings using HuggingFaceEmbeddings
    4. Create a Chroma vector store
    
    Args:
        url (str): The URL of the website to scrape
        
    Returns:
        VectorStore: A Chroma vector store containing the embedded document chunks
    """
    try:
        from langchain_community.document_loaders import WebBaseLoader
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain_community.embeddings import HuggingFaceEmbeddings
        
        logger.debug(f"Loading content from URL: {url}")
        
        # Use WebBaseLoader directly like in the successful Streamlit app
        try:
            # Set custom headers to mimic a browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0"
            }
            
            # Use WebBaseLoader with custom headers
            loader = WebBaseLoader(
                web_paths=[url],
                header_template=headers
            )
            
            logger.debug("Using WebBaseLoader to load document")
            document = loader.load()
            logger.debug(f"Successfully loaded document with {len(document)} pages")
            
            logger.debug(f"Splitting document into chunks")
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
            document_chunks = text_splitter.split_documents(document)
            logger.debug(f"Created {len(document_chunks)} document chunks")
            
            # Use HuggingFace embeddings like in the Streamlit app
            logger.debug("Creating HuggingFaceEmbeddings")
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            logger.debug("Successfully created HuggingFaceEmbeddings")
            
            # Create vector store
            logger.debug("Creating Chroma vector store")
            vector_store = Chroma.from_documents(document_chunks, embedding=embeddings)
            logger.debug("Successfully created vector store")
            
            return vector_store
            
        except Exception as inner_e:
            logger.error(f"Error in WebBaseLoader: {str(inner_e)}")
            raise  # Re-raise to be caught by outer exception handler
        
    except Exception as e:
        logger.error(f"Error in get_vectorstore_from_url: {str(e)}")
        raise Exception(f"Failed to process website: {str(e)}")
