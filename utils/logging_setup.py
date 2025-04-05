

"""
Logging configuration for the Resume Analyzer application.
Sets up console and file logging with appropriate formatting.
"""

import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logging(log_level=logging.INFO, log_to_file=True):
    """
    Configure application logging with console and optional file output.
    
    Args:
        log_level: The minimum log level to capture (default: INFO)
        log_to_file: Whether to also log to a file (default: True)
    
    Returns:
        Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('resume_analyzer')
    logger.setLevel(log_level)
    
    # Clear any existing handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Create console handler with formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    
    # Create formatters
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    verbose_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Apply formatter to console handler
    console_handler.setFormatter(console_format)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # If file logging is enabled
    if log_to_file:
        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Create unique log filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'resume_analyzer_{timestamp}.log'
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(verbose_format)
        
        # Add file handler to logger
        logger.addHandler(file_handler)
        
        logger.info(f"Log file created at {log_file}")
    
    logger.info(f"Logging initialized at level {logging.getLevelName(log_level)}")
    return logger

def get_logger(name=None):
    """
    Get a named logger derived from the main application logger.
    
    Args:
        name: Optional name for the logger (default: None)
    
    Returns:
        Logger: Named logger instance
    """
    if name:
        return logging.getLogger(f'resume_analyzer.{name}')
    return logging.getLogger('resume_analyzer')

