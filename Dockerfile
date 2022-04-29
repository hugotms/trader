FROM python:3.8

ENV TRADER_VERSION=1.1.0

RUN mkdir -p /app && \
    mkdir -p /data && \
    groupadd trader && \
    useradd -g trader trader && \
    chown -R trader:trader /app && \
    chown -R trader:trader /data

USER trader

WORKDIR /app

RUN pip install requests && \
    git clone --branch master https://github.com/hugotms/trader.git /app

CMD ["/app/monitor.py"]
ENTRYPOINT ["python","-u"]
