# utils/json_handler.py
import json
import re
import os
from utils.logging_setup import get_logger

logger = get_logger(__name__)

class JSONHandler:
    @staticmethod
    def clean_and_parse(json_str):
        """Clean and parse JSON string from LLM response"""
        try:
            # First try parsing directly
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            try:
                # Clean the JSON string
                cleaned = json_str.strip()
                
                # Remove markdown code blocks if present
                if cleaned.startswith('```') and cleaned.endswith('```'):
                    cleaned = cleaned[3:-3].strip()
                    if cleaned.startswith('json'):
                        cleaned = cleaned[4:].strip()
                
                # Parse the cleaned JSON
                return json.loads(cleaned)
            except Exception as e:
                logger.error(f"JSON parsing error: {str(e)}")
                return {"error": f"Failed to parse JSON: {str(e)}"}

    @staticmethod
    def save_to_json(data, file_path=None):
        """Save data to JSON file with error handling"""
        try:
            if file_path is None:
                # Create default path if none provided
                output_dir = os.path.abspath("outputs")
                os.makedirs(output_dir, exist_ok=True)
                file_path = os.path.join(output_dir, "evaluation_result.json")
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON to {file_path}: {str(e)}")
            return False
