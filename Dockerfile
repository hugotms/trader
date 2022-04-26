FROM python:3.8

ENV TZ=Europe/Paris

RUN apt -y update && \
    apt -y install git && \
    mkdir /app && \
    mkdir /data && \
    pip install requests

WORKDIR /app

RUN git clone --branch master https://github.com/hugotms/trader.git ./

ENTRYPOINT python monitor.py
