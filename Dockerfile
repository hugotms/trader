FROM alpine:3.14

ENV TRADER_VERSION=v2.0.0
ENV PYTHON_VERSION=3.8

RUN apk add --update --no-cache git mongodb python3=~${PYTHON_VERSION} && \
    python3 -m ensurepip && \
    pip3 install --no-cache --upgrade pip setuptools && \
    mkdir -p /app && \
    mkdir -p /data/db && \
    rc-update add mongodb default && \
    adduser -s /bin/bash trader && \
    chown -R trader:trader /app

VOLUME ["/data/db"]

WORKDIR /app

USER trader

RUN git clone --branch ${TRADER_VERSION} https://github.com/hugotms/trader.git ./ && \
    pip3 install -r requirements.txt

CMD ["/app/monitor.py"]
ENTRYPOINT ["python3","-u"]
