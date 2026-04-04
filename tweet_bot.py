import os
import json
import tweepy
import feedparser
from groq import Groq
from datetime import date
import time

# API設定
x_client = tweepy.Client(
      consumer_key=os.environ["X_API_KEY"],
      consumer_secret=os.environ["X_API_SECRET"],
      access_token=os.environ["X_ACCESS_TOKEN"],
      access_token_secret=os.environ["X_ACCESS_SECRET"]
)
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

RSS_FEEDS = [
      "https://greenfunding.jp/feed",
      "https://coolbacker.com/feed",
      "https://thegadgetflow.com/category/crowdfunding/feed/",
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
            except:
        return {"date": str(date.today()), "count": 0, "posted_urls": []}

def save_state(state):
      with open(STATE_FILE, "w") as f:
                json.dump(state, f)

def should_tweet(title, summary, url):
      prompt = f"""あなたはSOMAのSNS担当です。SOMAはライフスタイル提案型のラウンジバーです。
      以下の記事をXでツイートすべきか判断してください。

      【必ずツイートすべき】
      - 日本のチームがKickstarter・IndieGogoで出品し、バズっているプロジェクト
      - クラファンで目標額を大きく超えて注目されている製品
      - 変わり種・ニッチだが急速に注目を集めているプロダクト

      【ツイートしてもよい】
      - デザイン性・ストーリー性の高いガジェット・プロダクト
      - ライフスタイル・インテリア・食・ファッション系の革新的な製品
      - 海外トレンドで日本未上陸のもの

      【絶対にツイートしてはいけない】
      - 「令和最新版」「最新改良版」など怪しいコピーが含まれる製品
      - Amazonの異常な割引（50%OFF・80%OFFなど）を前面に出した商品
      - 中国OEM系の粗悪品・パクリ製品の疑いがあるもの
      - 単なるセール・値下げ情報

      記事タイトル：{title}
      概要：{summary[:300]}

      「YES」か「NO」だけ答えてください。"""

    try:
              response = groq_client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=10
              )
        answer = response.choices[0].message.content.strip().upper()
        return "YES" in answer
    except:
        return False

def generate_tweet(title, summary, url):
      prompt = f"""以下の海外クラファン・トレンド情報を、SOMAのXアカウント向けの日本語ツイートに変換してください。

      SOMAはライフスタイル提案型のラウンジバーです。
      - 140文字以内
      - ワクワク感・発見感のある文体
      - ハッシュタグ2〜3個（#クラファン #海外トレンド など適切なもの）
      - URLを末尾に追加

      タイトル：{title}
      概要：{summary[:400]}
      URL：{url}

      ツイート文のみ出力してください。"""

    try:
              response = groq_client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=200
              )
        return response.choices[0].message.content.strip()
    except:
        return None

def main():
      state = load_state()

    if state["count"] >= MAX_TWEETS_PER_DAY:
              print(f"今日は{MAX_TWEETS_PER_DAY}件投稿済み。終了。")
        return

    for feed_url in RSS_FEEDS:
              if state["count"] >= MAX_TWEETS_PER_DAY:
                            break

        try:
                      feed = feedparser.parse(feed_url)
                  except:
            continue

        for entry in feed.entries[:5]:
                      if state["count"] >= MAX_TWEETS_PER_DAY:
                                        break

                      url = entry.get("link", "")
                      if url in state["posted_urls"]:
                                        continue

                      title = entry.get("title", "")
                      summary = entry.get("summary", "")

            print(f"判定中: {title}")

            if not should_tweet(title, summary, url):
                              print("→ スキップ")
                              continue

            tweet_text = generate_tweet(title, summary, url)
            if not tweet_text:
                              continue

            try:
                              x_client.create_tweet(text=tweet_text[:280])
                              print(f"→ ツイート完了: {tweet_text[:50]}...")
                              state["count"] += 1
                              state["posted_urls"].append(url)
                              save_state(state)
                              time.sleep(60)
except Exception as e:
                  print(f"→ ツイートエラー: {e}")

    print(f"完了。本日の投稿数: {state['count']}")

if __name__ == "__main__":
      main()
