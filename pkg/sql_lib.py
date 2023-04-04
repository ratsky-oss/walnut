# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.

import datetime
import pyodbc
import subprocess
import gzip
import redis
import os
import urllib
from pathlib import Path
from time import sleep

from loguru import logger
from pkg.db_connection import get_db_info, db_write_backup_info, db_delete_backup_info, check_path_in_backupinfo
from sqlalchemy import create_engine
from pkg.sec import Cryptorator
from pkg.redis_lib import RedisHandler
from pkg.config import WorkerConfig


@logger.catch 
def check_file_count(path, rotation):
    return False if len(list(Path(path).iterdir())) <= rotation else True

class SQL:
    
    def __init__(self, db_name, db_host, db_port, db_username, db_password):
        self.db_name = db_name
        self.db_host = db_host 
        self.db_port = db_port
        self.db_username = db_username
        self.db_password = db_password

    @logger.catch
    def check_connection(self):
        c = Cryptorator() 
        self.db_password = c.decrypt(str(self.db_password))
        del c

class MSSQL(SQL):
    
    def __init__(self, remote_path, db_name, db_host, db_port, db_username, db_password):
        super().__init__(db_name, db_host, db_port, db_username, db_password)
        self.remote_path = remote_path
    
    @logger.catch
    def backup(self, engine, conf, worker_name, job_name):
        conf = WorkerConfig()
        redis_handler = RedisHandler(conf.redis_url)
        logger.info("Start backup MSSQL")
        full_path = f"{self.remote_path}/mssql_{self.db_name}_{datetime.datetime.now().strftime('%Y_%m_%d_%H:%M:%S')}.bak"
        db_write_backup_info(engine, worker_name.split("_")[-1], full_path)
        try:
            conn = pyodbc.connect('DRIVER={FreeTDS};'+f'SERVER={ self.db_host };PORT={ self.db_port };DATABASE={ self.db_name };UID={ self.db_username };PWD={ self.db_password };TrustServerCertificate=yes;')
            conn.autocommit = True
            cur = conn.cursor()
            backup = cur.execute(f"BACKUP DATABASE [{ self.db_name }] TO DISK = N'{full_path}' WITH BUFFERCOUNT = 2200,BLOCKSIZE = 32768,INIT,SKIP,NOREWIND,NOUNLOAD")
            logger.info(f"[{worker_name}] Successfully backuped {self.db_host} from {self.db_host}")
            redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {"job_name": job_name, "worker_status": "success","timestamp": str(datetime.datetime.now()),"db_name": "all","db_host": self.db_host})
            sleep(5)
            redis_handler.del_info_into_redis(conf.redis_worker_database, worker_name)
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"[{worker_name}] {e}")
            db_delete_backup_info(engine, full_path)
            redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {"job_name": job_name, "worker_status": "error","timestamp": str(datetime.datetime.now()),"db_name": self.db_name,"db_host": self.db_host})
            redis_handler.send_error_to_redis(conf.redis_error_database, job_name, str(datetime.datetime.now()), e)
        

    @logger.catch
    def check_connection(self):
        super().check_connection()
        try:
            pyodbc.connect('DRIVER={FreeTDS};'+f'SERVER={ self.db_host };PORT={ self.db_port };DATABASE={ self.db_name };UID={ self.db_username };PWD={ self.db_password };TrustServerCertificate=yes;')
            #pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};'+f'SERVER={ self.db_host };PORT={ self.db_port };DATABASE={ self.db_name };UID={ self.db_username };PWD={ self.db_password };TrustServerCertificate=yes;')
            return True
        except Exception as e:
            logger.error(f"Can`t connect to MSSQL server: {e}")
            return False

