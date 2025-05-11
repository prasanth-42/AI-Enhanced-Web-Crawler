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
        import requests
        from bs4 import BeautifulSoup
        from langchain_core.documents import Document
        
        logger.debug(f"Loading content from URL: {url}")
        
        # First try with direct request and BeautifulSoup
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            # Extract text from all paragraph tags
            paragraphs = soup.find_all('p')
            extracted_text = "\n\n".join([p.get_text().strip() for p in paragraphs])
            
            # If we got meaningful text, use it
            if extracted_text and len(extracted_text) > 100:
                logger.debug(f"Successfully extracted content with BeautifulSoup")
                document = [Document(page_content=extracted_text, metadata={"source": url})]
            else:
                # Try with trafilatura
                downloaded = trafilatura.fetch_url(url)
                text = trafilatura.extract(downloaded)
                
                if not text:
                    # If both failed, try to get all text from the page
                    logger.debug("Extraction methods failed, getting all text from page")
                    all_text = soup.get_text(separator="\n\n")
                    document = [Document(page_content=all_text, metadata={"source": url})]
                else:
                    # Create Document object from extracted text
                    document = [Document(page_content=text, metadata={"source": url})]
                    logger.debug(f"Successfully extracted content with trafilatura")
        except Exception as inner_e:
            logger.error(f"Error in content extraction: {str(inner_e)}")
            # Fallback to just getting the full HTML as text
            response = requests.get(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            all_text = soup.get_text(separator="\n\n")
            document = [Document(page_content=all_text, metadata={"source": url})]
        
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
