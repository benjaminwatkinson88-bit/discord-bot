import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import json
import os
import math
from cogs.settings_cog import require_setting

DATA_FILE = "data/levels.json"


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_xp(guild_id, user_id):
    data = load_data()
    return data.get(str(guild_id), {}).get(str(user_id), {}).get("xp", 0)


def change_xp(guild_id, user_id, amount):
    data = load_data()
    g, u = str(guild_id), str(user_id)
    if g not in data:
        data[g] = {}
    if u not in data[g]:
        data[g][u] = {"xp": 0, "level": 0}
    data[g][u]["xp"] = max(0, data[g][u]["xp"] + amount)
    data[g][u]["level"] = int(math.sqrt(data[g][u]["xp"] / 100))
    save_data(data)


# ──────────────────────────────────────────────
# GAME: Coin Flip
# ──────────────────────────────────────────────
class CoinFlipView(discord.ui.View):
    def __init__(self, user_id, guild_id, amount):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.guild_id = guild_id
        self.amount = amount

    async def resolve(self, interaction, picked):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"🪙 Flipping...", embed=None, view=self
        )
        frames = ["🪙", "✨", "🌀", "✨", "🪙"]
        for frame in frames:
            await asyncio.sleep(0.4)
            try:
                await interaction.edit_original_response(content=frame)
            except Exception:
                pass

        result = random.choice(["Heads", "Tails"])
        won = result.lower() == picked.lower()
        if won:
            change_xp(self.guild_id, self.user_id, self.amount)
            new_xp = get_xp(self.guild_id, self.user_id)
            text = f"🟢 **{result}!** You picked {picked} — **correct!**\n+{self.amount:,} XP → Balance: **{new_xp:,} XP**"
        else:
            change_xp(self.guild_id, self.user_id, -self.amount)
            new_xp = get_xp(self.guild_id, self.user_id)
            text = f"🔴 **{result}!** You picked {picked} — **wrong.**\n-{self.amount:,} XP → Balance: **{new_xp:,} XP**"
        try:
            await interaction.edit_original_response(content=text, view=None)
        except Exception:
            pass

    @discord.ui.button(label="Heads", style=discord.ButtonStyle.primary, emoji="👑")
    async def heads(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        self.stop()
        await self.resolve(interaction, "Heads")

    @discord.ui.button(label="Tails", style=discord.ButtonStyle.secondary, emoji="🪙")
    async def tails(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        self.stop()
        await self.resolve(interaction, "Tails")


# ──────────────────────────────────────────────
# GAME: High or Low Dice
# ──────────────────────────────────────────────
class DiceView(discord.ui.View):
    def __init__(self, user_id, guild_id, amount):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.guild_id = guild_id
        self.amount = amount

    DICE_EMOJI = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

    async def resolve(self, interaction, picked_high):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="🎲 Rolling...", embed=None, view=self)
        for _ in range(4):
            await asyncio.sleep(0.35)
            try:
                await interaction.edit_original_response(content=f"🎲 {random.choice(self.DICE_EMOJI)}")
            except Exception:
                pass

        roll = random.randint(1, 6)
        is_high = roll >= 4
        won = (picked_high and is_high) or (not picked_high and not is_high)
        label = "High (4-6)" if picked_high else "Low (1-3)"

        if won:
            change_xp(self.guild_id, self.user_id, self.amount)
            new_xp = get_xp(self.guild_id, self.user_id)
            text = f"🟢 Rolled **{self.DICE_EMOJI[roll-1]} {roll}** — {label} was right!\n+{self.amount:,} XP → Balance: **{new_xp:,} XP**"
        else:
            change_xp(self.guild_id, self.user_id, -self.amount)
            new_xp = get_xp(self.guild_id, self.user_id)
            text = f"🔴 Rolled **{self.DICE_EMOJI[roll-1]} {roll}** — {label} was wrong.\n-{self.amount:,} XP → Balance: **{new_xp:,} XP**"
        try:
            await interaction.edit_original_response(content=text, view=None)
        except Exception:
            pass

    @discord.ui.button(label="High (4-6)", style=discord.ButtonStyle.danger, emoji="⬆️")
    async def high(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        self.stop()
        await self.resolve(interaction, True)

    @discord.ui.button(label="Low (1-3)", style=discord.ButtonStyle.primary, emoji="⬇️")
    async def low(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        self.stop()
        await self.resolve(interaction, False)


# ──────────────────────────────────────────────
# GAME: Slots
# ──────────────────────────────────────────────
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍇", "⭐", "💎"]
SLOT_WEIGHTS = [35, 25, 20, 12, 5, 3]


def spin_slots():
    return random.choices(SLOT_SYMBOLS, weights=SLOT_WEIGHTS, k=3)


def slots_payout(symbols, amount):
    if symbols[0] == symbols[1] == symbols[2]:
        sym = symbols[0]
        if sym == "💎":
            return amount * 10, "💎 JACKPOT! Triple diamonds!"
        if sym == "⭐":
            return amount * 5, "⭐ Triple stars!"
        return amount * 3, f"Triple {sym}!"
    if symbols[0] == symbols[1] or symbols[1] == symbols[2]:
        return amount // 2, "Partial match — half back."
    if "💎" in symbols:
        return amount // 4, "Diamond saves a little."
    return -amount, "No match. Nothing."


class SlotsView(discord.ui.View):
    def __init__(self, user_id, guild_id, amount):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.guild_id = guild_id
        self.amount = amount

    @discord.ui.button(label="Pull the Lever!", style=discord.ButtonStyle.success, emoji="🎰")
    async def pull(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        button.disabled = True
        self.stop()
        await interaction.response.edit_message(content="🎰 Spinning...", embed=None, view=self)

        for _ in range(5):
            s = spin_slots()
            await asyncio.sleep(0.4)
            try:
                await interaction.edit_original_response(content=f"🎰  {s[0]} | {s[1]} | {s[2]}")
            except Exception:
                pass

        final = spin_slots()
        net, desc = slots_payout(final, self.amount)
        change_xp(self.guild_id, self.user_id, net)
        new_xp = get_xp(self.guild_id, self.user_id)
        sign = "🟢" if net >= 0 else "🔴"
        xp_str = f"+{net:,}" if net >= 0 else f"{net:,}"
        try:
            await interaction.edit_original_response(
                content=f"🎰  **{final[0]} | {final[1]} | {final[2]}**\n\n{sign} {desc}\n{xp_str} XP → Balance: **{new_xp:,} XP**",
                view=None,
            )
        except Exception:
            pass


# ──────────────────────────────────────────────
# GAME: Red or Black (card draw)
# ──────────────────────────────────────────────
CARDS = (
    [("A", "♠"), ("2", "♠"), ("3", "♠"), ("4", "♠"), ("5", "♠"), ("6", "♠"),
     ("7", "♠"), ("8", "♠"), ("9", "♠"), ("10", "♠"), ("J", "♠"), ("Q", "♠"), ("K", "♠")] +
    [("A", "♣"), ("2", "♣"), ("3", "♣"), ("4", "♣"), ("5", "♣"), ("6", "♣"),
     ("7", "♣"), ("8", "♣"), ("9", "♣"), ("10", "♣"), ("J", "♣"), ("Q", "♣"), ("K", "♣")] +
    [("A", "♥"), ("2", "♥"), ("3", "♥"), ("4", "♥"), ("5", "♥"), ("6", "♥"),
     ("7", "♥"), ("8", "♥"), ("9", "♥"), ("10", "♥"), ("J", "♥"), ("Q", "♥"), ("K", "♥")] +
    [("A", "♦"), ("2", "♦"), ("3", "♦"), ("4", "♦"), ("5", "♦"), ("6", "♦"),
     ("7", "♦"), ("8", "♦"), ("9", "♦"), ("10", "♦"), ("J", "♦"), ("Q", "♦"), ("K", "♦")]
)
RED_SUITS = {"♥", "♦"}


class CardView(discord.ui.View):
    def __init__(self, user_id, guild_id, amount):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.guild_id = guild_id
        self.amount = amount

    async def resolve(self, interaction, picked_red):
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content="🂠 Drawing...", embed=None, view=self)
        await asyncio.sleep(1)

        val, suit = random.choice(CARDS)
        is_red = suit in RED_SUITS
        won = (picked_red and is_red) or (not picked_red and not is_red)
        color_word = "Red" if is_red else "Black"
        picked_word = "Red" if picked_red else "Black"

        if won:
            change_xp(self.guild_id, self.user_id, self.amount)
            new_xp = get_xp(self.guild_id, self.user_id)
            text = f"🟢 Drew **{val}{suit}** ({color_word}) — you picked {picked_word}, correct!\n+{self.amount:,} XP → Balance: **{new_xp:,} XP**"
        else:
            change_xp(self.guild_id, self.user_id, -self.amount)
            new_xp = get_xp(self.guild_id, self.user_id)
            text = f"🔴 Drew **{val}{suit}** ({color_word}) — you picked {picked_word}, wrong.\n-{self.amount:,} XP → Balance: **{new_xp:,} XP**"
        try:
            await interaction.edit_original_response(content=text, view=None)
        except Exception:
            pass

    @discord.ui.button(label="Red", style=discord.ButtonStyle.danger, emoji="♥️")
    async def red(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        self.stop()
        await self.resolve(interaction, True)

    @discord.ui.button(label="Black", style=discord.ButtonStyle.secondary, emoji="♠️")
    async def black(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        self.stop()
        await self.resolve(interaction, False)


# ──────────────────────────────────────────────
# GAME: Number Guess
# ──────────────────────────────────────────────
class NumberView(discord.ui.View):
    def __init__(self, user_id, guild_id, amount):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.guild_id = guild_id
        self.amount = amount
        self.secret = random.randint(1, 5)
        for n in range(1, 6):
            self.add_item(NumberButton(n, self))


class NumberButton(discord.ui.Button):
    def __init__(self, number, nview):
        super().__init__(label=str(number), style=discord.ButtonStyle.secondary)
        self.number = number
        self.nview = nview

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.nview.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        self.nview.stop()
        for item in self.nview.children:
            item.disabled = True
            if hasattr(item, "number") and item.number == self.nview.secret:
                item.style = discord.ButtonStyle.success

        won = self.number == self.nview.secret
        if won:
            payout = self.nview.amount * 4
            change_xp(self.nview.guild_id, self.nview.user_id, payout)
            new_xp = get_xp(self.nview.guild_id, self.nview.user_id)
            text = f"🟢 You guessed **{self.number}** — correct! 4× payout!\n+{payout:,} XP → Balance: **{new_xp:,} XP**"
        else:
            change_xp(self.nview.guild_id, self.nview.user_id, -self.nview.amount)
            new_xp = get_xp(self.nview.guild_id, self.nview.user_id)
            text = f"🔴 You guessed **{self.number}** — it was **{self.nview.secret}**.\n-{self.nview.amount:,} XP → Balance: **{new_xp:,} XP**"
        await interaction.response.edit_message(content=text, embed=None, view=self.nview)


# ──────────────────────────────────────────────
# GAME PICKER VIEW
# ──────────────────────────────────────────────
class GamePickerView(discord.ui.View):
    def __init__(self, user_id, guild_id, amount):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.guild_id = guild_id
        self.amount = amount

    async def start_game(self, interaction, view, description):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not your game!", ephemeral=True)
            return
        self.stop()
        await interaction.response.edit_message(content=description, embed=None, view=view)

    @discord.ui.button(label="Coin Flip", style=discord.ButtonStyle.primary, emoji="🪙", row=0)
    async def coin(self, interaction, button):
        view = CoinFlipView(self.user_id, self.guild_id, self.amount)
        await self.start_game(interaction, view, "🪙 **Coin Flip** — Pick heads or tails!")

    @discord.ui.button(label="High / Low Dice", style=discord.ButtonStyle.primary, emoji="🎲", row=0)
    async def dice(self, interaction, button):
        view = DiceView(self.user_id, self.guild_id, self.amount)
        await self.start_game(interaction, view, "🎲 **High or Low?** — Guess the dice roll range!")

    @discord.ui.button(label="Slots", style=discord.ButtonStyle.primary, emoji="🎰", row=1)
    async def slots(self, interaction, button):
        view = SlotsView(self.user_id, self.guild_id, self.amount)
        await self.start_game(interaction, view, "🎰 **Slots** — Pull the lever and hope for the best!")

    @discord.ui.button(label="Red or Black", style=discord.ButtonStyle.primary, emoji="🃏", row=1)
    async def card(self, interaction, button):
        view = CardView(self.user_id, self.guild_id, self.amount)
        await self.start_game(interaction, view, "🃏 **Red or Black?** — Draw a card and call the colour!")

    @discord.ui.button(label="Number Guess (1-5)", style=discord.ButtonStyle.primary, emoji="🔢", row=2)
    async def number(self, interaction, button):
        view = NumberView(self.user_id, self.guild_id, self.amount)
        await self.start_game(interaction, view, "🔢 **Number Guess** — Pick 1–5. Correct = 4× your bet!")


# ──────────────────────────────────────────────
# COG
# ──────────────────────────────────────────────
class GambleCog(commands.Cog, name="Gamble"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gamble", description="Pick a gambling game and bet your XP!")
    @app_commands.describe(amount="How much XP to bet (minimum 10)")
    @require_setting("gambling_enabled")
    async def gamble(self, interaction: discord.Interaction, amount: int):
        if not interaction.guild:
            await interaction.response.send_message("This only works in a server.", ephemeral=True)
            return
        if amount < 10:
            await interaction.response.send_message("Minimum bet is **10 XP**.", ephemeral=True)
            return

        current_xp = get_xp(interaction.guild.id, interaction.user.id)
        if current_xp < amount:
            await interaction.response.send_message(
                f"You only have **{current_xp:,} XP** — can't bet **{amount:,} XP**.",
                ephemeral=True,
            )
            return

        view = GamePickerView(interaction.user.id, interaction.guild.id, amount)
        embed = discord.Embed(
            title="🎲 Gambling Den",
            description=(
                f"**Bet:** {amount:,} XP\n\n"
                "Pick a game below:"
            ),
            color=discord.Color.dark_gold(),
        )
        embed.add_field(name="🪙 Coin Flip", value="Pick heads or tails. 50/50. Double or nothing.", inline=False)
        embed.add_field(name="🎲 High / Low Dice", value="Guess if the roll lands high (4-6) or low (1-3).", inline=False)
        embed.add_field(name="🎰 Slots", value="Match symbols. Triple 💎 = 10× jackpot.", inline=False)
        embed.add_field(name="🃏 Red or Black", value="Draw a card and guess the colour.", inline=False)
        embed.add_field(name="🔢 Number Guess", value="Pick 1–5. Only a 20% chance — but pays 4×.", inline=False)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(GambleCog(bot))
