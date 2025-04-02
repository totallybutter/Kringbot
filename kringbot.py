import discord
import os
import time
from dotenv import load_dotenv
from discord.ext import commands
from discord.commands import option
load_dotenv()
from utils import gsheet_utils, gimg_utils

GUILD_IDS = [int(os.getenv("GUILD_ID_1")), int(os.getenv("GUILD_ID_2"))]
bot = discord.Bot(debug_guilds=GUILD_IDS)

bot.load_extension("cogs.kb_ask_cog")  # Load KBAskCog
bot.load_extension("cogs.kb_img_cog")  # Load KBImgCog
bot.load_extension("cogs.kb_help_cog")  # Load KBHelpCog

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is ready and online!")

@bot.slash_command(name="sync-cogs", description="Sync up cog commands")
async def sync_cogs(ctx: discord.ApplicationContext):
    await ctx.defer()
    await bot.sync_commands()
    await ctx.followup.send("🔄 Slash commands synced globally.")

bot.run(os.getenv("DISCORD_BOT_TOKEN"))
