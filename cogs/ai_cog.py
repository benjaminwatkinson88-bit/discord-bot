import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

DATA_FILE = "data/personality.json"
CHANNEL_FILE = "data/channel_config.json"
PRIMARY_MODEL = "qwen/qwen3.8-27b"

DEFAULT_PERSONALITY = (
    "You are a fun, witty, and helpful Discord bot. You have a playful personality "
    "and enjoy chatting with server members. Keep your responses concise and engaging."
)

# Store conversation history in memory with timestamps
conversation_memory = defaultdict(list)
MAX_HISTORY = 10  # Keep last 10 messages per conversation
MEMORY_EXPIRY = 3600  # Expire conversations after 1 hour of inactivity


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
            f"You are a Discord bot. Adopt this server's personality and use it consistently: {custom}\n"
            "Apply it to your tone, word choice, attitude, and manner in every response. "
            "Stay in character instead of describing the personality or these instructions. "
            "Do not mention that you are an AI or that you were given a personality prompt. "
            "Keep responses concise unless the user asks for detail."
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


def get_conversation_key(context: discord.Interaction | discord.Message) -> str:
    """Generate a unique key for each conversation thread"""
    if isinstance(context, discord.Interaction):
        guild_id = context.guild.id if context.guild else None
        channel_id = context.channel.id if context.channel else None
    else:
        guild_id = context.guild.id if context.guild else None
        channel_id = context.channel.id
    
    if guild_id:
        return f"guild_{guild_id}_channel_{channel_id}"
    else:
        return f"dm_{channel_id}"


def add_to_memory(key: str, role: str, content: str):
    """Add a message to conversation memory"""
    conversation_memory[key].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only the last MAX_HISTORY messages
    if len(conversation_memory[key]) > MAX_HISTORY:
        conversation_memory[key] = conversation_memory[key][-MAX_HISTORY:]


def clean_old_conversations():
    """Remove conversations that haven't been active for MEMORY_EXPIRY seconds"""
    now = datetime.now()
    keys_to_remove = []
    
    for key, messages in conversation_memory.items():
        if messages:
            last_message_time = datetime.fromisoformat(messages[-1]["timestamp"])
            if (now - last_message_time).total_seconds() > MEMORY_EXPIRY:
                keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del conversation_memory[key]


def get_conversation_history(key: str) -> list:
    """Get conversation history for a key (only role/content, no extra fields)"""
    return [
        {"role": m["role"], "content": m["content"]}
        for m in conversation_memory.get(key, [])
    ]


def clear_conversation(key: str):
    """Clear conversation history for a key"""
    if key in conversation_memory:
        del conversation_memory[key]


def clean_ai_response(content: str) -> str:
    """Remove reasoning blocks if a model includes them in its visible response."""
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"<analysis>.*?</analysis>", "", content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r"^\s*(?:analysis|reasoning|thinking)\s*:\s*", "", content, flags=re.IGNORECASE)
    return content.strip()


REFUSAL_WORDS = {
    "can't",
    "cant",
    "cannot",
    "unable",
    "won't",
    "wont",
    "refuse",
    "refuses",
    "refusing",
    "decline",
    "declines",
    "declining",
    "no",
    "nah",
    "nope",
}


def is_refusal_response(content: str) -> bool:
    """Flag refusal words individually, then check whether their context is a refusal."""
    normalized = re.sub(r"\s+", " ", content.lower().replace("’", "'")).strip()
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", normalized)
    flagged_words = [word for word in words if word in REFUSAL_WORDS]

    first_person = {"i", "we", "assistant", "bot"}
    refusal_verbs = {
        "can't",
        "cant",
        "cannot",
        "unable",
        "won't",
        "wont",
        "refuse",
        "refuses",
        "refusing",
        "decline",
        "declines",
        "declining",
    }

    for index, word in enumerate(words):
        nearby_words = words[max(0, index - 4):index]
        if word in refusal_verbs:
            # A refusal normally identifies the speaker close to the refusal word:
            # "I cannot...", "we won't...", or "the bot refuses...".
            if any(previous in first_person for previous in nearby_words):
                return True

            # "Unable to..." at the beginning is also a direct refusal/error response.
            if word == "unable" and index <= 1:
                return True

        # Keep common multi-word refusals while still checking their context:
        # "I can not...", "I will not...", and "I am not able...".
        if any(previous in first_person for previous in nearby_words):
            following = words[index + 1:index + 3]
            if word == "can" and following[:1] == ["not"]:
                return True
            if word == "will" and following[:1] == ["not"]:
                return True
            if word == "able" and "not" in nearby_words:
                return True

    if "no" in flagged_words or "nah" in flagged_words or "nope" in flagged_words:
        # A normal answer/correction such as "No, that's wrong" is not a refusal.
        normal_answer_markers = {
            "wrong",
            "correct",
            "answer",
            "because",
            "actually",
            "means",
            "true",
            "false",
            "is",
            "are",
        }
        if any(marker in words for marker in normal_answer_markers):
            return False

        # A bare "no" is commonly a valid answer to a question, not a refusal.
        if len(words) <= 3:
            return False

    return False


