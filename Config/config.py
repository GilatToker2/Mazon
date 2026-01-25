"""
Configuration file for Azure OpenAI API credentials and settings.
Fill in your Azure OpenAI credentials before running the translation scripts.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Azure OpenAI API Configuration
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION')
AZURE_OPENAI_CHAT_COMPLETION_MODEL = os.getenv('AZURE_OPENAI_CHAT_COMPLETION_MODEL')

# Other Configuration (if needed)
INDEX_NAME = os.getenv('INDEX_NAME')
QUIZ_QUESTIONS_COUNT = int(os.getenv('QUIZ_QUESTIONS_COUNT', '10'))