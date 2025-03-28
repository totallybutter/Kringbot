import discord
import os
import random
import hashlib
from dotenv import load_dotenv
from discord.ext import commands
from discord import option

GUILD_ID_1 = int(os.getenv("GUILD_ID_1")) 
GUILD_ID_2 = int(os.getenv("GUILD_ID_2"))
load_dotenv()
bot = discord.Bot(debug_guilds=[GUILD_ID_1, GUILD_ID_2])

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and online!")

@bot.slash_command(name="hello", description="Say hello to the bot")
async def hello(ctx: discord.ApplicationContext):
    await ctx.respond("^ w^ Hewwo!")
    
@bot.slash_command(name="about",description="Show bot info and list of available commands.")
async def about(ctx: discord.ApplicationContext):
    info_text = (
        f"Bot name: {bot.user.name}\n"
        "- `/about`: Show bot info.\n"
        "- `/ask <question>`: Ask the bot a question.\n"
    )
    await ctx.respond(info_text)

@bot.slash_command(description="Ask Kringbot a question.")
@option("question", description="Type your question", required=True)
async def ask(ctx, question: str):
    responses = [
        "kring",
        "kwing",
        "nyah nyah",
        "sniff snoof",
        "the answer is more shleep",
        "try just going to shleep",
        "^ w^",
        "maybwe",
        "yes",
        "no",
        "think about it on kringday",
        "take a break!",
        "shleeping is always the answer",
        "mocha",
        "ask godgab"
    ]
    question_hash = hashlib.sha256(question.lower().encode("utf-8")).hexdigest()
    seed_value = int(question_hash, 16)
    random.seed(seed_value)
    response = random.choice(responses)
    random.seed()
    await ctx.respond(f"**Question**: {question}\n**Kringbot says**: {response}")

bot.run(os.getenv("DISCORD_BOT_TOKEN")) # run the bot with the token
