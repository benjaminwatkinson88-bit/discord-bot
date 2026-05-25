import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio

DATA_FILE = "data/title_config.json"

DEFAULT_KEYWORDS = {
    "red": "🔥",
    "blue": "💧",
    "green": "🌿",
    "gold": "⭐",
    "silver": "⚔️",
    "purple": "💜",
    "black": "🌑",
    "white": "⬜",
    "pink": "🌸",
    "yellow": "☀️",
    "orange": "🍊",
    "admin": "👑",
    "owner": "💎",
    "mod": "🛡️",
    "moderator": "🛡️",
    "staff": "🔧",
    "helper": "💚",
    "vip": "✨",
    "booster": "🚀",
    "member": "🌀",
    "new": "🌱",
    "veteran": "🏅",
    "legend": "🦁",
    "elite": "⚡",
    "pro": "🎯",
    "developer": "💻",
    "dev": "💻",
    "artist": "🎨",
    "music": "🎵",
    "gamer": "🎮",
    "bot": "🤖",
}


def load_config() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(config: dict):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_keyword_map(guild_id: int) -> dict:
    config = load_config()
    guild_key = str(guild_id)
    if guild_key in config:
        merged = dict(DEFAULT_KEYWORDS)
        merged.update(config[guild_key])
        return merged
    return dict(DEFAULT_KEYWORDS)


def get_base_name(member: discord.Member) -> str:
    name = member.display_name
    if name.startswith("[") and "]" in name:
        name = name[name.index("]") + 1:].strip()
    return name


def get_role_title(member: discord.Member, keyword_map: dict):
    roles = sorted(
        [r for r in member.roles if r.name != "@everyone"],
        key=lambda r: r.position,
        reverse=True
    )
    for role in roles:
        role_name_lower = role.name.lower()
        for keyword, emoji in keyword_map.items():
            if keyword.lower() in role_name_lower:
                return role.name, keyword, emoji
    return None, None, None


async def update_member_title(member: discord.Member, keyword_map: dict = None):
    if member.bot:
        return False
    if keyword_map is None:
        keyword_map = get_keyword_map(member.guild.id)

    role_name, keyword, emoji = get_role_title(member, keyword_map)
    base_name = get_base_name(member)

    if role_name:
        label = f"{keyword}{emoji}"
        new_nick = f"[{label}] {base_name}"
        if len(new_nick) > 32:
            new_nick = new_nick[:32]
    else:
        new_nick = base_name if member.nick else None

    try:
        current = member.nick or ""
        desired = new_nick or ""
        if current != desired:
            await member.edit(nick=new_nick)
        return True
    except discord.Forbidden:
        return False
    except Exception:
        return False


