# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.
import os
import redis
import sys
import datetime
from pathlib import Path

from loguru import logger
from sqlalchemy import create_engine

from pkg.db_connection import get_db_info, check_path_in_backupinfo
from pkg.config import WorkerConfig
from pkg.sql_lib import MSSQL, PGSQL, MYSQL
from pkg.redis_lib import RedisHandler


worker_name = sys.argv[1]

@logger.catch
def create_file_mssql_backup(db_name, full_path, worker_name):
    with open(f"component-worker/{worker_name}.sql",'w') as file:
        file = open(os.path.dirname(os.path.realpath(__file__))+"/sql/dbbkp.sql","w")
        file.write(f"""use {db_name}\nBACKUP DATABASE {db_name} TO DISK '{full_path}'\nBACKUP LOG {db_name} WITH  truncate_only
        """)

@logger.catch 
def check_file_count(path, rotation):
    return False if len(list(Path(path).iterdir())) <= rotation else True


@logger.catch
def back_up(worker_name, engine):

    db_info = get_db_info(engine, worker_name.split("_")[-1])
    db_host = db_info["connection"]["host"]
    db_port = db_info["connection"]["port"]
    db_username = db_info["connection"]["username"]
    db_password = db_info["connection"]["password"]
    dms_type = db_info["dms"]["type"]
    db_name = db_info["connection"]["db_name"]
    name = db_info["job"]["name"]
    full_path = f'{conf.backup_base_path}/{name}/{dms_type}_{db_name}_{datetime.datetime.now().strftime("%Y_%m_%d_%H:%M:%S")}.gz'

    redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {
                                                                    "job_name": name, 
                                                                    "worker_status": "pending",
                                                                    "timestamp": str(datetime.datetime.now()),
                                                                    "db_name": db_name,
                                                                    "db_host": db_host
                                                                })
    
    if not check_path_in_backupinfo(engine, full_path):# and check_path_in_filesystem()
        if not(os.path.exists(f'{conf.backup_base_path}/{name}')):
            os.mkdir(f'{conf.backup_base_path}/{name}')
        logger.info(f'[{worker_name}] start backuping {db_name} from {db_host}')
        logger.debug(f'[{worker_name}] start backuping {dms_type}')
        redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {
                                                                    "job_name": name, 
                                                                    "worker_status": "started",
                                                                    "timestamp": str(datetime.datetime.now()),
                                                                    "db_name": db_name,
                                                                    "db_host": db_host
                                                                })
        if dms_type == "mysql":
            mysql = MYSQL(db_name, db_host, db_port, db_username, db_password)
            if db_name == "all":
                mysql.backup(conf, engine, name, f"{conf.backup_base_path}/{name}", full_path, db_info["job"]["rotation"], worker_name, "--all-databases")
            else:
                mysql.backup(conf, engine, name, f"{conf.backup_base_path}/{name}", full_path, db_info["job"]["rotation"], worker_name, db_name)
        if dms_type == "postgres":
            pgsql = PGSQL(db_name, db_host, db_port, db_username, db_password)
            pgsql.create_file_pgpass(worker_name)
            pgsql.backup(conf, engine, name, f"{conf.backup_base_path}/{name}", full_path, db_info["job"]["rotation"], worker_name)
        if dms_type == "mssql":
            remote_path = db_info["job"]["remote_path"]
            mssql = MSSQL(db_name = db_name, db_host = db_host, db_port = db_port, db_username = db_username, db_password = db_password, remote_path = remote_path)
            mssql.backup(engine, conf, worker_name, name)    
    else:
        redis_handler.del_info_into_redis(conf.redis_worker_database, worker_name)
        logger.error(f"[{worker_name}] Not started, backup exists")
    
if __name__ == "__main__":
    conf = WorkerConfig()
    redis_handler = RedisHandler(conf.redis_url)
    logger.add(conf.log_path, rotation=conf.log_rotation, level=conf.log_level)
    engine = create_engine(conf.db_url)
    back_up(worker_name, engine)

