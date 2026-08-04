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
        channel="Channel to send the message in (defaults to current channel)",
    )
    @app_commands.check(is_owner)
    async def say(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: discord.TextChannel = None,
    ):
        target = channel or interaction.channel

        if target is None:
            await interaction.response.send_message(
                "❌ No channel found — specify one with the `channel` option.", ephemeral=True
            )
            return

        try:
            await target.send(message)
            where = target.mention if hasattr(target, "mention") else "the channel"
            await interaction.response.send_message(
                f"✅ Sent to {where}.", ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to send messages in that channel.", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Something went wrong: {e}", ephemeral=True
            )

    @say.error
    async def say_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message(
                "❌ This command is owner-only.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