class PGSQL(SQL):
    
    def __init__(self, db_name, db_host, db_port, db_username, db_password):
        super().__init__(db_name, db_host, db_port, db_username, db_password)
    
    @logger.catch
    def backup(self, conf, engine, job_name,backup_dir, full_path, rotation, worker_name):
        conf = WorkerConfig()
        redis_handler = RedisHandler(conf.redis_url)
        logger.info("Start backup PGSQL")
        db_write_backup_info(engine, worker_name.split("_")[-1], full_path)
        if self.db_name == "all":
            with gzip.open(full_path, 'wb') as f:
                popen = subprocess.Popen(
                                            [
                                                "pg_dumpall", 
                                                f"--dbname=postgresql://{self.db_username}@{self.db_host}:{self.db_port}?passfile=/tmp/walnut/.{worker_name}",
                                            ], 
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, 
                                            universal_newlines=True
                                        )
                for stdout_line in iter(popen.stdout.readline, ""):
                    f.write(stdout_line.encode('utf-8'))
                popen.wait()
            if popen.returncode != 0:
                err_message = popen.stderr.read()
                logger.error(f"[{worker_name}]  {err_message}")
                os.remove(full_path)
                db_delete_backup_info(engine, full_path)
                redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {"job_name": job_name, "worker_status": "error","timestamp": str(datetime.datetime.now()),"db_name": self.db_name,"db_host": self.db_host})
                redis_handler.send_error_to_redis(conf.redis_error_database, job_name, str(datetime.datetime.now()), f"[{worker_name}] {err_message}")
            else:
                logger.info(f"[{worker_name}] Successfully backuped {self.db_host} from {self.db_host}")
                redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {"job_name": job_name, "worker_status": "success","timestamp": str(datetime.datetime.now()),"db_name": "all","db_host": self.db_host})
                sleep(5)
                redis_handler.del_info_into_redis(conf.redis_worker_database, worker_name)
                while check_file_count(backup_dir, rotation): 
                    files = list(Path(backup_dir).iterdir())
                    files.sort()
                    os.remove(files[0])
                    db_delete_backup_info(engine, str(files[0]))
                    logger.info(f"[{worker_name}] Old backup deleted")
            os.remove(f"/tmp/walnut/.{worker_name}")
            popen.stdout.close()
            popen.stderr.close()
        else:
            db_write_backup_info(engine, worker_name.split("_")[-1], full_path)
            with gzip.open(full_path, 'wb') as f:
                popen = subprocess.Popen(
                                            [
                                                "pg_dump", 
                                                f"--dbname=postgresql://{self.db_username}@{self.db_host}:{self.db_port}/{self.db_name}?passfile=/tmp/walnut/.{worker_name}",
                                            ], 
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, 
                                            universal_newlines=True
                                        )
                for stdout_line in iter(popen.stdout.readline, ""):
                    f.write(stdout_line.encode('utf-8'))
                popen.wait()
            if popen.returncode != 0:
                err_message = popen.stderr.read()
                logger.error(f"[{worker_name}]  {err_message}")
                os.remove(full_path)
                db_delete_backup_info(engine, full_path)
                redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {"job_name": job_name, "worker_status": "error","timestamp": str(datetime.datetime.now()),"db_name": self.db_name,"db_host": self.db_host})
                redis_handler.send_error_to_redis(conf.redis_error_database, job_name, str(datetime.datetime.now()), f"[{worker_name}] {err_message}")
            else:
                logger.info(f"[{worker_name}] Successfully backuped {self.db_host} from {self.db_host}")
                redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {"job_name": job_name, "worker_status": "success","timestamp": str(datetime.datetime.now()),"db_name": self.db_name,"db_host": self.db_host})
                sleep(5)
                redis_handler.del_info_into_redis(conf.redis_worker_database, worker_name)
                while check_file_count(backup_dir, rotation): 
                    files = list(Path(backup_dir).iterdir())
                    files.sort()
                    os.remove(files[0])
                    db_delete_backup_info(engine, str(files[0]))
                    logger.info(f"[{worker_name}] Old backup deleted")
            os.remove(f"/tmp/walnut/.{worker_name}")
            popen.stdout.close()
            popen.stderr.close()

    @logger.catch
    def create_file_pgpass(self, worker_name):
        try:
            with open(f"/tmp/walnut/.{worker_name}",'w') as file:
                file.write(f"{self.db_host}:{self.db_port}:*:{self.db_username}:{self.db_password}")
            os.chmod(f"/tmp/walnut/.{worker_name}", 0o600)
        except Exception as e:
            logger.error(f'[FILE SYSTEM] {e}')

    @logger.catch
    def check_connection(self):
        super().check_connection()

        if self.db_name == "all":
            db_name = 'postgres'
        else: 
            db_name = self.db_name

        dst_url=f'postgresql+psycopg2://{urllib.parse.quote(self.db_username)}:' +\
            f'{urllib.parse.quote(self.db_password)}@' +\
            f'{urllib.parse.quote(self.db_host)}:' +\
            f'{urllib.parse.quote(str(self.db_port))}/' +\
            f'{urllib.parse.quote(db_name)}'
        try:
            engine = create_engine(dst_url)
            engine.connect()
            return True
        except Exception:
            return False    

