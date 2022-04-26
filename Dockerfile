FROM python:3.8

ENV TZ=Europe/Paris

RUN mkdir /app && \
    mkdir /data && \
    pip install requests && \
    git clone --branch master https://github.com/hugotms/trader.git /app

WORKDIR /app

ENTRYPOINT python monitor.py
