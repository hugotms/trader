FROM python:3.8

ENV TRADER_VERSION=1.0.8

RUN mkdir /app && \
    mkdir /data && \
    pip install requests && \
    git clone --branch master https://github.com/hugotms/trader.git /app

WORKDIR /app

CMD ["/app/monitor.py"]
ENTRYPOINT ["python","-u"]
