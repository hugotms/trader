FROM python:3.8

RUN mkdir /app && \
    mkdir /data && \
    pip install requests && \
    git clone --branch master https://github.com/hugotms/trader.git /app

CMD ["/app/monitor.py"]
ENTRYPOINT ["python"]
