import gradio as gr
import asyncio
import logging
from datetime import datetime
from utils.config_class import Config  # Import Config class
from utils.resume_batch import ResumeBatch  # Import ResumeBatch class (adjust path if necessary)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Add a console handler to output logs to the console
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

class GradioApp:
    """Main Gradio UI application with enhanced features"""
    
    def __init__(self, pdf_processor, llm_client, json_handler, report_generator):
        self.pdf_processor = pdf_processor
        self.llm_client = llm_client
        self.json_handler = json_handler
        self.report_generator = report_generator
        self.session_results = {}

    def build_ui(self):
        """Create the Gradio UI with all components"""
        custom_css = """
        #chat-container {
            max-width: 800px;
            margin: 0 auto;
        }
        .resume-section {
            background: #f0f0f0;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .dark .resume-section {
            background: #2a2a2a;
        }
        .job-section {
            background: #e6f7ff;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .dark .job-section {
            background: #102a40;
        }
        .export-button {
            background-color: #4CAF50;
            color: white;
        }
        """
        
        with gr.Blocks(css=custom_css, theme=gr.themes.Default()) as demo:
            gr.Markdown("# 🧑💼 Advanced AI Recruitment Assistant")
            
            with gr.Row():
                with gr.Column(scale=2):
                    chatbot = gr.Chatbot(label="Recruitment Assistant", elem_id="chatbot", height=600)
                    
                    with gr.Row():
                        msg = gr.Textbox(
                            label="Your Message",
                            placeholder="Ask questions about resumes or recruitment...",
                            scale=8
                        )
                        clear_btn = gr.Button("Clear Chat", scale=1)
                        export_btn = gr.Button("Export JSON", scale=1, elem_classes=["export-button"])
                        export_html_btn = gr.Button("Export HTML", scale=1, elem_classes=["export-button"])
                        
                with gr.Column(scale=1):
                    with gr.Group(elem_classes="resume-section"):
                        file_input = gr.File(
                            label="Upload Resumes (PDF)",
                            file_count="multiple",
                            file_types=[".pdf"]
                        )
                        
                        criteria_input = gr.Textbox(
                            label="Required Criteria",
                            placeholder="Enter criteria (one per line or separate with commas)",
                            lines=3
                        )
                        
                    with gr.Group(elem_classes="job-section"):
                        job_description = gr.Textbox(
                            label="Job Description (Optional)",
                            placeholder="Paste the job description to enable AI matching and recommendations",
                            lines=7
                        )
                        
                    analyze_btn = gr.Button("Analyze Resumes", variant="primary", size="lg")
            
            # Export components
            export_file = gr.File(label="Download Report", visible=False)
            
            # Event handlers
            analyze_btn.click(
                self.analyze_resumes_wrapper,
                inputs=[chatbot, file_input, criteria_input, job_description],
                outputs=[chatbot, msg]
            )
            
            msg.submit(
                self.chat_wrapper,
                inputs=[chatbot, msg],
                outputs=[chatbot, msg]
            )
            
            clear_btn.click(
                lambda: ([], ""),
                outputs=[chatbot, msg]
            )
            
            export_btn.click(
                self.export_results_to_json_wrapper,
                inputs=[chatbot],
                outputs=[chatbot, export_file]
            )
            
            export_html_btn.click(
                self.export_results_to_html_wrapper,
                inputs=[chatbot],
                outputs=[export_file]
            )

        return demo
    
    def analyze_resumes_wrapper(self, history, files, criteria_text, job_description):
        """Wrapper for analyze_resumes to handle async function in Gradio"""
        return asyncio.run(
            self.analyze_resumes(history, files, criteria_text, job_description)
    )

        
    async def analyze_resumes(self, history, files, criteria_text, job_description):
        """Process resume analysis with enhanced error handling"""
        if not files:
            return history, "Error: No PDF resumes uploaded."
        if not criteria_text.strip():
            return history, "Error: Evaluation criteria is missing."
            
        logger.info(f"Starting resume analysis for {len(files)} files")
            
        # Parse criteria - split by newlines or commas
        criteria_items = []
        for line in criteria_text.split('\n'):
            if ',' in line:
                criteria_items.extend([item.strip() for item in line.split(',') if item.strip()])
            else:
                if line.strip():
                    criteria_items.append(line.strip())
                    
        # Fallback if no criteria were parsed
        if not criteria_items:
            criteria_items = [criteria_text.strip()]
            
        # Create resume batch processor
        resume_batch = ResumeBatch(self.pdf_processor, self.llm_client, self.json_handler)
        
        # Process resumes
        try:
            summary, detailed_results = await resume_batch.process_resumes(
                files, criteria_items, job_description
            )
            
            # Store results for export
            session_id = datetime.now().strftime("%Y%m%d%H%M%S")
            self.session_results[session_id] = detailed_results
            
            # Format result for display
            result_header = f"📋 Resume Analysis Results ({len(files)} candidates)"
            history.append([f"Criteria Evaluation:", f"{result_header}\n\n{summary}"])
            
            return history, ""
        except Exception as e:
            logger.error(f"Error during resume analysis: {str(e)}")
            history.append(["System", f"❌ Error during analysis: {str(e)}"])
            return history, ""
        
    def chat_wrapper(self, history, message):
        """Wrapper for chat to handle async function in Gradio"""
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            self.chat(history, message)
        )
        
    async def chat(self, history, message):
        """Handle chat interactions with LLM"""
        if not message.strip():
            return history, ""
            
        logger.info(f"Chat request: {message[:50]}..." if len(message) > 50 else f"Chat request: {message}")
            
        system_prompt = "You are a helpful AI assistant for recruitment. Respond concisely and accurately."
        formatted_prompt = f"[INST] {system_prompt}\n\n{message} [/INST]"
        
        response = await self.llm_client.generate(
            prompt=formatted_prompt,
            max_tokens=512,
            temperature=0.7,
            top_p=0.9
        )
        
        if response["status"] == "error":
            full_response = f"API Error: {response.get('error', 'Unknown error')}"
            logger.error(f"Chat API error: {response.get('error')}")
        else:
            full_response = response["result"]
            logger.debug(f"Chat response: {full_response[:50]}..." if len(full_response) > 50 else f"Chat response: {full_response}")
            
        history.append([message, full_response])
        return history, ""
        
    def export_results_to_json_wrapper(self, history):
        """Wrapper for export_results_to_json to handle file export in Gradio"""
        if not self.session_results:
            history.append(["Export Results", "No analysis results to export."])
            return history, None
            
        # Get the most recent session
        latest_session = max(self.session_results.keys())
        results = self.session_results[latest_session]
        
        # Generate JSON
        try:
            filename = self.report_generator.generate_json_report(results)
            
            if filename:
                history.append(["Export Results", f"Analysis exported to {os.path.basename(filename)}"])
                return history, filename
            else:
                history.append(["Export Results", "Failed to create JSON export."])
                return history, None
        except Exception as e:
            logger.error(f"Error during JSON export: {str(e)}")
            history.append(["Export Results", f"Error: {str(e)}"])
            return history, None
        
    def export_results_to_html_wrapper(self, history):
        """Wrapper for export_results_to_html to handle file export in Gradio"""
        if not self.session_results:
            return None
            
        # Get the most recent session
        latest_session = max(self.session_results.keys())
        detailed_results = self.session_results[latest_session]
        
        # Generate HTML
        try:
            filename = self.report_generator.generate_html_report(detailed_results)
            
            if filename:
                return filename
            else:
                return None
        except Exception as e:
            logger.error(f"Error during HTML export: {str(e)}")
            return None

# Fix to launch the Gradio UI properly
if __name__ == "__main__":
    # Ensure the components are properly initialized before passing them to GradioApp
    gradio_app = GradioApp(pdf_processor, llm_client, json_handler, report_generator)

    # Build the Gradio UI
    demo = gradio_app.build_ui()

    # Directly call demo.launch() to start the Gradio app
    demo.launch(server_port=8080, share=True)  # Adjust the port and share options as required
