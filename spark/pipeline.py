import os
import json
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, from_json, current_timestamp
from pyspark.sql.types import (
    StructType, StructField, StringType, FloatType,
    IntegerType, ArrayType, TimestampType
)
from pyspark.ml.feature import Tokenizer, StopWordsRemover, HashingTF, IDF
from pyspark.ml.clustering import LDA
from pyspark.ml import Pipeline
import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────
KAFKA_SERVERS  = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
KAFKA_TOPIC    = "reddit-posts"
PG_URL         = os.environ["POSTGRES_URL"]
PG_USER        = os.environ["POSTGRES_USER"]
PG_PASS        = os.environ["POSTGRES_PASSWORD"]
CHECKPOINT_DIR = "/tmp/spark-checkpoints"
NUM_TOPICS     = 8
BATCH_SIZE     = 50   # min posts before LDA trains

# ── Schema for incoming Kafka JSON ─────────────────────────────────────────
POST_SCHEMA = StructType([
    StructField("id",          StringType()),
    StructField("subreddit",   StringType()),
    StructField("title",       StringType()),
    StructField("selftext",    StringType()),
    StructField("score",       IntegerType()),
    StructField("text",        StringType()),
    StructField("ingested_at", StringType()),
])

# ── spaCy NER as a broadcast UDF ───────────────────────────────────────────
def make_ner_udf(spark: SparkSession):
    """
    Broadcast spaCy model to all workers.
    Returns UDF that extracts (text, label) entity pairs.
    """
    import spacy
    nlp = spacy.load("en_core_web_sm")
    bc_nlp = spark.sparkContext.broadcast(nlp)

    @udf(returnType=ArrayType(StringType()))
    def extract_entities(text: str):
        if not text:
            return []
        doc = bc_nlp.value(text[:1000])   # cap to keep it fast
        return [f"{ent.text}::{ent.label_}" for ent in doc.ents
                if ent.label_ in {"PERSON", "ORG", "GPE", "PRODUCT", "EVENT"}]

    return extract_entities

# ── Text cleaning UDF ──────────────────────────────────────────────────────
import re
@udf(returnType=StringType())
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"http\S+", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ── Write batch to PostgreSQL ──────────────────────────────────────────────
def write_to_postgres(rows, table: str):
    conn = psycopg2.connect(
        host="postgres", dbname="nlp_results",
        user=PG_USER, password=PG_PASS
    )
    cur = conn.cursor()
    for row in rows:
        if table == "topics":
            cur.execute(
                "INSERT INTO topics (post_id, subreddit, topic_id, topic_words, processed_at) "
                "VALUES (%s, %s, %s, %s, NOW()) ON CONFLICT (post_id) DO NOTHING",
                (row.id, row.subreddit, row.dominant_topic, row.topic_words)
            )
        elif table == "entities":
            for entity in (row.entities or []):
                parts = entity.split("::")
                if len(parts) == 2:
                    cur.execute(
                        "INSERT INTO entities (post_id, entity_text, entity_label, processed_at) "
                        "VALUES (%s, %s, %s, NOW())",
                        (row.id, parts[0], parts[1])
                    )
    conn.commit()
    cur.close()
    conn.close()

# ── Build MLlib feature pipeline ──────────────────────────────────────────
def build_feature_pipeline() -> Pipeline:
    tokenizer    = Tokenizer(inputCol="cleaned_text", outputCol="tokens")
    remover      = StopWordsRemover(inputCol="tokens", outputCol="filtered")
    hashing_tf   = HashingTF(inputCol="filtered", outputCol="raw_features", numFeatures=10000)
    idf          = IDF(inputCol="raw_features", outputCol="features", minDocFreq=2)
    return Pipeline(stages=[tokenizer, remover, hashing_tf, idf])

# ── Process each micro-batch ───────────────────────────────────────────────
accumulated = []   # simple in-memory accumulator for small demo

