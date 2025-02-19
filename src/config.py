import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
TIMEZONE = 'Asia/Bangkok'
DEFAULT_REMINDER_TIME = "10:00"
# Add default topic ID (0 means main group chat)
DEFAULT_TOPIC_ID = int(os.getenv('DEFAULT_TOPIC_ID', '39824')) 