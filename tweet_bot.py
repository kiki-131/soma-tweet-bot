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


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def should_tweet(title, summary, url):
    prompt = f"""あなたはSOMAというライフスタイルラウンジバーのSNS担当です。
以下の海外クラウドファンディング・トレンド記事をツイートすべきか判断してください。

【ツイートすべき基準】
- 日本チームがKickstarterやIndiegogoでバズっているもの
- クラウドファンディングで目標額を大幅に超えているもの
- 変わり種で急上昇してきたニッチな製品
- デザイン性が高いガジェット、ライフスタイル/インテリア/食/ファッションの革新
- 海外で話題だがまだ日本未上陸のトレンド

【絶対ツイートしない基準】
- 「令和最新版」のような怪しい商品
- Amazonの異常な割引（50-80%オフ）
- 中国OEM系のコピー商品
- 単なるセール・割引情報

タイトル: {title}
概要: {summary[:300]}
URL: {url}

YES か NO だけで答えてください。"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
        )
        answer = response.choices[0].message.content.strip().upper()
        return "YES" in answer
    except Exception as e:
        print(f"Groq error: {e}")
        return False


def generate_tweet(title, summary, url):
    prompt = f"""あなたは海外クラウドファンディングのプロコンサルタントです。
日本のフォロワーに向けて、以下のプロダクトについてツイートしてください。

【キャラクター設定】
- 海外クラファンを日々ウォッチしているプロ目線
- 単なる紹介ではなく「なぜ这れが刺さるのか」「なぜ目標額を超えたのか」など、短い講評・分析を一言添える
- 自然でこなれた日本語（硬い翻訳調はNG）
- 例: 「このシンプルさが逆に刺さる」「素材へのこだわりが支持者を動かした」「日本にまだ来てないのが不思議なくらい」

【条件】
- 140文字以内（URLは別途追加するので含めない）
- 絵文字は必ず1つだけ（2つ以上は厳禁）
- ハッシュタグを2〜3個（#クラファン #海外トレンド など自然なもの）
- ツイート本文のみ出力（説明文・前置き不要）

タイトル: {title}
概要: {summary[:300]}"""

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        tweet_text = response.choices[0].message.content.strip()
        full_tweet = tweet_text + "\n" + url
        if len(full_tweet) > 280:
            tweet_text = tweet_text[:200] + "..."
            full_tweet = tweet_text + "\n" + url
        return full_tweet
    except Exception as e:
        print(f"Groq error: {e}")
        return None


def main():
    state = load_state()
    print(f"State: count={state['count']}, date={state['date']}")
    if state["count"] >= MAX_TWEETS_PER_DAY:
        print("Today's tweet limit reached.")
        return

    for feed_url in RSS_FEEDS:
        if state["count"] >= MAX_TWEETS_PER_DAY:
            break
        try:
            print(f"Fetching: {feed_url}")
            feed = feedparser.parse(feed_url)
            print(f"  -> {len(feed.entries)} entries, status={feed.get('status', 'N/A')}")
            for entry in feed.entries[:5]:
                if state["count"] >= MAX_TWEETS_PER_DAY:
                    break
                url = entry.get("link", "")
                if url in state.get("posted_urls", []):
                    continue
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))
                print(f"Checking: {title}")
                if not should_tweet(title, summary, url):
                    print(f"Skipped: {title}")
                    continue
                tweet_text = generate_tweet(title, summary, url)
                if not tweet_text:
                    continue
                try:
                    x_client.create_tweet(text=tweet_text)
                    print(f"Tweeted: {tweet_text[:80]}...")
                    state["count"] += 1
                    state["posted_urls"].append(url)
                    save_state(state)
                    time.sleep(2)
                except Exception as e:
                    print(f"Tweet error: {e}")
        except Exception as e:
            print(f"Feed error for {feed_url}: {e}")


if __name__ == "__main__":
    main()
