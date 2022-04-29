FROM python:3.8

ENV TRADER_VERSION=v1.1.0

RUN mkdir -p /app && \
    mkdir -p /data && \
    groupadd trader && \
    useradd -g trader trader && \
    chown -R trader:trader /app && \
    chown -R trader:trader /data

USER trader

WORKDIR /app

RUN git clone --branch $TRADER_VERSION https://github.com/hugotms/trader.git ./ && \
    pip install -r requirements.txt

CMD ["/app/monitor.py"]
ENTRYPOINT ["python","-u"]
