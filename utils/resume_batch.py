# utils/resume_batch.py

from core.pdf_processor import PDFProcessor  # Update this import
# In utils/resume_batch.py
from core.llm_client import LLMClient  # Correct the path to 'core.llm_client'
# In utils/resume_batch.py
from core.json_handler import JSONHandler  # Correct the path to 'core.json_handler'

import asyncio

class ResumeBatch:
    def __init__(self, pdf_processor, llm_client, json_handler):
        self.pdf_processor = pdf_processor
        self.llm_client = llm_client
        self.json_handler = json_handler

    async def process_resumes(self, files, criteria_items, job_description):
        """
        Process a batch of resumes based on provided criteria.
        """
        try:
            # Process each resume (Use asyncio.to_thread if extract_text is synchronous)
            processed_resumes = []
            for file in files:
                print(f"Processing file: {file}")  # Optional logging

                # Run extract_text asynchronously using asyncio.to_thread
                resume_data = await asyncio.to_thread(self.pdf_processor.extract_text, file)
                processed_resumes.append(resume_data)

            # Evaluate the extracted resume data
            evaluation_results = []
            for resume in processed_resumes:
                evaluation_result = await self.llm_client.evaluate_resume(resume, criteria_items, job_description)
                evaluation_results.append(evaluation_result)

            # Generate summary and detailed results
            summary = "Processed " + str(len(evaluation_results)) + " resumes."
            detailed_results = {
                "resumes": evaluation_results
            }

            # Optionally, store the results as JSON
            self.json_handler.save_to_json(detailed_results)

            return summary, detailed_results

        except Exception as e:
            raise Exception(f"Error while processing resumes: {e}")
