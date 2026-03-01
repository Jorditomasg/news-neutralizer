import math
import redis
from app.config import settings

# Thread-safe connection pool for sync usage
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

def get_expected_duration(provider_name: str) -> int:
    """
    Get the expected duration in milliseconds for a specific model provider using EMA.
    Rounds up to the nearest 15 seconds (15000 ms) as specified by the user.
    """
    key = f"nn:ema:duration:{provider_name}"
    val = redis_client.get(key)
    
    if val is None:
        # Default starting values per provider if no history exists
        defaults = {
            "openai": 30000,
            "anthropic": 30000,
            "google": 30000,
            "ollama": 255000  # Ollama is typically much slower
        }
        avg_ms = defaults.get(provider_name.lower(), 30000)
    else:
        avg_ms = float(val)

    # Convert to seconds to do the round-up math
    avg_sec = avg_ms / 1000.0
    
    # "intenta que los tiempos se redonden en 15 segundos para arriba, por ejemplo tarda 62seg de media redundea a 75seg"
    rounded_sec = math.ceil(avg_sec / 15.0) * 15
    rounded_sec = max(15, rounded_sec)
    
    return int(rounded_sec * 1000)

def set_expected_duration(provider_name: str, new_duration_ms: int):
    """
    Update the Exponential Moving Average for a specific provider.
    Weight is 70% historical, 30% new execution to quickly adapt but not jump wildly.
    """
    if new_duration_ms < 1000 or new_duration_ms > 600000:
        return # Ignore impossible values (< 1s or > 10 min)
        
    key = f"nn:ema:duration:{provider_name}"
    val = redis_client.get(key)
    
    if val is None:
        # First execution initializes the EMA
        new_val = float(new_duration_ms)
    else:
        old_ema = float(val)
        new_val = (old_ema * 0.7) + (new_duration_ms * 0.3)
        
    redis_client.set(key, new_val)
