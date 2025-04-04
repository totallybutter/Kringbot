import discord
import random
from discord.ext import commands
from discord.commands import slash_command, Option, SlashCommandGroup
from utils import bot_prefs

# How often a user can claim a token (in seconds)
CLAIM_COOLDOWN = 3600  # 1 hour

# 1 token = 1 second of cooldown modification
SECONDS_PER_TOKEN = 1

class TokenCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ TokenCog loaded!")

    def get_balance(self, user_id: int) -> int:
        """Returns how many tokens the user currently has."""
        return int(bot_prefs.get(f"ktoken_balance_{user_id}", 0))
    
    def set_balance(self, user_id: int, new_balance: int):
        """Set the user's new token balance."""
        bot_prefs.set(f"ktoken_balance_{user_id}", max(new_balance, 0))
    
    def get_claim_cooldown_remaining(self, user_id: int) -> int:
        """Returns how many seconds remain before user can claim again."""
        return int(bot_prefs.get(f"ktoken_claim_cd_{user_id}", 0))

    def set_claim_cooldown(self, user_id: int, seconds: int):
        """Sets the claim cooldown for a user to 'seconds' time-based."""
        bot_prefs.set(f"ktoken_claim_cd_{user_id}", seconds, time_based=True)

    def modify_cooldown(self, cooldown_type: str, target_id: int, delta_seconds: int):
        """
        Modify a user's daily or kringpic cooldown by +/- delta_seconds.
        If negative, it reduces. If positive, it adds.
        """
        # The image cogs store daily cooldown in "daily_img_cd_{user_id}"
        # and kring pic in "kringpic_img_cd_{user_id}"
        if cooldown_type == "daily":
            key = f"daily_img_cd_{target_id}"
        elif cooldown_type == "claim":
            key = f"ktoken_claim_cd_{target_id}"
        else:
            return False  # Unknown type

        current = bot_prefs.get(key, 0)  # how many seconds remain
        new_val = max(0, current + delta_seconds)  # can't go below 0
        # Re-save as time-based so it counts down
        bot_prefs.set(key, new_val, time_based=True)
        return True
    
    ktokengrp = SlashCommandGroup("ktoken", "Base slash command for ktoken commands.")

    ktokengrp_owner = SlashCommandGroup(
        "ktoken_owner",
        "Base slash command for owner related ktoken commands",
        checks=[
            commands.is_owner().predicate
        ],  # Ensures the owner_id user can access this group, and no one else
    )

    @ktokengrp.command(name="claim", description="Claim your ktokens every hour!")
    async def claim(self, ctx: discord.ApplicationContext):
        """Users can claim one token if they're past their cooldown."""
        user_id = ctx.author.id
        remaining = self.get_claim_cooldown_remaining(user_id)
        if remaining > 0:
            # Show the user how long until they can claim again
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            seconds = remaining % 60
            return await ctx.respond(
                f"⏳ You must wait {hours}h {minutes}m {seconds}s before claiming again.", 
                ephemeral=True
            )

        # Award 1 token
        balance = self.get_balance(user_id)
        self.set_balance(user_id, balance + 3600)
        # Set claim cooldown
        self.set_claim_cooldown(user_id, CLAIM_COOLDOWN)

        await ctx.respond(f"✅ You have claimed 1 ktoken! Your new balance: {balance+1}", ephemeral=True)

    @ktokengrp.command(name="balance", description="Check your token balance")
    async def balance(self, ctx: discord.ApplicationContext):
        user_id = ctx.author.id
        bal = self.get_balance(user_id)
        await ctx.respond(f"**{ctx.author.display_name}**: You have **{bal}** ktokens.", ephemeral=True)

    @ktokengrp.command(
        name="spend",
        description="Spend tokens to modify someone's command cooldown"
    )
    async def spend(
        self,
        ctx: discord.ApplicationContext,
        target: Option(discord.Member, description="Who to modify cooldown for"),
        cooldown: Option(str, description="Which cooldown to adjust", choices=["daily", "claim"]),
        tokens: Option(int, description="Number of tokens to spend (≥1) [1 Ktoken = 1 s]", min_value=1),
        mode: Option(str, description="Extend or reduce?", choices=["extend", "reduce"])
    ):
        await ctx.defer()
        """
        Example usage:
        /ktoken spend @gcww daily 3 reduce
        => Reduce gcww's "daily" cooldown by 3 tokens worth of seconds
        """
        user_id = ctx.author.id

        # 1) Check user has enough tokens
        current_balance = self.get_balance(user_id)
        if current_balance < tokens:
            return await ctx.respond(
                f"❌ You only have {current_balance} tokens, but that requires {tokens}.",
                ephemeral=True
            )

        # 2) Convert tokens → seconds
        seconds = tokens * SECONDS_PER_TOKEN
        # If the mode is reduce, we’ll use a negative to reduce the user’s cooldown
        if mode == "reduce":
            seconds = -seconds

        # 3) Modify target's cooldown
        success = self.modify_image_cooldown(cooldown, target.id, seconds)
        if not success:
            return await ctx.respond("❌ Unknown cooldown type.", ephemeral=True)

        # 4) Deduct tokens from the spender
        self.set_balance(user_id, current_balance - tokens)

        # 5) Notify
        if mode == "reduce":
            verb = "reduced"
            delta_str = f"-{tokens} tokens → {abs(seconds)}s less"
        else:
            verb = "extended"
            delta_str = f"+{tokens} tokens → {seconds}s more"

        await ctx.respond(
            f"✅ {ctx.author.display_name} has {verb} **{target.display_name}**'s **{cooldown}** cooldown.\n"
            f"**Cooldown change:** {delta_str}\n"
            f"**{ctx.author.display_name} current balance:** {current_balance - tokens}"
        )
        
    @ktokengrp_owner.command(
        name="modify",
        description="Change a given users balance of ktokens"
    )
    async def modify(
        self,
        ctx: discord.ApplicationContext,
        target: Option(discord.Member, description="Who to modify balance of"),
        tokens: Option(int, description="number of tokens to add/remove"),
    ):
        user_id = target.id
        current_balance = self.get_balance(user_id)
        new_balance = current_balance + tokens
        # prevent negative final balance
        if new_balance < 0:
            new_balance = 0

        self.set_balance(user_id, new_balance)

        # Decide how you want to phrase it
        verb = "increased" if tokens >= 0 else "decreased"
        abs_tokens = abs(tokens)
        await ctx.respond(
            f"✅ Successfully {verb} **{target.display_name}**'s balance by {abs_tokens} tokens.\n"
            f"**New balance:** {new_balance}",
            ephemeral=True
        )


    #####################
    # Dice Gamble with Higher/Lower + Single Numbers
    #####################
    @ktokengrp.command(name="gamba", description="Bet ktokens on a dice roll, with higher/lower or exact number!")
    async def gamba(
        self,
        ctx: discord.ApplicationContext,
        bet: Option(int, description="How many tokens to bet", min_value=1),
    ):
        """
        /ktoken gamble 10
        => Creates a publicly-visible embed with 8 buttons:
           Higher, Lower, 1, 2, 3, 4, 5, 6.
        => If "Higher" or "Lower" is correct, user wins +bet (1:1).
           If an exact number guess is correct, user wins +2×bet (1:2).
        """
        user_id = ctx.author.id
        current_balance = self.get_balance(user_id)
        if bet > current_balance:
            return await ctx.respond(
                f"❌ You only have {current_balance} tokens, but you tried to bet {bet}.",
                ephemeral=True
            )

        view = DiceBetView(token_cog=self, user_id=user_id, bet_amount=bet)
        embed = discord.Embed(
            title="Dice Gamble!",
            description=(
                f"{ctx.author.mention} is betting **{bet}** tokens.\n"
                "Choose **Higher**, **Lower**, or a specific number 1–6.\n"
                "**Higher** wins if roll is 4–6 (50% chance, 1:1 payout).\n"
                "**Lower** wins if roll is 1–3 (50% chance, 1:1 payout).\n"
                "Exact number wins if you guess it exactly (1/6 chance, 1:5 payout).\n"
                "Mikan will collect your entire bet if you lose."
            ),
            color=discord.Color.blurple()
        )
        await ctx.respond(embed=embed, view=view)

    #####################
    # Black Jack with Kringles
    #####################
    @ktokengrp.command(name="blackjack", description="Play blackjack with ktokens!")
    async def blackjack(
    self,
    ctx: discord.ApplicationContext,
    bet: Option(int, description="How many tokens to bet", min_value=1)
    ):
    user_id = ctx.author.id
    current_balance = self.get_balance(user_id)
    if bet > current_balance:
        return await ctx.respond(
            f"❌ You only have {current_balance} tokens, but you tried to bet {bet}.",
            ephemeral=True
        )

    # Deduct the bet up front
    self.set_balance(user_id, current_balance - bet)

    # Start the blackjack game
    view = BlackjackView(self, ctx.author, bet)
    await view.start(ctx)


