import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio

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
            "cogs.settings_cog",   # load first — other cogs import from it
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
            "cogs.masspig",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"[OK] Loaded {ext}")
            except Exception as e:
                print(f"[ERROR] Failed to load {ext}: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

        # Clear any old globally-registered commands (removes stale ones like old /masspig)
        try:
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            print("Cleared global commands")
        except Exception as e:
            print(f"Global clear failed: {e}")

        # Sync to each guild immediately — guild commands appear within seconds, no duplicates
        for guild in self.guilds:
            try:
                self.tree.copy_global_to(guild=guild)
                guild_cmds = await self.tree.sync(guild=guild)
                print(f"Guild sync [{guild.name}]: {len(guild_cmds)} command(s)")
            except Exception as e:
                print(f"Guild sync failed for {guild.name}: {e}")

        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="/help | Powered by AI"
        )
        await self.change_presence(activity=activity)

    async def on_guild_join(self, guild: discord.Guild):
        print(f"Joined new guild: {guild.name}")
        # Sync commands to the new guild immediately
        try:
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Synced to new guild: {guild.name}")
        except Exception as e:
            print(f"Sync failed for new guild {guild.name}: {e}")


bot = DiscordBot()


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        msg = "❌ This command is disabled."
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
    print("ERROR: DISCORD_TOKEN is not set.")
    raise SystemExit(1)

try:
    bot.run(token, log_handler=None)
except discord.LoginFailure:
    print("ERROR: Invalid token. Check DISCORD_TOKEN in your Railway environment variables.")
    raise SystemExit(1)
except discord.PrivilegedIntentsRequired:
    print("ERROR: Message Content Intent not enabled. Go to Discord Developer Portal -> Bot -> Privileged Gateway Intents and enable it.")
    raise SystemExit(1)
except Exception as e:
    print(f"ERROR: Bot crashed: {e}")
    raise
