import discord
from discord import app_commands
from discord.ext import commands
import os
import time

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

SYNC_LOCK_FILE = "data/.sync_lock"
SYNC_LOCK_TTL = 45  # seconds — prevents two instances from double-syncing


def should_sync() -> bool:
    os.makedirs("data", exist_ok=True)
    now = time.time()
    try:
        if os.path.exists(SYNC_LOCK_FILE):
            with open(SYNC_LOCK_FILE) as f:
                last = float(f.read().strip())
            if now - last < SYNC_LOCK_TTL:
                return False  # Another instance just synced
    except Exception:
        pass
    with open(SYNC_LOCK_FILE, "w") as f:
        f.write(str(now))
    return True


class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self):
        extensions = [
            "cogs.fun",
            "cogs.extra_fun",
            "cogs.utility",
            "cogs.titles",
            "cogs.levels",
            "cogs.ai_cog",
            "cogs.help_cog",
            "cogs.hangman",
            "cogs.horsle",
            "cogs.horsle_game",
            "cogs.gamble",
            "cogs.settings_cog",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Loaded {ext}")
            except Exception as e:
                print(f"Failed to load {ext}: {e}")

        if should_sync():
            try:
                await self.tree.sync()
                print("Commands synced.")
            except Exception as e:
                print(f"Sync failed: {e}")
        else:
            print("Sync skipped — another instance synced recently.")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="/help | Powered by AI"
        )
        await self.change_presence(activity=activity)

    async def on_guild_join(self, guild: discord.Guild):
        print(f"Joined new guild: {guild.name}")


bot = DiscordBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        msg = "❌ This feature is disabled in this server. An admin can enable it with `/settings`."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        except Exception:
            pass
        return
    if isinstance(error, app_commands.MissingPermissions):
        msg = "❌ You need **Administrator** permission to use this command."
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        except Exception:
            pass
        return
    print(f"Unhandled app command error: {error}")


token = os.environ.get("DISCORD_TOKEN")
if not token:
    print("ERROR: DISCORD_TOKEN is not set. Please add it to Secrets.")
    exit(1)

bot.run(token)
