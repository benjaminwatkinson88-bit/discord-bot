import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
import random
import math
import time

DATA_FILE = "data/levels.json"
XP_COOLDOWN = 60
XP_MIN = 15
XP_MAX = 25


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_level(xp: int) -> int:
    return int(math.sqrt(xp / 100))


def xp_for_level(level: int) -> int:
    return level ** 2 * 100


def xp_to_next(xp: int) -> tuple:
    level = get_level(xp)
    current_floor = xp_for_level(level)
    next_floor = xp_for_level(level + 1)
    progress = xp - current_floor
    needed = next_floor - current_floor
    return level, progress, needed


def get_user_data(data: dict, guild_id: int, user_id: int) -> dict:
    g = str(guild_id)
    u = str(user_id)
    if g not in data:
        data[g] = {}
    if u not in data[g]:
        data[g][u] = {"xp": 0, "level": 0}
    return data[g][u]


def rank_in_guild(data: dict, guild_id: int, user_id: int) -> tuple:
    g = str(guild_id)
    if g not in data:
        return 1, 1
    guild_data = data[g]
    sorted_users = sorted(guild_data.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
    for i, (uid, _) in enumerate(sorted_users):
        if uid == str(user_id):
            return i + 1, len(sorted_users)
    return len(sorted_users) + 1, len(sorted_users)


class LevelsCog(commands.Cog, name="Levels"):
    def __init__(self, bot):
        self.bot = bot
        self._lock = asyncio.Lock()
        self._cooldowns: dict = {}

    def _on_cooldown(self, guild_id: int, user_id: int) -> bool:
        """Check if user is on cooldown. If not, set cooldown and return False."""
        key = (guild_id, user_id)
        now = time.time()
        last = self._cooldowns.get(key, 0)
        if now - last < XP_COOLDOWN:
            return True
        # Only update cooldown if check passed (not on cooldown)
        self._cooldowns[key] = now
        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        from cogs.settings_cog import get_setting
        if not get_setting(message.guild.id, "xp_enabled"):
            return

        if self._on_cooldown(message.guild.id, message.author.id):
            return

        xp_gain = random.randint(XP_MIN, XP_MAX)

        async with self._lock:
            data = load_data()
            user = get_user_data(data, message.guild.id, message.author.id)
            old_level = get_level(user["xp"])
            user["xp"] += xp_gain
            new_level = get_level(user["xp"])
            user["level"] = new_level
            save_data(data)

        if new_level > old_level and get_setting(message.guild.id, "levelup_announce"):
            embed = discord.Embed(
                title="⬆️ Level Up!",
                description=f"**{message.author.display_name}** just reached **Level {new_level}**! 🎉",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            await message.channel.send(embed=embed)

    @app_commands.command(name="rank", description="Check your XP and level rank.")
    @app_commands.describe(member="The member to check (defaults to you)")
    async def rank(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user

        data = load_data()
        user = get_user_data(data, interaction.guild.id, member.id)
        xp = user["xp"]
        level, progress, needed = xp_to_next(xp)
        position, total = rank_in_guild(data, interaction.guild.id, member.id)

        bar_filled = round((progress / needed) * 10) if needed > 0 else 10
        bar = "█" * bar_filled + "░" * (10 - bar_filled)

        embed = discord.Embed(
            title=f"📊 {member.display_name}'s Rank",
            color=member.color or discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="Server Rank", value=f"**#{position}** / {total}", inline=True)
        embed.add_field(name="Total XP", value=f"**{xp:,}** XP", inline=True)
        embed.add_field(
            name=f"Progress to Level {level + 1}",
            value=f"`{bar}` {progress:,} / {needed:,} XP",
            inline=False
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="See the top members by XP in this server.")
    async def leaderboard(self, interaction: discord.Interaction):
        data = load_data()
        g = str(interaction.guild.id)

        if g not in data or not data[g]:
            await interaction.response.send_message(
                "No one has earned any XP yet — start chatting!", ephemeral=True
            )
            return

        sorted_users = sorted(data[g].items(), key=lambda x: x[1].get("xp", 0), reverse=True)[:10]

        embed = discord.Embed(
            title=f"🏆 {interaction.guild.name} Leaderboard",
            color=discord.Color.gold()
        )

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (uid, udata) in enumerate(sorted_users):
            xp = udata.get("xp", 0)
            level = get_level(xp)
            medal = medals[i] if i < 3 else f"`#{i + 1}`"
            member = interaction.guild.get_member(int(uid))
            name = member.display_name if member else f"Unknown ({uid})"
            lines.append(f"{medal} **{name}** — Level {level} · {xp:,} XP")

        embed.description = "\n".join(lines)
        embed.set_footer(text="XP is earned by chatting (1 message per minute)")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="givexp", description="[Admin] Give XP to a member.")
    @app_commands.describe(member="The member to give XP to", amount="Amount of XP to give")
    @app_commands.checks.has_permissions(administrator=True)
    async def givexp(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return

        async with self._lock:
            data = load_data()
            user = get_user_data(data, interaction.guild.id, member.id)
            old_level = get_level(user["xp"])
            user["xp"] += amount
            new_level = get_level(user["xp"])
            user["level"] = new_level
            save_data(data)

        leveled = f" — they leveled up to **Level {new_level}**! 🎉" if new_level > old_level else ""
        await interaction.response.send_message(
            f"✅ Gave **{amount:,} XP** to {member.mention}{leveled}", ephemeral=False
        )

    @app_commands.command(name="resetxp", description="[Admin] Reset a member's XP to zero.")
    @app_commands.describe(member="The member to reset")
    @app_commands.checks.has_permissions(administrator=True)
    async def resetxp(self, interaction: discord.Interaction, member: discord.Member):
        async with self._lock:
            data = load_data()
            g, u = str(interaction.guild.id), str(member.id)
            if g in data and u in data[g]:
                data[g][u] = {"xp": 0, "level": 0}
                save_data(data)

        await interaction.response.send_message(
            f"✅ Reset XP for {member.mention}.", ephemeral=True
        )

    @givexp.error
    @resetxp.error
    async def admin_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Administrator** permission to use this command.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(LevelsCog(bot))
