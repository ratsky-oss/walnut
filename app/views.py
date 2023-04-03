# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.
from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.generic import TemplateView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import IntegrityError
from django.utils import timezone
from django.urls import reverse

import sqlalchemy
import psutil
import humanize
import pika
import redis
import copy

import logging
import json
import os
import re

from .functions import get_queue_len
from pkg.config import Config, MasterConfig, WorkerConfig, ObserverConfig, DjangoConfig
from pkg.db_connection import check_dst_db
from pkg.sql_lib import MSSQL, PGSQL, MYSQL
from pkg.sec import Cryptorator
from app.models import DestinationDatabase, DMSInfo, Job, BackupInfo
from pkg.status_lib import check_connection_telnet, process_running,  worker_status, worker_error
from pkg.redis_lib import RedisHandler


logger = logging.getLogger(__name__)
#logger.debug('Log whatever you want')

def send_massage(message):
    connection = pika.BlockingConnection(pika.URLParameters(Config().rabbitmq_url))
    channel = connection.channel()
    channel.queue_declare(queue='job_relay')
    channel.basic_publish(exchange='', routing_key='job_relay', body=json.dumps(message))
    connection.close()

def validate_cron(cron_string):
    regex = '^(\*(/[0-9]+)?|[0-9,-]+)(\s+(\*(/[0-9]+)?|[0-9,-]+)){4}$'
    if re.match(regex, cron_string):
        return True
    else:
        return False


class BaseContextMixin:

    def get_context_data(self, **kwargs):
        django_conf = DjangoConfig()
        context = super().get_context_data(**kwargs)
        context['base_url_path'] = f"/{django_conf.base_url_path}"
        return context

class Main_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'index.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated == True:
            pass
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            return handler(request, *args, **kwargs)
        else:
            return redirect(reverse('app:login_page'))

    def get_context_data(self, **kwargs):
        conf = Config()
        django_conf = DjangoConfig()
        conf_master = MasterConfig()
        worker_config = WorkerConfig()
        conf_observer = ObserverConfig()
        context = super().get_context_data(**kwargs)
        jobs = Job.objects.all()

        redis_connect = redis.StrictRedis.from_url(conf.redis_url, decode_responses=True, db=0)
        redis_connect_error = redis.StrictRedis.from_url(conf.redis_url + "/1", decode_responses=True)
        try:
            worker_status_bufer =  worker_status(redis_connect)
            worker_error_bufer = worker_error(redis_connect_error)
            context["worker_status"] =  copy.deepcopy(worker_status_bufer)
            for key,value in worker_status_bufer.items():
                if value["worker_status"] == "error":
                    context["worker_status"][key]["error_text"] = worker_error_bufer[value["job_name"]]["error_text"]
        except  Exception as e:
            context["worker_status"] = {}
            
        try:
            context['disk'] = [ humanize.intcomma(int(psutil.disk_usage(worker_config.backup_base_path).free/(1024*1024))), 
                            humanize.intcomma(int(psutil.disk_usage(worker_config.backup_base_path).total/(1024*1024))),
                            psutil.disk_usage(worker_config.backup_base_path).percent,
                            f"{(psutil.disk_io_counters(perdisk=False).write_bytes/1024/1024)/(psutil.disk_io_counters(perdisk=False).write_time*1000):.6f}"
                            ]
        except:
            context['disk'] = [ 0, 0, 0, 0 ]
        try:    
            context['cpu_usage'] = psutil.cpu_percent()
        except:
            context['cpu_usage'] = 0
        try:
            context['ram_usage'] = psutil.virtual_memory().percent
        except:
            context['ram_usage'] = 0
        try:
            worker_count = 0
            for key in redis_connect.keys():
                if redis_connect.hget(key, "worker_status") != "error":
                    worker_count += 1
            context['worker_count'] = worker_count
        except:
            context['worker_count'] = 0
        try:
            context['worker_difference'] = ((worker_count)/conf_master.max_worker) * 100 if worker_count != 0 else 0
        except:
            context['worker_difference'] = 0
        try:
            context['shedular_difference'] = (len(jobs)/conf_observer.max_apschedule_instances) * 100 if len(jobs) != 0 else 0
        except:
            context['shedular_difference'] = 0
        try:
            checker = 0           
            if check_connection_telnet(conf.rabbitmq_host, conf.rabbitmq_port) != True:
                checker += 1
            if check_connection_telnet(conf.redis_host, conf.redis_port) != True:
                checker += 1
            if check_connection_telnet(conf.db_host, conf.db_port) != True:
                checker += 1
            if not process_running("observer.py"):
                checker += 1
            if not process_running("master.py"):
                checker += 1
            redis_handler = RedisHandler(conf.redis_url)
            context['critical_error_count'] = redis_handler.get_redis_len(1) + checker
        except:
            context['critical_error_count'] = 666
        try:
            context['queue_len'] = get_queue_len(conf.rabbitmq_url, conf.rabbitmq_queue_name)
        except:
            context['queue_len'] = 0
            
            
            
            
            
            
            

        context['jobs'] = [[item, item.dst_db.dmsinfo_set.first()] for item in jobs]
        context['max_worker_count'] = conf_master.max_worker
        context['shedular_count'] = len(jobs)
        context['max_shedular_count'] = conf_observer.max_apschedule_instances

        return context

