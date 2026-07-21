import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from cogs.settings_cog import get_setting


class StopView(discord.ui.View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=300)
        self.owner_id = owner_id
        self.stopped = False

    @discord.ui.button(label="⏹ Stop", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the person who started this can stop it.", ephemeral=True
            )
            return
        self.stopped = True
        button.disabled = True
        button.label = "⏹ Stopped"
        await interaction.response.edit_message(
            content="⏹ Mass ping stopped.", view=self
        )


class MassPingCog(commands.Cog, name="MassPing"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="massping", description="Spam ping a user until you press Stop.")
    @app_commands.describe(target="The user to spam ping")
    async def massping(self, interaction: discord.Interaction, target: discord.Member):
        # Block self-ping if the setting is off
        if target.id == interaction.user.id:
            if not get_setting(interaction.guild.id, "masspig_self"):
                await interaction.response.send_message(
                    "❌ You can't mass ping yourself.", ephemeral=True
                )
                return

        # Block pinging bots
        if target.bot:
            await interaction.response.send_message(
                "❌ You can't mass ping a bot.", ephemeral=True
            )
            return

        view = StopView(interaction.user.id)
        await interaction.response.send_message(
            f"🔔 Mass pinging {target.mention} — press **Stop** to end.",
            view=view
        )

        pending: list[discord.Message] = []

        try:
            while not view.stopped:
                msg = await interaction.channel.send(target.mention)
                pending.append(msg)
                await asyncio.sleep(0.8)

                # Delete oldest ping once we have a few queued up to keep the channel tidy
                if len(pending) >= 3:
                    try:
                        await pending.pop(0).delete()
                    except Exception:
                        pass

                if view.stopped:
                    break
        except Exception:
            pass

        # Clean up any leftover ping messages
        for msg in pending:
            try:
                await msg.delete()
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(MassPingCog(bot))
