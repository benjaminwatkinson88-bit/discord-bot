import discord
from discord import app_commands
from discord.ext import commands
import json
import os

SETTINGS_FILE = "data/settings.json"

DEFAULTS = {
    "ai_ping_replies":    True,
    "ai_channel_replies": True,
    "xp_enabled":         True,
    "levelup_announce":   True,
    "fun_commands":       True,
    "games_enabled":      True,
    "gambling_enabled":   True,
}

LABELS = {
    "ai_ping_replies":    ("🤖", "AI Ping Replies",       "Bot replies when @mentioned"),
    "ai_channel_replies": ("💬", "AI Channel Replies",    "Bot replies in the set AI channel"),
    "xp_enabled":         ("⭐", "XP System",             "Members earn XP from chatting"),
    "levelup_announce":   ("📢", "Level-Up Alerts",       "Level-up messages posted in chat"),
    "fun_commands":       ("🎉", "Fun Commands",          "/joke, /roast, /ship, /8ball, /fortune etc."),
    "games_enabled":      ("🎮", "Games",                 "/hangman, /horsle, /racestart, /tictactoe, /rps"),
    "gambling_enabled":   ("🎰", "Gambling",              "/gamble and XP betting in /racestart"),
}


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_settings(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_setting(guild_id, key: str) -> bool:
    data = load_settings()
    return data.get(str(guild_id), {}).get(key, DEFAULTS.get(key, True))


def set_setting(guild_id, key: str, value: bool):
    data = load_settings()
    g = str(guild_id)
    if g not in data:
        data[g] = {}
    data[g][key] = value
    save_settings(data)


def toggle_setting(guild_id, key: str) -> bool:
    new_val = not get_setting(guild_id, key)
    set_setting(guild_id, key, new_val)
    return new_val


def require_setting(key: str):
    """app_commands.check decorator — blocks command if the setting is OFF for this guild."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.guild and not get_setting(interaction.guild.id, key):
            return False
        return True
    return app_commands.check(predicate)


def build_settings_embed(guild_id) -> discord.Embed:
    embed = discord.Embed(
        title="⚙️ Server Settings",
        description="Toggle features on or off for this server.\nOnly admins can change these.",
        color=discord.Color.blurple(),
    )
    for key, (icon, name, desc) in LABELS.items():
        val = get_setting(guild_id, key)
        status = "🟢 **ON**" if val else "🔴 **OFF**"
        embed.add_field(name=f"{icon} {name}", value=f"{desc}\n{status}", inline=True)
    return embed


class ToggleButton(discord.ui.Button):
    def __init__(self, key: str, icon: str, name: str, guild_id: int):
        val = get_setting(guild_id, key)
        super().__init__(
            label=name,
            emoji=icon,
            style=discord.ButtonStyle.success if val else discord.ButtonStyle.danger,
        )
        self.key = key
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ Only admins can change settings.", ephemeral=True
            )
            return
        new_val = toggle_setting(self.guild_id, self.key)
        self.style = discord.ButtonStyle.success if new_val else discord.ButtonStyle.danger
        embed = build_settings_embed(self.guild_id)
        await interaction.response.edit_message(embed=embed, view=self.view)


class SettingsView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        for key, (icon, name, _) in LABELS.items():
            self.add_item(ToggleButton(key, icon, name, guild_id))


class SettingsCog(commands.Cog, name="Settings"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="settings", description="[Admin] View and toggle bot features for this server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def settings(self, interaction: discord.Interaction):
        embed = build_settings_embed(interaction.guild.id)
        view = SettingsView(interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SettingsCog(bot))
