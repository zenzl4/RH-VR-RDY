import asyncio
import re
from utils.logging_setup import get_logger
logger = get_logger(__name__)

class CriteriaMatcher:
    """Enhanced criteria matching with improved accuracy"""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        
    async def analyze_criterion(self, resume_text, criterion, lang='en'):
        """Analyze resume against a single criterion with enhanced error handling"""
        system_prompt = (
            f"You are a Recruitment Assistant Expert. Analyze the ENTIRE {'French' if lang == 'fr' else 'English'} resume "
            f"and STRICTLY evaluate against this criterion: {criterion}. Follow these rules:\n"
            "1. Carefully scan ALL SECTIONS, including education, experience, skills, and projects.\n"
            "2. Only return a match if the EXACT phrase appears VERBATIM anywhere in the resume.\n"
            "3. Partial matches or close variations are NOT allowed.\n"
            "4. If you find an exact match, ONLY return '✅'\n"
            "5. If no match is found, ONLY return '❌'\n"
        )
        
        user_prompt = f"Resume Content:\n{resume_text}\n\nEvaluation Criterion:\n{criterion}"
        full_prompt = f"[INST] {system_prompt}\n\n{user_prompt} [/INST]"
        
        response = await self.llm_client.generate(
            prompt=full_prompt,
            max_tokens=10,
            temperature=0.1,
            top_p=0.3,
            stop=["\n"]
        )
        
        if response["status"] == "error":
            logger.warning(f"Error analyzing criterion '{criterion}': {response.get('error')}")
            return f"❌ {criterion} (Error: {response.get('error', 'API request failed')})"
            
        result = response["result"]
        
        # Check for match indicators in the response
        if "✅" in result or "PASS" in result.upper():
            logger.info(f"Criterion matched: {criterion}")
            return f"✅ {criterion}"
        else:
            logger.info(f"Criterion not matched: {criterion}")
            return f"❌ {criterion}"
    
    async def analyze_criteria_batch(self, resume_text, criteria_items, lang='en'):
        """Process multiple criteria in parallel"""
        logger.info(f"Analyzing {len(criteria_items)} criteria")
        
        tasks = []
        for criterion in criteria_items:
            task = self.analyze_criterion(resume_text, criterion, lang)
            tasks.append(task)
            
        return await asyncio.gather(*tasks)
    
    def get_match_rate(self, criteria_results):
        """Calculate the match rate for criteria results"""
        if not criteria_results:
            return 0
            
        total = len(criteria_results)
        matched = sum(1 for result in criteria_results if "✅" in result)
        return (matched / total * 100) if total > 0 else 0
    
    def format_criteria_results(self, criteria_results):
        """Format criteria results for display"""
        return "\n".join(criteria_results)
    
    def get_criteria_from_text(self, criteria_text):
        """Parse criteria from text input"""
        if not criteria_text.strip():
            return []
            
        criteria_items = []
        for line in criteria_text.split('\n'):
            if ',' in line:
                criteria_items.extend([item.strip() for item in line.split(',') if item.strip()])
            else:
                if line.strip():
                    criteria_items.append(line.strip())
                    
        # Fallback if no criteria were parsed
        if not criteria_items and criteria_text.strip():
            criteria_items = [criteria_text.strip()]
            
        return criteria_items