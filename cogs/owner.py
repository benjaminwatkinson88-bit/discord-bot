import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import re


# In-memory only: restarting the bot clears this temporary allow-list.
temporary_say_users: set[int] = set()

_INTERVAL_PART = re.compile(
    r"(\d+(?:\.\d+)?)"
    r"(milliseconds?|seconds?|minutes?|hours?|days?|weeks?|ms|s|m|h|d|w)",
    re.IGNORECASE,
)
_INTERVAL_MULTIPLIERS = {
    "ms": 0.001,
    "millisecond": 0.001,
    "milliseconds": 0.001,
    "s": 1,
    "second": 1,
    "seconds": 1,
    "m": 60,
    "minute": 60,
    "minutes": 60,
    "h": 3600,
    "hour": 3600,
    "hours": 3600,
    "d": 86400,
    "day": 86400,
    "days": 86400,
    "w": 604800,
    "week": 604800,
    "weeks": 604800,
}


def parse_interval(value: str) -> float:
    """Parse values such as 1s, 1m, 1h, 1d, or 1h30m into seconds."""
    compact = re.sub(r"\s+", "", value.strip().lower())
    if not compact:
        raise ValueError("interval cannot be empty")

    total = 0.0
    position = 0
    for match in _INTERVAL_PART.finditer(compact):
        if match.start() != position:
            raise ValueError("interval contains an unknown value")
        amount = float(match.group(1))
        unit = match.group(2).lower()
        total += amount * _INTERVAL_MULTIPLIERS[unit]
        position = match.end()

    if position != len(compact) or total <= 0:
        raise ValueError("interval must be greater than zero")
    return total


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
        self._mass_tasks: set[asyncio.Task] = set()

    async def cog_load(self):
        self._console_task = asyncio.create_task(self._read_console())
        print("[SAY] Type a Discord user ID in the host console to temporarily allow /say.")

    async def cog_unload(self):
        if self._console_task:
            self._console_task.cancel()
        for task in self._mass_tasks:
            task.cancel()

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
        interval="Time between repeats, e.g. 1s, 1m, 1h, 1d, or 1h30m",
        use_ai="Use the AI to create a unique response for each repeat",
        ai_instruction="What the AI should do differently at each sequence position",
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
        interval: str = "1s",
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
        try:
            send_interval = parse_interval(interval)
        except (TypeError, ValueError) as e:
            await interaction.followup.send(
                f"❌ Invalid interval. Use values like `1s`, `1m`, `1h`, `1d`, or `1h30m` ({e}).",
                ephemeral=True,
            )
            return

        ai_cog = self.bot.get_cog("AI") if use_ai else None
        if use_ai and not ai_cog:
            await interaction.followup.send("❌ AI is not available right now.", ephemeral=True)
            return

        base_message = message
        instruction = (
            ai_instruction or
            "Rewrite the message while preserving its meaning, making each sequence position distinct."
        ).strip()

        destination_name = "the current channel"

        # DM a user by ID
        if user is not None:
            try:
                uid = int(user.strip())
                target_user = interaction.client.get_user(uid) or await interaction.client.fetch_user(uid)
            except (ValueError, discord.NotFound, discord.Forbidden):
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
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
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

        async def build_message(index: int, previous_messages: list[str]) -> str:
            if not use_ai:
                return base_message[:2000]

            previous = ""
            if previous_messages:
                previous = (
                    "\nRecent earlier outputs to avoid repeating:\n"
                    + "\n".join(
                        f"{position}: {text}"
                        for position, text in previous_messages[-3:]
                    )
                )

            generated = await ai_cog.quick_ai(
                "Create exactly one final message from the original message below. "
                f"This is sequence item {index} of {send_count}. Use the item position to "
                "make it meaningfully unique and consistent with the requested progression. "
                "Return only the message, with no preamble or explanation.\n\n"
                f"Instruction: {instruction}\n"
                f"Original message: {base_message}"
                f"{previous}",
                system="You are a precise message editor creating ordered, distinct messages.",
                max_tokens=128,
            )
            if not generated:
                raise RuntimeError("The AI returned an empty message.")
            return generated[:2000]

        async def run_mass_send():
            sent = 0
            previous_messages = []
            try:
                for index in range(1, send_count + 1):
                    outgoing = await build_message(index, previous_messages)
                    await send_one(outgoing)
                    sent += 1
                    if use_ai:
                        previous_messages.append((index, outgoing))
                    if index < send_count:
                        await asyncio.sleep(send_interval)
            except asyncio.CancelledError:
                print(f"[SAY] Mass send cancelled after {sent}/{send_count} messages.")
            except Exception as e:
                print(f"[SAY] Mass send stopped after {sent}/{send_count} messages: {e}")

        if mass:
            task = asyncio.create_task(run_mass_send())
            self._mass_tasks.add(task)
            task.add_done_callback(self._mass_tasks.discard)
            await interaction.followup.send(
                f"✅ Started sending {send_count} messages to {destination_name} "
                f"with `{interval}` between them.",
                ephemeral=True,
            )
            return

        try:
            await send_one(await build_message(1, []))
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ I don't have permission to send to {destination_name}.",
                ephemeral=True,
            )
            return
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Discord rejected the send ({e}).", ephemeral=True)
            return
        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                await interaction.followup.send(
                    "❌ The Groq AI token quota has been reached. Please wait for it to reset.",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(f"❌ Couldn't generate the message: {e}", ephemeral=True)
            return

        await interaction.followup.send(f"✅ Sent to {destination_name}.", ephemeral=True)

    @say.error
    async def say_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            try:
                await interaction.response.send_message("no", ephemeral=True)
            except Exception:
                pass


async def setup(bot):
    await bot.add_cog(OwnerCog(bot))
