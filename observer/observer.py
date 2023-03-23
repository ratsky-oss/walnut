# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.
import json
from multiprocessing import parent_process
import pika
from loguru import logger

from time import sleep
from sqlalchemy import create_engine, select, MetaData, Table
from pkg.pgnotify import await_pg_notifications
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from pkg.config import ObserverConfig

# Hi boyz, LVTSKY was here


@logger.catch
def send_massage(message):
    connection = pika.BlockingConnection(pika.URLParameters(conf.rabbitmq_url))
    channel = connection.channel()
    channel.queue_declare(queue='job_relay')
    channel.basic_publish(exchange='', routing_key='job_relay', body=json.dumps(message))
    connection.close()

@logger.catch
def notify2rmq_translation(parsed):
    rmq_message = {
        "job_id": parsed['record']['id'],
    }
    return rmq_message

@logger.catch
def init_jobs():
    engine = create_engine(conf.db_url)
    metadata = MetaData(bind=None)
    table = Table(
        'app_job', 
        metadata, 
        autoload=True, 
        autoload_with=engine
    )
    stmt = select([table.columns.id, table.columns.frequency, table.columns.name]).where(table.columns.status == 'e')
    connection = engine.connect()
    results = connection.execute(stmt).fetchall()
    return results

@logger.catch
def init_scheduler():

    job_defaults = {
        'coalesce': False,
        'max_instances': conf.max_apschedule_instances
    }

    scheduler = BackgroundScheduler(job_defaults=job_defaults)

    jobs = init_jobs()
    for job in jobs:
        message = {
            "job_id": job[0],
        }
        scheduler.add_job(send_massage, args=[message],
                        trigger=CronTrigger.from_crontab(job[1]),
                        id=f'db_job_{str(job[2])}')

    scheduler.start()
    return scheduler

@logger.catch
def prog():
    scheduler = init_scheduler()
    logger.debug(scheduler.get_jobs())
    try:
        for notification in await_pg_notifications(conf.db_url, ['core_db_event']):

            parsed = json.loads(notification.payload)
            logger.debug(f'Incoming notification: \n {json.dumps(parsed, indent=4)}')
            
            if parsed['action'] == 'update':
                if parsed['record']['status'] == 'e' and parsed['old']['status'] == 'e':
                    scheduler.remove_job(f"db_job_{parsed['old']['name']}")
                    scheduler.add_job(
                        send_massage, args=[notify2rmq_translation(parsed)], 
                        trigger=CronTrigger.from_crontab(parsed['record']['frequency']),
                        id=f"db_job_{parsed['record']['name']}"
                    )
                if parsed['record']['status'] == 'e' and parsed['old']['status'] == 'd':
                    scheduler.add_job(
                        send_massage, args=[notify2rmq_translation(parsed)], 
                        trigger=CronTrigger.from_crontab(parsed['record']['frequency']),

                        id=f"db_job_{parsed['record']['name']}"
                    )
                if parsed['record']['status'] == 'd' and parsed['old']['status'] == 'e':
                    scheduler.remove_job(f"db_job_{parsed['old']['name']}")


            if parsed['action'] == 'delete':
                if parsed['record']['status'] == 'e':
                    scheduler.remove_job(f"db_job_{parsed['old']['name']}")


            if parsed['action'] == 'insert':
                if parsed['record']['status'] == 'e':
                    scheduler.add_job(
                        send_massage, args=[notify2rmq_translation(parsed)], 
                        trigger=CronTrigger.from_crontab(parsed['record']['frequency']),
                        id=f"db_job_{parsed['record']['name']}"
                    )

            logger.debug(scheduler.get_jobs())
    except Exception as e:
        scheduler.shutdown()
        raise e


if __name__ == "__main__":
    conf = ObserverConfig()
    logger.add(conf.log_path, rotation=conf.log_rotation, level=conf.log_level)
    while True:
        prog()
        logger.info("30 sec timeout")
        sleep(30)
        
    
