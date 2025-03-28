import discord
import os
import random
import hashlib
import glob
import time
import datetime
import collections
from dotenv import load_dotenv
from discord.ext import commands
from discord import option
from collections import defaultdict

load_dotenv()
GUILD_ID_1 = int(os.getenv("GUILD_ID_1"))
GUILD_ID_2 = int(os.getenv("GUILD_ID_2"))
bot = discord.Bot(debug_guilds=[GUILD_ID_1, GUILD_ID_2])
DATA_FOLDER = "data"

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
        "- `/daily-kringles`: Get your personalised daily kringle image"
    )
    await ctx.respond(info_text)

CATEGORY_FILE = DATA_FOLDER + "/categories.txt"
def load_categories(filepath=CATEGORY_FILE) -> dict:
    category_keywords = defaultdict(list)
    current_category = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):  # skip comments or blank lines
                continue
            if line.startswith("[") and line.endswith("]"):
                current_category = line[1:-1].lower()
            elif current_category:
                category_keywords[current_category].append(line.lower())

    return category_keywords

RESPONSES_FILE = DATA_FOLDER + "/responses.txt"
def load_responses(filepath=RESPONSES_FILE) -> dict:
    responses = defaultdict(list)
    current_category = "general"

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                current_category = line[1:-1].lower()
            else:
                responses[current_category].append(line)

    return responses

SPECIALS_FILE = DATA_FOLDER + "/special.txt"
def load_special_responses(filepath=SPECIALS_FILE) -> dict:
    special_responses = {}
    with open(filepath, "r", encoding="utf-8") as f:
        current_key = None
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("[") and line.endswith("]"):
                current_key = line[1:-1].lower()
            elif current_key:
                special_responses[current_key] = line  # only one response per special
    return special_responses

def categorize_question(question: str, category_keywords: dict) -> str:
    question = question.lower()
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in question:
                return category
    return "general"

@bot.slash_command(description="Ask Kringbot a question.")
@option("question", description="Type your question", required=True)
async def ask(ctx, question: str):
    question = question.lower()

    category_keywords = load_categories()
    responses_by_category = load_responses()
    special_responses = load_special_responses()

    for pattern, response in special_responses.items():
        if pattern in question_lower:
            response = response.replace("{user}", ctx.author.display_name)
            await ctx.respond(f"**{ctx.author.display_name} asks**: {question}\n**Kringbot says**: {response}")
            return  # Skip the rest — we already responded

    category = categorize_question(question, category_keywords)
    responses = responses_by_category.get(category, responses_by_category["general"])

    # Deterministic answer using hashed question
    now =  datetime.datetime.now(datetime.UTC)
    minutes = (now.minute // 3) * 3  # Round down to nearest 3 minutes
    time_key = now.strftime(f"%Y-%m-%d %H:{minutes:02d}")
    hash_input = f"{question.lower()}_{time_key}"
    question_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
    seed_value = int(question_hash, 16)

    random.seed(seed_value)
    response = random.choice(responses)
    random.seed()

    #add user's display name to personalize
    response = response.replace("{user}", ctx.author.display_name)
    await ctx.respond(f"**{ctx.author.display_name} asks**: {question}\n**Kringbot says**: {response}")


IMAGE_FOLDER = DATA_FOLDER + "/images"
def get_image_paths():
    extensions = ("*.png", "*.jpg", "*.jpeg", "*.gif")
    image_paths = []
    for ext in extensions:
        image_paths.extend(glob.glob(os.path.join(IMAGE_FOLDER, ext)))
    return image_paths
image_cooldowns = {}  # Dict to track last use time per user (user_id: timestamp)
COOLDOWN_SECONDS = 60 * 60 * 24
@bot.slash_command(name="daily-kringles", description="Get your daily kringle image!")
async def daily_image(ctx):
    user_id = ctx.author.id
    now = time.time()

     # Check if user is on cooldown
    last_used = image_cooldowns.get(user_id, 0)
    time_since_last = now - last_used
    time_left = COOLDOWN_SECONDS - time_since_last
    if time_since_last < COOLDOWN_SECONDS:
        hours = int(time_left // 3600)
        minutes = int((time_left % 3600) // 60)
        seconds = int(time_left % 60)
        await ctx.respond(f"⏳ You've already received your image of the day! Try again in {hours}h {minutes}m {seconds}s.")
        return
    
    image_paths = get_image_paths()
    if not image_paths:
        await ctx.respond("No images found in the folder.")
        return

    image = random.choice(image_paths)
    image_cooldowns[user_id] = now  # Update timestamp

    await ctx.respond("🖼️ Here's your image of the day!", file=discord.File(image))

bot.run(os.getenv("DISCORD_BOT_TOKEN")) # run the bot with the token
