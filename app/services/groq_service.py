from functools import lru_cache
from groq import Groq
from app.core.config import GROQ_API_KEY

@lru_cache(maxsize=1)
def get_groq() -> Groq:
    return Groq(api_key=GROQ_API_KEY)  