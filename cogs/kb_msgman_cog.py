import discord
import time
from discord.ext import commands
from collections import OrderedDict, defaultdict

DELETION_WINDOW = 128
MAX_TRACKED_MESSAGES = 128
MAX_DELETED_PER_USER = 16

class MessageManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_timestamps = OrderedDict()  # msg.id → (timestamp, author, content, channel)
        self.recent_deletes = defaultdict(list)  # user_id → list of (content, channel_name, timestamp)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        self.message_timestamps[message.id] = (
            time.time(),
            message.author,
            message.content,
            message.channel
        )
        if len(self.message_timestamps) > MAX_TRACKED_MESSAGES:
            self.message_timestamps.popitem(last=False)
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        data = self.message_timestamps.pop(message.id, None)
        if not data:
            return
        timestamp, author, content, channel = data
        age = time.time() - timestamp
        if age <= DELETION_WINDOW:
            entry = (content, channel.name, time.time())
            messages = self.recent_deletes[author.id]
            messages.insert(0, entry)  # Add newest to front
            self.recent_deletes[author.id] = messages[:MAX_DELETED_PER_USER]

    @discord.slash_command(
        name="deleted",
        description="Show a user's recently deleted messages",
        default_member_permissions=discord.Permissions(manage_messages=True)
    )
    async def show_deleted(
        self,
        ctx: discord.ApplicationContext,
        user_name: discord.Option(str, description="Display name to search for")
    ):
        await ctx.defer()

        user = None
        for member in ctx.guild.members:
            if user_name.lower() in member.display_name.lower():
                user = member
                break

        if not user:
            await ctx.respond(f"❌ No user found matching '{user_name}'.")
            return

        deleted = self.recent_deletes.get(user.id)
        if not deleted:
            await ctx.respond(f"✅ No recently deleted messages found for **{user.display_name}**.")
            return

        msg_lines = []
        for content, channel, ts in deleted:
            age = int(time.time() - ts)
            msg_lines.append(f"🕒 `{age}s ago` in **#{channel}**: {content}")

        await ctx.respond(
            f"🗑️ Recently deleted messages by **{user.display_name}**:\n" + "\n".join(msg_lines)
        )

    @commands.Cog.listener()
    async def on_ready(self):
        print("✅ MessageManager Cog loaded!")

def setup(bot):
    bot.add_cog(MessageManager(bot))
