import discord
from discord import app_commands
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


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
        self._synced = False

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
            "cogs.betrace",
            "cogs.gamble",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Loaded {ext}")
            except Exception as e:
                print(f"Failed to load {ext}: {e}")

        # Sync commands once here — not in on_ready, which fires on every reconnect
        try:
            await self.tree.sync()
            print("Synced all commands globally.")
        except Exception as e:
            print(f"Global sync failed: {e}")

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
