import discord
import os
import random
import hashlib
import glob
import time
import datetime
import collections
import ask_utils
import gsheet_utils
import gimg_utils
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
    roles = [role.name for role in ctx.author.roles]
    response = gsheet_utils.get_response_for_role(roles, "hello")
    if not response:
        await ctx.respond("^ w^ Hewwo!")
    else:
        response = response.replace("{user}", ctx.author.display_name)
        await ctx.respond(response)


@bot.slash_command(name="show-cache", description="display internal cache")
@option("Cache name", description="Cache to display", required=True)
async def show_cache(ctx: discord.ApplicationContext, cache_name: str):
    roles = [role.name for role in ctx.author.roles]
    cache_list = gsheet_utils.try_get_from_cache(cache_name.lower())
    responses_by_category = gsheet_utils._sheet_cache["responses"]
    special_responses = gsheet_utils._sheet_cache["specials"]
    print(f"{cache_name}: {cache_list}")
    await ctx.respond("Shown cache in console")
    return


@bot.slash_command(name="about",description="Show bot info and list of available commands.")
async def about(ctx: discord.ApplicationContext):
    info_text = (
        f"Bot name: {bot.user.name}\n"
        "- `/about`: Show bot info.\n"
        "- `/ask <question>`: Ask the bot a question.\n"
        "- `/refresh-ask <cache_name>`: Refreshes the specified response cache for the bot."
        "- `/daily-kringles`: Get your personalised daily kringle image.\n"
        "- `/refresh-images`: Reload images from the Kringbot Daily Google Drive folder."
    )
    await ctx.respond(info_text)

refresh_ask_cooldown = 0
REFRESH_ASK_COOLDOWN_SECONDS = 120
@bot.slash_command(name="refresh-ask", description="Recache the responses from online")
@option("Cache name", description="Cache to refresh", required=True)
async def refresh_cache(ctx:discord.ApplicationContext, cache_name: str):
    now = time.time()
    last_used = refresh_ask_cooldown
    time_since_last = now - last_used
    time_left = REFRESH_ASK_COOLDOWN_SECONDS - time_since_last
    if time_since_last > REFRESH_ASK_COOLDOWN_SECONDS:
        gsheet_utils.try_get_from_cache(cache_name.lower(), True)
        await ctx.respond(f"📝 Refreshed {cache_name} cache!")
    else:
        minutes = int((time_left % 3600) // 60)
        seconds = int(time_left % 60)
        await ctx.respond(f"⏳ A refresh was done recently! Try again in {minutes}m {seconds}s.")

@bot.slash_command(description="Ask Kringbot a question.")
@option("question", description="Type your question", required=True)
async def ask(ctx, question: str):
    question = question.lower()

    special_responses = gsheet_utils.try_get_from_cache("specials")
    if special_responses:
        if question.strip() in special_responses:
            # This ensures only exact matches trigger the response
            response = special_responses[question.strip()].replace("{user}", ctx.author.display_name)
            await ctx.respond(f"**{ctx.author.display_name} asks**: {question}\n**Kringbot says**: {response}")
            return

    role_substring_rules = gsheet_utils.try_get_from_cache("role_ask_responses")
    role_names = [role.name for role in ctx.author.roles]
    if role_substring_rules:
        for role in role_names:
            for rule_role, substr, responses in role_substring_rules:
                if rule_role == role and substr in question:
                    response = random.choice(responses).replace("{user}", ctx.author.display_name)
                    await ctx.respond(f"**{ctx.author.display_name} asks**: {question}\n**Kringbot says**: {response}")
                    return

    category_keywords = gsheet_utils.try_get_from_cache("categories")
    responses_by_category = gsheet_utils.try_get_from_cache("responses")
    if not category_keywords or not responses_by_category:
        await ctx.respond("⚠️ UmU I couldn't load my response data. Try `/refresh-ask` or contact the dev.")
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


refresh_img_cooldown = 0
REFRESH_IMG_COOLDOWN_SECONDS = 300
@bot.slash_command(name="refresh-images", description="Reload images from the Kringbot Daily Google Drive folder.")
async def refresh_images(ctx):

    now = time.time()
    last_used = refresh_img_cooldown
    time_since_last = now - last_used
    time_left = REFRESH_IMG_COOLDOWN_SECONDS - time_since_last
    if time_since_last < REFRESH_IMG_COOLDOWN_SECONDS:
        minutes = int((time_left % 3600) // 60)
        seconds = int(time_left % 60)
        await ctx.respond(f"⏳ A refresh was done recently! Try again in {minutes}m {seconds}s.")
        return

    folder_id = os.getenv("DAILY_IMAGE_FOLDER_ID")
    success = gimg_utils.refresh_folder_cache(folder_id)

    if success:
        await ctx.respond("✅ Image list has been refreshed.")
    else:
        await ctx.respond("❌ Could not refresh image list. Check folder access or ID.")

image_cooldowns = {}  # Dict to track last use time per user (user_id: timestamp)
DAILY_FOLDER_NAME = os.getenv("DAILY_IMAGE_FOLDER_ID")  # Optional override
COOLDOWN_SECONDS = 60 * 60 * 12
@bot.slash_command(name="daily-kringles", description="Get your daily kringle image!")
async def daily_image(ctx):
    user_id = ctx.author.id
    now = time.time()

    # Cooldown check
    last_used = image_cooldowns.get(user_id, 0)
    time_since_last = now - last_used
    time_left = COOLDOWN_SECONDS - time_since_last

    if time_since_last < COOLDOWN_SECONDS:
        hours = int(time_left // 3600)
        minutes = int((time_left % 3600) // 60)
        seconds = int(time_left % 60)
        await ctx.respond(f"⏳ You've already received your image of the day! Try again in {hours}h {minutes}m {seconds}s.")
        return
    
    # Get image from Google Drive folder
    image_url = gimg_utils.get_random_image_url(DAILY_FOLDER_NAME)
    if not image_url:
        await ctx.respond("⚠️ UmU Could not find images in the daily folder. Try contacting the dev.")
        return

    image_cooldowns[user_id] = now  # Save the time
    embed = discord.Embed(title="🖼️ Here's your image of the day!")
    embed.set_image(url=image_url)

    await ctx.respond(embed=embed)


bot.run(os.getenv("DISCORD_BOT_TOKEN")) # run the bot with the token
