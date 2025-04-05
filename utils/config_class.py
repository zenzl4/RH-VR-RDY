import os

class Config:
    EXPORT_DIR = "exports"  # Default export directory
    TEMPLATE_DIR = "templates"  # Default template directory, adjust as necessary

    @staticmethod
    def ensure_export_dir():
        """Ensure the export directory exists, and create it if it doesn't."""
        if not os.path.exists(Config.EXPORT_DIR):
            os.makedirs(Config.EXPORT_DIR)
        return Config.EXPORT_DIR

    """Configuration management for the Resume Analyzer"""
    
    # API Settings
    OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "45"))
    
    # LLM Model Settings
    LLM_MODEL = os.getenv("LLM_MODEL", "mistral:latest")  # Added LLM_MODEL here
    DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "mistral:latest")
    DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.1"))
    DEFAULT_TOP_P = float(os.getenv("DEFAULT_TOP_P", "0.3"))
    
    # Application Settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Server Settings
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    GRADIO_HOST = os.getenv("GRADIO_HOST", "0.0.0.0")
    GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7860"))
    
    # API and UI Port
    API_PORT = int(os.getenv("API_PORT", "5000"))  # Port for Flask API
    UI_PORT = int(os.getenv("UI_PORT", "7860"))    # Port for Gradio UI
    
    # Feature Flags
    ENABLE_FLASK_API = os.getenv("ENABLE_FLASK_API", "True").lower() == "true"
    ENABLE_ADVANCED_JSON_CLEANING = os.getenv("ENABLE_ADVANCED_JSON_CLEANING", "True").lower() == "true"
    ENABLE_PDF_FALLBACKS = os.getenv("ENABLE_PDF_FALLBACKS", "True").lower() == "true"
    USE_ADVANCED_CLEANUP = os.getenv("USE_ADVANCED_CLEANUP", "True").lower() == "true"  # Added this line
    
    # Path Settings
    TEMPLATE_DIR = os.getenv("TEMPLATE_DIR", "ui/templates")
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
    EXPORT_DIR = os.getenv("EXPORT_DIR", "export")  # Added EXPORT_DIR
    
    @classmethod
    def get_llm_api_url(cls):
        """Get the LLM API URL"""
        return os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    
    @classmethod
    def get_prompt_template(cls, template_name):
        """Get a prompt template by name"""
        templates = {
            "resume_summary": (
                "You are a Recruitment Expert. Extract key information from this {lang} resume. "
                "Create a JSON object with these fields (leave empty if not found):\n"
                "1. name: Candidate's full name\n"
                "2. email: Candidate's email address\n"
                "3. phone: Candidate's phone number\n"
                "4. years_experience: Total years of professional experience (numeric only)\n"
                "5. education: Highest degree and institution\n"
                "6. top_skills: Array of 3-5 core skills mentioned\n"
                "7. last_position: Most recent job title and company\n"
                "Format response as valid JSON only."
            ),
            "criteria_matcher": (
                "You are a Recruitment Assistant Expert. Analyze the ENTIRE {lang} resume "
                "and STRICTLY evaluate against this criterion: {criterion}. Follow these rules:\n"
                "1. Carefully scan ALL SECTIONS, including education, experience, skills, and projects.\n"
                "2. Only return a match if the EXACT phrase appears VERBATIM anywhere in the resume.\n"
                "3. Partial matches or close variations are NOT allowed.\n"
                "4. If you find an exact match, ONLY return '✅'\n"
                "5. If no match is found, ONLY return '❌'\n"
            ),
            "skill_matcher": (
                "You are a Recruitment Expert. Compare this {lang} resume to the job description. "
                "Calculate a numeric match score from 0-100 based on skills alignment only.\n"
                "Provide JSON with:\n"
                "1. match_score: numeric score (0-100)\n"
                "2. matching_skills: array of 3-5 key matching skills\n"
                "3. missing_skills: array of 3-5 important skills from job description missing in the resume\n"
                "Format response as valid JSON only."
            ),
            "recommendation": (
                "You are a Senior Recruitment Expert. Analyze this {lang} resume against the job description. "
                "Based on the resume content and the criteria evaluation results, provide your professional recommendation.\n"
                "Structure your response in JSON with:\n"
                "1. overall_rating: numeric score (1-10)\n"
                "2. strengths: Array of 2-3 key candidate strengths relevant to this role\n"
                "3. concerns: Array of 2-3 potential concerns or gaps\n"
                "4. interview_questions: Array of 2-3 specific questions you would ask this candidate\n"
                "5. recommendation: Short hiring recommendation (Highly Recommend, Recommend, Consider, or Not Recommended)\n"
                "Format response as valid JSON only."
            ),
            "chat": (
                "You are a helpful AI assistant for recruitment. Respond concisely and accurately."
            )
        }
        
        return templates.get(template_name, "")
    
    @classmethod
    def init_app(cls):
        """Initialize application configuration"""
        # Create output directory if it doesn't exist
        if not os.path.exists(cls.OUTPUT_DIR):
            os.makedirs(cls.OUTPUT_DIR)
        
        # Ensure export directory exists
        cls.ensure_export_dir()
        
        # Initialize any other app configuration here
        return cls

    @classmethod
    def ensure_export_dir(cls):
        """Ensure the export directory exists"""
        if not os.path.exists(cls.EXPORT_DIR):
            os.makedirs(cls.EXPORT_DIR)
            print(f"Export directory '{cls.EXPORT_DIR}' created.")
        return cls.EXPORT_DIR
