import os
import json
import tweepy
import feedparser
from groq import Groq
from datetime import date
import time

x_client = tweepy.Client(
    consumer_key=os.environ["X_API_KEY"],
    consumer_secret=os.environ["X_API_SECRET"],
    access_token=os.environ["X_ACCESS_TOKEN"],
    access_token_secret=os.environ["X_ACCESS_SECRET"]
)
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

RSS_FEEDS = [
    "https://www.crowdfundinsider.com/feed/",
    "https://techcrunch.com/tag/crowdfunding/feed/",
    "https://www.yankodesign.com/feed/",
]

STATE_FILE = "state.json"
MAX_TWEETS_PER_DAY = 3


def load_state():
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        if state.get("date") != str(date.today()):
            return {"date": str(date.today()), "count": 0, "posted_urls": []}
        return state
    except Exception:
        return {"date": str(date.today()), "count": 0, "posted_urls": []}

