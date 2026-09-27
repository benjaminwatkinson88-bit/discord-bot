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
        mass="Repeat the final message multiple times",
        repeats="How many times to send it (any positive number)",
        interval="Seconds between repeats (1-30)",
        use_ai="Use the AI once to transform the message before sending",
        ai_instruction="What the AI should do with the message",
    )
    @app_commands.check(is_owner)
    async def say(
        self,
        interaction: discord.Interaction,
        message: str,
        channel_id: str = None,
        user: str = None,
        mass: bool = False,
        repeats: int = 1,
        interval: app_commands.Range[float, 1.0, 30.0] = 1.0,
        use_ai: bool = False,
        ai_instruction: str = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if repeats < 1:
            await interaction.followup.send(
                "❌ `repeats` must be a positive number.",
                ephemeral=True,
            )
            return

        send_count = int(repeats) if mass else 1
        send_interval = float(interval)

        if use_ai:
            ai_cog = self.bot.get_cog("AI")
            if not ai_cog:
                await interaction.followup.send("❌ AI is not available right now.", ephemeral=True)
                return

            instruction = (ai_instruction or "Rewrite the message while preserving its meaning.").strip()
            try:
                message = await ai_cog.quick_ai(
                    "Transform the following message according to the instruction. "
                    "Return only the final message, with no preamble or explanation.\n\n"
                    f"Instruction: {instruction}\n"
                    f"Message: {message}",
                    system="You are a precise message editor. Follow the requested transformation.",
                    max_tokens=128,
                )
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    await interaction.followup.send(
                        "❌ The Groq AI token quota has been reached. Please wait for it to reset.",
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(f"❌ Couldn't transform the message: {e}", ephemeral=True)
                return

            if not message:
                await interaction.followup.send("❌ The AI returned an empty message.", ephemeral=True)
                return

        if len(message) > 2000:
            message = message[:1997] + "..."

        destination_name = "the current channel"

        # DM a user by ID
        if user is not None:
            try:
                uid = int(user.strip())
                target_user = interaction.client.get_user(uid) or await interaction.client.fetch_user(uid)
            except (ValueError, discord.NotFound):
                await interaction.followup.send(
                    "❌ Couldn't find that user. Make sure you're providing a valid user ID.",
                    ephemeral=True,
                )
                return

            async def send_one(text: str):
                await target_user.send(text)

            destination_name = f"**{target_user.display_name}**"

        # Send to a channel by ID
        elif channel_id is not None:
            try:
                cid = int(channel_id.strip())
            except ValueError:
                await interaction.followup.send(
                    "❌ That doesn't look like a valid channel ID.", ephemeral=True
                )
                return
            try:
                channel = interaction.client.get_channel(cid) or await interaction.client.fetch_channel(cid)
            except (discord.NotFound, discord.Forbidden):
                channel = None
            if channel is None:
                await interaction.followup.send(
                    "❌ Couldn't find that channel.", ephemeral=True
                )
                return

            async def send_one(text: str):
                await channel.send(text)

            destination_name = f"**{getattr(channel, 'name', str(cid))}**"

        # Fall back: current channel (only works inside a server/group)
        elif interaction.channel is None:
            await interaction.followup.send(
                "❌ Provide a `channel_id` or `user` when using this from DMs.", ephemeral=True
            )
            return
        else:
            async def send_one(text: str):
                await interaction.channel.send(text)

        sent = 0
        try:
            for index in range(send_count):
                await send_one(message)
                sent += 1
                if index < send_count - 1:
                    await asyncio.sleep(send_interval)
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ I don't have permission to send to {destination_name}. "
                f"Sent {sent} of {send_count}.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as e:
            await interaction.followup.send(
                f"❌ Discord rejected the send ({e}). Sent {sent} of {send_count}.",
                ephemeral=True,
            )
            return

        if send_count == 1:
            await interaction.followup.send(f"✅ Sent to {destination_name}.", ephemeral=True)
        else:
            await interaction.followup.send(
                f"✅ Sent {sent} copies to {destination_name} "
                f"with {send_interval:g}s between messages.",
                ephemeral=True,
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
