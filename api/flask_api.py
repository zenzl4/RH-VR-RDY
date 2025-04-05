from flask import Flask, request, jsonify, send_file
import os
import tempfile
import json
import asyncio
from utils.logging_setup import get_logger
logger = get_logger(__name__)
from utils.config import Config
from analysis import ResumeBatch

class FlaskAPI:
    """Flask API for programmatic access to resume analysis"""
    
    def __init__(self, pdf_processor, llm_client, json_handler, report_generator):
        self.pdf_processor = pdf_processor
        self.llm_client = llm_client
        self.json_handler = json_handler
        self.report_generator = report_generator
        self.app = Flask(__name__)
        self.configure_routes()
        
    def configure_routes(self):
        """Set up API routes"""
        @self.app.route('/')
        def index():
            return "Resume Analyzer API Service - Use the Gradio UI for interaction or API endpoints for programmatic access"
            
        @self.app.route('/api/analyze', methods=['POST'])
        def analyze_resumes():
            # Check if files were uploaded
            if 'files' not in request.files:
                return jsonify({"error": "No files provided"}), 400
                
            files = request.files.getlist('files')
            if not files or files[0].filename == '':
                return jsonify({"error": "No files selected"}), 400
                
            # Get criteria and job description
            criteria_text = request.form.get('criteria', '')
            job_description = request.form.get('job_description', '')
            
            if not criteria_text:
                return jsonify({"error": "Criteria is required"}), 400
                
            # Save files to temporary location
            temp_files = []
            for file in files:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp:
                    file.save(temp.name)
                    temp_files.append(temp.name)
                    
            # Parse criteria
            criteria_items = []
            for line in criteria_text.split('\n'):
                if ',' in line:
                    criteria_items.extend([item.strip() for item in line.split(',') if item.strip()])
                else:
                    if line.strip():
                        criteria_items.append(line.strip())
                        
            if not criteria_items:
                criteria_items = [criteria_text.strip()]
                
            # Process resumes
            try:
                # Create batch processor
                resume_batch = ResumeBatch(self.pdf_processor, self.llm_client, self.json_handler)
                
                # Process in async context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Create file objects
                class FileObj:
                    def __init__(self, filepath):
                        self.name = filepath
                        
                file_objs = [FileObj(f) for f in temp_files]
                
                # Run analysis
                summary, detailed_results = loop.run_until_complete(
                    resume_batch.process_resumes(file_objs, criteria_items, job_description)
                )
                
                # Clean up temporary files
                for file_path in temp_files:
                    try:
                        os.unlink(file_path)
                    except:
                        pass
                        
                return jsonify({
                    "status": "success",
                    "results": detailed_results
                })
                
            except Exception as e:
                # Clean up temporary files
                for file_path in temp_files:
                    try:
                        os.unlink(file_path)
                    except:
                        pass
                        
                logger.error(f"API error: {str(e)}")
                return jsonify({"error": str(e)}), 500
                
        @self.app.route('/api/generate-report', methods=['POST'])
        def generate_report():
            # Get analysis results from request
            if not request.json or 'results' not in request.json:
                return jsonify({"error": "No analysis results provided"}), 400
                
            results = request.json['results']
            report_type = request.json.get('type', 'html')
            
            try:
                if report_type.lower() == 'json':
                    # Generate JSON report
                    filename = self.report_generator.generate_json_report(results)
                else:
                    # Generate HTML report
                    filename = self.report_generator.generate_html_report(results)
                    
                if filename:
                    return send_file(filename, as_attachment=True)
                else:
                    return jsonify({"error": "Failed to generate report"}), 500
                    
            except Exception as e:
                logger.error(f"Report generation error: {str(e)}")
                return jsonify({"error": str(e)}), 500
                
    def run(self, host="0.0.0.0", port=5000, debug=False):
        """Run the Flask API server"""
        self.app.run(host=host, port=port, debug=debug)