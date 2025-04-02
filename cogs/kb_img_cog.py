import discord
import time
import os
from discord.ext import commands
from discord.commands import slash_command
from utils import gimg_utils  # Assuming this is your utility for Google Drive

REFRESH_IMG_COOLDOWN_SECONDS = 300
COOLDOWN_SECONDS = 65

class ImgCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.refresh_img_cooldown = 0
        self.image_cooldowns = {}
        self.img_folder_name = os.environ.get("DAILY_IMAGE_FOLDER_ID")
        if not self.img_folder_name:
            raise RuntimeError("DAILY_IMAGE_FOLDER_ID not found in environment variables!")
        print("✅ ImgCog loaded!")

    @discord.slash_command(name="refresh-images", description="Reload images from the Kringbot Daily Google Drive folder.")
    async def refresh_images(self, ctx):
        await ctx.defer()
        now = time.time()
        time_since_last = now - self.refresh_img_cooldown
        time_left = REFRESH_IMG_COOLDOWN_SECONDS - time_since_last

        if time_since_last < REFRESH_IMG_COOLDOWN_SECONDS:
            minutes = int((time_left % 3600) // 60)
            seconds = int(time_left % 60)
            await ctx.respond(f"⏳ A refresh was done recently! Try again in {minutes}m {seconds}s.")
            return

        success = gimg_utils.refresh_folder_cache(self.img_folder_name)

        if success:
            self.refresh_img_cooldown = now
            await ctx.respond("✅ Image list has been refreshed.")
        else:
            await ctx.respond("❌ UmU Could not refresh image list. Check folder access or ID.")

    @discord.slash_command(name="daily-kringles", description="Get your daily kringle image!")
    async def daily_image(self, ctx):
        await ctx.defer()
        user_id = ctx.author.id
        now = time.time()

        last_used = self.image_cooldowns.get(user_id, 0)
        time_since_last = now - last_used
        time_left = COOLDOWN_SECONDS - time_since_last

        if time_since_last < COOLDOWN_SECONDS:
            minutes = int((time_left % 3600) // 60)
            seconds = int(time_left % 60)
            await ctx.respond(f"⏳ You've already received your image of the day! Try again in {minutes}m {seconds}s.")
            return

        image_url = gimg_utils.get_random_image_url(self.img_folder_name)
        if not image_url:
            await ctx.respond("⚠️ UmU Could not find images in the daily folder. Try contacting the dev.")
            return

        self.image_cooldowns[user_id] = now
        embed = discord.Embed(title=f"🖼️ Here's your image of the day, {ctx.author.display_name}!")
        embed.set_image(url=image_url)

        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(ImgCog(bot))