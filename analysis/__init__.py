from .criteria_matcher import CriteriaMatcher
from .resume_parser import ResumeParser
from .skill_analyzer import SkillAnalyzer
from .recommender import Recommender

class ResumeBatch:
    """Handle batch processing of multiple resumes"""
    
    def __init__(self, pdf_processor, llm_client, json_handler):
        self.pdf_processor = pdf_processor
        self.llm_client = llm_client
        self.json_handler = json_handler
        self.resume_parser = ResumeParser(llm_client, json_handler)
        self.criteria_matcher = CriteriaMatcher(llm_client)
        self.skill_analyzer = SkillAnalyzer(llm_client, json_handler)
        self.recommender = Recommender(llm_client, json_handler)
        self.results = []
        
    async def process_resumes(self, files, criteria_items, job_description=""):
        """Process multiple resumes with comprehensive analysis"""
        from datetime import datetime
        import asyncio
        import os
        from utils.logging_setup import logger
        from langdetect import detect
        
        logger.info(f"Starting batch processing of {len(files)} resumes")
        all_candidates = []
        detailed_results = []
        
        for file in files:
            # Get filename
            filename = os.path.basename(file.name)
            logger.info(f"Processing resume: {filename}")
            
            # Extract text from PDF
            resume_text = self.pdf_processor.extract_text(file)
            if not resume_text:
                logger.warning(f"No text extracted from {filename}")
                all_candidates.append((False, f"🧑 {filename}\n❌ Error: No text extracted\n---"))
                continue
                
            # Detect language
            try:
                lang = detect(resume_text[:500])
                logger.debug(f"Detected language: {lang}")
            except:
                logger.warning("Language detection failed, defaulting to English")
                lang = 'en'
                
            # Process criteria
            logger.info(f"Evaluating {len(criteria_items)} criteria")
            results = await self.criteria_matcher.analyze_criteria_batch(resume_text, criteria_items, lang)
            
            # Get resume summary
            logger.info("Extracting resume summary")
            resume_summary = await self.resume_parser.extract_resume_summary(resume_text, filename, lang)
            
            # Get skill match if job description provided
            skill_match = None
            if job_description.strip():
                logger.info("Analyzing skill match with job description")
                skill_match = await self.skill_analyzer.get_skill_match(resume_text, job_description, filename, lang)
                
            # Generate recommendation if job description provided
            recommendation = None
            if job_description.strip():
                logger.info("Generating hiring recommendation")
                recommendation = await self.recommender.get_recommendation(resume_text, job_description, results, filename, lang)
                
            # Format candidate entry for display
            candidate_entry = self.format_candidate_entry(
                filename, resume_summary, results, skill_match, recommendation
            )
            
            # Check if any criteria matched
            has_match = any("✅" in result for result in results)
            
            # Add to results
            all_candidates.append((has_match, candidate_entry))
            
            detailed_results.append({
                "filename": filename,
                "name": resume_summary.get("name", "Unknown"),
                "basic_info": resume_summary,
                "criteria_results": results,
                "skill_match": skill_match,
                "recommendation": recommendation,
                "has_match": has_match,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Completed processing resume: {filename}")
            
        # Sort candidates to show matches first
        sorted_candidates = sorted(all_candidates, key=lambda x: x[0], reverse=True)
        summary = "\n".join(candidate[1] for candidate in sorted_candidates)
        
        self.results = detailed_results
        logger.info(f"Batch processing complete: {len(detailed_results)} resumes analyzed")
        return summary, detailed_results
        
    def format_candidate_entry(self, filename, resume_summary, results, skill_match, recommendation):
        """Format candidate entry for display"""
        name = resume_summary.get("name", "Unknown")
        exp_years = resume_summary.get("years_experience", "?")
        top_skills_list = resume_summary.get("top_skills", [])
        top_skills = ", ".join(top_skills_list[:3]) if top_skills_list else "Unknown"
        
        # Add skill match score if available
        skill_score_text = ""
        if skill_match:
            match_score = skill_match.get("match_score", 0)
            if match_score >= 80:
                indicator = "🌟"  # Excellent
            elif match_score >= 60:
                indicator = "✨"  # Good
            elif match_score >= 40:
                indicator = "⭐"  # Average
            else:
                indicator = "⚠️"  # Poor
            
            skill_score_text = f"\n{indicator} Skill Match: {match_score}%"
        
        # Add recommendation if available
        recommendation_text = ""
        if recommendation:
            rec_value = recommendation.get("recommendation", "")
            if "highly recommend" in rec_value.lower():
                rec_emoji = "🔥"
            elif "recommend" in rec_value.lower() and "not" not in rec_value.lower():
                rec_emoji = "👍"
            elif "consider" in rec_value.lower():
                rec_emoji = "🤔"
            else:
                rec_emoji = "👎"
            
            recommendation_text = f"\n{rec_emoji} {rec_value}"
        
        # Format criteria results
        candidate_results = "\n".join(results)
        
        # Build the candidate entry
        candidate_entry = (
            f"🧑 {name} ({filename})\n"
            f"📊 Experience: {exp_years} years | Core Skills: {top_skills}"
            f"{skill_score_text}{recommendation_text}\n"
            f"{candidate_results}\n---"
        )
        
        return candidate_entry