class Jobs_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'jobs.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated == True:
            pass
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            return handler(request, *args, **kwargs)
        else:
            return redirect(reverse('app:login_page'))

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        jobs = Job.objects.all()

        
        # context['jobs'] = [[item, item.dst_db.dmsinfo_set.first()] for item in jobs]
        context['dmses'] = DMSInfo.objects.all()
        return context

class DMS_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'dms.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated == True:
            pass
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            return handler(request, *args, **kwargs)
        else:
            return redirect(reverse('app:login_page'))

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        
        context['dms'] = DMSInfo.objects.all()
        
        return context

class Backup_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'backup.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated == True:
            pass
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            return handler(request, *args, **kwargs)
        else:
            return redirect(reverse('app:login_page'))

    def get_context_data(self, **kwargs):

        jobs = Job.objects.all()        

        context = super().get_context_data(**kwargs)
        
        context["jobs"] = jobs
        
        return context

class Backup_Search_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'backup.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated == True:
            pass
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            return handler(request, *args, **kwargs)
        else:
            return redirect(reverse('app:login_page'))



    def get_context_data(self, **kwargs):

        search = self.request.GET.get("search")
        utc = self.request.GET.get("utc")
        jobs = Job.objects.filter(
            Q(name__icontains=search)
        )        

        context = super().get_context_data(**kwargs)
        
        context["jobs"] = jobs
        context["utc"] = utc
        context["search"] = search
        return context

class Status_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'status.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated == True:
            pass
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            return handler(request, *args, **kwargs)
        else:
            return redirect(reverse('app:login_page'))

    def get_context_data(self, **kwargs):
        conf = Config()
        redis_connect = redis.StrictRedis.from_url(conf.redis_url, decode_responses=True)
        redis_connect_error = redis.StrictRedis.from_url(conf.redis_url + "/1", decode_responses=True)
        context = super().get_context_data(**kwargs)

        context["rabbit_telnet_status"] = check_connection_telnet(conf.rabbitmq_host, conf.rabbitmq_port)
        context["redis_telnet_status"] = check_connection_telnet(conf.redis_host, conf.redis_port)
        context["db_telnet_status"] = check_connection_telnet(conf.db_host, conf.db_port)
        context["observer_proc_status"] = process_running("observer.py")
        context["master_proc_status"] = process_running("master.py")
        try:
            worker_status_bufer =  worker_status(redis_connect)
            worker_error_bufer = worker_error(redis_connect_error)
            context["worker_status"] =  copy.deepcopy(worker_status_bufer)
            for key,value in worker_status_bufer.items():
                if value["worker_status"] == "error":
                    context["worker_status"][key]["error_text"] = worker_error_bufer[value["job_name"]]["error_text"]
        except  Exception as e:
            context["worker_status"] = {}

        return context

