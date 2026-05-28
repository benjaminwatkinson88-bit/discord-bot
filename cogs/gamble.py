import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import json
import os
import math

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


def add_xp(guild_id, user_id, amount):
    data = load_data()
    g, u = str(guild_id), str(user_id)
    if g not in data:
        data[g] = {}
    if u not in data[g]:
        data[g][u] = {"xp": 0, "level": 0}
    data[g][u]["xp"] = max(0, data[g][u]["xp"] + amount)
    data[g][u]["level"] = int(math.sqrt(data[g][u]["xp"] / 100))
    save_data(data)


COIN_FRAMES = ["🪙", "✨", "🌀", "✨", "🪙"]


class GambleCog(commands.Cog, name="Gamble"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="gamble", description="Flip a coin and bet your XP. Double or nothing!")
    @app_commands.describe(amount="How much XP to bet (minimum 10)")
    async def gamble(self, interaction: discord.Interaction, amount: int):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        if amount < 10:
            await interaction.response.send_message("Minimum bet is **10 XP**.", ephemeral=True)
            return

        current_xp = get_xp(interaction.guild.id, interaction.user.id)
        if current_xp < amount:
            await interaction.response.send_message(
                f"You only have **{current_xp:,} XP** — not enough to bet **{amount:,} XP**.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"**{interaction.user.display_name}** bets **{amount:,} XP**...",
            color=discord.Color.yellow()
        )
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        # Animate the flip
        for frame in COIN_FRAMES:
            embed.description = f"**{interaction.user.display_name}** bets **{amount:,} XP**...\n\n{frame}"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.4)

        won = random.random() < 0.5
        side = random.choice(["Heads", "Tails"])

        if won:
            add_xp(interaction.guild.id, interaction.user.id, amount)
            new_xp = get_xp(interaction.guild.id, interaction.user.id)
            embed = discord.Embed(
                title="🪙 Coin Flip — WIN!",
                description=(
                    f"**{side}!** 🎉\n\n"
                    f"**{interaction.user.display_name}** won **+{amount:,} XP**!\n"
                    f"New balance: **{new_xp:,} XP**"
                ),
                color=discord.Color.green()
            )
        else:
            add_xp(interaction.guild.id, interaction.user.id, -amount)
            new_xp = get_xp(interaction.guild.id, interaction.user.id)
            embed = discord.Embed(
                title="🪙 Coin Flip — LOSS",
                description=(
                    f"**{side}!** 💸\n\n"
                    f"**{interaction.user.display_name}** lost **{amount:,} XP**.\n"
                    f"New balance: **{new_xp:,} XP**"
                ),
                color=discord.Color.red()
            )

        await msg.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(GambleCog(bot))