class DiceBetView(discord.ui.View):
    """
    This view has 8 buttons: Higher, Lower, 1,2,3,4,5,6
    - If user picks Higher (roll in [4,5,6]) => 50% chance => 1:1 payout
    - If user picks Lower  (roll in [1,2,3]) => 50% chance => 1:1 payout
    - If user picks a #    (roll == that # ) => ~16.7% chance => 1:5 payout
    """
    def __init__(self, token_cog, user_id, bet_amount):
        super().__init__(timeout=60)
        self.token_cog = token_cog
        self.user_id = user_id
        self.bet_amount = bet_amount
        self.chosen = False
        self.message = None

    # Restrict to user
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You're not the one gambling!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        # disable buttons if time runs out
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        # Try updating the message if we have it
        if self.message:
            try:
                await self.message.edit(content="Bet timed out!", view=self)
            except:
                pass

    def disable_all_buttons(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    async def do_roll(self, guess: str) -> str:
        roll = random.randint(1, 6)
        old_balance = self.token_cog.get_balance(self.user_id)
        # default payout is 0 => user loses bet
        new_balance = max(0, old_balance - self.bet_amount)
        outcome_str = ""

        # Check if guess is "higher" or "lower"
        if guess == "higher" and roll in (4,5,6):
            # 1:1 payout => user gains +bet
            new_balance = old_balance + self.bet_amount
            outcome_str = f"**WIN** +{self.bet_amount}"

        elif guess == "lower" and roll in (1,2,3):
            new_balance = old_balance + self.bet_amount
            outcome_str = f"**WIN** +{self.bet_amount}"

        # Or if guess is a single digit
        elif guess.isdigit():
            chosen_num = int(guess)
            if roll == chosen_num:
                # 1:2 payout => user gains +2×bet
                new_balance = old_balance + (self.bet_amount * 5)
                outcome_str = f"**WIN** +{self.bet_amount * 5}"

        # Then finalize
        self.token_cog.set_balance(self.user_id, new_balance)
        net_change = new_balance - old_balance

        # Format text
        if net_change >= 0:
            msg = (
                f"🎲 Rolled **{roll}**\n"
                f"**Guess**: {guess} => {outcome_str}\n"
                f"**Balance**: {old_balance} → {new_balance}"
            )
        else:
            msg = (
                f"🎲 Rolled **{roll}**\n"
                f"**Guess**: {guess} => You lose your bet!\n"
                f"**Balance**: {old_balance} → {new_balance}"
            )
        return msg

    # Because we have 8 possible buttons, we can do 2 for Higher/Lower, then 6 for digits.
    # Let's put them in 2 rows for readability.

    @discord.ui.button(label="Higher", style=discord.ButtonStyle.primary, row=0)
    async def higher_button(self, button, interaction: discord.Interaction):
        await self.handle_bet(interaction, guess="higher")

    @discord.ui.button(label="Lower", style=discord.ButtonStyle.primary, row=0)
    async def lower_button(self, button, interaction: discord.Interaction):
        await self.handle_bet(interaction, guess="lower")

    @discord.ui.button(label="1", style=discord.ButtonStyle.secondary, row=1)
    async def one_button(self, button, interaction: discord.Interaction):
        await self.handle_bet(interaction, guess="1")

    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary, row=1)
    async def two_button(self, button, interaction: discord.Interaction):
        await self.handle_bet(interaction, guess="2")

    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary, row=1)
    async def three_button(self, button, interaction: discord.Interaction):
        await self.handle_bet(interaction, guess="3")

    @discord.ui.button(label="4", style=discord.ButtonStyle.secondary, row=2)
    async def four_button(self, button, interaction: discord.Interaction):
        await self.handle_bet(interaction, guess="4")

    @discord.ui.button(label="5", style=discord.ButtonStyle.secondary, row=2)
    async def five_button(self, button, interaction: discord.Interaction):
        await self.handle_bet(interaction, guess="5")

    @discord.ui.button(label="6", style=discord.ButtonStyle.secondary, row=2)
    async def six_button(self, button, interaction: discord.Interaction):
        await self.handle_bet(interaction, guess="6")

    async def handle_bet(self, interaction: discord.Interaction, guess: str):
        if self.chosen:
            return await interaction.response.send_message("You've already bet once!", ephemeral=True)
        self.chosen = True

        # Actually do the dice roll
        result = await self.do_roll(guess)
        # disable the other buttons
        self.disable_all_buttons()

        # store the message reference so we can edit if needed
        self.message = interaction.message
        # update the original message
        await interaction.response.edit_message(content=result, embed=None, view=self)
    
