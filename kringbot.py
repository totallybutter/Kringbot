import discord
import os
import random
import hashlib
import glob
import time
import datetime
import collections
import ask_utils 
from dotenv import load_dotenv
from discord.ext import commands
from discord import option


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

@bot.slash_command(description="Ask Kringbot a question.")
@option("question", description="Type your question", required=True)
async def ask(ctx, question: str):
    question = question.lower()

    category_keywords = ask_utils.load_categories()
    responses_by_category = ask_utils.load_responses()
    special_responses = ask_utils.load_special_responses()

    if question.strip() in special_responses:
        # This ensures only exact matches trigger the response
        response = special_responses[question.strip()].replace("{user}", ctx.author.display_name)
        await ctx.respond(f"**{ctx.author.display_name} asks**: {question}\n**Kringbot says**: {response}")
        return

    category = ask_utils.categorize_question(question, category_keywords)
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
COOLDOWN_SECONDS = 60 * 60 * 12
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
