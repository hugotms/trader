FROM alpine/git:latest as clone

ENV TRADER_VERSION=v2.0.0

WORKDIR /trader

RUN git clone --branch $TRADER_VERSION https://github.com/hugotms/trader.git ./

FROM python:3.8-slim as run

RUN mkdir -p /app && \
    groupadd trader && \
    useradd -m -g trader trader && \
    chown -R trader:trader /app

WORKDIR /app

USER trader

COPY --from=clone /tarder .

RUN pip install -r requirements.txt

CMD ["/app/monitor.py"]
ENTRYPOINT ["python","-u"]
