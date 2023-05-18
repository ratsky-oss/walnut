import pytest
import datetime
import gzip
import os
import subprocess
import psycopg2
import mariadb

from pathlib import Path
from unittest.mock import MagicMock, patch, ANY, call
from pkg.sql_lib import SQL, MSSQL, PGSQL, MYSQL
from pkg.config import Config
from pkg.redis_lib import RedisHandler
from sqlalchemy import create_engine



@pytest.fixture
def sql():
    return SQL(db_host="localhost", db_port=1433, db_username="username", db_password="password", db_name="test_db")


# MSSQL========================
@pytest.fixture
def mssql(sql):
    return MSSQL(sql, "test_db")

def test_decrypt_passwd(sql):
    with patch("pkg.sql_lib.Cryptorator") as mock_cryptorator:
        instance = mock_cryptorator.return_value
        instance.decrypt.return_value = "decrypted_password"
        decrypted_password = sql._decrypt_passwd()
        assert decrypted_password == "decrypted_password"

def test_check_dump_permissions(mssql):
    with patch("pkg.sql_lib.pyodbc") as mock_pyodbc:
        cursor = MagicMock()
        cursor.fetchall.return_value = [("test_db",)]
        mock_pyodbc.connect.return_value.cursor.return_value = cursor

        accessible_databases = mssql.check_dump_permissions()
        assert accessible_databases == ["all","test_db"]

def test_backup_mssql(mssql):
    engine = MagicMock()
    conf = Config()
    worker_name = "worker_1"
    job_name = "test_job"

    mssql._decrypt_passwd = MagicMock(return_value="test_password")
    mssql.redis_handler = MagicMock()

    with patch("pkg.sql_lib.pyodbc") as mock_pyodbc, patch("pkg.sql_lib.db_write_backup_info") as mock_db_write, patch("pkg.sql_lib.db_delete_backup_info") as mock_db_delete, patch("pkg.sql_lib.logger") as mock_logger:
        conn = MagicMock()
        cur = MagicMock()
        mock_pyodbc.connect.return_value = conn
        conn.cursor.return_value = cur

        timestamp = datetime.datetime.now().strftime('%Y_%m_%d_%H:%M:%S')
        full_path = f"{mssql.remote_path}/mssql_{mssql.db_name}_{timestamp}.bak"

        mssql.backup(engine, conf, worker_name, job_name)

        mock_db_write.assert_called_once_with(engine, worker_name.split("_")[-1], full_path)
        cur.execute.assert_called_once_with(f"BACKUP DATABASE [{mssql.db_name}] TO DISK = N'{full_path}' WITH BUFFERCOUNT = 2200,BLOCKSIZE = 32768,INIT,SKIP,NOREWIND,NOUNLOAD")
        cur.close.assert_called_once()
        conn.close.assert_called_once()
        mock_db_delete.assert_not_called()
        mssql.redis_handler.del_info_into_redis.assert_called_once_with(conf.redis_worker_database, worker_name)

def test_check_connection(mssql):
    with patch("pkg.sql_lib.pyodbc") as mock_pyodbc:
        mssql.check_connection()
        mock_pyodbc.connect.assert_called_once()

# PGSQL========================
@pytest.fixture
def pgsql():
    return PGSQL(db_host="localhost", db_port=5432, db_username="username", db_password="password", db_name="test_db")

def test_create_file_pgpass(pgsql):
    pgsql._decrypt_passwd = MagicMock(return_value="decrypted_password")
    worker_name = "worker_1"
    pgpass_path = f"/opt/venvs/walnut/.{worker_name}"

    if os.path.exists(pgpass_path):
        os.remove(pgpass_path)

    pgsql.create_file_pgpass(worker_name)

    assert os.path.exists(pgpass_path)
    with open(pgpass_path, 'r') as file:
        content = file.read()
    assert content == f"{pgsql.db_host}:{pgsql.db_port}:*:{pgsql.db_username}:decrypted_password"
    os.remove(pgpass_path)

@patch("psycopg2.connect")
def test_check_connection_all_db(mock_psycopg2_connect, pgsql):
    pgsql._decrypt_passwd = MagicMock(return_value="decrypted_password")
    pgsql.db_name = "all"
    pgsql.check_connection()
    mock_psycopg2_connect.assert_called_once_with(database='postgres', user=pgsql.db_username, password="decrypted_password", host=pgsql.db_host, port=pgsql.db_port)

