''' Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
 This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
 All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
 Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
 For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.'''
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
