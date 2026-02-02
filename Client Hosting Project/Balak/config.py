import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# Load config from JSON if exists
json_config = {}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r") as f:
            json_config = json.load(f)
    except Exception:
        pass

# Telegram API Credentials
API_ID = json_config.get("API_ID") or os.getenv("API_ID")
API_HASH = json_config.get("API_HASH") or os.getenv("API_HASH")
PHONE_NUMBER = json_config.get("PHONE_NUMBER") or os.getenv("PHONE_NUMBER")

# Configuration
TARGET_CHANNEL = -1003309759576

MONITORED_GROUPS = [
    "@COACH_BETA_1",
    "@COACH_BETA_3",
    "@COACH_BETA_4",
    "@COACH_BETA_5",
    "@COACH_BETA_6",
    "@COACH_BETA_7",
    "@COACH_BETA_8"
]

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(BASE_DIR, 'session')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
SESSION_FILE = os.path.join(SESSION_DIR, 'user')
LOG_FILE = os.path.join(LOG_DIR, 'activity.log')

# Keywords to detect
APPROVED_KEYWORDS = [
    "Approved",
    "Approved ✅",
    "Status – Approved",
    "Status - Approved"
]
