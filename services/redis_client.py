# services/redis_client.py
import os
import redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# decode_responses=True makes it return str instead of bytes
get_redis = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)