class BlackjackView(discord.ui.View):
    def __init__(self, token_cog, player, bet_amount):
        super().__init__(timeout=120)
        self.token_cog = token_cog
        self.player = player
        self.bet = bet_amount

        # Hands
        self.player_hand = []
        self.dealer_hand = []

        self.message = None
        self.finished = False

    async def start(self, ctx):
        # Deal initial cards
        self.deck = self.generate_deck()
        random.shuffle(self.deck)

        self.player_hand = [self.deck.pop(), self.deck.pop()]
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]

        embed = self.build_embed(initial=True)
        self.message = await ctx.respond(embed=embed, view=self)

    def generate_deck(self):
        return [r + s for r in "23456789TJQKA" for s in "♠♥♦♣"]

    def hand_value(self, hand):
        value, aces = 0, 0
        for card in hand:
            rank = card[0]
            if rank in "JQKT":
                value += 10
            elif rank == "A":
                value += 11
                aces += 1
            else:
                value += int(rank)

        # Adjust for Aces
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value

    def build_embed(self, initial=False, reveal_dealer=False):
        pval = self.hand_value(self.player_hand)
        dval = self.hand_value(self.dealer_hand if reveal_dealer else [self.dealer_hand[0]])

        desc = f"**Your hand** ({pval}): {', '.join(self.player_hand)}\n"
        if reveal_dealer:
            desc += f"**Dealer hand** ({dval}): {', '.join(self.dealer_hand)}"
        else:
            desc += f"**Dealer hand** (?): {self.dealer_hand[0]}, ??"

        embed = discord.Embed(title="🃏 Blackjack", description=desc)

        if self.finished:
            embed.color = discord.Color.gold()
        else:
            embed.color = discord.Color.blue()

        return embed

    async def end_game(self, interaction):
        self.disable_all_buttons()
        self.finished = True

        player_val = self.hand_value(self.player_hand)
        dealer_val = self.hand_value(self.dealer_hand)

        # Dealer hits until 17+
        while dealer_val < 17:
            self.dealer_hand.append(self.deck.pop())
            dealer_val = self.hand_value(self.dealer_hand)

        result = ""
        payout = 0

        if player_val > 21:
            result = f"💥 You bust! Lose {self.bet} tokens."
        elif dealer_val > 21 or player_val > dealer_val:
            if player_val == 21 and len(self.player_hand) == 2:
                payout = int(self.bet * 1.5)
                result = f"🂡 Blackjack! You win {payout} tokens!"
            else:
                payout = self.bet * 2
                result = f"✅ You win! Earned {self.bet} tokens."
        elif player_val == dealer_val:
            payout = self.bet
            result = "🤝 It's a tie! Your bet is returned."
        else:
            result = f"❌ Dealer wins. You lost {self.bet} tokens."

        # Update balance
        self.token_cog.set_balance(self.player.id, self.token_cog.get_balance(self.player.id) + payout)

        embed = self.build_embed(reveal_dealer=True)
        embed.add_field(name="Result", value=result, inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

    def disable_all_buttons(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.success)
    async def hit_button(self, button, interaction: discord.Interaction):
        self.player_hand.append(self.deck.pop())
        if self.hand_value(self.player_hand) > 21:
            await self.end_game(interaction)
        else:
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.danger)
    async def stand_button(self, button, interaction: discord.Interaction):
        await self.end_game(interaction)


def setup(bot):
    bot.add_cog(TokenCog(bot))