class Config_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'config.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated == True:
            pass
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            return handler(request, *args, **kwargs)
        else:
            return redirect(reverse('app:login_page'))

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        
        return context

class Users_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'users.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated == True:
            pass
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed
            return handler(request, *args, **kwargs)
        else:
            return redirect(reverse('app:login_page'))

    def get_context_data(self, **kwargs):

        users = User.objects.all()
        context = super().get_context_data(**kwargs)
        
        context["users"] = users
        
        return context

class Login_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'login.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        
        return context
    
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        user = authenticate(request, username=data["username"], password=data["password"])
        if user is not None: 
            if user.is_active:
                login(request, user)
                return JsonResponse({"status":"200"})
            else:
                return JsonResponse({"status":"500"}) 
        else:
            return JsonResponse({"status":"500"})

class Logout_Page_View(BaseContextMixin, TemplateView ):
    
    template_name = 'login.html'

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        return context
    
    def dispatch(self, request, *args, **kwargs):
        logout(request)
        return redirect(reverse('app:login_page'))

def get_form_add_dms(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            dst_db = DestinationDatabase(host=data['host'], port=data['port'], username=data['username'], password=data['password'])
            dms = DMSInfo(type=data['type'],version=data['version'],dst_db=dst_db)
            dst_db.save()
            dms.save()
        except IntegrityError as e:
            if "already exists" in e.args[0]:
                return JsonResponse({"status":"500","error": " DMS already exists"})
            else:
                return JsonResponse({"status":"500","error": f" {e.args[0]}"})
        return JsonResponse({"status":"200"})
    elif request.method == 'DELETE':
        data = json.loads(request.body)
        try:
            dms = DMSInfo.objects.filter(id=data["id"]).first()
            DestinationDatabase(id=dms.dst_db.id).delete()
            dms.delete()
        except Exception:
            return JsonResponse({"status":"500","error": " Can not del DMS"})
        return JsonResponse({"status":"200"})
    elif request.method == 'PUT':
        data = json.loads(request.body)
        try:
            c = Cryptorator()
            dms = DMSInfo.objects.filter(id=data["id"]).update(type=data['type'],version=data['version'])
            dms = DMSInfo.objects.filter(id=data["id"]).first()
            dst_db = DestinationDatabase.objects.filter(id=dms.dst_db.id).update(host=data['host'], port=data['port'], username=data['username'], password=c.encrypt(data['password']))
            dms.dst_db = DestinationDatabase.objects.filter(id=dms.dst_db.id).first()
            del c
        except Exception as e:
            return JsonResponse({"status":"500","error": "Can not update DMS"})
        return JsonResponse({"status":"200"})
    else:
        return JsonResponse({"status":"500","error": " Bad request"})

def get_form_add_job(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        add_job_bufer = []
        if validate_cron(data["frequency"]):
            for data_db_name in data["db_name"].replace(" ","").split(","):
                try:
                    dst_db = DestinationDatabase.objects.filter(id=data["dst_db"]).first()
                    dms_info = DMSInfo.objects.filter(dst_db=dst_db).first()
                    if dms_info.type == "mssql":
                        mssql = MSSQL(remote_path=data["remote_path"],db_name = data_db_name, db_host = dst_db.host, db_port = dst_db.port, db_username = dst_db.username, db_password = dst_db.password)
                        if not mssql.check_connection():
                            for job in add_job_bufer:
                                job.delete()
                            return JsonResponse({"status":"500", "error":f" Couldn't connect dst to db {data_db_name}"})
                    elif dms_info.type == "postgres":
                        pgsql = PGSQL(db_name = data_db_name, db_host = dst_db.host, db_port = dst_db.port, db_username = dst_db.username, db_password = dst_db.password)
                        data["remote_path"] = ""
                        if not pgsql.check_connection():
                            for job in add_job_bufer:
                                job.delete()
                            return JsonResponse({"status":"500", "error":f" Couldn't connect dst to db {data_db_name}"})
                    elif dms_info.type == "mysql":
                        mysql = MYSQL(db_name = data_db_name, db_host = dst_db.host, db_port = dst_db.port, db_username = dst_db.username, db_password = dst_db.password)
                        data["remote_path"] = ""
                        if not mysql.check_connection():
                            for job in add_job_bufer:
                                job.delete()
                            return JsonResponse({"status":"500", "error":f" Couldn't connect dst to db {data_db_name}"})
                    if len(data["frequency"].split(' ')) != 5:
                        return JsonResponse({"status":"500", "error": " Frequency error"})
                    if len(data["db_name"].replace(" ","").split(",")) == 1:
                        job = Job(name=f"{data['name']}", dst_db=dst_db, db_name=data_db_name, action= "b" if data["action"] == "backup" else "r", frequency=data["frequency"], rotation=data["rotation"],remote_path = data["remote_path"])
                    else:
                        job = Job(name=f"{data['name']}_{data_db_name}", dst_db=dst_db, db_name=data_db_name, action= "b" if data["action"] == "backup" else "r", frequency=data["frequency"], rotation=data["rotation"],remote_path = data["remote_path"])
                    job.save()
                    add_job_bufer.append(job)
                except Exception:
                    for job in add_job_bufer:
                        job.delete()
                    return JsonResponse({"status":"500", "error":" Critical server error"})   
            return JsonResponse({"status":"200"})
        else:
            return JsonResponse({"status":"500", "error":" Incorrect frequency format"})
    elif request.method == 'DELETE':
        data = json.loads(request.body)
        try:
            Job.objects.filter(id=data["id"]).first()
            job = Job.objects.filter(id=data["id"]).first()
            job.delete()
        except Exception:
            return JsonResponse({"status":"500", "error": " Can not del job"})
        return JsonResponse({"status":"200"})
    elif request.method == 'PUT':
        data = json.loads(request.body)
        print(data)
        if "," in data["db_name"]:
            return JsonResponse({"status":"500", "error":" You can`t add more than 1 database when editing!"})
        if validate_cron(data["frequency"]):
            try:
                dst_db = DestinationDatabase.objects.filter(id=data["dst_db"]).first()
                dms_info = DMSInfo.objects.filter(dst_db=dst_db).first()
                if dms_info.type == "mssql":
                    mssql = MSSQL(db_name = data["db_name"], db_host = dst_db.host, db_port = dst_db.port, db_username = dst_db.username, db_password = dst_db.password, remote_path=data["remote_path"])
                    if not mssql.check_connection():
                        return JsonResponse({"status":"500", "error":" Couldn't connect dst to db"})
                elif dms_info.type == "postgres":
                    pgsql = PGSQL(db_name = data["db_name"], db_host = dst_db.host, db_port = dst_db.port, db_username = dst_db.username, db_password = dst_db.password)
                    if not pgsql.check_connection():
                        return JsonResponse({"status":"500", "error":" Couldn't connect dst to db"})
                elif dms_info.type == "mysql":
                    mysql = MYSQL(db_name = data["db_name"], db_host = dst_db.host, db_port = dst_db.port, db_username = dst_db.username, db_password = dst_db.password)
                    if not mysql.check_connection():
                        return JsonResponse({"status":"500", "error":" Couldn't connect dst to db"})
                if len(data["frequency"].split(' ')) != 5:
                    return JsonResponse({"status":"500", "error": " Frequency error"})
                job = Job.objects.filter(id=data["id"]).update(name=data["name"], dst_db=dst_db, db_name=data["db_name"], action= "b" if data["action"] == "backup" else "r", frequency=data["frequency"], rotation=data["rotation"])
            except Exception as e:
                return JsonResponse({"status":"500", "error": " Critical server error"})
            return JsonResponse({"status":"200"})
        else:
            return JsonResponse({"status":"500", "error":" Incorrect frequency format"})
    else:
        return JsonResponse({"status":"500", "error": " Bad request"})

def get_form_add_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            if data['username'] and data['password'] and 'repeat_password' and data['repeat_password']:
                if User.objects.filter(username=data['username']).exists():
                    return JsonResponse({"status":"500", "error": "User exist"}) 
                else:
                    if data['password'] == data['repeat_password']:
                        user = User.objects.create_user(username=data['username'], password=data['password'], is_staff=True)
                        user.save()
                        return JsonResponse({"status":"200"})
                    else:
                        return JsonResponse({"status":"500", "error": "Passwords don't match"}) 
            else:
                return JsonResponse({"status":"Form error"}) 
        except Exception:
            return JsonResponse({"status":"500", "error": "Server error"})          
    elif request.method == 'DELETE':
        data = json.loads(request.body)
        if  data['id']:
            user = User.objects.filter(id = data['id']).first()
            user.delete()
            return JsonResponse({"status":"200"})
        else:
            return JsonResponse({"status":"500"})
    elif request.method == 'PUT':
        data = json.loads(request.body)
        if data['password'] and data['repeat_password']:
            user = User.objects.filter(id = data['id']).first()
            user.set_password(data['password'])
            user.save()
            return JsonResponse({"status":"200"})
        else:
            return JsonResponse({"status":"500", "error": "Passwords don't match"})
    else:
        return JsonResponse({"status":"500", "error": " Bad request"})

# CREATOR NIKITA SHVORA (FROOT) 

def get_form_add_backup(request):
    if request.method == 'POST':
        pass          
    elif request.method == 'DELETE':
        data = json.loads(request.body)
        try:
            if  data['id']:
                backup = BackupInfo.objects.filter(id = data['id']).first()
                try:
                    backup.delete()
                except Exception as e:
                    return JsonResponse({"status":"500", "error": "Can`t delete metadata"})           
                try:
                    os.remove(backup.fs_path)                              
                except Exception as e:
                    return JsonResponse({"status":"450", "error": " Backup not found in folder, metadata deleted"})
                return JsonResponse({"status":"200"})
            else:
                return JsonResponse({"status":"500", "error": " Backup not found"})
        except Exception:
            return JsonResponse({"status":"500", "error": " Critical server error"})
    elif request.method == 'PUT':
        pass
    else:
        return JsonResponse({"status":"500", "error": " Bad request"})

def get_status_job(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        job = Job.objects.filter(id=data["id"].split("-")[-1]).first()
        job.status = "e" if data["status"] else "d"
        job.save()
        return JsonResponse({"status":"200"})

def get_edit_object_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        if data["form-type"] == "dms":
            dms = DMSInfo.objects.filter(id=data["id"]).first()
            ddb = DestinationDatabase.objects.filter(id=dms.dst_db.id).first()
            job = Job.objects.filter(id=data["id"]).first()
            return JsonResponse({
                "type":dms.type,
                "version":dms.version,
                "host":ddb.host,
                "port":ddb.port,
                "username":ddb.username,
                "password":"HUYATINA BLYAT KUDA LEZHESH TVAR"
            })
        else:
            job = Job.objects.filter(id=data["id"]).first()  
            return JsonResponse({
                "dst_db": job.dst_db.dmsinfo_set.all().first().type,
                "name":job.name,
                "db_name":job.db_name,
                "rotation":job.rotation,
                "frequency":job.frequency,
                "remote_path": job.remote_path,
            })

def get_databases(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        return JsonResponse({"status": "200" ,"databases": ["master","tembdb",'test','test2']})

def start_job(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        send_massage({"job_id": data["id"],})
        return JsonResponse({"status":"200"})

def download_backup(request, id):
    backup = BackupInfo.objects.get(id=id)
    response = FileResponse(open(backup.fs_path, 'rb'))
    return response