def process_batch(batch_df, batch_id, ner_udf, feature_pipeline, spark):
    global accumulated

    if batch_df.rdd.isEmpty():
        return

    log.info(f"Batch {batch_id}: {batch_df.count()} records")

    # 1. Clean text
    df = batch_df.withColumn("cleaned_text", clean_text(col("text")))

    # 2. NER extraction
    df = df.withColumn("entities", ner_udf(col("text")))

    # 3. Accumulate for LDA (need enough docs to train meaningfully)
    accumulated.append(df)
    combined = accumulated[0]
    for d in accumulated[1:]:
        combined = combined.union(d)

    # Write entities immediately (no minimum needed)
    try:
        entity_rows = df.select("id", "subreddit", "entities").collect()
        write_to_postgres(entity_rows, "entities")
    except Exception as e:
        log.error(f"Entity write failed: {e}")

    # 4. LDA topic modeling (only once we have enough docs)
    total = combined.count()
    if total < BATCH_SIZE:
        log.info(f"Accumulating docs for LDA: {total}/{BATCH_SIZE}")
        return

    try:
        # Fit feature pipeline
        model    = feature_pipeline.fit(combined)
        features = model.transform(combined)

        # Train LDA
        lda      = LDA(k=NUM_TOPICS, maxIter=10, featuresCol="features")
        lda_model = lda.fit(features)

        # Get top words per topic
        vocab_size = 10000
        top_words_per_topic = {}
        topics_df = lda_model.describeTopics(maxTermsPerTopic=6)
        for row in topics_df.collect():
            top_words_per_topic[row.topic] = ",".join(
                [str(i) for i in row.termIndices]  # indices (word lookup needs vocab)
            )

        # Assign dominant topic to each document
        transformed = lda_model.transform(features)

        from pyspark.sql.functions import array_max, array_position, expr
        # topicDistribution is a vector; find argmax
        @udf(returnType=IntegerType())
        def argmax_vec(vec):
            if vec is None:
                return 0
            arr = vec.toArray().tolist()
            return int(arr.index(max(arr)))

        @udf(returnType=StringType())
        def topic_label(topic_id):
            return top_words_per_topic.get(topic_id, "unknown")

        result = (transformed
                  .withColumn("dominant_topic", argmax_vec(col("topicDistribution")))
                  .withColumn("topic_words", topic_label(col("dominant_topic")))
                  .select("id", "subreddit", "dominant_topic", "topic_words"))

        topic_rows = result.collect()
        write_to_postgres(topic_rows, "topics")
        log.info(f"LDA complete: {total} docs → {NUM_TOPICS} topics")

        # Reset accumulator after successful LDA run
        accumulated = []

    except Exception as e:
        log.error(f"LDA pipeline failed: {e}")

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    spark = (SparkSession.builder
             .appName("RedditNLPPipeline")
             .config("spark.jars.packages",
                     "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0,"
                     "org.postgresql:postgresql:42.7.1")
             .config("spark.sql.streaming.checkpointLocation", CHECKPOINT_DIR)
             .config("spark.driver.memory", "3g")
             .config("spark.executor.memory", "3g")
             .getOrCreate())

    spark.sparkContext.setLogLevel("WARN")

    ner_udf          = make_ner_udf(spark)
    feature_pipeline = build_feature_pipeline()

    # Read from Kafka
    raw = (spark.readStream
           .format("kafka")
           .option("kafka.bootstrap.servers", KAFKA_SERVERS)
           .option("subscribe", KAFKA_TOPIC)
           .option("startingOffsets", "latest")
           .option("failOnDataLoss", "false")
           .load())

    # Parse JSON
    parsed = (raw
              .select(from_json(col("value").cast("string"), POST_SCHEMA).alias("data"))
              .select("data.*")
              .filter(col("text").isNotNull()))

    # Stream with foreachBatch
    query = (parsed.writeStream
             .foreachBatch(
                 lambda df, bid: process_batch(df, bid, ner_udf, feature_pipeline, spark)
             )
             .trigger(processingTime="30 seconds")
             .option("checkpointLocation", CHECKPOINT_DIR)
             .start())

    log.info("Spark streaming started — waiting for data...")
    query.awaitTermination()

if __name__ == "__main__":
    main()
