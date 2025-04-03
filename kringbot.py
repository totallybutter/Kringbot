import discord
import os
import time
from dotenv import load_dotenv
from discord.ext import commands
from discord.commands import option
load_dotenv()
from utils import gsheet_utils, gimg_utils, bot_prefs

# allows for instant testing of functions within specified guilds
GUILD_IDS = [int(os.getenv("GUILD_ID_1")), int(os.getenv("GUILD_ID_2"))]
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(debug_guilds=GUILD_IDS, intents=intents)

# --- Loading Cogs (modules) ---
bot.load_extension("cogs.kb_prefsman_cog")  # Load PrefsManager
bot.load_extension("cogs.kb_ask_cog")       # Load AskCog
bot.load_extension("cogs.kb_img_cog")       # Load ImgCog
bot.load_extension("cogs.kb_help_cog")      # Load HelpCog
bot.load_extension("cogs.kb_msgman_cog")    # Load MessageManager

@bot.event
async def on_ready():
    print("\n======================")
    print(f"🤖 Bot Name     : {bot.user}")
    print(f"🆔 Bot ID       : {bot.user.id}")
    print(f"📡 Latency      : {round(bot.latency * 1000)}ms")
    print(f"🌐 Guilds       : {len(bot.guilds)}")
    print(f"👥 Users        : {sum(g.member_count or 0 for g in bot.guilds)}")
    print(f"📋 Slash Commands: {len(bot.application_commands)}")
    print(f"✅ {bot.user} is ready and online!")
    print("======================\n")

@bot.slash_command(name="sync-cogs", description="Sync up cog commands")
async def sync_cogs(ctx: discord.ApplicationContext):
    await ctx.defer(ephemeral=True)
    await bot.sync_commands(delete_existing=True)
    await ctx.followup.send("🔄 Slash commands synced globally.")

bot.run(os.getenv("DISCORD_BOT_TOKEN")) # run bot
