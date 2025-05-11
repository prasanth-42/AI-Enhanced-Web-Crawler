import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

def check_api_key_exists():
    """Check if the GROQ_API_KEY environment variable is set"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY environment variable is not set")
        return False
    return True

def get_environment_config():
    """Get configuration from environment variables"""
    return {
        "has_api_key": check_api_key_exists(),
        "model_name": os.getenv("MODEL_NAME", "llama3-8b-8192"),
        "temperature": float(os.getenv("TEMPERATURE", "0.7"))
    }
