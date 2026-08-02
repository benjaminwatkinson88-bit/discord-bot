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
        # Allow commands to work when bot is installed as a personal/user app
        self.tree.allowed_installs = app_commands.AppInstallationType(guild=True, user=True)
        self.tree.allowed_contexts = app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True)

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
            "cogs.selftalk",
        ]
        for ext in extensions:
            try:
                await self.load_extension(ext)
                print(f"[OK] Loaded {ext}")
            except Exception as e:
                print(f"[ERROR] Failed to load {ext}: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")

        # Global sync only — required for user-install (personal app) to work.
        try:
            cmds = await self.tree.sync()
            print(f"Global sync: {len(cmds)} command(s)")
        except Exception as e:
            print(f"Global sync failed: {e}")

        # Clear any guild-specific commands left over from previous syncs (they cause duplicates).
        for guild in self.guilds:
            try:
                self.tree.clear_commands(guild=guild)
                await self.tree.sync(guild=guild)
                print(f"Cleared guild commands [{guild.name}]")
            except Exception as e:
                print(f"Failed to clear guild commands [{guild.name}]: {e}")

        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="/help | Powered by AI"
        )
        await self.change_presence(activity=activity)


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
