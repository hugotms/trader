FROM alpine/git:latest as clone

ENV TRADER_VERSION=v2.0.1

WORKDIR /trader

RUN git clone --branch $TRADER_VERSION https://github.com/hugotms/trader.git ./

FROM python:3.8-slim as run

ENV TRADER_VERSION=v2.0.1

RUN groupadd trader && \
    useradd -m -g trader trader

USER trader

WORKDIR /app

COPY --from=clone /trader .

RUN pip install -r requirements.txt

CMD ["monitor.py"]
ENTRYPOINT ["python","-u"]
