# core/llm_client.py
import ollama
import asyncio
import os
import json
from utils.logging_setup import get_logger
from utils.config_class import Config

logger = get_logger(__name__)

class LLMClient:
    def __init__(self, model_name=None, timeout=None):
        self.model_name = model_name or Config.LLM_MODEL
        self.timeout = timeout or Config.API_TIMEOUT
        self.retry_count = 3
        self.retry_delay = 2

    async def evaluate_resume(self, resume_data, criteria_items, job_description):
        """Complete fixed evaluation pipeline"""
        try:
            from utils.json_handler import JSONHandler
            
            # 1. Generate strict prompt
            prompt = self._create_structured_prompt(resume_data, criteria_items, job_description)
            
            # 2. Get LLM response
            llm_response = await self._get_llm_response(prompt)
            logger.debug(f"Raw LLM response: {llm_response}")

            if not llm_response.strip():
                raise ValueError("Received empty response from LLM")

            # 3. Parse response
            parsed_data = JSONHandler.clean_and_parse(llm_response)
            if "error" in parsed_data:
                raise ValueError(parsed_data["error"])
            
            # 4. Build evaluation result
            evaluation = {
                "score": parsed_data.get("score", 0),
                "feedback": parsed_data.get("summary", "No feedback generated"),
                "missing_skills": parsed_data.get("missing_skills", []),
                "recommendation": parsed_data.get("recommendation", "neutral")
            }
            
            # 5. Save results with explicit file path
            output_dir = os.path.abspath("outputs")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "evaluation_result.json")
            
            # Call save_to_json with both arguments explicitly named
            JSONHandler.save_to_json(data=evaluation, file_path=output_path)
            
            return evaluation
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            return {
                "error": f"Invalid JSON response from LLM: {str(e)}",
                "score": 0,
                "feedback": "Evaluation failed - invalid response format"
            }
        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            return {
                "error": str(e),
                "score": 0,
                "feedback": "Evaluation failed - check logs"
            }

    async def _get_llm_response(self, prompt):
        """Fixed async LLM call with better error handling"""
        for attempt in range(self.retry_count):
            try:
                response = await ollama.AsyncClient().chat(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    options={'temperature': 0.3}
                )
                content = response['message']['content']
                
                if not content.strip():
                    raise ValueError("Empty response from LLM")
                    
                return content
                
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed: {str(e)}")
                if attempt < self.retry_count - 1:
                    await asyncio.sleep(self.retry_delay)
        raise Exception("All retry attempts failed")

    def _create_structured_prompt(self, resume_data, criteria_items, job_description):
        """Create a structured prompt that forces JSON response"""
        prompt = f"""You are a resume evaluation assistant. Respond ONLY with valid JSON in this exact format:
        {{
            "score": 0-100,
            "summary": "evaluation summary",
            "missing_skills": ["list", "of", "missing", "skills"],
            "recommendation": "strong/neutral/weak"
        }}
        
        Evaluation Criteria: {', '.join(criteria_items)}
        Job Description: {job_description}
        
        Resume Content:
        {resume_data}
        """
        return prompt
