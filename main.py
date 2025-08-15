import discord
from discord.ext import commands
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import os

print("✅ main.py が開始しました")

# 環境変数の取得とチェック
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
ALLOWED_CHANNEL = os.getenv("ALLOWED_CHANNEL")

if not DISCORD_TOKEN:
    raise ValueError("❌ DISCORD_TOKEN が設定されていません")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY が設定されていません")
if not BRAVE_API_KEY:
    raise ValueError("❌ BRAVE_API_KEY が設定されていません")
if not ALLOWED_CHANNEL:
    raise ValueError("❌ ALLOWED_CHANNEL が設定されていません")

ALLOWED_CHANNEL = int(ALLOWED_CHANNEL)

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Brave Search APIの関数（スニペットとURL取得）
def search_brave(query):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    # 最新情報を優先（過去24時間の結果）
    params = {
        "q": query + " 最新",  # クエリに「最新」を追加
        "count": 3,
        "freshness": "pd"  # 過去24時間以内の結果
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Brave API レスポンスステータス: {response.status_code}")
        print(f"Brave API レスポンスボディ: {response.text}")
        if response.status_code == 200:
            results = response.json().get("web", {}).get("results", [])
            if not results:
                return ["最新の検索結果が見つかりませんでした。"], []
            formatted = []
            urls = []
            for r in results:
                title = r.get("title", "タイトルなし")
                url = r.get("url", "URLなし")
                desc = r.get("description", "説明なし")
                formatted.append(f"■ {title}\n{desc}\n🔗 {url}")
                urls.append(url)
            return formatted, urls
        else:
            return [f"検索エラー: {response.status_code} - {response.text}"], []
    except Exception as e:
        print(f"Brave API リクエストエラー: {str(e)}")
        return [f"検索エラー: {str(e)}"], []

# URLからコンテンツをスクレイピングする関数
def scrape_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # ニュースサイト向けセレクタ
            if "yahoo.co.jp" in url:
                content = soup.find("div", class_="article_body")
            elif "nhk.or.jp" in url:
                content = soup.find("div", class_="content--body")
            else:
                content = soup.find_all("p")
            content = content.get_text().strip() if content else "コンテンツが見つかりませんでした。"
            return content[:3000]
        else:
            return f"URLの取得エラー: {response.status_code}"
    except Exception as e:
        return f"スクレイピングエラー: {str(e)}"

# Discordボットの設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ ボットが {bot.user} として準備完了')

@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id != ALLOWED_CHANNEL:
        return

    content = message.content.strip()

    if not content:
        return

    async with message.channel.typing():
        if content.startswith("!find "):
            query = content[len("!find "):]
        else:
            query = content

        snippets, urls = search_brave(query)
        scraped_contents = []
        for url in urls[:2]:
            content = scrape_url(url)
            scraped_contents.append(f"{content}")

        # 自然な応答を生成するプロンプト
        search_summary_prompt = (
            f"以下の情報は「{query}」に関する最新の検索結果とウェブページの内容です。\n\n"
            f"{'\n\n'.join(snippets + scraped_contents)}\n\n"
            "この情報を基に、ユーザーに直接話しかけるような自然な日本語で、簡潔に要点をまとめてください。"
            "プロンプトや「スニペット」「ウェブページの内容」などの内部的な言葉は使わず、"
            "まるで友人に話すようにカジュアルでわかりやすく説明してください。"
        )

        try:
            response = model.generate_content(search_summary_prompt)
            await message.channel.send(response.text[:2000])
        except Exception as e:
            await message.channel.send(f"ごめん、情報をまとめるのに失敗しちゃった... エラー: {str(e)}")

    await bot.process_commands(message)

# ボットの起動処理
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)