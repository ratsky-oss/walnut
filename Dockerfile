FROM python

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . . 

CMD ["python", "master.py"]
