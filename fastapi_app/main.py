from fastapi import FastAPI
import pandas as pd
import os

app = FastAPI()

# File path
DATA_PATH = os.path.join(os.path.dirname(__file__), "../final_output/processed_news.csv")

def load_data():
    try:
        return pd.read_csv(DATA_PATH)
    except:
        return pd.DataFrame()

@app.get("/")
def home():
    return {"message": "News API is running 🚀"}

@app.get("/news")
def get_news():
    df = load_data()
    df = df.fillna("")  # 🔥 fix
    return df.to_dict(orient="records")
@app.get("/sentiment")
def sentiment_summary():
    df = load_data()
    if df.empty:
        return {}
    return df["sentiment"].value_counts().to_dict()