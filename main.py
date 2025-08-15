import discord
from discord.ext import commands
import google.generativeai as genai
import os

# 環境変数の取得
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ALLOWED_CHANNEL = int(os.getenv("ALLOWED_CHANNEL"))

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Discordボットの設定
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user or message.channel.id != ALLOWED_CHANNEL:
        return
    try:
        response = model.generate_content(message.content)
        await message.channel.send(response.text)
    except Exception as e:
        await message.channel.send(f"エラーが発生しました: {str(e)}")
    await bot.process_commands(message)

bot.run(DISCORD_TOKEN)