class TitlesCog(commands.Cog, name="Titles"):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.roles != after.roles:
            keyword_map = get_keyword_map(after.guild.id)
            await update_member_title(after, keyword_map)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.name != after.name:
            keyword_map = get_keyword_map(after.guild.id)
            for member in after.members:
                if not member.bot:
                    await update_member_title(member, keyword_map)
                    await asyncio.sleep(0.5)

    @app_commands.command(name="settitleall", description="[Admin] Set titles for all members based on their roles.")
    @app_commands.checks.has_permissions(administrator=True)
    async def settitleall(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        keyword_map = get_keyword_map(interaction.guild.id)

        updated = 0
        failed = 0
        skipped = 0

        members = [m for m in interaction.guild.members if not m.bot]
        await interaction.followup.send(
            f"⏳ Updating titles for **{len(members)}** members... This may take a moment.",
            ephemeral=True
        )

        for member in members:
            success = await update_member_title(member, keyword_map)
            if success:
                updated += 1
            else:
                failed += 1
            await asyncio.sleep(0.4)

        embed = discord.Embed(title="✅ Title Update Complete", color=discord.Color.green())
        embed.add_field(name="Updated", value=str(updated), inline=True)
        embed.add_field(name="Failed (no permission)", value=str(failed), inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="settitle", description="[Admin] Set the title for a specific member.")
    @app_commands.describe(member="The member to update")
    @app_commands.checks.has_permissions(administrator=True)
    async def settitle(self, interaction: discord.Interaction, member: discord.Member):
        keyword_map = get_keyword_map(interaction.guild.id)
        success = await update_member_title(member, keyword_map)

        if success:
            role_name, keyword, emoji = get_role_title(member, keyword_map)
            if role_name:
                await interaction.response.send_message(
                    f"✅ Updated title for **{member.display_name}**: `[{keyword}{emoji}]`",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ No matching title keyword found for **{member.display_name}**'s roles. Title cleared.",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                f"❌ Could not update **{member.display_name}**'s nickname. I may lack permission (e.g., server owner).",
                ephemeral=True
            )

    @app_commands.command(name="removetitle", description="[Admin] Remove the title from a specific member.")
    @app_commands.describe(member="The member whose title to remove")
    @app_commands.checks.has_permissions(administrator=True)
    async def removetitle(self, interaction: discord.Interaction, member: discord.Member):
        base_name = get_base_name(member)
        try:
            await member.edit(nick=base_name if member.nick else None)
            await interaction.response.send_message(
                f"✅ Removed title from **{member.display_name}**.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"❌ I don't have permission to change **{member.display_name}**'s nickname.", ephemeral=True
            )

    @app_commands.command(name="titlekeywords", description="[Admin] View current keyword → emoji mappings.")
    @app_commands.checks.has_permissions(administrator=True)
    async def titlekeywords(self, interaction: discord.Interaction):
        keyword_map = get_keyword_map(interaction.guild.id)

        lines = [f"`{kw}` → {em}" for kw, em in sorted(keyword_map.items())]
        chunks = []
        chunk = []
        for line in lines:
            chunk.append(line)
            if len(chunk) >= 20:
                chunks.append("\n".join(chunk))
                chunk = []
        if chunk:
            chunks.append("\n".join(chunk))

        embed = discord.Embed(
            title="🏷️ Title Keyword Mappings",
            description=chunks[0] if chunks else "No keywords configured.",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Use /addkeyword and /removekeyword to customize.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="addkeyword", description="[Admin] Add a custom keyword → emoji mapping.")
    @app_commands.describe(keyword="The keyword to match in role names", emoji="The emoji to assign")
    @app_commands.checks.has_permissions(administrator=True)
    async def addkeyword(self, interaction: discord.Interaction, keyword: str, emoji: str):
        config = load_config()
        guild_key = str(interaction.guild.id)
        if guild_key not in config:
            config[guild_key] = {}
        config[guild_key][keyword.lower()] = emoji
        save_config(config)
        await interaction.response.send_message(
            f"✅ Added mapping: `{keyword.lower()}` → {emoji}", ephemeral=True
        )

    @app_commands.command(name="removekeyword", description="[Admin] Remove a keyword mapping.")
    @app_commands.describe(keyword="The keyword to remove")
    @app_commands.checks.has_permissions(administrator=True)
    async def removekeyword(self, interaction: discord.Interaction, keyword: str):
        config = load_config()
        guild_key = str(interaction.guild.id)
        kw_lower = keyword.lower()

        removed = False
        if guild_key in config and kw_lower in config[guild_key]:
            del config[guild_key][kw_lower]
            save_config(config)
            removed = True
        elif kw_lower in DEFAULT_KEYWORDS:
            if guild_key not in config:
                config[guild_key] = {}
            config[guild_key][kw_lower] = None
            save_config(config)
            removed = True

        if removed:
            await interaction.response.send_message(
                f"✅ Removed keyword mapping for `{kw_lower}`.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"❌ Keyword `{kw_lower}` not found.", ephemeral=True
            )

    @settitleall.error
    @settitle.error
    @removetitle.error
    @titlekeywords.error
    @addkeyword.error
    @removekeyword.error
    async def admin_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Administrator** permission to use this command.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(TitlesCog(bot))
