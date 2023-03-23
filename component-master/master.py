# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.

import pika
import redis
import json
import os
import  subprocess
import datetime

from distutils.command.build import build
from time import sleep
from loguru import logger

from pkg.config import MasterConfig 



@logger.catch
def del_info_into_redis(redis_connect, key):
    try:
        redis_connect.delete(key)
    except Exception as e:
        logger.error(f'[REDIS] {e}')

def del_all_keys_into_redis(db_number):
    try:
        redis_connect = redis.StrictRedis.from_url(f"{conf.redis_url}/{db_number}", decode_responses=True)
        for key in redis_connect.keys("*"):
            del_info_into_redis(redis_connect, key)
        logger.info(f"[REDIS] Clear redis db {db_number}")
    except Exception as e:
        logger.error(f'[REDIS] {e}')

@logger.catch          
def send_error_to_redis(worker_name , timestamp, error):
    try:
        redis_connect = redis.StrictRedis.from_url(conf.redis_url+"/1", decode_responses=True)
        error_info = {
            "timestamp": timestamp,
            "error": error,
        }
        redis_connect.hmset(worker_name, error_info)
        redis_connect.expire(name = worker_name, time=86400)
    except Exception as e:
        logger.error(f'[REDIS] {e}')

@logger.catch
def send_info_to_redis(message, worker_name):
    try:
        redis_connect = redis.StrictRedis.from_url(
                                        conf.redis_url, 
                                        decode_responses=True
                                    )
        redis_connect.hmset(worker_name,  message)
    except Exception as e:
        logger.error(f'[REDIS] {e}')
    

@logger.catch
def check_avalibl_space(back_up_size, backup_path):
    try:
        info = os.statvfs(backup_path)
        avalibal_space = info.f_bsize * info.f_bavail / 1024 / 1024 # Получаем данные по свободному месту на диске - передаем точку монтирования
        if back_up_size < avalibal_space:
            return True
        else:
            logger.error(f"Not enough space  (backup - {back_up_size}mb, avaliable - {avalibal_space}mb)")
            return False
    except Exception as e:
        logger.error(f'[FILE SYSTEM] {e}')
    

@logger.catch
def check_worker_count(max_worker):
    try:
        redis_connect = redis.StrictRedis.from_url(conf.redis_url, decode_responses=True)
        worker_count = 0
        for key in redis_connect.keys():
            if redis_connect.hget(key, "worker_status") != "error":
                worker_count += 1
        if worker_count + 1 <= max_worker:
            logger.debug(f"New job catched, status: {worker_count}/{max_worker} workers running")
            return True
        else:
            logger.error(f"No worker avaliable, {worker_count}/{max_worker} workers running")
            return False 
    except Exception as e:
        logger.error(f'[REDIS] {e}')

@logger.catch
def callback(ch, method, properties, body):
    redis_connect = redis.StrictRedis.from_url(conf.redis_url, decode_responses=True)
    worker_count = len(redis_connect.keys())
    rabbitmq_message = json.loads(body)
    send_info_to_redis(rabbitmq_message, f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}")
    if check_worker_count(conf.max_worker):
        logger.info("Starting new worker")
        try:
            popen = subprocess.Popen(['opt/venvs/walnut/bin/python', 'opt/venvs/walnut/bin/worker.py', f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except Exception as e:
            logger.error(f"[arkadiy_{worker_count}_{rabbitmq_message['job_id']}] {e}")
            send_error_to_redis(f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}" ,str(datetime.datetime.now()), f"[arkadiy_{worker_count}_{rabbitmq_message['job_id']}] {e}")
    else:
        while not(check_worker_count(conf.max_worker)):
            sleep(5)
        try:
            popen = subprocess.Popen(['opt/venvs/walnut/bin/python', 'opt/venvs/walnut/bin/worker.py', f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except Exception as e:
            logger.error(f"[arkadiy_{worker_count}_{rabbitmq_message['job_id']}] {e}")
            send_error_to_redis(f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}" ,str(datetime.datetime.now()), f"[arkadiy_{worker_count}_{rabbitmq_message['job_id']}] {e}")  
    ch.basic_ack(delivery_tag=method.delivery_tag)

@logger.catch               
def get_message():
    connection = pika.BlockingConnection(pika.URLParameters(conf.rabbitmq_url))
    channel = connection.channel()
    channel.queue_declare(queue=conf.rabbitmq_queue_name)
    channel.basic_consume(conf.rabbitmq_queue_name, callback, auto_ack=False)
    channel.start_consuming()

if __name__ == "__main__":
    conf = MasterConfig()
    logger.add(conf.log_path, rotation=conf.log_rotation, level=conf.log_level)
    del_all_keys_into_redis(0)
    get_message()
