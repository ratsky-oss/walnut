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
import psycopg2
import mariadb
import netifaces as ni

from loguru import logger
from pkg.db_connection import get_db_info, db_write_backup_info, db_delete_backup_info, check_path_in_backupinfo
from sqlalchemy import create_engine
from pkg.sec import Cryptorator

@logger.catch          
def send_error_to_redis(conf, job_name,timestamp, error):
    try:
        redis_connect = redis.StrictRedis.from_url(conf.redis_url+"/1", decode_responses=True)
        error_info = {
            "job_name": job_name,
            "timestamp": timestamp,
            "error": error,
        }
        key = len(redis_connect.keys())+1
        redis_connect.hmset(key, error_info)
        redis_connect.expire(name = key, time=86400)
    except Exception as e:
        logger.error(f'[REDIS] {e}')

def send_info_to_redis(conf, key, job_name,status, timestamp, db_name, db_host, expired):
    redis_connect = redis.StrictRedis.from_url(conf.redis_url+"/0", decode_responses=True)
    try:
        worker_info = {
        "job_name": job_name, 
        "worker_status": status,
        "timestamp": timestamp,
        "db_name": db_name,
        "db_host": db_host
        }
        redis_connect.hmset(key,  worker_info)
        if expired == True:
            redis_connect.expire(name = key, time=86400)
    except Exception as e:
        logger.error(f'[REDIS] {e}')

@logger.catch
def del_info_into_redis(conf, key):
    redis_connect = redis.StrictRedis.from_url(conf.redis_url+"/0", decode_responses=True)
    try:
        redis_connect.delete(key)
    except Exception as e:
        logger.error(f'[REDIS] {e}')

@logger.catch 
def check_file_count(path, rotation):
    return False if len(list(Path(path).iterdir())) <= rotation else True

class SQL:
    '''
        2 main constructors:
            (SQL class, database name)
            or
            (database name(optional), database host, database posrt, database username, database userpasswd)
    '''
    

    def __init__(self, *args):
        if len(args) == 2:
            self.db_host = args[0].db_host 
            self.db_port = args[0].db_port
            self.db_username = args[0].db_username
            self.db_password = args[0].db_password
            self.db_name = args[1]
        elif len(args) == 4:
            self.db_host = args[0] 
            self.db_port = args[1]
            self.db_username = args[2]
            self.db_password = args[3]
        elif len(args) == 5:
            self.db_name = args[0]
            self.db_host = args[1] 
            self.db_port = args[2]
            self.db_username = args[3]
            self.db_password = args[4]
            
    @logger.catch
    def check_connection(self):
        c = Cryptorator() 
        self.db_password = c.decrypt(str(self.db_password))
        del c

    @logger.catch
    def _decrypt_passwd(self):
        try:
            c = Cryptorator() 
            passwd = c.decrypt(str(self.db_password))
            del c
            return passwd
        except:
            logger.warning("Password decryption failed, passing bare string")
            return self.db_password
        
