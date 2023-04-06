import redis
from loguru import logger
from datetime import timedelta

class RedisHandler:
    def __init__(self, connection_string):
        self.connections =redis.StrictRedis.from_url(connection_string, decode_responses=True)

    def get_connection(self, db_number):
        if db_number not in self.connections:
            self.connections[db_number] = redis.StrictRedis.from_url(self.redis_url, decode_responses=True, db=db_number)
        return self.connections[db_number]

    def del_info_into_redis(self, db_number, key):
        try:
            connection = self.get_connection(db_number)
            connection.delete(key)
        except Exception as e:
            logger.error(f'[REDIS] {e}')

    def send_info_to_redis(self, db_number, key, message):
        try:
            connection = self.get_connection(db_number)
            connection.hmset(key, message)
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
            connection = self.get_connection(db_number)
            key = len(connection.keys()) + 1
            connection.hmset(key, error_info)
            connection.expire(key, timedelta(days=1))
        except Exception as e:
            logger.error(f'[REDIS] {e}')

    def del_all_keys_into_redis(self, db_number):
        try:
            connection = self.get_connection(db_number)
            for key in connection.keys("*"):
                self.del_info_into_redis(db_number, key)
            logger.info(f"[REDIS] Clear redis db {db_number}")
        except Exception as e:
            logger.error(f'[REDIS] {e}')
    
    def get_values_from_redis(self, db_number, keys_list, field):
        result = {}
        try:
            connection = self.get_connection(db_number)
            for key in keys_list:
                value = connection.hget(key, field)
                if value is not None:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f'[REDIS] {e}')
            return None
    
    def get_redis_len(self, db_number, key_pattern="arkadiy_*"):
        try:
            connection = self.get_connection(db_number)
            return len(connection.keys(key_pattern))
        except Exception as e:
            logger.error(f'[REDIS] {e}')
            return None

    