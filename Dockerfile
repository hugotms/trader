FROM python:3.8

ENV TRADER_VERSION=v2.0.0

RUN mkdir -p /app && \
    groupadd trader && \
    useradd -m -g trader trader && \
    chown -R trader:trader /app

WORKDIR /app

USER trader

RUN git clone --branch $TRADER_VERSION https://github.com/hugotms/trader.git ./ && \
    pip install -r requirements.txt

CMD ["/app/monitor.py"]
ENTRYPOINT ["python","-u"]
