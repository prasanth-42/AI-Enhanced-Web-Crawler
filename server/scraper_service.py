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
    
    Args:
        url (str): The URL of the website to scrape
        
    Returns:
        VectorStore: A Chroma vector store containing the embedded document chunks
    """
    try:
        logger.debug(f"Loading content from URL: {url}")
        loader = WebBaseLoader(url)
        document = loader.load()
        
        logger.debug(f"Splitting document into chunks")
        text_splitter = RecursiveCharacterTextSplitter()
        document_chunks = text_splitter.split_documents(document)
        
        logger.debug(f"Creating embeddings and vector store")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vector_store = Chroma.from_documents(document_chunks, embedding=embeddings)
        
        return vector_store
        
    except Exception as e:
        logger.error(f"Error in get_vectorstore_from_url: {str(e)}")
        raise Exception(f"Failed to process website: {str(e)}")
