from functools import lru_cache
from supabase import create_client, Client
from app.core.config import SUPABASE_URL, SUPABASE_SERVICE_KEY

@lru_cache(maxsize=1)
def get_db() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)