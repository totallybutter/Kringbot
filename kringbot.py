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

@bot.slash_command(name="hello", description="Say hello to the bot")
async def hello(ctx: discord.ApplicationContext):
    roles = [role.name for role in ctx.author.roles]
    response = gsheet_utils.get_response_for_role(roles, "hello")
    if not response:
        await ctx.respond("^ w^ Hewwo!")
    else:
        await ctx.respond(response.replace("{user}", ctx.author.display_name))


bot.run(os.getenv("DISCORD_BOT_TOKEN"))
