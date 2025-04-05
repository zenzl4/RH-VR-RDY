import os
import json
import logging
import re

logger = logging.getLogger(__name__)

class JSONHandler:
    """Combined JSON cleaning and parsing pipeline"""

    def clean_and_parse(self, json_str):
        """Comprehensive JSON cleaning for LLM responses"""
        # First, try basic parsing
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Apply progressive cleaning steps
            cleaned_json = self._apply_cleaning_pipeline(json_str)
            
            try:
                return json.loads(cleaned_json)
            except json.JSONDecodeError:
                # Try extraction-based approach as final fallback
                return self._extract_fields_with_regex(json_str)
    
    def _apply_cleaning_pipeline(self, json_str):
        """Apply progressive JSON cleaning steps from both systems"""
        result = str(json_str)
        
        # Logging for debugging
        logger.debug(f"Original JSON before cleaning: {result[:100]}...")
        
        # Extract JSON content (if wrapped in other text)
        json_match = re.search(r'(\{[\s\S]*\})', result)
        if json_match:
            result = json_match.group(1)
            
        # 1. Remove code blocks markers
        result = re.sub(r'```(? :json)?\s*', '', result, flags=re.IGNORECASE)
        result = re.sub(r'```\s*$', '', result, flags=re.IGNORECASE)
        
        # 2. Fix property names with spaces
        result = re.sub(r'"([^"]+\s+[^"]+)":',
                        lambda m: f'"{m.group(1).replace(" ", "_")}":', 
                        result)
        
        # 3. Fix unquoted property names
        result = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?=\s*:)',
                        r'"\1"', 
                        result)
        
        # 4. Convert single quotes to double quotes
        result = result.replace("'", '"')
        
        # 5. Remove trailing commas
        result = re.sub(r',\s*(?=[\]}])', '', result)
        
        # 6. Add missing commas between properties
        result = re.sub(r'(["}\d])\s*\n\s*"', r'\1,\n"', result)
        
        # 7. Fix boolean and numeric values
        result = re.sub(r':\s*"(true|false)"', r': \1', result, flags=re.IGNORECASE)
        result = re.sub(r':\s*"(\d+)"', r': \1', result)
        
        # 8. Fix missing braces or brackets if needed
        if result.count('{') > result.count('}'):
            result += '}' * (result.count('{') - result.count('}'))
        if result.count('[') > result.count(']'):
            result += ']' * (result.count('[') - result.count(']'))
        
        logger.debug(f"Cleaned JSON: {result[:100]}...")
        return result
        
    def _extract_fields_with_regex(self, json_str):
        """Extract fields using regex patterns when JSON parsing fails"""
        logger.warning(f"Falling back to regex extraction for: {json_str[:50]}...")
        data = {}
        
        # Extract common fields using regex
        name_match = re.search(r'"name"\s*:\s*"([^"]+)"', json_str)
        if name_match:
            data["name"] = name_match.group(1)
            
        email_match = re.search(r'"email"\s*:\s*"([^"]+)"', json_str)
        if email_match:
            data["email"] = email_match.group(1)
            
        phone_match = re.search(r'"phone"\s*:\s*"([^"]+)"', json_str)
        if phone_match:
            data["phone"] = phone_match.group(1)
            
        years_match = re.search(r'"years_experience"\s*:\s*"?(\d+)"?', json_str)
        if years_match:
            data["years_experience"] = years_match.group(1)
            
        education_match = re.search(r'"education"\s*:\s*"([^"]+)"', json_str)
        if education_match:
            data["education"] = education_match.group(1)
            
        position_match = re.search(r'"last_position"\s*:\s*"([^"]+)"', json_str)
        if position_match:
            data["last_position"] = position_match.group(1)
            
        # Extract skills array
        skills_matches = re.findall(r'"top_skills"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
        if skills_matches:
            skills_raw = skills_matches[0]
            skills = re.findall(r'"([^"]+)"', skills_raw)
            data["top_skills"] = skills
            
        # Extract match_score
        match_score = re.search(r'"match_score"\s*:\s*(\d+)', json_str)
        if match_score:
            data["match_score"] = int(match_score.group(1))
            
        # Extract matching_skills
        matching_skills_matches = re.findall(r'"matching_skills"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
        if matching_skills_matches:
            skills_raw = matching_skills_matches[0]
            matching_skills = re.findall(r'"([^"]+)"', skills_raw)
            data["matching_skills"] = matching_skills
            
        # Extract missing_skills
        missing_skills_matches = re.findall(r'"missing_skills"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
        if missing_skills_matches:
            skills_raw = missing_skills_matches[0]
            missing_skills = re.findall(r'"([^"]+)"', skills_raw)
            data["missing_skills"] = missing_skills
            
        # Extract recommendation details
        recommendation_match = re.search(r'"recommendation"\s*:\s*"(.*?)"', json_str)
        if recommendation_match:
            data["recommendation"] = recommendation_match.group(1)
            
        overall_rating_match = re.search(r'"overall_rating"\s*:\s*(\d+)', json_str)
        if overall_rating_match:
            data["overall_rating"] = int(overall_rating_match.group(1))
            
        logger.info(f"Extracted {len(data)} fields using regex fallback")
        return data
    
    def try_json5_parse(self, json_str):
        """Try parsing with JSON5 if available (more lenient JSON parser)"""
        try:
            import json5
            return json5.loads(json_str)
        except ImportError:
            logger.warning("json5 module not available for fallback parsing")
            return None
        except Exception as e:
            logger.warning(f"JSON5 parsing failed: {str(e)}")
            return None

    def save_to_json(self, data, file_path):
        """Save the parsed data to a JSON file."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write the data to the file
            with open(file_path, 'w', encoding='utf-8') as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)
            
            logger.info(f"Data successfully saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving data to JSON: {str(e)}")
