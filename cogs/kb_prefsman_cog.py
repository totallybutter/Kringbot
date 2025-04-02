import discord
import atexit
from discord.ext import commands
from utils import bot_prefs, drive_prefs

LOCAL_PREF_PATH = "kringbot_prefs.json"

def _save_prefs():
    bot_prefs.save(LOCAL_PREF_PATH)
    drive_prefs.upload_to_drive(LOCAL_PREF_PATH)
    print("[PrefsManager] 🧷 Saved prefs via atexit.")

atexit.register(_save_prefs)

class PrefsManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Load from Drive on first ready
        if drive_prefs.download_from_drive(LOCAL_PREF_PATH):
            bot_prefs.load(LOCAL_PREF_PATH)
        else:
            print("[PrefsManager] ⚠️ No cloud prefs found. Starting fresh.")

    @commands.Cog.listener()
    async def on_disconnect(self):
        self._save_prefs()

    @commands.Cog.listener()
    async def on_close(self):
        self._save_prefs()

    @discord.slash_command(description="Save current bot prefs to Drive")
    async def save_db(self, ctx):
        await ctx.defer()
        self._save_prefs()
        await ctx.respond("✅ Preferences saved to Google Drive.")

    @discord.slash_command(description="Load bot prefs from Drive (manual override)")
    async def load_db(self, ctx):
        await ctx.defer()
        success = drive_prefs.download_from_drive(LOCAL_PREF_PATH)
        if success:
            bot_prefs.load(LOCAL_PREF_PATH)
            await ctx.respond("✅ Preferences loaded from Google Drive.")
        else:
            await ctx.respond("⚠️ Could not load prefs from Drive.")

def setup(bot):
    bot.add_cog(PrefsManager(bot))