class MSSQL(SQL):
    
    def check_dump_permissions(self):
        connection = pyodbc.connect('DRIVER={FreeTDS};'+f'SERVER={ self.db_host };PORT={ self.db_port }; UID={ self.db_username };PWD={ self._decrypt_passwd() };TrustServerCertificate=yes;')
        cursor = connection.cursor()

        query = """
        SET NOCOUNT ON

        DECLARE @DatabaseName NVARCHAR(128)
        DECLARE @User NVARCHAR(128)
        DECLARE @SQL NVARCHAR(MAX)
        DECLARE @UserDatabases TABLE (DatabaseName NVARCHAR(128))
        DECLARE @BackupableDatabases TABLE (DatabaseName NVARCHAR(128))

        -- Получить имя текущего пользователя
        SELECT @User = SUSER_NAME()

        -- Получить список баз данных пользователя
        INSERT INTO @UserDatabases (DatabaseName)
        SELECT name
        FROM sys.databases
        WHERE owner_sid = SUSER_SID(@User) OR name = 'master'

        -- Проверка наличия роли sysadmin
        IF IS_SRVROLEMEMBER('sysadmin', @User) = 1
        BEGIN
            INSERT INTO @UserDatabases (DatabaseName)
            SELECT name
            FROM sys.databases
        END

        -- Проверка разрешений BACKUP DATABASE, CONTROL и CONNECT
        DECLARE UserDatabasesCursor CURSOR FOR
        SELECT DatabaseName
        FROM @UserDatabases

        OPEN UserDatabasesCursor

        FETCH NEXT FROM UserDatabasesCursor
        INTO @DatabaseName

        WHILE @@FETCH_STATUS = 0
        BEGIN
            SET @SQL = 'USE ' + QUOTENAME(@DatabaseName) + ';
                        DECLARE @HasBackupPermission INT;
                        DECLARE @HasControlPermission INT;
                        DECLARE @HasConnectPermission INT;
                        SELECT @HasBackupPermission = COUNT(*)
                        FROM sys.fn_my_permissions(NULL, ''DATABASE'')
                        WHERE permission_name = ''BACKUP DATABASE'';
                        SELECT @HasControlPermission = COUNT(*)
                        FROM sys.fn_my_permissions(NULL, ''DATABASE'')
                        WHERE permission_name = ''CONTROL'';
                        SELECT @HasConnectPermission = COUNT(*)
                        FROM sys.fn_my_permissions(NULL, ''DATABASE'')
                        WHERE permission_name = ''CONNECT'';
                        IF (@HasBackupPermission = 1) OR (@HasControlPermission = 1) AND (@HasConnectPermission = 1)
                        BEGIN
                            SELECT ''' + @DatabaseName + ''' AS DatabaseName
                        END'

            INSERT INTO @BackupableDatabases (DatabaseName)
            EXEC sp_executesql @SQL

            FETCH NEXT FROM UserDatabasesCursor
            INTO @DatabaseName
        END

        CLOSE UserDatabasesCursor
        DEALLOCATE UserDatabasesCursor

        -- Вывести таблицу с базами данных, доступными для резервного копирования
        SELECT * FROM @BackupableDatabases
        """

        cursor.execute(query)
        
        databases = cursor.fetchall()
        accessible_databases = set([db[0] for db in databases])
        all_databases = set([db[0] for db in databases])

        if len(accessible_databases) == len(all_databases):
            accessible_databases = list(accessible_databases)
            accessible_databases.append("all")
            accessible_databases.sort()
            return accessible_databases
        elif len(accessible_databases) > 0:
            accessible_databases = list(accessible_databases)
            return accessible_databases
        else:
            return None
    
    @logger.catch
    def backup(self, engine, conf, worker_name, job_name):
        logger.info("Start backup MSSQL")
        full_path = f"{self.remote_path}/mssql_{self.db_name}_{datetime.datetime.now().strftime('%Y_%m_%d_%H:%M:%S')}.bak"
        db_write_backup_info(engine, worker_name.split("_")[-1], full_path)
        try:
            conn = pyodbc.connect('DRIVER={FreeTDS};'+f'SERVER={ self.db_host };PORT={ self.db_port };DATABASE={ self.db_name };UID={ self.db_username };PWD={ self._decrypt_passwd() };TrustServerCertificate=yes;')
            conn.autocommit = True
            cur = conn.cursor()
            backup = cur.execute(f"BACKUP DATABASE [{ self.db_name }] TO DISK = N'{full_path}' WITH BUFFERCOUNT = 2200,BLOCKSIZE = 32768,INIT,SKIP,NOREWIND,NOUNLOAD")
            logger.info(f"[{worker_name}] Successfully backuped {self.db_host} from {self.db_host}")
            send_info_to_redis(conf, worker_name, job_name, "success", str(datetime.datetime.now()), "all", self.db_host, False)
            sleep(5)
            del_info_into_redis(conf, worker_name)
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"[{worker_name}] {e}")
            db_delete_backup_info(engine, full_path)
            send_error_to_redis(conf, job_name, str(datetime.datetime.now()), f"[{worker_name}] {e}")
            send_info_to_redis(conf, worker_name, job_name, "error", str(datetime.datetime.now()), "all", self.db_host, True)
        

    @logger.catch
    def check_connection(self):
        try:
            if self.db_name =="all":
                db_name = "master"
            else:
                db_name = self.db_name
            pyodbc.connect('DRIVER={FreeTDS};'+f'SERVER={ self.db_host };PORT={ self.db_port };DATABASE={ db_name };UID={ self.db_username };PWD={ self._decrypt_passwd() };TrustServerCertificate=yes;')
            #pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};'+f'SERVER={ self.db_host };PORT={ self.db_port };DATABASE={ self.db_name };UID={ self.db_username };PWD={ self.db_password };TrustServerCertificate=yes;')
            return True
        except Exception as e:
            logger.error(f"Can`t connect to MSSQL server: {e}")
            return False

