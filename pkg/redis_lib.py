import redis
from loguru import logger
from datetime import timedelta

class RedisHandler:
    def __init__(self, connection_string):
        self.connection_string = connection_string
    
    def get_connection(self, db_number):
        return redis.StrictRedis.from_url(self.connection_string, decode_responses=True, db=db_number)

    def del_info_into_redis(self, db_number, key):
        try:
            connection = self.get_connection(db_number)
            connection.delete(key)
        except Exception as e:
            logger.error(f'[REDIS] {e}')

    def send_info_to_redis(self, db_number, key, message, expired=False):
        try:
            сonnection = self.get_connection(db_number)
            сonnection.hmset(key, message)
            if expired == True:
                сonnection.expire(name = key, time=86400)
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
            сonnection = self.get_connection(db_number)
            key = len(сonnection.keys()) + 1
            сonnection.hmset(key, error_info)
            сonnection.expire(key, timedelta(days=1))
            logger.debug(f"Send error to redis db:{db_number} key:{key} message:{error_info}")
        except Exception as e:
            logger.error(f'[REDIS] {e}')

    def del_all_keys_into_redis(self, db_number):
        try:
            сonnection = self.get_connection(db_number)
            for key in сonnection.keys("*"):
                self.del_info_into_redis(db_number, key)
            logger.info(f"[REDIS] Clear redis db {db_number}")
        except Exception as e:
            logger.error(f'[REDIS] {e}')
    
    def get_values_from_redis(self, db_number, keys_list, field):
        result = {}
        try:
            сonnection = self.get_connection(db_number)
            for key in keys_list:
                value = сonnection.hget(key, field)
                if value is not None:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f'[REDIS] {e}')
            return None
    
    def get_redis_len(self, db_number, key_pattern="arkadiy_*"):
        try:
            сonnection = self.get_connection(db_number)
            return len(сonnection.keys(key_pattern))
        except Exception as e:
            logger.error(f'[REDIS] {e}')
            return None
