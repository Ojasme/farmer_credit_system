import os
import redis

REDIS_URL = os.environ.get("REDIS_URL")
if REDIS_URL:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
else:
    redis_host = os.environ.get("REDIS_HOST", "localhost")
    redis_port = int(os.environ.get("REDIS_PORT", 6379))
    redis_db = int(os.environ.get("REDIS_DB", 0))
    redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
