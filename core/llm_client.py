import ollama
import json
import asyncio
from utils.logging_setup import get_logger
from utils.config_class import Config
from utils.json_handler import JSONHandler  # Ensure this is correctly imported
import os

logger = get_logger(__name__)

class LLMClient:
    """Unified Mistral LLM client with Ollama integration"""

    def __init__(self, model_name=None, timeout=None):
        self.model_name = model_name or Config.LLM_MODEL
        self.timeout = timeout or Config.API_TIMEOUT
        self.retry_count = 3
        self.retry_delay = 2  # seconds

    async def generate(self, prompt, model=None, max_tokens=1024, temperature=0.1, top_p=0.3):
        model = model or self.model_name

        for attempt in range(self.retry_count):
            try:
                logger.debug(f"Sending request to Mistral model (attempt {attempt+1}/{self.retry_count})")

                response = ollama.chat(model=self.model_name, messages=[{"role": "user", "content": prompt}])

                if 'message' not in response or 'content' not in response['message']:
                    logger.error(f"Unexpected response format: {response}")
                    if attempt < self.retry_count - 1:
                        logger.info(f"Retrying in {self.retry_delay} seconds...")
                        await asyncio.sleep(self.retry_delay)
                        continue
                    return {"error": "Invalid response format from Mistral model", "status": "error"}

                result = response["message"]["content"].strip()

                if not result:
                    logger.warning("Empty response received from Mistral model")
                    if attempt < self.retry_count - 1:
                        logger.info(f"Retrying in {self.retry_delay} seconds...")
                        await asyncio.sleep(self.retry_delay)
                        continue
                    return {"error": "Empty response", "status": "error"}

                logger.debug("Successfully received response from Mistral model")
                return {"result": result, "status": "success"}

            except KeyError as e:
                logger.error(f"Missing key in response: {str(e)}")
                return {"error": f"Missing key in response: {str(e)}", "status": "error"}
            except Exception as e:
                logger.error(f"Error during request: {str(e)}")
                if attempt < self.retry_count - 1:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    await asyncio.sleep(self.retry_delay)
                else:
                    return {"error": f"Request failed: {str(e)}", "status": "error"}

    async def evaluate_resume(self, resume_data, criteria_items, job_description):
        prompt = self.create_prompt(resume_data, criteria_items, job_description)
        response = await self.generate(prompt)

        if response.get("status") == "success":
            result = response["result"]
            score = self.extract_score_from_result(result)
            feedback = self.generate_feedback(result)

            evaluation = {
                "resume": resume_data,
                "score": score,
                "feedback": feedback
            }

            # Ensure the output directory exists before saving
            output_dir = "outputs"
            os.makedirs(output_dir, exist_ok=True)

            # Save to JSON with a valid file path
            try:
                output_path = os.path.join(output_dir, "evaluation_result.json")  # Customize the path as needed
                JSONHandler.save_to_json(evaluation, output_path)
                logger.info(f"Evaluation saved to {output_path}")
            except Exception as e:
                logger.error(f"Failed to save evaluation to JSON: {str(e)}")

            return evaluation
        else:
            return {"error": response.get("error", "Unknown error")}

    def create_prompt(self, resume_data, criteria_items, job_description):
        prompt = f"Evaluate the following resume based on these criteria: {', '.join(criteria_items)}\n"
        prompt += f"Job description: {job_description}\n\n"
        prompt += f"Resume:\n{resume_data}"
        return prompt

    def extract_score_from_result(self, result):
        try:
            if "Score:" in result:
                score = int(result.split("Score:")[1].split("\n")[0].strip())
                return score
            else:
                logger.warning("No score found in result.")
                return 0
        except Exception as e:
            logger.warning(f"Error extracting score: {str(e)}")
            return 0

    def generate_feedback(self, result):
        return f"Feedback: {result[:100]}..."
