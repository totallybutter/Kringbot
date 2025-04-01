import discord
import os
import time
from dotenv import load_dotenv
from discord.ext import commands
from discord.commands import option

from utils import gsheet_utils, gimg_utils

load_dotenv()
GUILD_IDS = [int(os.getenv("GUILD_ID_1")), int(os.getenv("GUILD_ID_2"))]
bot = discord.Bot(debug_guilds=GUILD_IDS)
DAILY_FOLDER_NAME = os.getenv("DAILY_IMAGE_FOLDER_ID")

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ready and online!")
    bot.load_extension("cogs.kb_ask_cog")  # Load KBAskCog

@bot.slash_command(name="sync-cogs", description="Sync up cog commands")
async def sync_cogs(ctx: discord.ApplicationContext):
    await ctx.defer()
    await bot.sync_commands()
    await ctx.followup.send("🔄 Slash commands synced globally.")

@bot.slash_command(name="hello", description="Say hello to the bot")
async def hello(ctx: discord.ApplicationContext):
    roles = [role.name for role in ctx.author.roles]
    response = gsheet_utils.get_response_for_role(roles, "hello")
    if not response:
        await ctx.respond("^ w^ Hewwo!")
    else:
        await ctx.respond(response.replace("{user}", ctx.author.display_name))



@bot.slash_command(name="about", description="Show bot info and list of available commands.")
async def about(ctx: discord.ApplicationContext):
    info_text = (
        f"Bot name: {bot.user.name}\n"
        "- `/about`: Show bot info.\n"
        "- `/ask <question>`: Ask the bot a question.\n"
        "- `/refresh-ask <cache_name>`: Refreshes the specified response cache for the bot.\n"
        "- `/daily-kringles`: Get your personalised daily kringle image.\n"
        "- `/refresh-images`: Reload images from the Kringbot Daily Google Drive folder.\n"
    )
    await ctx.respond(info_text)


refresh_img_cooldown = 0
REFRESH_IMG_COOLDOWN_SECONDS = 300
@bot.slash_command(name="refresh-images", description="Reload images from the Kringbot Daily Google Drive folder.")
async def refresh_images(ctx):
    global refresh_img_cooldown

    now = time.time()
    time_since_last = now - refresh_img_cooldown
    time_left = REFRESH_IMG_COOLDOWN_SECONDS - time_since_last

    if time_since_last < REFRESH_IMG_COOLDOWN_SECONDS:
        minutes = int((time_left % 3600) // 60)
        seconds = int(time_left % 60)
        await ctx.respond(f"⏳ A refresh was done recently! Try again in {minutes}m {seconds}s.")
        return

    success = gimg_utils.refresh_folder_cache(DAILY_FOLDER_NAME)

    if success:
        refresh_img_cooldown = now
        await ctx.respond("✅ Image list has been refreshed.")
    else:
        await ctx.respond("❌ Could not refresh image list. Check folder access or ID.")


image_cooldowns = {}
COOLDOWN_SECONDS = 60 * 60 * 12
@bot.slash_command(name="daily-kringles", description="Get your daily kringle image!")
async def daily_image(ctx):
    user_id = ctx.author.id
    now = time.time()

    last_used = image_cooldowns.get(user_id, 0)
    time_since_last = now - last_used
    time_left = COOLDOWN_SECONDS - time_since_last

    if time_since_last < COOLDOWN_SECONDS:
        hours = int(time_left // 3600)
        minutes = int((time_left % 3600) // 60)
        seconds = int(time_left % 60)
        await ctx.respond(f"⏳ You've already received your image of the day! Try again in {hours}h {minutes}m {seconds}s.")
        return

    image_url = gimg_utils.get_random_image_url(DAILY_FOLDER_NAME)
    if not image_url:
        await ctx.respond("⚠️ UmU Could not find images in the daily folder. Try contacting the dev.")
        return

    image_cooldowns[user_id] = now
    embed = discord.Embed(title="🖼️ Here's your image of the day!")
    embed.set_image(url=image_url)

    await ctx.respond(embed=embed)

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
