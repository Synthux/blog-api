from pathlib import Path
from decouple import Config, RepositoryEnv

# 1. Get the path to the 'settings' folder
SETTINGS_DIR = Path(__file__).resolve().parent
ENV_PATH = SETTINGS_DIR / '.env'

# 2. Check if the file actually exists
if not ENV_PATH.exists():
    raise FileNotFoundError(
        f"The .env file was not found at {ENV_PATH}. "
        "Please create it and add your BLOG_SECRET_KEY."
    )

# 3. Initialize config to read specifically from settings/.env
config = Config(RepositoryEnv(ENV_PATH))

# --- Read variables ---

# Environment
ENV_ID = config('BLOG_ENV_ID', default='local')
SECRET_KEY = config('BLOG_SECRET_KEY')
DEBUG = config('BLOG_DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('BLOG_ALLOWED_HOSTS', default='localhost').split(',')

# Database
DB_NAME = config('BLOG_DB_NAME', default='blog_db')
DB_USER = config('BLOG_DB_USER', default='postgres')
DB_PASSWORD = config('BLOG_DB_PASSWORD', default='postgres')
DB_HOST = config('BLOG_DB_HOST', default='localhost')
DB_PORT = config('BLOG_DB_PORT', default='5432')

# Redis
REDIS_URL = config('BLOG_REDIS_URL', default='redis://localhost:6379/0')
