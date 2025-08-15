import discord
from discord.ext import commands
import google.generativeai as genai
import requests
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

# Brave Search APIの関数（スニペット付き）
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
                return ["検索結果がありませんでした。"]
            formatted = []
            for r in results:
                title = r.get("title", "タイトルなし")
                url = r.get("url", "URLなし")
                desc = r.get("description", "説明なし")
                formatted.append(f"■ {title}\n{desc}\n🔗 {url}")
            return formatted
        else:
            return [f"検索エラー: {response.status_code} - {response.text}"]
    except Exception as e:
        print(f"Brave API リクエストエラー: {str(e)}")
        return [f"検索エラー: {str(e)}"]

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

    if content.startswith("!find "):  # コマンドを !search から !find に変更
        query = content[len("!find "):]
        async with message.channel.typing():
            results = search_brave(query)

            # Geminiに渡すプロンプトを構築（スニペット付き）
            search_summary_prompt = (
                f"以下は「{query}」に関する最新の検索結果です。\n"
                + "\n\n".join(results)
                + "\n\nこれらの最新の情報をもとに、簡潔に内容をまとめてください。"
            )

            try:
                response = model.generate_content(search_summary_prompt)
                await message.channel.send(response.text)
            except Exception as e:
                await message.channel.send(f"要約中にエラーが発生しました: {str(e)}")
    else:
        try:
            async with message.channel.typing():
                response = model.generate_content(content)
                await message.channel.send(response.text)
        except Exception as e:
            await message.channel.send(f"エラーが発生しました: {str(e)}")

    await bot.process_commands(message)

# ボットの起動処理
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)