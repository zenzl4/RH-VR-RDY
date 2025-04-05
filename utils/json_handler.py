import json
from utils.logging_setup import get_logger

logger = get_logger(__name__)

class JSONHandler:
    """Handles saving and loading JSON data."""

    @staticmethod
    def save_to_json(data, file_path):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logger.info(f"Data successfully saved to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save data to {file_path}: {e}")
            raise

    @staticmethod
    def load_from_json(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load data from {file_path}: {e}")
            raise
