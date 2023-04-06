# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.

from loguru import logger
import psycopg2
from pkg.sec import Cryptorator

class DatabaseChecker:
    
    def __init__(self, db_host, db_port, db_username, db_password):
        self.db_host = db_host 
        self.db_port = db_port
        self.db_username = db_username
        self.db_password = db_password
    
    def check_connection(self):
        pass

    def check_dump_permissions(self):
        pass

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

class MSChecker(DatabaseChecker):
    
    def __init__(self, remote_path, db_name, db_host, db_port, db_username, db_password):
        super().__init__(db_name, db_host, db_port, db_username, db_password)
        self.remote_path = remote_path
    

class PGChecker(DatabaseChecker):
    
    def __init__(self, db_host, db_port, db_username, db_password):
        super().__init__(db_host, db_port, db_username, db_password)
       
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

class MYChecker(DatabaseChecker):
    
    def __init__(self, db_host, db_port, db_username, db_password):
        super().__init__(db_host, db_port, db_username, db_password)

if __name__=="__main__":
    # a = PGChecker("192.168.8.24","5432","aaa","qwe")
    a = PGChecker("192.168.8.24","5432","boardsuser","gAAAAABkLKICS1-srYtXVbKgYA9T5Lm7AaB2wlGvTOwnvxJi0dAsmN1RifcsFRFLESV_mzVHKhQpqWgbOpUeGdmE7-jlITPpr1ytKyfEUmKSE-DDiNH4KbM=")
    a = PGChecker("192.168.8.24","5432","boardsuser","boardsuser-password")
    l=a.check_dump_permissions()
    print(l)
    from pkg.sql_lib import PGSQL
    b=PGSQL(a,"all")
    print(b.check_connection())