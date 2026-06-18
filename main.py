import discord
from discord import app_commands
from discord.ext import commands
import os
import hashlib
import json

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

FINGERPRINT_FILE = "data/.sync_fingerprint"


def get_fingerprint(extensions: list) -> str:
    h = hashlib.md5()
    for ext in sorted(extensions):
        path = ext.replace(".", "/") + ".py"
        if os.path.exists(path):
            h.update(str(os.path.getmtime(path)).encode())
        h.update(ext.encode())
    return h.hexdigest()


def read_fingerprint() -> str:
    try:
        with open(FINGERPRINT_FILE) as f:
            return f.read().strip()
    except Exception:
        return ""


def write_fingerprint(fp: str):
    os.makedirs("data", exist_ok=True)
    with open(FINGERPRINT_FILE, "w") as f:
        f.write(fp)


class DiscordBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )
        self.tree.allowed_installs = app_commands.AppInstallationType(
            guild=True, user=True
        )
        self.tree.allowed_contexts = app_commands.AppCommandContext(
            guild=True, dm_channel=True, private_channel=True
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

        # Only sync if cog files have changed since the last sync.
        # Discord keeps commands permanently — re-syncing on every restart
        # is what causes commands to disappear when two instances compete.
        current_fp = get_fingerprint(extensions)
        stored_fp = read_fingerprint()

        if current_fp != stored_fp:
            try:
                await self.tree.sync()
                write_fingerprint(current_fp)
                print("Commands synced (cogs changed).")
            except Exception as e:
                print(f"Sync failed: {e}")
        else:
            print("Commands unchanged — skipped sync.")

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

token = os.environ.get("DISCORD_TOKEN")
if not token:
    print("ERROR: DISCORD_TOKEN is not set. Please add it to Secrets.")
    exit(1)

bot.run(token)
