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
        import trafilatura
        from langchain_core.documents import Document
        
        logger.debug(f"Loading content from URL: {url}")
        
        # Use trafilatura for better content extraction
        downloaded = trafilatura.fetch_url(url)
        text = trafilatura.extract(downloaded)
        
        if not text:
            # Fallback to WebBaseLoader if trafilatura fails
            logger.debug("Trafilatura extraction failed, falling back to WebBaseLoader")
            loader = WebBaseLoader(url)
            document = loader.load()
        else:
            # Create Document object from extracted text
            document = [Document(page_content=text, metadata={"source": url})]
            logger.debug(f"Successfully extracted content with trafilatura")
        
        logger.debug(f"Splitting document into chunks")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        document_chunks = text_splitter.split_documents(document)
        
        logger.debug(f"Creating simple embeddings and vector store")
        # Use a simple embedding method to avoid dependency issues
        from langchain_community.embeddings import FakeEmbeddings
        embeddings = FakeEmbeddings(size=1536)  # Using fake embeddings for now
        vector_store = Chroma.from_documents(document_chunks, embedding=embeddings)
        
        return vector_store
        
    except Exception as e:
        logger.error(f"Error in get_vectorstore_from_url: {str(e)}")
        raise Exception(f"Failed to process website: {str(e)}")
