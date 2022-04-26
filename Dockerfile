FROM python:3.8

RUN mkdir /app && \
    pip install requests json smtplib email

WORKDIR /app
