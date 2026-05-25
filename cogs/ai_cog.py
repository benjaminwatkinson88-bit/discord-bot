import discord
from discord import app_commands
from discord.ext import commands
import os
import json

DATA_FILE = "data/personality.json"
CHANNEL_FILE = "data/channel_config.json"

DEFAULT_PERSONALITY = (
    "You are a fun, witty, and helpful Discord bot. You have a playful personality "
    "and enjoy chatting with server members. Keep your responses concise and engaging."
)


def load_personalities() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_personalities(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_personality(guild_id: int) -> str:
    data = load_personalities()
    custom = data.get(str(guild_id))
    if custom:
        return (
            f"You are a Discord bot with the following personality: {custom}. "
            f"Always stay fully in character. Never break character or explain that you're an AI. "
            f"Keep responses concise and fitting to your personality."
        )
    return DEFAULT_PERSONALITY


def load_channels() -> dict:
    if os.path.exists(CHANNEL_FILE):
        try:
            with open(CHANNEL_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_channels(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(CHANNEL_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_active_channel(guild_id: int):
    return load_channels().get(str(guild_id))


def set_active_channel(guild_id: int, channel_id: int | None):
    data = load_channels()
    if channel_id is None:
        data.pop(str(guild_id), None)
    else:
        data[str(guild_id)] = channel_id
    save_channels(data)


class AICog(commands.Cog, name="AI"):
    def __init__(self, bot):
        self.bot = bot
        self._groq_client = None

    def get_groq_client(self):
        if self._groq_client is not None:
            return self._groq_client

        api_key = os.environ.get("GROQ_KEY")
        if not api_key:
            return None

        try:
            from groq import AsyncGroq
            self._groq_client = AsyncGroq(api_key=api_key)
            return self._groq_client
        except Exception:
            return None

    async def quick_ai(self, prompt: str, guild_id: int = None, system: str = None) -> str:
        client = self.get_groq_client()
        if not client:
            raise RuntimeError("GROQ_KEY is not set or Groq is unavailable.")

        system_msg = system or (get_personality(guild_id) if guild_id else DEFAULT_PERSONALITY)

        response = await client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
        )
        return response.choices[0].message.content.strip()

    async def _send_ai_reply(self, message: discord.Message, content: str):
        client = self.get_groq_client()
        if not client:
            await message.reply("⚠️ AI is not configured yet. An admin needs to set the `GROQ_KEY` secret.")
            return

        async with message.channel.typing():
            try:
                guild_id = message.guild.id if message.guild else None
                reply = await self.quick_ai(content, guild_id=guild_id)
                if len(reply) > 2000:
                    reply = reply[:1997] + "..."
                await message.reply(reply)
            except Exception as e:
                await message.reply(f"⚠️ Something went wrong with the AI: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        guild_id = message.guild.id if message.guild else None

        active_channel = get_active_channel(guild_id) if guild_id else None
        in_active_channel = active_channel and message.channel.id == active_channel

        is_mentioned = self.bot.user in message.mentions

        if not is_mentioned and not in_active_channel:
            return

        content = (
            message.content
            .replace(f"<@{self.bot.user.id}>", "")
            .replace(f"<@!{self.bot.user.id}>", "")
            .strip()
        )
        if not content:
            content = "Hello! Say something to me."

        await self._send_ai_reply(message, content)

    @app_commands.command(name="channel", description="[Admin] Set a channel for the bot to reply to all messages in.")
    @app_commands.describe(channel="The channel to activate (leave empty to disable)")
    @app_commands.checks.has_permissions(administrator=True)
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if channel is None:
            current = get_active_channel(interaction.guild.id)
            if current:
                set_active_channel(interaction.guild.id, None)
                embed = discord.Embed(
                    title="🔕 AI Channel Disabled",
                    description="The bot will no longer reply to all messages in a channel.\nIt will still respond when pinged.",
                    color=discord.Color.red()
                )
            else:
                embed = discord.Embed(
                    title="ℹ️ No Active Channel",
                    description="There is no active AI channel set. Provide a channel to enable it.",
                    color=discord.Color.blurple()
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        set_active_channel(interaction.guild.id, channel.id)

        embed = discord.Embed(
            title="✅ AI Channel Set",
            description=f"The bot will now reply to **every message** in {channel.mention}.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Run /channel with no argument to disable. Set by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @channel.error
    async def channel_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Administrator** permission to use this command.", ephemeral=True
            )

    @app_commands.command(name="setpersonality", description="[Admin] Change the bot's AI personality for this server.")
    @app_commands.describe(personality="Describe the bot's personality (e.g. 'sarcastic pirate who loves memes')")
    @app_commands.checks.has_permissions(administrator=True)
    async def setpersonality(self, interaction: discord.Interaction, personality: str):
        data = load_personalities()
        data[str(interaction.guild.id)] = personality
        save_personalities(data)

        self._groq_client = None

        embed = discord.Embed(
            title="🧠 Personality Updated",
            description=f"The bot's personality has been changed to:\n> {personality}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Changed by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="personality", description="View the bot's current AI personality.")
    async def personality(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id if interaction.guild else None
        current = get_personality(guild_id) if guild_id else DEFAULT_PERSONALITY

        embed = discord.Embed(
            title="🧠 Current Bot Personality",
            description=current,
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="story", description="Generate an AI story based on your prompt!")
    @app_commands.describe(prompt="What should the story be about?")
    async def story(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()

        client = self.get_groq_client()
        if not client:
            await interaction.followup.send("⚠️ AI is not configured. The `GROQ_KEY` secret needs to be set.")
            return

        try:
            story_text = await self.quick_ai(
                f"Write a creative, engaging short story (around 150-250 words) about: {prompt}",
                system="You are a creative storyteller who writes captivating, imaginative short stories.",
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ Couldn't generate a story: {e}")
            return

        if len(story_text) > 4096:
            story_text = story_text[:4093] + "..."

        embed = discord.Embed(
            title=f"📖 Story: {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
            description=story_text,
            color=discord.Color.teal()
        )
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    @setpersonality.error
    async def setpersonality_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Administrator** permission to use this command.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(AICog(bot))
