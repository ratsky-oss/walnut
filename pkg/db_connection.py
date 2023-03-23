# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.
import json
from datetime import datetime
import urllib.parse

from loguru import logger
from sqlalchemy import create_engine, select, MetaData, Table, insert, delete

from pkg.sec import Cryptorator
# Livi(Rat)sky was the one who created this crap

@logger.catch
def create_table(name,engine):
    return Table(name, 
                 MetaData(bind=None), 
                 autoload=True, 
                 autoload_with=engine)

@logger.catch
def get_db_info(engine, id):
    connection = engine.connect()

    job_table = create_table('app_job', engine)
    dst_db_table = create_table('app_destinationdatabase', engine)
    dms_info_table = create_table('app_dmsinfo', engine)

    job_req = select([job_table.columns.name,
                      job_table.columns.db_name,
                      job_table.columns.dst_db_id,
                      job_table.columns.action,
                      job_table.columns.frequency,
                      job_table.columns.rotation,
                      job_table.columns.remote_path,]).where(job_table.columns.id == id)

    job_info = connection.execute(job_req).fetchall()
                    
    dst_db_req = select([dst_db_table.columns.username,
                      dst_db_table.columns.password,
                      dst_db_table.columns.host,
                      dst_db_table.columns.port]).where(dst_db_table.columns.id == job_info[0][2])

    dms_info_req = select([dms_info_table.columns.type,
                    dms_info_table.columns.version]).where(dms_info_table.columns.dst_db_id == job_info[0][2])
    
    
    dst_db_info = connection.execute(dst_db_req).fetchall()
    dms_info_info = connection.execute(dms_info_req).fetchall()
    db_name = job_info[0][1] if job_info[0][1] != None else 'all'
    result = {
        "job":          {"name": job_info[0][0],
                        "action": job_info[0][3],
                        "frequency": job_info[0][4],
                        "rotation": job_info[0][5],
                        "remote_path": job_info[0][6]},
        "dms":          {"type": dms_info_info[0][0],
                        "version": dms_info_info[0][1],},
        "connection":   {"username": dst_db_info[0][0],
                        "password": '|0___o|',
                        "host": dst_db_info[0][2],
                        "port": dst_db_info[0][3],
                        "db_name": db_name,},
        
        
    }
    logger.debug(f'\n Job stats:  {json.dumps(result, indent=4)}')

    try:
        c = Cryptorator() 
        result["connection"]["password"] = c.decrypt(str(dst_db_info[0][1]))
        del c
    except:
        result["connection"]["password"] = dst_db_info[0][1]



    return result

@logger.catch
def db_write_backup_info(engine, job_id, fs_path):
    backupinfo_table = create_table('app_backupinfo', engine)
    stmt = (
        insert(backupinfo_table).
        values(fs_path=fs_path, job_id=job_id, timestamp=datetime.utcnow())
    )
    connection = engine.connect()
    connection.execute(stmt).fetchall()


def check_dst_db(type,host,port,username,password,db_name):
    if db_name == "all":
        db_name = type
    if type == "postgres":
        type = "postgresql+psycopg2"
    if type == "mysql":
        type = "mysql+mariadbconnector"

    dst_url=f'{type}://{urllib.parse.quote(username)}:' +\
            f'{urllib.parse.quote(password)}@' +\
            f'{urllib.parse.quote(host)}:' +\
            f'{urllib.parse.quote(str(port))}/' +\
            f'{urllib.parse.quote(db_name)}'

    try:
        engine = create_engine(dst_url)
        engine.connect()
        return True
    except Exception:
        return False

@logger.catch
def db_delete_backup_info(engine, fs_path):
    backupinfo_table = create_table('app_backupinfo', engine)
    stmt = (
        delete(backupinfo_table).
        where(backupinfo_table.c.fs_path == fs_path)
    )
    connection = engine.connect()
    connection.execute(stmt)
    logger.debug(f'Backup metadata deleted for {fs_path}')
    
def check_path_in_backupinfo(engine, fs_path):
    connection = engine.connect()
    backupinfo_table = create_table('app_backupinfo', engine)
    backupinfo_req = select([backupinfo_table.columns.id]).where(backupinfo_table.columns.fs_path == fs_path)
    backupinfo_info = connection.execute(backupinfo_req).fetchall()
    if backupinfo_info:
        return True
    return False

if __name__=='__main__':
    from pkg.config import Config
    # print(check_backupinfo_exist(create_engine(Config().db_url),'/home/nshvora/prod-db/mysql_all_2022_12_01_18:29:45.gz'))

