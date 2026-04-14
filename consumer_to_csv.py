from kafka import KafkaConsumer
import json
import csv

consumer = KafkaConsumer(
    'hn-live',  # MUST match your producer topic
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print("Listening and saving to CSV...")

with open("raw_news.csv", "a", newline='', encoding='utf-8') as file:
    writer = csv.writer(file)

    for message in consumer:
        data = message.value

        title = data.get('title', '')
        url = data.get('url', '')
        time = data.get('time', '')

        writer.writerow([title, url, time])
        print("Saved:", title)