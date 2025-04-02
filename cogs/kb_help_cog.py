import discord
from discord.ext import commands
from discord.commands import slash_command, Option

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ HelpCog loaded!")

    @discord.slash_command(name="help", description="Show help info for all commands or a specific command.")
    async def help(
        self,
        ctx,
        command_name: Option(str, "Optional command to get detailed help", required=False)
    ):
        if command_name:
            # Show help for a specific command
            cmd = self.bot.get_application_command(command_name)
            if not cmd:
                await ctx.respond(f"❌ Command `{command_name}` not found.")
                return

            embed = discord.Embed(
                title=f"❔ Help: /{cmd.name}",
                description=cmd.description or "No description provided.",
                color=discord.Color.green()
            )

            # Optionally list parameters
            if hasattr(cmd, "options") and cmd.options:
                for opt in cmd.options:
                    opt_type = str(opt.input_type).split('.')[-1].capitalize()
                    required = "✅" if opt.required else "❌"
                    embed.add_field(
                        name=f"`{opt.name}` ({opt_type}, Required: {required})",
                        value=opt.description or "No description.",
                        inline=False
                    )

            await ctx.respond(embed=embed)

        else:
            # Show paginated general command list
            await self.show_paginated_help(ctx)

    async def show_paginated_help(self, ctx):
        seen = set()
        unique_commands = []
        for cmd in self.bot.application_commands:
            if cmd.name not in seen:
                unique_commands.append(cmd)
                seen.add(cmd.name)

        per_page = 5
        pages = [
            unique_commands[i:i + per_page]
            for i in range(0, len(unique_commands), per_page)
        ]

        current_page = 0
        embed = self.make_help_embed(pages[current_page], current_page, len(pages))
        view = HelpPaginationView(pages, self.make_help_embed, ctx.author.id)

        await ctx.respond(embed=embed, view=view)


    def make_help_embed(self, commands, page, total_pages):
        embed = discord.Embed(
            title=f"📚 Kringbot Commands (Page {page + 1}/{total_pages})",
            color=discord.Color.blurple()
        )
        for cmd in commands:
            embed.add_field(
                name=f"/{cmd.name}",
                value=cmd.description or "No description",
                inline=False
            )
        return embed


class HelpPaginationView(discord.ui.View):
    def __init__(self, pages, make_embed_fn, author_id):
        super().__init__(timeout=120)
        self.pages = pages
        self.make_embed_fn = make_embed_fn
        self.current = 0
        self.author_id = author_id

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.primary)
    async def go_prev(self, button, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You're not the one who requested this help message!", ephemeral=True)
            return

        if self.current > 0:
            self.current -= 1
            embed = self.make_embed_fn(self.pages[self.current], self.current, len(self.pages))
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.primary)
    async def go_next(self, button, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You're not the one who requested this help message!", ephemeral=True)
            return

        if self.current < len(self.pages) - 1:
            self.current += 1
            embed = self.make_embed_fn(self.pages[self.current], self.current, len(self.pages))
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger)
    async def close_view(self, button, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You're not the one who requested this help message!", ephemeral=True)
            return

        await interaction.message.delete()


def setup(bot):
    bot.add_cog(HelpCog(bot))
