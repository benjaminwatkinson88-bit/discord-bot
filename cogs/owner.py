import discord
from discord import app_commands
from discord.ext import commands


async def is_owner(interaction: discord.Interaction) -> bool:
    app = await interaction.client.application_info()
    return interaction.user.id == app.owner.id


class OwnerCog(commands.Cog, name="Owner"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="say", description="Make the bot say something.")
    @app_commands.describe(
        message="What the bot should say",
        channel_id="Channel ID to send to (paste any channel ID — works from DMs too)",
        user="Username or user ID to DM (no need to share a server if you use their ID)",
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

            # Try as a numeric user ID first (works without a shared server)
            try:
                uid = int(user.strip().lstrip('<@!>'))
                target_user = interaction.client.get_user(uid) or await interaction.client.fetch_user(uid)
            except (ValueError, discord.NotFound):
                pass

            # Fall back: search cached users by username / display name
            if target_user is None:
                search = user.strip().lower()
                target_user = discord.utils.find(
                    lambda u: u.name.lower() == search or u.display_name.lower() == search,
                    interaction.client.users,
                )

            if target_user is None:
                await interaction.followup.send(
                    f"❌ Couldn't find a user matching **{user}**. "
                    "If they don't share a server with the bot, use their user ID instead.",
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
                await interaction.response.send_message(
                    "❌ This command is owner-only.", ephemeral=True
                )
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
