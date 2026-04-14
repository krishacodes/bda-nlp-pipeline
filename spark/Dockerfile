FROM python:3.11-slim

# Java is required for PySpark
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jdk-headless curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/default-java

WORKDIR /app

RUN pip install --no-cache-dir \
    pyspark==3.5.0 \
    spacy==3.7.2 \
    psycopg2-binary==2.9.9 \
    kafka-python==2.0.2

# Download spaCy model
RUN python -m spacy download en_core_web_sm

COPY pipeline.py .

CMD ["python", "pipeline.py"]
