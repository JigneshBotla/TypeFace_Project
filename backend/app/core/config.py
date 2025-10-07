# app/core/config.py
# Simple config loader that works with Pydantic v1 or v2 environments
import os
from dotenv import load_dotenv

load_dotenv()

class SimpleSettings:
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:password@127.0.0.1:3306/finances_dev")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

settings = SimpleSettings()
