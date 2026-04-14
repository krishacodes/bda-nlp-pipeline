from fastapi import FastAPI
import pandas as pd
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(BASE_DIR, "..", "final_output", "processed_news.csv")

def load_data():
    try:
        df = pd.read_csv(DATA_PATH)
        return df.fillna("")
    except Exception as e:
        print("ERROR LOADING FILE:", e)  # 👈 important for logs
        return pd.DataFrame()

@app.get("/")
def home():
    return {"message": "News API is running 🚀"}

@app.get("/news")
def get_news():
    df = load_data()
    return df.to_dict(orient="records")

@app.get("/sentiment")
def sentiment_summary():
    df = load_data()
    if df.empty:
        return {}
    return df["sentiment"].value_counts().to_dict()

@app.get("/debug")
def debug():
    return {
        "path": DATA_PATH,
        "exists": os.path.exists(DATA_PATH)
    }