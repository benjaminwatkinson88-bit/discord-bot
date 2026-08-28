import discord
from discord import app_commands
from discord.ext import commands
import asyncio


# In-memory only: restarting the bot clears this temporary allow-list.
temporary_say_users: set[int] = set()


async def is_owner(interaction: discord.Interaction) -> bool:
    app = await interaction.client.application_info()
    return interaction.user.id == app.owner.id or interaction.user.id in temporary_say_users


async def is_app_owner(interaction: discord.Interaction) -> bool:
    app = await interaction.client.application_info()
    return interaction.user.id == app.owner.id


class OwnerCog(commands.Cog, name="Owner"):
    def __init__(self, bot):
        self.bot = bot
        self._console_task = None

    async def cog_load(self):
        self._console_task = asyncio.create_task(self._read_console())
        print("[SAY] Type a Discord user ID in the host console to temporarily allow /say.")

    async def cog_unload(self):
        if self._console_task:
            self._console_task.cancel()

    async def _read_console(self):
        while True:
            try:
                line = await asyncio.to_thread(input)
            except (EOFError, asyncio.CancelledError):
                return

            user_id = line.strip()
            if user_id.isdigit():
                temporary_say_users.add(int(user_id))
                print(f"[SAY] Temporarily allowed user ID {user_id}.")
            elif user_id:
                print("[SAY] Enter a numeric Discord user ID.")

    @app_commands.command(
        name="sayallow",
        description="Temporarily allow a user to use /say until restart.",
    )
    @app_commands.describe(user_id="The numeric Discord user ID to allow")
    @app_commands.check(is_app_owner)
    async def sayallow(self, interaction: discord.Interaction, user_id: str):
        try:
            allowed_id = int(user_id.strip())
        except ValueError:
            await interaction.response.send_message(
                "❌ Enter a numeric Discord user ID.", ephemeral=True
            )
            return

        temporary_say_users.add(allowed_id)
        await interaction.response.send_message(
            f"✅ User ID `{allowed_id}` can use `/say` until the bot restarts.",
            ephemeral=True,
        )

    @sayallow.error
    async def sayallow_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            try:
                await interaction.response.send_message("no", ephemeral=True)
            except Exception:
                pass

    @app_commands.command(
        name="saydeny",
        description="Remove a user's temporary /say access.",
    )
    @app_commands.describe(user_id="The numeric Discord user ID to remove")
    @app_commands.check(is_app_owner)
    async def saydeny(self, interaction: discord.Interaction, user_id: str):
        try:
            removed_id = int(user_id.strip())
        except ValueError:
            await interaction.response.send_message(
                "❌ Enter a numeric Discord user ID.", ephemeral=True
            )
            return

        temporary_say_users.discard(removed_id)
        await interaction.response.send_message(
            f"✅ Removed temporary `/say` access for `{removed_id}`.",
            ephemeral=True,
        )

    @saydeny.error
    async def saydeny_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            try:
                await interaction.response.send_message("no", ephemeral=True)
            except Exception:
                pass

    @app_commands.command(name="say", description="Make the bot say something.")
    @app_commands.describe(
        message="What the bot should say",
        channel_id="Channel ID to send to (paste any channel ID — works from DMs too)",
        user="User ID to DM (no need to share a server)",
    )
    @app_commands.check(is_owner)
    async def say(
        self,
        interaction: discord.Interaction,
        message: str,
        channel_id: str = None,
        user: str = None,
    ):
        await interaction.response.defer(ephemeral=True)

        # DM a user by username or ID
        if user is not None:
            target_user = None

            # Look up by user ID
            try:
                uid = int(user.strip())
                target_user = interaction.client.get_user(uid) or await interaction.client.fetch_user(uid)
            except (ValueError, discord.NotFound):
                await interaction.followup.send(
                    "❌ Couldn't find that user. Make sure you're providing a valid user ID.",
                    ephemeral=True,
                )
                return

            try:
                await target_user.send(message)
                await interaction.followup.send(
                    f"✅ DM sent to **{target_user.display_name}**.", ephemeral=True
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Couldn't DM that user (they may have DMs disabled).", ephemeral=True
                )
            return

        # Send to a channel by ID
        if channel_id is not None:
            try:
                cid = int(channel_id.strip())
            except ValueError:
                await interaction.followup.send(
                    "❌ That doesn't look like a valid channel ID.", ephemeral=True
                )
                return
            channel = interaction.client.get_channel(cid) or await interaction.client.fetch_channel(cid)
            if channel is None:
                await interaction.followup.send(
                    "❌ Couldn't find that channel.", ephemeral=True
                )
                return
            try:
                await channel.send(message)
                await interaction.followup.send(
                    f"✅ Sent to **{getattr(channel, 'name', str(cid))}**.", ephemeral=True
                )
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ I don't have permission to send messages there.", ephemeral=True
                )
            return

        # Fall back: current channel (only works inside a server/group)
        if interaction.channel is not None:
            try:
                await interaction.channel.send(message)
                await interaction.followup.send("✅ Sent.", ephemeral=True)
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ I don't have permission to send messages here.", ephemeral=True
                )
        else:
            await interaction.followup.send(
                "❌ Provide a `channel_id` or `user` when using this from DMs.", ephemeral=True
            )

    @say.error
    async def say_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            try:
                await interaction.response.send_message("no", ephemeral=True)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
