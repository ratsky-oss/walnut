# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.
import os
import yaml
import urllib.parse

# btw created by Andrew Livitskiy :D
file = os.environ.get(f'WALNUT_CONF_PATH') or "/etc/walnut/config.yaml"

class Logging():

    def __init__(self, component):
        try:
            self.log_path = os.environ.get(f'APP_{component.upper()}_LOG_PATH') or \
                            self._Config__config['main'][component]['log']['path']
        except:    
            self.log_path = f'/var/walnut/{component}.log'
        
        try:
            self.log_rotation = os.environ.get(f'APP_{component.upper()}_LOG_ROTATION') or \
                            self._Config__config['main'][component]['log']['rotation']
        except:
            self.log_rotation = '50 MB'
        try:
            self.log_level = os.environ.get(f'APP_{component.upper()}_LOG_LEVEL') or \
                                self._Config__config['main'][component]['log']['level']
        except:
            self.log_level = 'INFO'

class Config():
    def __create_db_url(self):
        return f'postgresql://{urllib.parse.quote(self.__config["main"]["database"]["username"])}:' +\
                                f'{urllib.parse.quote(self.__config["main"]["database"]["password"])}@' +\
                                f'{urllib.parse.quote(self.__config["main"]["database"]["host"])}:' +\
                                f'{urllib.parse.quote(self.__config["main"]["database"]["port"])}/' +\
                                f'{urllib.parse.quote(self.__config["main"]["database"]["db_name"])}'
    
    def __create_rabbitmq_url(self):

        credentials = urllib.parse.quote(self.__config["main"]["rabbitMQ"]["username"]) + ":" +\
                        urllib.parse.quote(self.__config["main"]["rabbitMQ"]["password"]) + "@" \
                        if "username" in self.__config["main"]["rabbitMQ"].keys() else ""

        return f'amqp://{credentials}'+\
                                f'{urllib.parse.quote(self.__config["main"]["rabbitMQ"]["host"])}:' +\
                                f'{urllib.parse.quote(self.__config["main"]["rabbitMQ"]["port"]) if (self.__config["main"]["rabbitMQ"]["port"]) else "5672"}/'

    def __create_redis_url(self):
        
        credentials = urllib.parse.quote(self.__config["main"]["redis"]["username"]) + ":" +\
                urllib.parse.quote(self.__config["main"]["redis"]["password"]) + "@" \
                if "username" in self.__config["main"]["redis"].keys() else ""

        return f'redis://{credentials}' +\
                                f'{urllib.parse.quote(self.__config["main"]["redis"]["host"])}:' +\
                                f'{urllib.parse.quote(self.__config["main"]["redis"]["port"]) if (self.__config["main"]["redis"]["port"]) else "6379"}/'                                
    
    def __init__(self):
        with open(file) as f:
                self.__config = yaml.load(f, Loader=yaml.FullLoader)
        
        try:
            self.rabbitmq_url = os.environ.get('APP_RABBITMQ_URL') or self.__create_rabbitmq_url()
        except:
            self.rabbitmq_url = f'amqp://walnut:asjdhfjbvsu2737yf@localhost:5672/walnut'

        try:
            self.rabbitmq_host = os.environ.get('APP_RABBITMQ_HOST') or self.__config["main"]["rabbitMQ"]["host"]
        except:
            self.rabbitmq_host = "localhost"

        try:
            self.rabbitmq_port = os.environ.get('APP_RABBITMQ_PORT') or self.__config["main"]["rabbitMQ"]["port"]
        except:
            self.rabbitmq_port ="5672"

        try:
            self.rabbitmq_queue_name = os.environ.get('APP_RABBITMQ_QUEUE_NAME') or self.__config["main"]["rabbitMQ"]["queue_name"]
        except:
            self.rabbitmq_queue_name = "job_relay"

        try:
            self.db_url = os.environ.get('APP_DB_URL') or self.__create_db_url()
        except:
            self.db_url = f'postgresql://walnut:asjdhfjbvsu2737yf@localhost:5432/walnut'

        try:
            self.db_host = os.environ.get('APP_DB_HOST') or self.__config["main"]["database"]["host"]
        except:
            self.db_host = "localhost"

        try:
            self.db_port = os.environ.get('APP_DB_PORT') or self.__config["main"]["database"]["port"]
        except:
            self.db_port ="5432"

        try:
            self.redis_url = os.environ.get('APP_REDIS_URL') or self.__create_redis_url()
        except:
            self.redis_url = 'redis://walnut:asjdhfjbvsu2737yf@localhost:6379/'

        try:
            self.redis_host = os.environ.get('APP_REDIS_HOST') or self.__config["main"]["redis"]["host"]
        except:
            self.redis_host = 'localhost'

        try:
            self.redis_port = os.environ.get('APP_REDIS_PORT') or self.__config["main"]["redis"]["port"]
        except:
            self.redis_port = '6379'



class MasterConfig(Config, Logging):
    def __init__(self):
        Config.__init__(self)
        Logging.__init__(self, "master")
        try:
            self.max_worker = os.environ.get('APP_MASTER_MAX_WORKER') or self._Config__config['main']['master']['max_worker'] or '2'
        except:
            self.max_worker = '2'
        try: 
            self.worker_mode = os.environ.get('APP_MASTER_WORKER_MODE') or self._Config__config['main']['master']['worker_mode'] or 'internal'
        except:
            self.worker_mode = 'internal'

class WorkerConfig(Config, Logging):
    def __init__(self):
        Config.__init__(self)
        Logging.__init__(self, "worker")
        try:
            self.backup_base_path = os.environ.get('APP_WORKER_BACKUP_ВASE_PATH') or self._Config__config['main']['backup_base_path']
        except:
            self.backup_base_path = '/var/walnut-backup/'

class ObserverConfig(Config):
    def __init__(self):
        Config.__init__(self)
        Logging.__init__(self, "observer")
        try:
            self.max_apschedule_instances = os.environ.get('APP_OBSERVER_MAX_APSCHEDULE_INSTANCES') or \
            self._Config__config['main']['observer']['max_apschedule_instances']
        except:
            self.max_apschedule_instances = "30"

class DjangoConfig(Config):
    def __init__(self):
        Config.__init__(self)
        Logging.__init__(self, "django")
        try:
            self.base_url_path = os.environ.get('APP_DJANGO_ВASE_URL') or self._Config__config['main']['django']['base_url_path'] or ''
        except:
            self.base_url_path = ""
        
