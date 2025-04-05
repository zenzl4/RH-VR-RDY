import re
import os
from PyPDF2 import PdfReader
from utils.logging_setup import get_logger
logger = get_logger(__name__)  # Create logger instance
from utils.config import Config

class PDFProcessor:
    """Enhanced PDF text extraction with multiple fallback methods"""
    
    def __init__(self, use_advanced_cleanup=None):
        # Default to using Config setting for advanced cleanup
        self.use_advanced_cleanup = use_advanced_cleanup if use_advanced_cleanup is not None else Config.USE_ADVANCED_CLEANUP
        
    def extract_text(self, file):
        """Extract text with fallbacks if primary method fails"""
        try:
            # Primary extraction using PyPDF2
            reader = PdfReader(file)
            text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
            
            # Apply cleanup if enabled
            if self.use_advanced_cleanup:
                text = self._cleanup_text(text)
                
            return text.encode('utf-8', 'replace').decode('utf-8') if text else ""
        except Exception as primary_error:
            logger.warning(f"Primary PDF extraction failed: {str(primary_error)}")
            return self._fallback_extraction(file)
    
    def _cleanup_text(self, text):
        """Apply advanced text cleanup"""
        if not text:
            return ""
        
        # Remove formatting markers and normalize whitespace
        text = re.sub(r'\*\*|__|#', '', text)  # Remove bold/italic markers
        text = re.sub(r'\s+', ' ', text)       # Collapse multiple spaces
        
        # Fix common encoding issues
        text = text.replace("\x00", "")  # Remove null bytes
        
        # Remove redundant line breaks while preserving paragraph structure
        text = re.sub(r'(\r?\n){3,}', '\n\n', text)  # Ensure no more than two consecutive line breaks
        
        return text
    
    def _fallback_extraction(self, file):
        """Use alternative extraction methods if primary fails"""
        try:
            # Attempt alternative PyPDF2 approach
            reader = PdfReader(file)
            
            # Try different extraction approach
            all_text = []
            for page in reader.pages:
                # Try extracting text directly
                text = page.extract_text()
                if text:
                    all_text.append(text)
                else:
                    # If no text, try to extract raw content
                    if '/Contents' in page:
                        all_text.append("Page content unavailable for direct extraction")
            
            combined_text = "\n".join(all_text)
            
            if combined_text:
                logger.info("Successfully used fallback extraction")
                return combined_text
            else:
                logger.warning("Fallback extraction failed to get text")
                return "No readable text found in document"
        except Exception as fallback_error:
            logger.error(f"All PDF extraction methods failed: {str(fallback_error)}")
            return f"Error extracting text: {str(fallback_error)}"