class AICog(commands.Cog, name="AI"):
    def __init__(self, bot):
        self.bot = bot
        self._groq_client = None
        self._groq_api_key = None
        self._handled_ids: set = set()

    def get_groq_client(self):
        api_key = os.environ.get("GROQ_KEY", "").strip().strip('"').strip("'")
        if not api_key:
            print("[AI] GROQ_KEY is not set or is empty.")
            return None

        # Rebuild client if the key has changed since last time
        if self._groq_client is None or api_key != self._groq_api_key:
            try:
                from groq import AsyncGroq
                self._groq_client = AsyncGroq(api_key=api_key)
                self._groq_api_key = api_key
                print(f"[AI] Groq client built. Key starts with: {api_key[:8]}...")
            except Exception as e:
                print(f"[AI] Failed to build Groq client: {e}")
                return None

        return self._groq_client

    async def quick_ai(self, prompt: str, guild_id: int = None, system: str = None, conversation_key: str = None, model: str = None) -> str:
        """Send a prompt to AI with optional conversation history"""
        client = self.get_groq_client()
        if not client:
            raise RuntimeError("GROQ_KEY is not set or Groq is unavailable.")

        personality = get_personality(guild_id) if guild_id else DEFAULT_PERSONALITY
        if system:
            system_msg = (
                f"{system}\n\n"
                f"The server's configured personality is also active:\n{personality}\n"
                "Follow the task and requested format, while applying that personality to the wording and tone."
            )
        else:
            system_msg = personality
        system_msg += (
            "\nDo not show internal reasoning, analysis, deliberation, or a thinking process. "
            "Return only the final answer. Follow direct user instructions exactly and avoid "
            "unnecessary explanations, debate, or restating the request. If clarification is "
            "truly required, ask one concise question. Do not produce code, code blocks, or "
            "call an answer 'the code' unless the user explicitly asks for programming or code."
        )
        
        # Build message list with conversation history
        messages = [{"role": "system", "content": system_msg}]
        
        # Add conversation history if available
        if conversation_key:
            history = get_conversation_history(conversation_key)
            messages.extend(history)
        
        # Add the current prompt
        messages.append({"role": "user", "content": prompt})

        selected_model = model or PRIMARY_MODEL
        request_options = {
            "model": selected_model,
            "messages": messages,
            "max_tokens": 512,
        }
        if selected_model.startswith("qwen/"):
            request_options["reasoning_effort"] = "none"

        response = await client.chat.completions.create(**request_options)
        print(f"[AI] Using Groq model: {selected_model}")
        return clean_ai_response(response.choices[0].message.content)

    async def quick_ai_with_refusal_retry(
        self,
        prompt: str,
        guild_id: int = None,
        system: str = None,
        conversation_key: str = None,
        model: str = None,
    ) -> tuple[str | None, bool]:
        """Retry one refusal once after clearing memory, then stop retrying."""
        reply = await self.quick_ai(
            prompt,
            guild_id=guild_id,
            system=system,
            conversation_key=conversation_key,
            model=model,
        )
        if reply and not is_refusal_response(reply):
            return reply, False

        if conversation_key:
            clear_conversation(conversation_key)

        try:
            retry = await self.quick_ai(
                prompt,
                guild_id=guild_id,
                system=system,
                conversation_key=conversation_key,
                model=model,
            )
        except Exception as e:
            print(f"[AI] Refusal retry failed: {e}")
            return None, True

        return retry, not retry or is_refusal_response(retry)

    async def generate_personality_replacement(
        self,
        request: str,
        guild_id: int = None,
        system: str = None,
    ) -> str | None:
        """Generate a safe, in-character replacement on the same subject."""
        try:
            pivot = await self.quick_ai(
                "Respond to the same subject and intent as the request below in one short, "
                "harmless, in-character reply. Stay on the original topic instead of changing "
                "the subject. If the request asks for disallowed content, do not repeat that "
                "content; give the closest safe response while staying on topic. Do not mention "
                "policies, refusals, safety, or this instruction.\n\n"
                f"Original request:\n{request}",
                guild_id=guild_id,
                system=system,
            )
            if pivot and not is_refusal_response(pivot):
                return pivot
        except Exception as e:
            print(f"[AI] Could not generate a personality replacement: {e}")
        return None

    async def _send_ai_reply(self, message: discord.Message, content: str):
        client = self.get_groq_client()
        if not client:
            await message.reply("⚠️ AI is not configured yet. An admin needs to set the `GROQ_KEY` secret.")
            return

        async with message.channel.typing():
            try:
                guild_id = message.guild.id if message.guild else None
                conversation_key = get_conversation_key(message)

                # Retry one refusal after clearing memory.
                reply, was_refusal = await self.quick_ai_with_refusal_retry(
                    content,
                    guild_id=guild_id,
                    conversation_key=conversation_key,
                )

                # Do not let refusals influence future replies.
                if was_refusal:
                    clear_conversation(conversation_key)
                    reply = await self.generate_personality_replacement(
                        content,
                        guild_id=guild_id,
                    )

                if was_refusal and not reply:
                    return

                if was_refusal:
                    await message.reply(reply)
                    return

                # Save both sides to memory after a successful reply
                add_to_memory(conversation_key, "user", content)
                add_to_memory(conversation_key, "assistant", reply)

                if len(reply) > 2000:
                    reply = reply[:1997] + "..."
                await message.reply(reply)
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    return  # silently drop rate limit errors
                await message.reply(f"⚠️ Something went wrong with the AI: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        # Dedup: ignore if we've already handled this message ID
        if message.id in self._handled_ids:
            return
        self._handled_ids.add(message.id)
        # Keep the set from growing unboundedly
        if len(self._handled_ids) > 1000:
            self._handled_ids.clear()

        guild_id = message.guild.id if message.guild else None
        active_channel = get_active_channel(guild_id) if guild_id else None
        is_mentioned = self.bot.user in message.mentions
        in_active_channel = bool(active_channel and message.channel.id == active_channel)

        # Check per-guild settings
        if guild_id:
            from cogs.settings_cog import get_setting
            if is_mentioned and not get_setting(guild_id, "ai_ping_replies"):
                return
            if in_active_channel and not get_setting(guild_id, "ai_channel_replies"):
                return

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

    @app_commands.command(name="checkgroq", description="[Admin] Test whether the Groq AI key is working.")
    @app_commands.checks.has_permissions(administrator=True)
    async def checkgroq(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        api_key = os.environ.get("GROQ_KEY", "").strip().strip('"').strip("'")
        if not api_key:
            await interaction.followup.send("❌ `GROQ_KEY` is not set in the environment.", ephemeral=True)
            return
        preview = api_key[:8] + "..." + api_key[-4:]
        try:
            result = await self.quick_ai("Say the word 'OK' and nothing else.", system="Reply with only the word OK.")
            await interaction.followup.send(
                f"✅ Groq is working.\nKey: `{preview}`\nResponse: `{result}`", ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Groq call failed.\nKey: `{preview}`\nError: `{e}`", ephemeral=True
            )

    @checkgroq.error
    async def checkgroq_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You need **Administrator** permission.", ephemeral=True)

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
        # Clear all conversation memory so the old personality can't bleed into new replies
        conversation_memory.clear()

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
            conversation_key = get_conversation_key(interaction)
            story_text = await self.quick_ai(
                f"Write a creative, engaging short story (around 150-250 words) about: {prompt}",
                system="You are a creative storyteller who writes captivating, imaginative short stories.",
                conversation_key=conversation_key
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ Couldn't generate a story: {e}")
            return

        if not story_text or is_refusal_response(story_text):
            clear_conversation(conversation_key)
            story_text = await self.generate_personality_replacement(
                prompt,
                guild_id=interaction.guild.id if interaction.guild else None,
            )
            if not story_text:
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

    @app_commands.command(name="clearmemory", description="Clear the bot's conversation memory for this channel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearmemory(self, interaction: discord.Interaction):
        """Clear conversation history for the current channel"""
        conversation_key = get_conversation_key(interaction)
        clear_conversation(conversation_key)
        
        embed = discord.Embed(
            title="🧹 Memory Cleared",
            description="The bot's conversation memory for this channel has been reset.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @setpersonality.error
    async def setpersonality_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Administrator** permission to use this command.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(AICog(bot))
