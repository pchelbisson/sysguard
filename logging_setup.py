import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Logging setup: file + stderr console.

    Important contract for CLI mode:
    - stdout is reserved for machine-readable JSON report only;
    - human-readable logs go to file/stderr.
    """
    
    # Create a root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # We catch EVERYTHING, filtering at the handler level
    logger.handlers.clear()
    
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
    
    # Handler for console (INFO) -> stderr to keep stdout JSON-only
    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Adding handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    logging.debug("Logging initialized")  # It will only get into the file