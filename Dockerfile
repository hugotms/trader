FROM python:3.8

ENV TRADER_VERSION=v1.2.0

RUN mkdir -p /app && \
    mkdir -p /data && \
    groupadd trader && \
    useradd -m -g trader trader && \
    chown -R trader:trader /app && \
    chown -R trader:trader /data

VOLUME ["/data"]

WORKDIR /app

USER trader

RUN git clone --branch $TRADER_VERSION https://github.com/hugotms/trader.git ./ && \
    pip install -r requirements.txt

CMD ["/app/monitor.py"]
ENTRYPOINT ["python","-u"]
