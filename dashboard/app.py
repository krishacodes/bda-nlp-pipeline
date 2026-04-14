import streamlit as st
import pandas as pd
import plotly.express as px
from collections import Counter
import requests

st.set_page_config(
    page_title="News Analytics",
    layout="wide",
    page_icon="📰"
)

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .metric-label { font-size: 0.75rem !important; color: #888 !important; text-transform: uppercase; letter-spacing: 0.05em; }
        .metric-value { font-size: 1.8rem !important; font-weight: 600 !important; }
        div[data-testid="stMetric"] {
            background: #f9f9f9;
            border-radius: 10px;
            padding: 1rem 1.25rem;
            border: 1px solid #eee;
        }
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

@st.cache_data
def load_data():
    try:
        response=requests.get("https://news-api-dzb9.onrender.com/news")
        data = response.json()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

df = load_data()
pos = (df["sentiment"] == "positive").sum()
neg = (df["sentiment"] == "negative").sum()
neu = (df["sentiment"] == "neutral").sum()

# ── Metrics ──────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Articles", len(df))
col2.metric("Positive", pos, delta=f"{round(pos / len(df) * 100)}% of total")
col3.metric("Negative", neg, delta=f"{round(neg / len(df) * 100)}% of total", delta_color="inverse")
col4.metric("Neutral", neu)

st.divider()

# ── Charts Row ───────────────────────────────────────
left, right = st.columns(2)

with left:
    st.markdown('<p class="section-header">Sentiment distribution</p>', unsafe_allow_html=True)
    sentiment_counts = df["sentiment"].value_counts().reset_index()
    sentiment_counts.columns = ["sentiment", "count"]

    color_map = {"positive": "#639922", "negative": "#E24B4A", "neutral": "#888780"}

    fig = px.bar(
        sentiment_counts,
        x="sentiment",
        y="count",
        color="sentiment",
        color_discrete_map=color_map,
        text="count",
    )
    fig.update_traces(textposition="outside", marker_line_width=0)
    fig.update_layout(
        height=300,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="Articles", gridcolor="#f0f0f0"),
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.markdown('<p class="section-header">Top keywords</p>', unsafe_allow_html=True)

    STOPWORDS = set([
        "the","is","in","and","to","of","for","on","with","a","an","by","from","at","as",
        "it","this","that","you","your","we","they","he","she","them","his","her",
        "can","will","just","into","over","more","less","using","show","new","one","two",
        "how","why","what","when","video","app","tool","use","used","via","based",
        "people","india","march","system","systems","management","website","between",
        "data","news","machine","modern","manage","science","linear","writing",
        "editing","pointless","hn","ask","would","could","should","make","made","like"
    ])

    words = [
        w for w in " ".join(df["clean_title"].dropna().astype(str)).split()
        if w not in STOPWORDS and len(w) > 4 and w.isalpha()
    ]
    word_freq = pd.DataFrame(
        Counter(words).most_common(10),
        columns=["keyword", "count"]
    )

    fig2 = px.bar(
        word_freq,
        x="count",
        y="keyword",
        orientation="h",
        text="count",
        color_discrete_sequence=["#378ADD"],
    )
    fig2.update_traces(textposition="outside", marker_line_width=0)
    fig2.update_layout(
        height=300,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(title="Frequency", gridcolor="#f0f0f0"),
        yaxis=dict(title="", autorange="reversed"),
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Article Table ─────────────────────────────────────
st.markdown('<p class="section-header">Article feed</p>', unsafe_allow_html=True)

search_col, filter_col = st.columns([3, 1])
with search_col:
    keyword = st.text_input("", placeholder="Filter by title or keyword…", label_visibility="collapsed")
with filter_col:
    sentiment_filter = st.selectbox("", ["All sentiments", "positive", "negative", "neutral"], label_visibility="collapsed")

filtered = df.copy()
if keyword:
    filtered = filtered[filtered["title"].str.contains(keyword, case=False, na=False)]
if sentiment_filter != "All sentiments":
    filtered = filtered[filtered["sentiment"] == sentiment_filter]

st.caption(f"{len(filtered)} article{'s' if len(filtered) != 1 else ''} shown")
st.dataframe(
    filtered,
    use_container_width=True,
    hide_index=True,
    height=400,
)