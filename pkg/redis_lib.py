import redis
from loguru import logger
from datetime import timedelta

class RedisHandler:
    def __init__(self, connection_string):
        self.redis_connection =redis.StrictRedis.from_url(connection_string, decode_responses=True)

    def del_info_into_redis(self, db_number, key):
        try:
            self.redis_connection.connection_pool.connection_kwargs['db'] = db_number
            self.redis_connection.delete(key)
        except Exception as e:
            logger.error(f'[REDIS] {e}')

    def send_info_to_redis(self, db_number, key, job_name, status, timestamp, db_name, db_host):
        worker_info = {
            "job_name": job_name,
            "worker_status": status,
            "timestamp": timestamp,
            "db_name": db_name,
            "db_host": db_host
        }
        try:
            self.redis_connection.connection_pool.connection_kwargs['db'] = db_number
            self.redis_connection.hmset(key, worker_info)
        except Exception as e:
            logger.error(f'[REDIS] {e}')

    def send_error_to_redis(self, db_number, job_name, timestamp, error):
        error_info = {
            "job_name": job_name,
            "timestamp": timestamp,
            "error": error,
        }
        try:
            self.redis_connection.connection_pool.connection_kwargs['db'] = db_number
            key = len(self.redis_connection.keys()) + 1
            self.redis_connection.hmset(key, error_info)
            self.redis_connection.expire(key, timedelta(days=1))
        except Exception as e:
            logger.error(f'[REDIS] {e}')