FROM python:3.10-slim

COPY requirements.txt /requirements.txt
RUN pip3 install --upgrade pip -r requirements.txt
COPY app /app
WORKDIR /

CMD ["gunicorn"  , "-b", "0.0.0.0:8000", "app:app"]
