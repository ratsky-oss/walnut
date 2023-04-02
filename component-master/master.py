import pika
import redis
import os
import json
import  subprocess
import datetime

from distutils.command.build import build
from time import sleep
from loguru import logger

from pkg.config import MasterConfig 
from pkg.redis_lib import RedisHandler
    

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
    worker_count = len(redis_handler.keys())
    rabbitmq_message = json.loads(body)
    redis_handler.send_info_to_redis(0,f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}", rabbitmq_message)
    if check_worker_count(conf.max_worker):
        logger.info("Starting new worker")
        try:
            popen = subprocess.Popen(['opt/venvs/walnut/bin/python', 'opt/venvs/walnut/bin/worker.py', f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except Exception as e:
            logger.error(f"[arkadiy_{worker_count}_{rabbitmq_message['job_id']}] {e}")
            redis_handler.send_error_to_redis(1,f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}" ,str(datetime.datetime.now()), f"[arkadiy_{worker_count}_{rabbitmq_message['job_id']}] {e}")
    else:
        while not(check_worker_count(conf.max_worker)):
            sleep(5)
        try:
            popen = subprocess.Popen(['opt/venvs/walnut/bin/python', 'opt/venvs/walnut/bin/worker.py', f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        except Exception as e:
            logger.error(f"[arkadiy_{worker_count}_{rabbitmq_message['job_id']}] {e}")
            redis_handler.send_error_to_redis(1,f"arkadiy_{worker_count}_{rabbitmq_message['job_id']}" ,str(datetime.datetime.now()), f"[arkadiy_{worker_count}_{rabbitmq_message['job_id']}] {e}")  
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
    redis_handler = RedisHandler(conf.redis_url)
    logger.add(conf.log_path, rotation=conf.log_rotation, level=conf.log_level)
    redis_handler.del_all_keys_into_redis(0)
    get_message()