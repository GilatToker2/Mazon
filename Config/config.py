"""
Configuration file for Azure OpenAI API credentials and settings.
Fill in your Azure OpenAI credentials before running the translation scripts.
"""

import os

# Azure OpenAI API Configuration
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY', '8bzusfmUItCctFE8B1GyYVakq31Yzpw6cwuqVLWCpi3g35k653ZuJQQJ99BFACHYHv6XJ3w3AAABACOGN8mS')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT', 'https://aoai-moodle-vi-eastus2.openai.azure.com/')
AZURE_OPENAI_API_VERSION = os.getenv('AZURE_OPENAI_API_VERSION', '2023-05-15')
AZURE_OPENAI_CHAT_COMPLETION_MODEL = os.getenv('AZURE_OPENAI_CHAT_COMPLETION_MODEL', 'gpt-4.1')

# Other Configuration (if needed)
INDEX_NAME = os.getenv('INDEX_NAME', 'default-index')
QUIZ_QUESTIONS_COUNT = int(os.getenv('QUIZ_QUESTIONS_COUNT', '10'))