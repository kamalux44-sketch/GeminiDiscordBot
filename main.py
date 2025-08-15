import os
import discord
import aiohttp
import asyncio

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
ALLOWED_CHANNEL = os.getenv("ALLOWED_CHANNEL")  # チャンネルID（文字列）

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

async def query_gemini(message_content):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "google/gemini-1.5-flash",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": message_content}
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data["choices"][0]["message"]["content"]
            else:
                error_text = await resp.text()
                return f"❌ API Error: {resp.status}\n{error_text}"

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if str(message.channel.id) != ALLOWED_CHANNEL:
        return

    await message.channel.typing()
    response = await query_gemini(message.content)
    await message.channel.send(response)

client.run(DISCORD_TOKEN)