class PGSQL(SQL):
    
    @logger.catch
    def backup(self, conf, engine, job_name,backup_dir, full_path, rotation, worker_name):
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
                send_error_to_redis(conf, job_name, str(datetime.datetime.now()), f"[{worker_name}] {err_message}")
                send_info_to_redis(conf, worker_name, job_name, "error", str(datetime.datetime.now()), "all", self.db_host, True)
            else:
                logger.info(f"[{worker_name}] Successfully backuped {self.db_host} from {self.db_host}")
                send_info_to_redis(conf, worker_name, job_name, "success", str(datetime.datetime.now()), "all", self.db_host, False)
                sleep(5)
                del_info_into_redis(conf, worker_name)
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
                send_error_to_redis(conf, job_name, str(datetime.datetime.now()), f"[{worker_name}] {err_message}")
                send_info_to_redis(conf, worker_name, job_name, "error", str(datetime.datetime.now()), self.db_host, self.db_host, True)
            else:
                logger.info(f"[{worker_name}] Successfully backuped {self.db_host} from {self.db_host}")
                send_info_to_redis(conf, worker_name, job_name, "success", str(datetime.datetime.now()), self.db_host, self.db_host, False)
                sleep(5)
                del_info_into_redis(conf, worker_name)
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
                file.write(f"{self.db_host}:{self.db_port}:*:{self.db_username}:{self._decrypt_passwd()}")
            os.chmod(f"/tmp/walnut/.{worker_name}", 0o600)
        except Exception as e:
            logger.error(f'[FILE SYSTEM] {e}')

    @logger.catch
    def check_connection(self):
        
        if self.db_name == "all":
            db_name = 'postgres'
        else: 
            db_name = self.db_name

        dst_url=f'postgresql+psycopg2://{urllib.parse.quote(self.db_username)}:' +\
            f'{urllib.parse.quote(self._decrypt_passwd())}@' +\
            f'{urllib.parse.quote(self.db_host)}:' +\
            f'{urllib.parse.quote(str(self.db_port))}/' +\
            f'{urllib.parse.quote(db_name)}'
        try:
            engine = create_engine(dst_url)
            engine.connect()
            return True
        except Exception:
            return False
           
    @logger.catch
    def check_dump_permissions(self):
        try:
            conn = psycopg2.connect(database='postgres', user=self.db_username, password=self._decrypt_passwd(), host=self.db_host, port=self.db_port)
        except psycopg2.OperationalError:
            logger.warning(f"Couldn't connect to psql://{self.db_username}:0_o@{self.db_host}:{self.db_port}/postgres")
            return None
        
        cur = conn.cursor()

        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
        databases = cur.fetchall()
        allowed_databases = []

        for db in databases:
            cur.execute("SELECT has_database_privilege(%s, %s, 'CONNECT')", (self.db_username, db[0]))
            has_connect_privilege = cur.fetchone()[0]

            if has_connect_privilege:
                allowed_databases.append(db[0])

        if len(allowed_databases) == len(databases):
            allowed_databases.append('all')
        
        logger.debug(f"psql://{self.db_username}:0_o@{self.db_host}:{self.db_port} can dump the following databases: {allowed_databases}")
        return sorted(allowed_databases)
     
