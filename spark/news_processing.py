from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace, when

# Start Spark
spark = SparkSession.builder \
    .appName("NewsProcessing") \
    .master("local[*]") \
    .getOrCreate()

# Load CSV
df = spark.read.csv("../raw_news.csv", header=False)
df = df.toDF("title", "url", "time")

# -------------------------------
# Clean text using Spark (NO UDF)
# -------------------------------
df = df.withColumn("clean_title", lower(regexp_replace(col("title"), "[^a-zA-Z\\s]", "")))

# -------------------------------
# Simple Sentiment Logic (RULE BASED)
# -------------------------------
df = df.withColumn(
    "sentiment",
    when(col("clean_title").rlike("good|great|excellent|success|win|growth"), "positive")
    .when(col("clean_title").rlike("bad|fail|error|crash|issue|down|bug"), "negative")
    .otherwise("neutral")
)

# Show result
df.show(10, truncate=False)

# Save output
df.toPandas().to_csv("../final_output/processed_news.csv", index=False)
print("PANDAS WRITE DONE")
