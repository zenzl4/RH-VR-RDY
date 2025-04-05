

import re
import os
from html import escape
from utils.logging_setup import get_logger
logger = get_logger(__name__)

# Import language detection with fallback
try:
    from langdetect import detect as detect_lang
except ImportError:
    # Simple fallback if langdetect is not available
    def detect_lang(text):
        return 'en'  # Default to English

class ResumeParser:
    """Extract key information from resume text with robust fallbacks"""
    
    def __init__(self, llm_client, json_handler):
        self.llm_client = llm_client
        self.json_handler = json_handler
        self.email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        self.phone_patterns = [
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # 555-555-5555 format
            r'\b\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4}\b',  # International format
            r'\b\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4}\b',  # (555) 555-5555 format
        ]
        
    async def extract_resume_summary(self, resume_text, filename, lang='en'):
        """Extract key information from resume for quick overview"""
        # First attempt regex extraction as a fallback
        fallback_data = self._extract_with_regex(resume_text)
        fallback_data["filename"] = filename
        
        # Then try LLM-based extraction
        system_prompt = (
            f"You are a Recruitment Expert. Extract key information from this {'French' if lang == 'fr' else 'English'} resume. "
            f"Create a JSON object with these fields (leave empty if not found):\n"
            "1. name: Candidate's full name\n"
            "2. email: Candidate's email address\n"
            "3. phone: Candidate's phone number\n"
            "4. years_experience: Total years of professional experience (numeric only)\n"
            "5. education: Highest degree and institution\n"
            "6. top_skills: Array of 3-5 core skills mentioned\n"
            "7. last_position: Most recent job title and company\n"
            "Format response as valid JSON only. Ensure all field names and string values are enclosed in double quotes.\n"
            "If you cannot find a value, use empty string for text fields and empty array for lists.\n"
        )
        
        user_prompt = f"Resume Content:\n{resume_text}"
        full_prompt = f"[INST] {system_prompt}\n\n{user_prompt} [/INST]"
        
        response = await self.llm_client.generate(
            prompt=full_prompt,
            max_tokens=1024,
            temperature=0.1,
            top_p=0.3
        )
        
        if response["status"] == "error":
            logger.warning(f"LLM API error when extracting resume summary: {response.get('error')}")
            return fallback_data
            
        # Process the response
        result = response["result"]
        
        try:
            # Use the JSON handler to clean and parse the response
            data = self.json_handler.clean_and_parse(result)
            
            # Add filename to the results
            data["filename"] = filename
            
            # Validate and merge with fallback data where needed
            return self._validate_and_merge(data, fallback_data)
            
        except Exception as e:
            logger.error(f"Error processing resume summary: {str(e)}")
            return fallback_data
            
    def _extract_with_regex(self, resume_text):
        """Extract basic resume data using regex patterns"""
        data = {
            "name": "",
            "email": "",
            "phone": "",
            "years_experience": "",
            "education": "",
            "top_skills": [],
            "last_position": ""
        }
        
        # Extract email
        email_match = re.search(self.email_pattern, resume_text)
        if email_match:
            data["email"] = email_match.group(0)
            
        # Extract phone number
        for pattern in self.phone_patterns:
            phone_match = re.search(pattern, resume_text)
            if phone_match:
                data["phone"] = phone_match.group(0)
                break
                
        # Extract years of experience
        exp_patterns = [
            r'(\d+)\+?\s*(?:years|year|yrs|yr)(?:\s+of\s+|\s+)(?:experience|work)',
            r'(?:experience|work)(?:\s+of\s+|\s+)(\d+)\+?\s*(?:years|year|yrs|yr)'
        ]
        for pattern in exp_patterns:
            exp_match = re.search(pattern, resume_text, re.IGNORECASE)
            if exp_match:
                data["years_experience"] = exp_match.group(1)
                break
                
        # Extract education
        edu_patterns = [
            r'(?:bachelor|master|phd|mba|bs|ba|ms|b\.s\.|m\.s\.|b\.a\.|ph\.d\.).{1,50}(?:university|college|institute|school)',
            r'(?:university|college|institute|school).{1,50}(?:bachelor|master|phd|mba|bs|ba|ms|b\.s\.|m\.s\.|b\.a\.|ph\.d\.)'
        ]
        for pattern in edu_patterns:
            edu_match = re.search(pattern, resume_text, re.IGNORECASE)
            if edu_match:
                data["education"] = edu_match.group(0).strip()
                break
                
        # Extract skills based on common skill keywords
        self._extract_skills(resume_text, data)
        
        # Extract last position
        position_patterns = [
            r'(?:current|present|latest|recent)\s+(?:position|title|role)[\s\:]+([^\n\.]+)',
            r'(?:position|title|role)[\s\:]+([^\n\.]+)',
            r'(?:senior|lead|principal|director|manager|engineer|developer|analyst|consultant|specialist)[^,\n\.]{1,30}(?:at|@|,|\-)([^,\n\.]{1,30})'
        ]
        for pattern in position_patterns:
            position_match = re.search(pattern, resume_text, re.IGNORECASE)
            if position_match:
                data["last_position"] = position_match.group(1).strip()
                break
                
        # Try to extract name (difficult with regex alone)
        name_patterns = [
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})(?:\n|\r)',  # Names at start of resume
            r'(?:name|cv|curriculum vitae|resume)\s*(?::|of|for)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})',  # "Name: John Smith"
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, resume_text, re.IGNORECASE)
            if name_match:
                data["name"] = name_match.group(1).strip()
                break
                
        return data
        
    def _extract_skills(self, resume_text, data):
        """Extract skills from resume text"""
        common_skills = [
            "python", "javascript", "java", "c++", "ruby", "go", "rust", "sql", 
            "nosql", "react", "angular", "vue", "node", "express", "django", 
            "flask", "rails", "spring", "bootstrap", "css", "html", "aws", 
            "azure", "gcp", "docker", "kubernetes", "terraform", "ci/cd", "git", 
            "agile", "scrum", "management", "leadership", "communication", 
            "teamwork", "problem solving", "analytical", "creative", 
            "time management", "project management", "marketing", "sales", 
            "crm", "seo", "digital marketing", "content writing", "copywriting", 
            "graphic design", "ui/ux", "product management", "data analysis", 
            "machine learning", "ai"
        ]
        
        found_skills = []
        for skill in common_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', resume_text, re.IGNORECASE):
                found_skills.append(skill.title())
                
        if found_skills:
            data["top_skills"] = found_skills[:5]  # Take up to 5 skills
        
        return data
        
    def _validate_and_merge(self, llm_data, fallback_data):
        """Validate LLM-extracted data and merge with regex fallbacks where needed"""
        # Create a new data object
        validated_data = {}
        
        # Copy filename
        validated_data["filename"] = llm_data.get("filename", fallback_data.get("filename", ""))
        
        # Validate name
        if "name" in llm_data and llm_data["name"] and len(llm_data["name"]) > 2:
            validated_data["name"] = llm_data["name"]
        else:
            # Use fallback or generate from filename
            validated_data["name"] = fallback_data.get("name", "")
            if not validated_data["name"] and "filename" in validated_data:
                basename = os.path.splitext(os.path.basename(validated_data["filename"]))[0]
                validated_data["name"] = basename.replace("_", " ").title()
                
        # Validate email with regex check
        if "email" in llm_data and llm_data["email"] and re.match(self.email_pattern, llm_data["email"]):
            validated_data["email"] = llm_data["email"]
        else:
            validated_data["email"] = fallback_data.get("email", "")
            
        # Validate phone
        if "phone" in llm_data and llm_data["phone"]:
            # Check if phone looks valid
            has_numbers = any(c.isdigit() for c in llm_data["phone"])
            if has_numbers and len(llm_data["phone"]) >= 7:
                validated_data["phone"] = llm_data["phone"]
            else:
                validated_data["phone"] = fallback_data.get("phone", "")
        else:
            validated_data["phone"] = fallback_data.get("phone", "")
            
        # Validate years_experience
        if "years_experience" in llm_data:
            try:
                years = llm_data["years_experience"]
                if isinstance(years, str) and years.strip():
                    # Extract digits from string if needed
                    digit_match = re.search(r'\d+', years)
                    if digit_match:
                        years = int(digit_match.group(0))
                    else:
                        years = None
                        
                if isinstance(years, (int, float)) and 0 <= years <= 50:
                    validated_data["years_experience"] = years
                else:
                    # Try fallback data
                    validated_data["years_experience"] = fallback_data.get("years_experience", "")
            except (ValueError, TypeError):
                validated_data["years_experience"] = fallback_data.get("years_experience", "")
        else:
            validated_data["years_experience"] = fallback_data.get("years_experience", "")
            
        # Validate education
        if "education" in llm_data and llm_data["education"] and len(llm_data["education"]) > 5:
            validated_data["education"] = llm_data["education"]
        else:
            validated_data["education"] = fallback_data.get("education", "")
            
        # Validate top_skills
        if "top_skills" in llm_data and isinstance(llm_data["top_skills"], list) and llm_data["top_skills"]:
            validated_data["top_skills"] = llm_data["top_skills"][:5]  # Limit to 5 skills
        else:
            validated_data["top_skills"] = fallback_data.get("top_skills", [])
            
        # Validate last_position
        if "last_position" in llm_data and llm_data["last_position"] and len(llm_data["last_position"]) > 3:
            validated_data["last_position"] = llm_data["last_position"]
        else:
            validated_data["last_position"] = fallback_data.get("last_position", "")
            
        return validated_data
    
    def detect_language(self, text):
        """Detect the language of the resume text"""
        try:
            return detect_lang(text[:1000])  # Use only first 1000 chars for detection
        except Exception as e:
            logger.warning(f"Language detection failed: {str(e)}")
            return 'en'  # Default to English

