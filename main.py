# main.py
import discord
from discord.ext import commands
import google.generativeai as genai
import requests
import os

print("✅ main.py has started")

# 環境変数の取得とチェック
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
ALLOWED_CHANNEL = os.getenv("ALLOWED_CHANNEL")

if not DISCORD_TOKEN:
    raise ValueError("❌ DISCORD_TOKEN is not set")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY is not set")
if not BRAVE_API_KEY:
    raise ValueError("❌ BRAVE_API_KEY is not set")
if not ALLOWED_CHANNEL:
    raise ValueError("❌ ALLOWED_CHANNEL is not set")

ALLOWED_CHANNEL = int(ALLOWED_CHANNEL)

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Brave Search APIの関数
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
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        results = response.json().get("web", {}).get("results", [])
        return [f"{r['title']}: {r['url']}" for r in results]
    else:
        return [f"検索エラー: {response.status_code}"]

# Discordボットの設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Bot is ready as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id != ALLOWED_CHANNEL:
        return

    content = message.content.strip()

    if content.startswith("!search "):
        query = content[len("!search "):]
        async with message.channel.typing():
            results = search_brave(query)
            await message.channel.send("\n".join(results))
    else:
        try:
            async with message.channel.typing():
                response = model.generate_content(content)
                await message.channel.send(response.text)
        except Exception as e:
            await message.channel.send(f"エラーが発生しました: {str(e)}")

    await bot.process_commands(message)

# Botの起動処理
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)