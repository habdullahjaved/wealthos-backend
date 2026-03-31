import os
from dotenv import load_dotenv

load_dotenv()

REQUIRED = ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "GROQ_API_KEY"]

missing = [k for k in REQUIRED if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Missing env vars: {', '.join(missing)}")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")