import discord
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

    async def setup_hook(self):
        extensions = [
            "cogs.fun",
            "cogs.extra_fun",
            "cogs.utility",
            "cogs.titles",
            "cogs.levels",
            "cogs.ai_cog",
            "cogs.help_cog",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"Loaded {ext}")
            except Exception as e:
                print(f"Failed to load {ext}: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

        # Wipe stale global commands from Discord (the source of duplicates)
        saved = self.tree.get_commands()
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        print("Cleared global commands.")

        # Restore commands to tree
        for cmd in saved:
            self.tree.add_command(cmd)

        # Sync to each guild instantly (guild commands appear immediately)
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                print(f"Synced to: {guild.name}")
            except Exception as e:
                print(f"Failed to sync to guild {guild.id}: {e}")

        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="/help | Powered by AI"
        )
        await self.change_presence(activity=activity)

    async def on_guild_join(self, guild: discord.Guild):
        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        except Exception:
            pass


bot = DiscordBot()

token = os.environ.get("DISCORD_TOKEN")
if not token:
    print("ERROR: DISCORD_TOKEN is not set. Please add it to Secrets.")
    exit(1)

bot.run(token)
