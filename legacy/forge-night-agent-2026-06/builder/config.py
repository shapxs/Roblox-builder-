import sys, os

# Get the directory where this config file is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Database and paths - use workspace-relative paths
DB_PATH       = os.path.join(SCRIPT_DIR, "data", "builder.duckdb")
SOULS_PATH    = os.path.join(SCRIPT_DIR, "souls")
SKILLS_PATH   = os.path.join(SCRIPT_DIR, "skills")
PROJECTS_PATH = os.path.join(SCRIPT_DIR, "projects", "roblox")

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MAX_MODEL_RAM_GB = int(os.getenv("MAX_MODEL_RAM_GB", 200))

# Telegram configuration (optional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Night agent schedule
SESSION_START_HOUR = 20  # 8 PM ET
SESSION_END_HOUR = 2   # 2 AM ET
TOP_GAMES_TO_BUILD = 2