@patch("psycopg2.connect")
def test_check_connection_single_db(mock_psycopg2_connect, pgsql):
    pgsql._decrypt_passwd = MagicMock(return_value="decrypted_password")
    pgsql.check_connection()
    mock_psycopg2_connect.assert_called_once_with(database=pgsql.db_name, user=pgsql.db_username, password="decrypted_password", host=pgsql.db_host, port=pgsql.db_port)

@patch("psycopg2.connect")
def test_check_dump_permissions(mock_psycopg2_connect, pgsql):
    pgsql._decrypt_passwd = MagicMock(return_value="decrypted_password")
    conn = MagicMock()
    cur = MagicMock()
    mock_psycopg2_connect.return_value = conn
    conn.cursor.return_value = cur
    databases = [("db1",), ("db2",)]
    cur.fetchall.return_value = databases

    cur.fetchone.side_effect = [(True,), (True,)]
    allowed_databases = pgsql.check_dump_permissions()
    assert allowed_databases == ["all", "db1", "db2"]

    cur.fetchone.side_effect = [(True,), (False,)]
    allowed_databases = pgsql.check_dump_permissions()
    assert allowed_databases == ["db1"]


# MYSQL========================
# @patch("your_module.mariadb.connect")  # Замените на имя вашего модуля
# def test_check_dump_permissions(mock_connect):
#     # Здесь мы мокааем функцию mariadb.connect для тестирования check_dump_permissions
#     mysql = MYSQL(Config())

#     # Настройка моков для проверки привилегий
#     mock_cursor = MagicMock()
#     mock_cursor.fetchall.return_value = [("db1",), ("db2",)]
#     mock_cursor.execute.side_effect = [None, None, None, None]
#     mock_cnx = MagicMock()
#     mock_cnx.cursor.return_value = mock_cursor
#     mock_connect.return_value = mock_cnx

#     targets = mysql.check_dump_permissions()
#     assert targets == ["db1", "db2", "all"]

# @patch("your_module.mariadb.connect")  # Замените на имя вашего модуля
# def test_has_database_privileges(mock_connect):
#     # Здесь мы мокааем функцию mariadb.connect для тестирования has_database_privileges
#     mysql = MYSQL(Config())

#     # Настройка моков для проверки привилегий
#     mock_cursor = MagicMock()
#     mock_cursor.fetchall.return_value = [("GRANT ALL PRIVILEGES ON *.*",)]
#     mock_cnx = MagicMock()
#     mock_cnx.cursor.return_value = mock_cursor
#     mock_connect.return_value = mock_cnx

#     result = mysql.has_database_privileges("db1", mock_cursor)
#     assert result

# @patch("your_module.gzip.open")  # Замените на имя вашего модуля
# @patch("your_module.subprocess.Popen")  # Замените на имя вашего модуля
# @patch("your_module.os.remove")  # Замените на имя вашего модуля
# @patch("your_module.ni.interfaces")  # Замените на имя вашего модуля
# def test_backup(mock_interfaces, mock_os_remove, mock_popen, mock_gzip_open):
#     # Здесь мы мокааем функцию gzip.open и subprocess.Popen для тестирования backup
#     mysql = MYSQL(Config())

#     # Настройка моков для тестирования backup
#     gzip_file = MagicMock()
#     gzip_file.__enter__.return_value = gzip_file
#     mock_gzip_open.return_value = gzip_file
#     mock_interfaces.return_value = ["eth0"]

#     # Настройка моков для subprocess.Popen
#     popen_instance = MagicMock()
#     popen_instance.returncode = 0
#     popen_instance.stdout.readline.side_effect = iter(["line1", "line2", StopIteration()])
#     popen_instance.stderr.read.return_value = ""
#     mock_popen.return_value = popen_instance

#     # Запуск функции backup
#     mysql.backup(Config(), MagicMock(), "test_job", "/opt/venvs/walnut/backup", "/opt/venvs/walnut/backup/backup.gz", 3, "worker_1", "all")

#     # Проверка вызовов функций
#     mock_popen.assert_called()
#     mock_gzip_open.assert_called_once_with("/tmp/walnut")