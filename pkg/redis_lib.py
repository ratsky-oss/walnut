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

    def send_info_to_redis(self, db_number, key, message):
        try:
            self.redis_connection.connection_pool.connection_kwargs['db'] = db_number
            self.redis_connection.hmset(key, message)
            logger.debug(f"Send info to redis db:{db_number} key:{key} message:{message}")
        except Exception as e:
            logger.error(f'[REDIS] {e}')

    def send_error_to_redis(self, db_number, job_name, timestamp, error):
        error_info = {
            "job_name": job_name,
            "timestamp": timestamp,
            "error": str(error),
        }
        try:
            self.redis_connection.connection_pool.connection_kwargs['db'] = db_number
            key = len(self.redis_connection.keys()) + 1
            self.redis_connection.hmset(key, error_info)
            self.redis_connection.expire(key, timedelta(days=1))
        except Exception as e:
            logger.error(f'[REDIS] {e}')

    def del_all_keys_into_redis(self, db_number):
        try:
            self.redis_connection.connection_pool.connection_kwargs['db'] = db_number
            for key in self.redis_connection.keys("*"):
                self.del_info_into_redis(db_number, key)
            logger.info(f"[REDIS] Clear redis db {db_number}")
        except Exception as e:
            logger.error(f'[REDIS] {e}')
    
    def get_values_from_redis(self, db_number, keys_list, field):
        result = {}
        try:
            self.redis_connection.connection_pool.connection_kwargs['db'] = db_number
            for key in keys_list:
                value = self.redis_connection.hget(key, field)
                if value is not None:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f'[REDIS] {e}')
            return None
    
    def get_redis_len(self, db_number, key_pattern="arkadiy_*"):
        try:
            self.redis_connection.connection_pool.connection_kwargs['db'] = db_number
            return len(self.redis_connection.keys(key_pattern))
        except Exception as e:
            logger.error(f'[REDIS] {e}')
            return None
