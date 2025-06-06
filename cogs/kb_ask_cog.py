import discord
import os
import time
import random
import hashlib
import datetime
from discord.ext import commands
from discord.commands import option
from dotenv import load_dotenv

from utils import gsheet_utils
from utils.ask_utils import categorize_question, load_specified_ask_sheet, load_all_ask_sheets, get_responses_for_role, get_substring_response

REFRESH_ASK_COOLDOWN_SECONDS = 60

class AskCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.refresh_ask_cooldown = 0
        self.sheet_name = os.environ.get("ASK_SHEET_NAME")
        if not self.sheet_name:
            raise RuntimeError("ASK_SHEET_NAME not found in environment variables!")
        print("✅ AskCog loaded!")

    @discord.slash_command(name="hello", description="Say hello to kringbot")
    async def hello(self, ctx: discord.ApplicationContext):
        defaultResponses = [
            "^ w^ Hewwo!",
            "^w ^ Nyah Nyah!",
            "Hewwo! ^w ^",
            "Nyah Nyah! ^ w^"
        ]
        username = ctx.author.name   # This is the real username, not display/nickname
        roles = [role.name for role in ctx.author.roles]
        responses = get_responses_for_role(self.sheet_name, roles, "hello", username=username)
        if not responses:
            response = random.choice(defaultResponses)
        else:
            response = random.choice(responses).replace("{user}", ctx.author.display_name)
        await ctx.respond(response)


    @discord.slash_command(name="refresh-ask", description="Recache the responses from online")
    @option("Cache name", description="Cache to refresh", required=True)
    async def refresh_cache(self, ctx: discord.ApplicationContext, cache_name: str):
        try:
            await ctx.defer(ephemeral=True)
            
            now = time.time()
            time_since_last = now - self.refresh_ask_cooldown
            time_left = REFRESH_ASK_COOLDOWN_SECONDS - time_since_last

            if time_since_last > REFRESH_ASK_COOLDOWN_SECONDS:
                if cache_name.lower().strip() == "all":
                    load_all_ask_sheets(self.sheet_name)
                else:
                    load_specified_ask_sheet(self.sheet_name, cache_name.lower(), force=True)
                self.refresh_ask_cooldown = now
                await ctx.respond(f"📝 Refreshed {cache_name} cache!")
            else:
                minutes = int((time_left % 3600) // 60)
                seconds = int(time_left % 60)
                await ctx.respond(f"⏳ Try again in {minutes}m {seconds}s.")
        except discord.errors.NotFound:
            print("❌ Interaction expired before response could be sent.")
        except Exception as e:
            print(f"❗ Unexpected error in /refresh-ask: {e}")

    @discord.slash_command(description="Ask Kringbot a question.")
    @option("question", description="Type your question", required=True)
    async def ask(self, ctx, question: str):
        try:
            await ctx.defer()

            question = question.lower()
            display_name = ctx.author.display_name
            role_names = [role.name for role in ctx.author.roles]

            # Special response
            special_responses = load_specified_ask_sheet(self.sheet_name, "specials")
            if special_responses and question.strip() in special_responses:
                response = special_responses[question.strip()][0].replace("{user}", display_name)
                await ctx.respond(f"**{display_name} asks**: {question}\n**Kringbot says**: {response}")
                return

            # Role-specific response
            response = get_substring_response(self.sheet_name, ctx.author.name, role_names, question)
            if response:
                response = response.replace("{user}", display_name)
                await ctx.respond(f"**{display_name} asks**: {question}\n**Kringbot says**: {response}")
                return

            category_keywords = load_specified_ask_sheet(self.sheet_name, "categories")
            responses_by_category = load_specified_ask_sheet(self.sheet_name, "responses")
            if not category_keywords or not responses_by_category:
                await ctx.respond("⚠️ UmU I couldn't load my response data. Try `/refresh-ask` or contact the dev.")
                return

            category = categorize_question(question, category_keywords)
            responses = responses_by_category.get(category, responses_by_category["general"])

            now = datetime.datetime.now(datetime.UTC)
            minutes = (now.minute // 3) * 3
            time_key = now.strftime(f"%Y-%m-%d %H:{minutes:02d}")
            hash_input = f"{question}_{time_key}"
            seed = int(hashlib.sha256(hash_input.encode("utf-8")).hexdigest(), 16)

            random.seed(seed)
            response = random.choice(responses)
            random.seed()

            response = response.replace("{user}", display_name)
            await ctx.respond(f"**{display_name} asks**: {question}\n**Kringbot says**: {response}")
        except discord.errors.NotFound:
            print("❌ Interaction expired before response could be sent.")
        except Exception as e:
            print(f"❗ Unexpected error in /ask: {e}")

    @discord.slash_command(name="show-ask-cache", description="Display specified `ask` internal cache")
    @option("Cache name", description="Cache to display", required=True)
    async def show_ask_cache(self, ctx: discord.ApplicationContext, cache_name: str):
        try:
            await ctx.defer(ephemeral=True)
            cache = load_specified_ask_sheet(self.sheet_name, cache_name.lower())
            print(f"{cache_name}: {cache}")
            await ctx.respond("✅ Cache printed to console.")
        except discord.errors.NotFound:
            print("❌ Interaction expired before response could be sent.")
        except Exception as e:
            print(f"❗ Unexpected error in /show-ask-cache: {e}")


def setup(bot):
    bot.add_cog(AskCog(bot))
