import gradio as gr
import threading
import argparse
from utils.resume_batch import ResumeBatch  # Import the newly created ResumeBatch class
from utils.config_class import Config  # Import Config class
from ui.gradio_app import GradioApp  # Correct import path based on your folder structure
from core.pdf_processor import PDFProcessor
from core.llm_client import LLMClient
from core.json_handler import JSONHandler
from core.report_generator import ReportGenerator
from api.flask_api import FlaskAPI
from utils.logging_setup import get_logger

# Set up logger
logger = get_logger(__name__)

# Instantiate the components
pdf_processor = PDFProcessor()  # Create an instance of PDFProcessor
llm_client = LLMClient()        # Create an instance of LLMClient
json_handler = JSONHandler()    # Create an instance of JSONHandler
report_generator = ReportGenerator(template_dir=Config.TEMPLATE_DIR)  # Create an instance of ReportGenerator

# Pass the initialized components to ResumeBatch
batch = ResumeBatch(pdf_processor=pdf_processor, llm_client=llm_client, json_handler=json_handler)

# Create the GradioApp instance
gradio_app = GradioApp(pdf_processor, llm_client, json_handler, report_generator)

# Build the Gradio UI
demo = gradio_app.build_ui()

# Now call demo.launch() directly to start the Gradio app
demo.launch(server_port=8080, share=True)  # Adjust the port and share options as required

# Define a function to create the app components
def create_app():
    # Initialize core components
    pdf_processor = PDFProcessor()  # You may need to pass any required arguments to PDFProcessor
    llm_client = LLMClient()  # Pass any required arguments to LLMClient
    json_handler = JSONHandler()  # Pass any required arguments to JSONHandler
    report_generator = ReportGenerator(template_dir=Config.TEMPLATE_DIR)  # Initialize ReportGenerator with template directory

    # Initialize Gradio app (UI) with the necessary components
    demo = GradioApp(
        pdf_processor=pdf_processor, 
        llm_client=llm_client, 
        json_handler=json_handler, 
        report_generator=report_generator
    )
    
    # Initialize Flask API component, pass the necessary arguments
    flask_api = FlaskAPI(
        pdf_processor=pdf_processor, 
        llm_client=llm_client, 
        json_handler=json_handler, 
        report_generator=report_generator
    )

    # Return the objects that need to be unpacked (Gradio demo and Flask API)
    return demo, flask_api

# Define function to run Flask API
def run_flask_api(flask_api, host, port, debug):
    # Ensure Flask app is started correctly
    flask_api.run(host=host, port=port, debug=debug)

# Define function to run Gradio UI
def run_gradio_ui(demo, server_port, share):
    # Run the Gradio UI
    demo.launch(server_port=server_port, share=share)

# Main execution entry
if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Resume Analyzer")
    parser.add_argument("--api-only", action="store_true", help="Run only the Flask API")
    parser.add_argument("--ui-only", action="store_true", help="Run only the Gradio UI")
    parser.add_argument("--api-port", type=int, default=Config.FLASK_PORT, help="Port for the Flask API")  # Updated to use FLASK_PORT from Config
    parser.add_argument("--ui-port", type=int, default=Config.GRADIO_PORT, help="Port for the Gradio UI")  # Updated to use GRADIO_PORT from Config
    parser.add_argument("--no-share", action="store_true", help="Disable Gradio sharing link")
    args = parser.parse_args()
    
    # Create application components (Gradio app and Flask API)
    demo, flask_api = create_app()
    
    # Determine what to run based on arguments
    if args.api_only:
        # Run Flask API only
        logger.info("Running in API-only mode")
        run_flask_api(flask_api, host="0.0.0.0", port=args.api_port, debug=Config.DEBUG)
    elif args.ui_only:
        # Run Gradio UI only
        logger.info("Running in UI-only mode")
        run_gradio_ui(demo, server_port=args.ui_port, share=not args.no_share)
    else:
        # Run both in separate threads
        logger.info("Running both API and UI")
        
        # Start Flask API in a separate thread
        api_thread = threading.Thread(
            target=run_flask_api,
            args=(flask_api, "0.0.0.0", args.api_port, Config.DEBUG),
            daemon=True
        )
        api_thread.start()
        
        # Run Gradio in the main thread
        run_gradio_ui(demo, server_port=args.ui_port, share=not args.no_share)
