import requests
import json
import time
from kafka import KafkaProducer

KAFKA_BROKER = "localhost:9092"
TOPIC = "hn-live"

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

HN_NEW_URL = "https://hacker-news.firebaseio.com/v0/newstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

seen_ids = set()

def fetch_new_stories():
    try:
        res = requests.get(HN_NEW_URL)
        return res.json()[:10]
    except:
        return []

def fetch_story(story_id):
    try:
        res = requests.get(HN_ITEM_URL.format(story_id))
        return res.json()
    except:
        return None

while True:
    story_ids = fetch_new_stories()

    for sid in story_ids:
        if sid in seen_ids:
            continue

        story = fetch_story(sid)
        if not story:
            continue

        data = {
            "id": story.get("id"),
            "title": story.get("title"),
            "url": story.get("url"),
            "score": story.get("score"),
            "timestamp": story.get("time"),
            "text": story.get("title")
        }

        print("Sending:", data["title"])
        producer.send(TOPIC, data)

        seen_ids.add(sid)

    time.sleep(30)