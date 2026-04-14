FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    praw==7.7.1 \
    kafka-python==2.0.2

COPY producer.py .

CMD ["python", "producer.py"]
