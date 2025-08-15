import os
import discord
from discord.ext import commands
import openai
import aiohttp

# ────────────────────────────────────────────────────────────
# 環境変数（Northflank → Service → Environment に設定）
DISCORD_TOKEN       = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY")
BRAVE_API_KEY       = os.getenv("BRAVE_API_KEY")
ALLOWED_CHANNEL     = int(os.getenv("ALLOWED_CHANNEL", 0))  # 0 のままなら制限なし

# 必須チェック
if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN が設定されていません")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY が設定されていません")

# OpenRouter（Gemini 2.0 Flash Experimental）の設定
openai.api_base = "https://openrouter.ai/api/v1"
openai.api_key  = OPENROUTER_API_KEY

# ────────────────────────────────────────────────────────────
# Discord ボットのセットアップ
intents = discord.Intents.default()
intents.messages = True

bot = commands.Bot(command_prefix="!", intents=intents)

def is_allowed_channel():
    """許可されたチャンネルかどうかを判定するデコレータ"""
    async def predicate(ctx):
        if ALLOWED_CHANNEL and ctx.channel.id != ALLOWED_CHANNEL:
            await ctx.send("❌ このチャンネルでは利用できません。")
            return False
        return True
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f"✅ ログイン完了: {bot.user} (ID: {bot.user.id})")

# ────────────────────────────────────────────────────────────
# Brave Search のヘルパー関数
async def fetch_brave(query: str, count: int = 3) -> list[dict]:
    url     = "https://api.brave.com/search"
    headers = {"X-API-KEY": BRAVE_API_KEY}
    params  = {"q": query, "source": "web_with_bing", "num": count}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            return data.get("web", {}).get("results", [])

# ────────────────────────────────────────────────────────────
# コマンド: !ask <プロンプト>
@bot.command(name="ask")
@is_allowed_channel()
async def ask(ctx, *, prompt: str):
    """Gemini 2.0 Flash に直接プロンプトを投げる"""
    await ctx.trigger_typing()
    try:
        res = openai.ChatCompletion.create(
            model="google/gemini-2.0-flash-experimental",
            messages=[{"role":"user","content":prompt}],
            temperature=0.7,
            max_tokens=800
        )
        answer = res.choices[0].message.content.strip()
    except Exception as e:
        return await ctx.send(f"⚠️ LLM 呼び出しエラー: {e}")

    await ctx.send(answer)

# コマンド: !search <クエリ>
@bot.command(name="search")
@is_allowed_channel()
async def search(ctx, *, query: str):
    """Brave Searchで取得した結果をGeminiで要約する"""
    await ctx.trigger_typing()

    # 1) Brave Search 実行
    try:
        results = await fetch_brave(query)
    except Exception as e:
        return await ctx.send(f"⚠️ 検索エラー: {e}")

    # 要約用プロンプトの組み立て
    snippet_text = "\n".join(
        f"- {r.get('title')}: {r.get('url')}" for r in results[:3]
    )
    summary_prompt = (
        f"以下の検索結果をもとに、\n"
        f"「{query}」について日本語で簡潔に要約してください。\n\n"
        f"{snippet_text}"
    )

    # 2) LLM に要約を依頼
    try:
        res = openai.ChatCompletion.create(
            model="google/gemini-2.0-flash-experimental",
            messages=[{"role":"user","content":summary_prompt}],
            temperature=0.2,
            max_tokens=500
        )
        summary = res.choices[0].message.content.strip()
    except Exception as e:
        return await ctx.send(f"⚠️ 要約エラー: {e}")

    await ctx.send(summary)

# ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)