class MYSQL(SQL):

    def check_dump_permissions(self):
        conn_params= {
            "user" : self.db_username,
            "password" : self._decrypt_passwd(),
            "host" : self.db_host,
            "port" : int(self.db_port)
        }
        cnx = mariadb.connect(**conn_params)
        cursor = cnx.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [row[0] for row in cursor.fetchall()]
        targets= []
        for database in databases:
            if self.has_database_privileges(database, cursor):
                targets.append(database)
        cursor.close()
        cnx.close()
        if len(targets) == len (databases):
            targets.append("all")
            targets.sort()
            return targets
        elif targets:
            return targets
        else:
            return None

    def has_database_privileges(self, database, cursor):
        cursor.execute("SHOW GRANTS FOR %s@%s", (self.db_username, '%'))
        grants1 = [grant[0] for grant in cursor.fetchall()]
        for grant in grants1:
            if grant.startswith(f"GRANT ALL PRIVILEGES ON *.*") or grant.startswith(f"GRANT ALL PRIVILEGES ON {database}.*") or grant.startswith(f"GRANT SELECT, LOCK TABLES, SHOW VIEW ON {database}.*"):
                return True
        for interface in ni.interfaces():
            addrs = ni.ifaddresses(interface).get(ni.AF_INET)
            if addrs:
                cursor.execute("SHOW GRANTS FOR %s@%s", (self.db_username, addrs[0]['addr']))
                grants2 = [grant[0] for grant in cursor.fetchall()]
                for grant in grants2:
                    if grant.startswith(f"GRANT ALL PRIVILEGES ON *.*") or grant.startswith(f"GRANT ALL PRIVILEGES ON {database}.*") or grant.startswith(f"GRANT SELECT, LOCK TABLES, SHOW VIEW ON {database}.*"):
                        return True
        return False 

    @logger.catch
    def backup(self, conf, engine, job_name, backup_dir, full_path, rotation, worker_name, backup_type):
        logger.info("Start backup MYSQL")
        db_write_backup_info(engine, worker_name.split("_")[-1], full_path)
        with gzip.open(full_path, 'wb') as f:
            popen = subprocess.Popen(
                                        [
                                            "mysqldump", 
                                            f"--host={self.db_host}",
                                            f"--port={self.db_port}",
                                            f"--user={self.db_username}",
                                            f"--password={self._decrypt_passwd()}",
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
            send_error_to_redis(conf, job_name, str(datetime.datetime.now()), f"[{worker_name}] {err_message}")
            send_info_to_redis(conf, worker_name, job_name, "error", str(datetime.datetime.now()), backup_type, self.db_host, True)
        else:
            logger.info(f"[{worker_name}] Successfully backuped {self.db_host} from {self.db_host}")
            send_info_to_redis(conf, worker_name, job_name, "success", str(datetime.datetime.now()), backup_type, self.db_host, False)
            while check_file_count(backup_dir, rotation): 
                files = list(Path(backup_dir).iterdir())
                files.sort()
                os.remove(files[0])
                db_delete_backup_info(engine, str(files[0]))
                logger.info(f"[{worker_name}] Old backup deleted")
            sleep(5)
            del_info_into_redis(conf, worker_name)
        popen.stdout.close()
        popen.stderr.close()

    @logger.catch
    def check_connection(self):

        if self.db_name == "all":
            db_name = 'mysql'
        else: 
            db_name = self.db_name

        dst_url=f'mysql+mariadbconnector://{urllib.parse.quote(self.db_username)}:' +\
            f'{urllib.parse.quote(self._decrypt_passwd())}@' +\
            f'{urllib.parse.quote(self.db_host)}:' +\
            f'{urllib.parse.quote(str(self.db_port))}/' +\
            f'{urllib.parse.quote(db_name)}'

        try:
            engine = create_engine(dst_url)
            engine.connect()
            return True
        except Exception as e:
            return False 


if __name__=="__main__":
    pass