import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
import requests
import time

# ── Page Config ──────────────────────────────────────
st.set_page_config(
    page_title="News Analytics",
    layout="wide",
    page_icon="📰"
)

# ── Styling ──────────────────────────────────────────
st.markdown("""
<style>
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
.section-header {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #aaa;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────
st.markdown('<p class="section-header">Live feed</p>', unsafe_allow_html=True)
st.title("News Analytics Dashboard")
st.caption("NLP-powered insights from streaming data")
st.divider()

# ── Data Loader (FIXED) ──────────────────────────────
@st.cache_data(ttl=30)
def load_data():
    url = "https://news-api-dzb9.onrender.com/news"

    for _ in range(3):  # retry logic
        try:
            res = requests.get(url, timeout=10)
            data = res.json()

            if isinstance(data, list) and len(data) > 0:
                return pd.DataFrame(data)

            time.sleep(2)
        except:
            time.sleep(2)

    return pd.DataFrame()

df = load_data()

# ── SAFETY CHECK (CRITICAL) ──────────────────────────
if df.empty or "sentiment" not in df.columns:
    st.warning("⏳ Backend waking up... please refresh in a few seconds")
    st.stop()

# ── Metrics ──────────────────────────────────────────
pos = (df["sentiment"] == "positive").sum()
neg = (df["sentiment"] == "negative").sum()
neu = (df["sentiment"] == "neutral").sum()
total = len(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Articles", total)

col2.metric(
    "Positive",
    pos,
    delta=f"{round(pos/total*100)}%" if total else "0%"
)

col3.metric(
    "Negative",
    neg,
    delta=f"{round(neg/total*100)}%" if total else "0%",
    delta_color="inverse"
)

col4.metric("Neutral", neu)

st.divider()

# ── Charts ───────────────────────────────────────────
left, right = st.columns(2)

with left:
    st.markdown('<p class="section-header">Sentiment distribution</p>', unsafe_allow_html=True)

    sentiment_counts = df["sentiment"].value_counts().reset_index()
    sentiment_counts.columns = ["sentiment", "count"]

    fig = px.bar(
        sentiment_counts,
        x="sentiment",
        y="count",
        color="sentiment",
        text="count"
    )

    fig.update_layout(height=300, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown('<p class="section-header">Top keywords</p>', unsafe_allow_html=True)

    STOPWORDS = set([
        "the","is","in","and","to","of","for","on","with","a","an","by","from","at","as",
        "it","this","that","you","your","we","they","he","she","them","his","her",
        "can","will","just","into","over","more","less","using","show","new","one","two",
        "how","why","what","when","video","app","tool","use","used","via","based",
        "data","news","hn","ask"
    ])

    words = [
        w for w in " ".join(df["clean_title"].dropna().astype(str)).split()
        if w not in STOPWORDS and len(w) > 4 and w.isalpha()
    ]

    word_freq = pd.DataFrame(
        Counter(words).most_common(10),
        columns=["keyword", "count"]
    )

    if not word_freq.empty:
        fig2 = px.bar(
            word_freq,
            x="count",
            y="keyword",
            orientation="h",
            text="count"
        )
        fig2.update_layout(height=300)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Not enough data for keywords")

st.divider()

# ── Filters ──────────────────────────────────────────
st.markdown('<p class="section-header">Article feed</p>', unsafe_allow_html=True)

search_col, filter_col = st.columns([3, 1])

with search_col:
    keyword = st.text_input("", placeholder="Filter by title...", label_visibility="collapsed")

with filter_col:
    sentiment_filter = st.selectbox("", ["All", "positive", "negative", "neutral"], label_visibility="collapsed")

filtered = df.copy()

if keyword:
    filtered = filtered[filtered["title"].str.contains(keyword, case=False, na=False)]

if sentiment_filter != "All":
    filtered = filtered[filtered["sentiment"] == sentiment_filter]

st.caption(f"{len(filtered)} articles shown")

st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
    height=400
)