class MYSQL(SQL):
    
    def __init__(self, db_name, db_host, db_port, db_username, db_password):
        super().__init__(db_name, db_host, db_port, db_username, db_password)
    
    @logger.catch
    def backup(self, conf, engine, job_name, backup_dir, full_path, rotation, worker_name, backup_type):
        conf = WorkerConfig()
        redis_handler = RedisHandler(conf.redis_url)
        logger.info("Start backup MYSQL")
        db_write_backup_info(engine, worker_name.split("_")[-1], full_path)
        with gzip.open(full_path, 'wb') as f:
            popen = subprocess.Popen(
                                        [
                                            "mysqldump", 
                                            f"--host={self.db_host}",
                                            f"--port={self.db_port}",
                                            f"--user={self.db_username}",
                                            f"--password={self.db_password}",
                                            backup_type,
                                        ], 
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        universal_newlines=True
                                    )
            for stdout_line in iter(popen.stdout.readline, ""):
                f.write(stdout_line.encode('utf-8'))
            popen.wait()
        if popen.returncode != 0:
            err_message = popen.stderr.read()
            logger.error(f"[{worker_name}]  {err_message}")
            os.remove(full_path)
            db_delete_backup_info(engine, full_path)
            redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {"job_name": job_name, "worker_status": "error","timestamp": str(datetime.datetime.now()),"db_name": self.db_name,"db_host": self.db_host})
            redis_handler.send_error_to_redis(conf.redis_error_database, job_name, str(datetime.datetime.now()), f"[{worker_name}] {err_message}")
        else:
            logger.info(f"[{worker_name}] Successfully backuped {self.db_host} from {self.db_host}")
            redis_handler.send_info_to_redis(conf.redis_worker_database, worker_name, {"job_name": job_name, "worker_status": "success","timestamp": str(datetime.datetime.now()),"db_name": backup_type,"db_host": self.db_host})
            while check_file_count(backup_dir, rotation): 
                files = list(Path(backup_dir).iterdir())
                files.sort()
                os.remove(files[0])
                db_delete_backup_info(engine, str(files[0]))
                logger.info(f"[{worker_name}] Old backup deleted")
            sleep(5)
            redis_handler.del_info_into_redis(conf.redis_worker_database, worker_name)
        popen.stdout.close()
        popen.stderr.close()

    @logger.catch
    def check_connection(self):
        super().check_connection()

        if self.db_name == "all":
            db_name = 'mysql'
        else: 
            db_name = self.db_name

        dst_url=f'mysql+mariadbconnector://{urllib.parse.quote(self.db_username)}:' +\
            f'{urllib.parse.quote(self.db_password)}@' +\
            f'{urllib.parse.quote(self.db_host)}:' +\
            f'{urllib.parse.quote(str(self.db_port))}/' +\
            f'{urllib.parse.quote(db_name)}'

        try:
            engine = create_engine(dst_url)
            engine.connect()
            return True
        except Exception as e:
            return False 
