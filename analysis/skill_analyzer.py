import re
from utils.logging_setup import get_logger
logger = get_logger(__name__)
from utils.config import Config

class SkillAnalyzer:
    """Analyze skills in resume against job requirements"""
    
    def __init__(self, llm_client, json_handler):
        self.llm_client = llm_client
        self.json_handler = json_handler
        
    async def get_skill_match(self, resume_text, job_description, filename, lang='en'):
        """Calculate skill match score between resume and job description"""
        # First try exact skill matching as fallback
        fallback_match = self._extract_skills_manually(resume_text, job_description)
        fallback_match["filename"] = filename
        
        # Prepare LLM prompt
        system_prompt = (
            f"You are a Recruitment Expert. Compare this {'French' if lang == 'fr' else 'English'} resume to the job description. "
            f"Calculate a numeric match score from 0-100 based on skills alignment only.\n"
            "Provide JSON with:\n"
            "1. match_score: numeric score (0-100)\n"
            "2. matching_skills: array of 3-5 key matching skills\n"
            "3. missing_skills: array of 3-5 important skills from job description missing in the resume\n"
            "Format response as valid JSON only.\n"
        )
        
        user_prompt = f"Resume Content:\n{resume_text}\n\nJob Description:\n{job_description}"
        full_prompt = f"[INST] {system_prompt}\n\n{user_prompt} [/INST]"
        
        # Request LLM analysis
        response = await self.llm_client.generate(
            prompt=full_prompt,
            max_tokens=1024,
            temperature=0.1,
            top_p=0.3
        )
        
        # Check for API errors
        if response["status"] == "error":
            logger.warning(f"API error when calculating skill match: {response.get('error')}")
            logger.info("Using manual skill extraction due to API error")
            return fallback_match
            
        result = response["result"]
        
        # Check for empty response
        if not result:
            logger.warning("Empty response received from API for skill match")
            logger.info("Using manual skill extraction due to empty API response")
            return fallback_match
            
        # Clean and parse JSON response
        try:
            data = self.json_handler.clean_and_parse(result)
            logger.debug("Successfully parsed skill match JSON")
            
            # Add filename to the results
            data["filename"] = filename
            
            # Ensure match_score is within range
            match_score = data.get("match_score", 0)
            try:
                match_score = int(match_score)
                if match_score < 0:
                    match_score = 0
                elif match_score > 100:
                    match_score = 100
                data["match_score"] = match_score
            except:
                data["match_score"] = fallback_match["match_score"]
                
            # Ensure arrays are properly formatted
            if not isinstance(data.get("matching_skills", []), list) or not data.get("matching_skills"):
                data["matching_skills"] = fallback_match["matching_skills"]
                
            if not isinstance(data.get("missing_skills", []), list) or not data.get("missing_skills"):
                data["missing_skills"] = fallback_match["missing_skills"]
                
            return data
            
        except Exception as e:
            logger.error(f"Error processing skill match data: {str(e)}")
            logger.info("Using manual skill extraction due to processing error")
            return fallback_match
    
    def _extract_skills_manually(self, resume_text, job_description):
        """Extract skills from resume and job description using keyword matching"""
        # Common tech and soft skills to look for
        common_skills = {
            # Programming languages
            "python": ["python", "py", "django", "flask"],
            "javascript": ["javascript", "js", "node", "react", "angular", "vue"],
            "java": ["java", "spring", "j2ee"],
            "c#": ["c#", ".net", "asp.net"],
            "c++": ["c++", "cpp"],
            "go": ["golang", "go lang"],
            "ruby": ["ruby", "rails"],
            "php": ["php", "laravel", "symfony"],
            
            # Databases
            "sql": ["sql", "mysql", "postgresql", "oracle"],
            "nosql": ["nosql", "mongodb", "dynamodb", "cosmosdb"],
            
            # Cloud platforms
            "aws": ["aws", "amazon web services", "ec2", "s3", "lambda"],
            "azure": ["azure", "microsoft azure"],
            "gcp": ["gcp", "google cloud"],
            
            # DevOps & tools
            "docker": ["docker", "container"],
            "kubernetes": ["kubernetes", "k8s"],
            "jenkins": ["jenkins", "ci/cd"],
            "git": ["git", "github", "gitlab"],
            
            # Project management
            "agile": ["agile", "scrum", "kanban"],
            "jira": ["jira", "atlassian"],
            
            # Soft skills
            "communication": ["communication", "interpersonal"],
            "leadership": ["leadership", "team lead", "manager"],
            "problem solving": ["problem solving", "analytical"],
            "team player": ["team player", "teamwork", "collaboration"]
        }
        
        # Find skills in resume and job description
        resume_skills = set()
        job_skills = set()
        
        resume_text_lower = resume_text.lower()
        job_description_lower = job_description.lower()
        
        for skill, keywords in common_skills.items():
            # Check resume
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', resume_text_lower):
                    resume_skills.add(skill)
                    break
                    
            # Check job description
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', job_description_lower):
                    job_skills.add(skill)
                    break
        
        # Calculate matching and missing skills
        matching_skills = resume_skills.intersection(job_skills)
        missing_skills = job_skills.difference(resume_skills)
        
        # Calculate match score (percent of job skills found in resume)
        match_score = int((len(matching_skills) / len(job_skills) * 100) if job_skills else 0)
        
        # Cap at 100%
        match_score = min(match_score, 100)
        
        # Return formatted result
        return {
            "match_score": match_score,
            "matching_skills": list(matching_skills)[:5],  # Limit to 5 skills
            "missing_skills": list(missing_skills)[:5]     # Limit to 5 skills
        }
        
    def highlight_matching_skills(self, resume_text, matching_skills):
        """Highlight occurrences of matching skills in resume text"""
        highlighted_text = resume_text
        for skill in matching_skills:
            # Create regex pattern that matches the skill (case insensitive)
            pattern = re.compile(r'\b' + re.escape(skill) + r'\b', re.IGNORECASE)
            
            # Replace with highlighted version
            highlighted_text = pattern.sub(f'**{skill.upper()}**', highlighted_text)
            
        return highlighted_text
    
    def extract_resume_skills_for_comparison(self, resume_text):
        """Extract all potential skills from a resume for manual review"""
        # Common skill indicators in resumes
        skill_indicators = [
            r'(?:technical|core|key|primary|language|programming)?\s*skills\s*(?::|include|are)?',
            r'proficient (?:in|with)',
            r'knowledge of',
            r'experience (?:in|with)',
            r'familiar with',
            r'expertise in'
        ]
        
        # Look for skill sections in the resume
        skill_sections = []
        for indicator in skill_indicators:
            matches = re.finditer(indicator, resume_text, re.IGNORECASE)
            for match in matches:
                # Extract text after the indicator (up to 200 chars)
                start_pos = match.end()
                section = resume_text[start_pos:start_pos + 200]
                # Split by common delimiters
                skills = re.split(r'[,;•\n]', section)
                skill_sections.extend([s.strip() for s in skills if s.strip()])
                
        # Filter out common non-skill text
        non_skill_patterns = [
            r'^and$', r'^in$', r'^with$', r'^of$', r'^the$', r'^a$', r'^to$',
            r'^years$', r'^year$', r'^including$', r'^using$', r'^or$'
        ]
        
        filtered_skills = []
        for skill in skill_sections:
            skip = False
            for pattern in non_skill_patterns:
                if re.match(pattern, skill, re.IGNORECASE):
                    skip = True
                    break
            if not skip and 2 <= len(skill) <= 30:  # Reasonable skill length
                filtered_skills.append(skill)
                
        return filtered_skills