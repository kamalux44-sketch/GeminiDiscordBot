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
model = genai.GenerativeModel('gemini-1.5闪')

# Brave Search APIの関数（スニペットとURL取得）
def search_brave(query):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": 3
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Brave API レスポンスステータス: {response.status_code}")
        print(f"Brave API レスポンスボディ: {response.text}")
        if response.status_code == 200:
            results = response.json().get("web", {}).get("results", [])
            if not results:
                return ["検索結果がありませんでした。"], []
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
            # 本文を抽出（例: <p>タグや記事本文のセレクタを調整）
            paragraphs = soup.find_all('p')
            content = ' '.join([para.get_text().strip() for para in paragraphs])
            # 文字数制限（例: 3000文字以内に制限）
            return content[:3000] if content else "コンテンツが見つかりませんでした。"
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
        # !find コマンドの場合
        if content.startswith("!find "):
            query = content[len("!find "):]
        else:
            query = content  # すべてのメッセージを検索クエリとして扱う

        # Brave Search APIで検索
        snippets, urls = search_brave(query)

        # URLからコンテンツを取得
        scraped_contents = []
        for url in urls[:2]:  # 最大2つのURLをスクレイピング（負荷軽減のため）
            content = scrape_url(url)
            scraped_contents.append(f"URL: {url}\n{content}\n")

        # Geminiに渡すプロンプトを構築（スニペット＋スクレイピング結果）
        search_summary_prompt = (
            f"以下は「{query}」に関する検索結果のスニペットとウェブページの内容です。\n\n"
            f"### 検索スニペット ###\n"
            + "\n\n".join(snippets)
            + "\n\n### ウェブページの内容 ###\n"
            + "\n\n".join(scraped_contents)
            + "\n\nこれらの情報をもとに、簡潔に内容をまとめてください。"
        )

        try:
            response = model.generate_content(search_summary_prompt)
            await message.channel.send(response.text[:2000])  # Discordのメッセージ文字数制限対応
        except Exception as e:
            await message.channel.send(f"要約中にエラーが発生しました: {str(e)}")

    await bot.process_commands(message)

# ボットの起動処理
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)