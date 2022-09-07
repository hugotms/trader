ARG VERSION=v5.0.0

FROM alpine/git:latest as clone

ARG VERSION

WORKDIR /trader

RUN git clone --branch test https://github.com/hugotms/trader.git ./

FROM python:3.8-slim as run

ARG VERSION

ENV TRADER_VERSION=$VERSION

RUN groupadd trader && \
    useradd -m -g trader trader

USER trader

WORKDIR /app

COPY --from=clone /trader .

RUN pip install -r requirements.txt

CMD ["launch.py"]
ENTRYPOINT ["python","-u"]
