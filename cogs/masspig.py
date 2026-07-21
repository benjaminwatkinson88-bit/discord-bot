import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import os

USER_SETTINGS_FILE = "data/user_settings.json"


def load_user_settings() -> dict:
    if os.path.exists(USER_SETTINGS_FILE):
        try:
            with open(USER_SETTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_user_settings(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(USER_SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_protected(user_id: int) -> bool:
    data = load_user_settings()
    return data.get(str(user_id), {}).get("massping_protected", False)


def toggle_protection(user_id: int) -> bool:
    data = load_user_settings()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {}
    new_val = not data[uid].get("massping_protected", False)
    data[uid]["massping_protected"] = new_val
    save_user_settings(data)
    return new_val


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
        # Block pinging bots
        if target.bot:
            await interaction.response.send_message(
                "❌ You can't mass ping a bot.", ephemeral=True
            )
            return

        # Check if target has protection enabled
        if is_protected(target.id):
            await interaction.response.send_message(
                f"❌ {target.display_name} has mass ping protection on.", ephemeral=True
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

    @app_commands.command(name="massprotect", description="Toggle whether others can mass ping you.")
    async def massprotect(self, interaction: discord.Interaction):
        new_val = toggle_protection(interaction.user.id)
        if new_val:
            await interaction.response.send_message(
                "🛡️ **Mass ping protection ON** — nobody can mass ping you.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "🔓 **Mass ping protection OFF** — you can be mass pinged.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(MassPingCog(bot))
