import os
import requests
import discord
from discord.ext import commands

# 環境変数読み込み
DISCORD_TOKEN      = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
BRAVE_API_KEY      = os.getenv("BRAVE_API_KEY")
# 通知を許可するチャンネルID（整数）
ALLOWED_CHANNEL    = int(os.getenv("ALLOWED_CHANNEL", 0))

# OpenRouter (Gemini) に問い合わせて要約を取得
def query_openrouter(prompt: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたは日本語でフレンドリーかつ簡潔に要点をまとめるアシスタントです。"
                    "ユーザーに直接話しかける自然な文体で回答してください。"
                )
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.6,
        "top_p": 0.9,
        "max_tokens": 700
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code == 429:
        raise RuntimeError("429: Rate limit or free tier limit reached")
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"No choices in response: {data}")
    return choices[0]["message"]["content"]

# Brave Search で上位3件を取得
def search_brave(query: str) -> str:
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-API-Key": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "size": 3
    }
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("web", [])
    snippets = []
    for i, item in enumerate(results, start=1):
        title   = item.get("title", "No Title")
        snippet = item.get("snippet", "No snippet available")
        url     = item.get("url", "")
        snippets.append(f"{i}. {title}\n{snippet}\n{url}")
    return "\n\n".join(snippets)

# Bot 定義
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

@bot.command(name="ask")
async def ask(ctx: commands.Context, *, question: str):
    # チャンネル制限
    if ALLOWED_CHANNEL and ctx.channel.id != ALLOWED_CHANNEL:
        return

    await ctx.trigger_typing()

    try:
        # 1) Brave で検索
        search_results = search_brave(question)
        # 2) 要約生成
        combined_prompt = (
            f"以下はウェブ検索の結果です：\n\n{search_results}\n\n"
            f"上記を踏まえて、次の質問に日本語で簡潔に答えてください。\n"
            f"{question}"
        )
        summary = query_openrouter(combined_prompt)
        # 3) レスポンス送信
        await ctx.reply(summary, mention_author=False)

    except Exception as e:
        await ctx.reply(f"エラーが発生しました: {e}", mention_author=False)

if __name__ == "__main__":
    if not all([DISCORD_TOKEN, OPENROUTER_API_KEY, BRAVE_API_KEY]):
        raise RuntimeError("環境変数が不足しています。DISCORD_TOKEN, OPENROUTER_API_KEY, BRAVE_API_KEY を設定してください。")
    bot.run(DISCORD_TOKEN)