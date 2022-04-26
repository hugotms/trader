FROM python:3.8

RUN mkdir /app && \
    pip install requests

WORKDIR /app
