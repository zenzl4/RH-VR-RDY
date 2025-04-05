from utils.logging_setup import get_logger
logger = get_logger(__name__)

class Recommender:
    """Generate hiring recommendations based on resume analysis"""
    
    def __init__(self, llm_client, json_handler):
        self.llm_client = llm_client
        self.json_handler = json_handler
        
    async def get_recommendation(self, resume_text, job_description, criteria_results, filename, lang='en'):
        """Generate hiring recommendation based on resume analysis"""
        # Combine criteria results into a summary
        criteria_summary = "\n".join(criteria_results)
        
        # Prepare LLM prompt
        system_prompt = (
            f"You are a Senior Recruitment Expert. Analyze this {'French' if lang == 'fr' else 'English'} resume against the job description. "
            f"Based on the resume content and the criteria evaluation results, provide your professional recommendation.\n"
            "Structure your response in JSON with:\n"
            "1. overall_rating: numeric score (1-10)\n"
            "2. strengths: Array of 2-3 key candidate strengths relevant to this role\n"
            "3. concerns: Array of 2-3 potential concerns or gaps\n"
            "4. interview_questions: Array of 2-3 specific questions you would ask this candidate\n"
            "5. recommendation: Short hiring recommendation (Highly Recommend, Recommend, Consider, or Not Recommended)\n"
            "Format response as valid JSON only.\n"
        )
        
        user_prompt = (
            f"Resume Content:\n{resume_text}\n\n"
            f"Job Description:\n{job_description}\n\n"
            f"Criteria Evaluation Results:\n{criteria_summary}"
        )
        
        full_prompt = f"[INST] {system_prompt}\n\n{user_prompt} [/INST]"
        
        # Request LLM analysis
        response = await self.llm_client.generate(
            prompt=full_prompt,
            max_tokens=1024,
            temperature=0.3,
            top_p=0.5
        )
        
        # Check for API errors
        if response["status"] == "error":
            logger.warning(f"API error when generating recommendation: {response.get('error')}")
            return self._fallback_recommendation(criteria_results, filename)
            
        result = response["result"]
        
        # Check for empty response
        if not result:
            logger.warning("Empty response received from API for recommendation")
            return self._fallback_recommendation(criteria_results, filename)
            
        # Clean and parse JSON response
        try:
            data = self.json_handler.clean_and_parse(result)
            logger.debug("Successfully parsed recommendation JSON")
            
            # Add filename
            data["filename"] = filename
            
            # Ensure all required fields are present
            required_fields = {
                "overall_rating": 0,
                "strengths": [],
                "concerns": [],
                "interview_questions": [],
                "recommendation": "Not available"
            }
            
            for field, default_value in required_fields.items():
                if field not in data or not data[field]:
                    data[field] = default_value
                    
            # Ensure overall_rating is within range (1-10)
            try:
                rating = int(data["overall_rating"])
                if rating < 1:
                    rating = 1
                elif rating > 10:
                    rating = 10
                data["overall_rating"] = rating
            except (ValueError, TypeError):
                data["overall_rating"] = 5  # Default to middle rating
                
            # Ensure arrays are lists
            array_fields = ["strengths", "concerns", "interview_questions"]
            for field in array_fields:
                if not isinstance(data.get(field), list):
                    data[field] = [str(data[field])] if data.get(field) else []
                    
            return data
            
        except Exception as e:
            logger.error(f"Error processing recommendation data: {str(e)}")
            return self._fallback_recommendation(criteria_results, filename)
            
    def _fallback_recommendation(self, criteria_results, filename):
        """Generate a fallback recommendation when API fails"""
        logger.info("Using fallback recommendation generation")
        
        # Count matching criteria
        matched_count = sum(1 for result in criteria_results if "✅" in result)
        total_count = len(criteria_results)
        match_percentage = (matched_count / total_count * 100) if total_count > 0 else 0
        
        # Determine overall rating based on criteria matches
        if match_percentage >= 80:
            overall_rating = 8
            recommendation = "Highly Recommend"
            strengths = ["Meets most job requirements", "Strong match for required criteria"]
            concerns = ["Verify depth of knowledge in matched areas"]
            questions = ["Can you elaborate on your experience with the technologies mentioned?"]
        elif match_percentage >= 60:
            overall_rating = 6
            recommendation = "Recommend"
            strengths = ["Meets many job requirements", "Good alignment with key criteria"]
            concerns = ["Some required skills may be missing", "Verify experience level"]
            questions = ["How would you address the gaps in your skillset for this role?"]
        elif match_percentage >= 40:
            overall_rating = 4
            recommendation = "Consider"
            strengths = ["Meets some job requirements", "May have transferable skills"]
            concerns = ["Several required skills missing", "May require significant training"]
            questions = ["How would you compensate for your missing qualifications?"]
        else:
            overall_rating = 2
            recommendation = "Not Recommended"
            strengths = ["May have some relevant background", "Could be considered for a different role"]
            concerns = ["Very few required skills present", "Significant skill gap for this position"]
            questions = ["Why do you believe you're qualified for this specific position?"]
            
        return {
            "filename": filename,
            "overall_rating": overall_rating,
            "strengths": strengths,
            "concerns": concerns,
            "interview_questions": questions,
            "recommendation": recommendation
        }
        
    def determine_recommendation_tier(self, criteria_match_rate, skill_match_score):
        """Determine recommendation tier based on criteria and skill matches"""
        # Weight: 60% criteria match, 40% skill match
        weighted_score = (criteria_match_rate * 0.6) + (skill_match_score * 0.4)
        
        if weighted_score >= 80:
            return "Highly Recommend", 8
        elif weighted_score >= 65:
            return "Recommend", 7
        elif weighted_score >= 50:
            return "Consider", 5
        else:
            return "Not Recommended", 3