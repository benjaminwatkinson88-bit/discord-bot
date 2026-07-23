import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio

SELFTALK_FILE = "data/selftalk.json"
MAX_TURNS = 12  # Max back-and-forths before pausing until a human speaks


def load_selftalk() -> dict:
    if os.path.exists(SELFTALK_FILE):
        try:
            with open(SELFTALK_FILE) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_selftalk(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(SELFTALK_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_selftalk_enabled(guild_id: int) -> bool:
    return load_selftalk().get(str(guild_id), {}).get("enabled", False)


def get_personality2(guild_id: int) -> str | None:
    return load_selftalk().get(str(guild_id), {}).get("personality2", None)


def get_selftalk_infinite(guild_id: int) -> bool:
    return load_selftalk().get(str(guild_id), {}).get("infinite", False)


def set_selftalk_enabled(guild_id: int, value: bool):
    data = load_selftalk()
    g = str(guild_id)
    if g not in data:
        data[g] = {}
    data[g]["enabled"] = value
    save_selftalk(data)


def set_selftalk_infinite(guild_id: int, value: bool):
    data = load_selftalk()
    g = str(guild_id)
    if g not in data:
        data[g] = {}
    data[g]["infinite"] = value
    save_selftalk(data)


def set_personality2(guild_id: int, personality: str):
    data = load_selftalk()
    g = str(guild_id)
    if g not in data:
        data[g] = {}
    data[g]["personality2"] = personality
    save_selftalk(data)


class SelfTalkCog(commands.Cog, name="SelfTalk"):
    def __init__(self, bot):
        self.bot = bot
        # Per-channel turn counts  {channel_id: int}
        self._turns: dict[int, int] = {}
        # Per-channel current persona index (0 = personality1, 1 = personality2)
        self._persona: dict[int, int] = {}
        # IDs of messages the bot sent as part of self-talk (to avoid double-triggering)
        self._selftalk_ids: set[int] = set()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        guild_id = message.guild.id
        channel_id = message.channel.id

        # If a human speaks, reset the turn counter for this channel
        if not message.author.bot:
            self._turns[channel_id] = 0
            return

        # Only react to the bot's own messages
        if message.author.id != self.bot.user.id:
            return

        # Don't double-trigger on messages we already sent as self-talk
        if message.id in self._selftalk_ids:
            return

        if not get_selftalk_enabled(guild_id):
            return

        # Enforce turn limit unless infinite mode is on
        turns = self._turns.get(channel_id, 0)
        if not get_selftalk_infinite(guild_id) and turns >= MAX_TURNS:
            return

        # Decide which personality responds next
        persona_index = self._persona.get(channel_id, 1)  # start with persona 2 replying to persona 1
        self._persona[channel_id] = 1 - persona_index  # flip for next time

        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            return

        from cogs.ai_cog import get_personality, DEFAULT_PERSONALITY

        if persona_index == 0:
            system = get_personality(guild_id)
        else:
            p2 = get_personality2(guild_id)
            if p2:
                system = (
                    f"You are a Discord bot with the following personality: {p2}. "
                    f"Always stay fully in character. Never break character or explain that you're an AI. "
                    f"Keep responses concise and fitting to your personality."
                )
            else:
                system = DEFAULT_PERSONALITY

        content = message.content
        if not content:
            content = "(the bot sent something with no text)"

        # Strip any bot mention from the content
        content = content.replace(f"<@{self.bot.user.id}>", "").replace(f"<@!{self.bot.user.id}>", "").strip()
        if not content:
            content = "Say something interesting."

        await asyncio.sleep(1.2)  # small pause so it feels like a conversation

        try:
            async with message.channel.typing():
                reply = await ai_cog.quick_ai(
                    content,
                    guild_id=guild_id,
                    system=system,
                )
                if len(reply) > 2000:
                    reply = reply[:1997] + "..."

            sent = await message.channel.send(reply)
            self._selftalk_ids.add(sent.id)

            # Keep the set from growing unboundedly
            if len(self._selftalk_ids) > 500:
                self._selftalk_ids.clear()

            self._turns[channel_id] = turns + 1

        except Exception as e:
            print(f"[SelfTalk] Error generating reply: {e}")

    @app_commands.command(name="selftalk", description="[Admin] Toggle the bot talking to itself.")
    @app_commands.describe(toggle="Turn self-talk on or off")
    @app_commands.choices(toggle=[
        app_commands.Choice(name="On", value="on"),
        app_commands.Choice(name="Off", value="off"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def selftalk(self, interaction: discord.Interaction, toggle: app_commands.Choice[str]):
        enabled = toggle.value == "on"
        set_selftalk_enabled(interaction.guild.id, enabled)

        if enabled:
            p2 = get_personality2(interaction.guild.id)
            warning = ""
            if not p2:
                warning = "\n\n⚠️ No second personality set yet — use `/setpersonality2` to give the second voice a character."
            embed = discord.Embed(
                title="🗣️ Self-Talk ON",
                description=(
                    f"The bot will now respond to its own messages using two personalities.\n"
                    f"It pauses after **{MAX_TURNS}** exchanges and waits for a human to speak first."
                    f"{warning}"
                ),
                color=discord.Color.green(),
            )
        else:
            embed = discord.Embed(
                title="🔇 Self-Talk OFF",
                description="The bot will no longer talk to itself.",
                color=discord.Color.red(),
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setpersonality2", description="[Admin] Set the second personality used during self-talk.")
    @app_commands.describe(personality="Describe the second personality (e.g. 'cynical philosopher who hates everything')")
    @app_commands.checks.has_permissions(administrator=True)
    async def setpersonality2(self, interaction: discord.Interaction, personality: str):
        set_personality2(interaction.guild.id, personality)
        embed = discord.Embed(
            title="🧠 Second Personality Set",
            description=f"The second self-talk personality is now:\n> {personality}",
            color=discord.Color.green(),
        )
        embed.set_footer(text=f"Set by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="selftalkinfinity", description="[Admin] Toggle whether self-talk runs infinitely or stops after a few exchanges.")
    @app_commands.describe(toggle="On = run forever, Off = stop after 12 exchanges")
    @app_commands.choices(toggle=[
        app_commands.Choice(name="On", value="on"),
        app_commands.Choice(name="Off", value="off"),
    ])
    @app_commands.checks.has_permissions(administrator=True)
    async def selftalkinfinity(self, interaction: discord.Interaction, toggle: app_commands.Choice[str]):
        enabled = toggle.value == "on"
        set_selftalk_infinite(interaction.guild.id, enabled)

        if enabled:
            embed = discord.Embed(
                title="♾️ Infinite Self-Talk ON",
                description="The bot will now respond to itself forever with no turn limit.\nUse `/selftalk off` or `/selftalkinfinity off` to stop it.",
                color=discord.Color.og_blurple(),
            )
        else:
            embed = discord.Embed(
                title="🔢 Infinite Self-Talk OFF",
                description=f"The bot will pause after **{MAX_TURNS}** exchanges and wait for a human to speak.",
                color=discord.Color.red(),
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @selftalk.error
    @setpersonality2.error
    @selftalkinfinity.error
    async def admin_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Administrator** permission to use this command.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(SelfTalkCog(bot))
