import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Logging setup: file + console."""
    
    # Create a root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # We catch EVERYTHING, filtering at the handler level
    
    # Message format
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (DEBUG, with rotation)
    file_handler = RotatingFileHandler(
        'sysguard.log',
        maxBytes=1_000_000,  # 1 MB
        backupCount=5        # Keep 5 old files
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Handler for console (INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Adding handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.debug("Logging initialized")  # It will only get into the file