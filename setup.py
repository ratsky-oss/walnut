import os
from setuptools import setup, find_packages

def get_req():
    with open('requirements.txt') as f:
        req = f.read().splitlines()
    return req

setup(
    name = "walnut",
    version = "0.0.1",
    author = "lvtsky&nsh",
    description = ("Ratsky Walnut Backup"),
    install_requires = get_req(),
    packages=["app","app/migrations","backsite","component-master","component-worker","observer","pkg"],
    scripts=['manage.py','observer/observer.py','component-master/master.py','component-worker/worker.py','pkg/sec.py'],
    include_package_data=True,
)

    
