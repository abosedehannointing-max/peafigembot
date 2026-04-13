"""
Configuration file - Reads sensitive data from environment variables
DO NOT hardcode your API credentials here!
"""

import os
from pathlib import Path

# ====== TELEGRAM API CREDENTIALS ======
# These will be set as environment variables on Render
API_ID = int(os.environ.get('API_ID', '0'))
API_HASH = os.environ.get('API_HASH', '')
PHONE_NUMBER = os.environ.get('PHONE_NUMBER', '')

# ====== FILE PATHS ======
BASE_DIR = Path(__file__).parent
SESSION_PATH = BASE_DIR / "session_name"
MEMBERS_JSON = BASE_DIR / "members.json"
MEMBERS_CSV = BASE_DIR / "members.csv"
LOG_FILE = BASE_DIR / "adder.log"

# ====== SAFETY SETTINGS ======
# Delay between adding members (seconds)
MIN_DELAY = 45
MAX_DELAY = 90

# Maximum members to add per session (set to 0 for unlimited)
MAX_PER_SESSION = 50

# Stop after this many consecutive failures
MAX_CONSECUTIVE_FAILURES = 5

# ====== VALIDATION ======
def validate_config():
    """Ensure all required credentials are set"""
    errors = []
    if API_ID == 0:
        errors.append("API_ID is not set in environment variables")
    if not API_HASH:
        errors.append("API_HASH is not set in environment variables")
    if not PHONE_NUMBER:
        errors.append("PHONE_NUMBER is not set in environment variables")
    
    if errors:
        raise ValueError("\n".join(errors))
    
    print("✅ Configuration validated successfully")
