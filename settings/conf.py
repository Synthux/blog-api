from pathlib import Path
from decouple import Config, RepositoryEnv, config as env_config

# 1. Get the path to the 'settings' folder
SETTINGS_DIR = Path(__file__).resolve().parent
ENV_PATH = SETTINGS_DIR / '.env'

# 2. Check if the file actually exists
if not ENV_PATH.exists():
    raise FileNotFoundError(
        f"The .env file was not found at {ENV_PATH}. "
        "Please create it and add your BLOG_SECRET_KEY."
    )

# 3. Use .env file if it exists (local dev), otherwise read from environment (Docker/CI)
if ENV_PATH.exists():
    config = Config(RepositoryEnv(ENV_PATH))
else:
    config = env_config

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

# Celery
CELERY_BROKER_URL = config('BLOG_CELERY_BROKER_URL', default='redis://localhost:6379/1')

# Flower
FLOWER_USER = config('BLOG_FLOWER_USER', default='admin')
FLOWER_PASSWORD = config('BLOG_FLOWER_PASSWORD', default='changeme')
