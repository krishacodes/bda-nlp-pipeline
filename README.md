# Real-Time Reddit NLP Intelligence Pipeline
**BDA Mini Project** — PySpark + Kafka + spaCy + Streamlit

## Architecture
- **Local**: Kafka, PySpark (LDA + NER), PostgreSQL — all via Docker
- **Cloud (Render.com)**: Streamlit dashboard — free public URL

---

## Prerequisites
- Docker Desktop (Windows) — https://docs.docker.com/desktop/install/windows-install/
- Python 3.11+ (for running dashboard locally during dev)
- Reddit account (for API credentials)

---

## Step 1 — Get Reddit API credentials
1. Go to https://www.reddit.com/prefs/apps
2. Click **create another app** → choose **script**
3. Name: `bda-nlp-pipeline`, redirect URI: `http://localhost:8080`
4. Copy `client_id` (under app name) and `client_secret`

---

## Step 2 — Configure environment
```bash
cp .env.example .env
# Edit .env and fill in your Reddit credentials
```

---

## Step 3 — Start the local pipeline
```bash
docker-compose up --build
```
This starts:
- Zookeeper + Kafka on port 9092
- PostgreSQL on port 5432
- Reddit producer (starts streaming immediately)
- PySpark NLP pipeline (processes every 30s)

Wait ~2 minutes for all services to be healthy.

---

## Step 4 — Run dashboard locally
```bash
cd dashboard
pip install streamlit psycopg2-binary pandas plotly
streamlit run app.py
```
Open http://localhost:8501

> The dashboard auto-refreshes every 30s. LDA topics appear after 50+ posts are collected.

---

## Step 5 — Deploy dashboard to Render.com (free public URL)
1. Push this repo to GitHub
2. Go to https://render.com → New → Web Service
3. Connect your GitHub repo, set root directory to `dashboard/`
4. Set environment variables:
   - `PG_HOST` → your machine's public IP or use a free hosted PostgreSQL
   - `PG_USER` → `nlpuser`
   - `PG_PASS` → `nlppass`
5. Render auto-builds the Dockerfile and gives you a public URL

> For the hosted DB, use Render's free PostgreSQL instance instead of local.

---

## Project structure
```
bda-nlp-pipeline/
├── docker-compose.yml       # Orchestrates all local services
├── .env.example             # Rename to .env and fill credentials
├── producer/
│   ├── producer.py          # PRAW → Kafka producer
│   └── Dockerfile
├── spark/
│   ├── pipeline.py          # PySpark streaming + TF-IDF + LDA + NER
│   └── Dockerfile
├── dashboard/
│   ├── app.py               # Streamlit dashboard
│   └── Dockerfile           # For Render.com deployment
└── sql/
    └── init.sql             # PostgreSQL schema
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Kafka container exits | Increase Docker memory to 4GB+ in Docker Desktop settings |
| Spark OOM error | In pipeline.py reduce `BATCH_SIZE` to 30 |
| No topics showing | Need 50+ posts first; check `docker logs spark-nlp` |
| Dashboard DB error | Ensure postgres container is running: `docker ps` |
