import discord
from discord import app_commands
from discord.ext import commands
import random
from cogs.settings_cog import require_setting

WORDS = [
    "python", "discord", "elephant", "umbrella", "jazz", "rhythm", "sphinx",
    "volcano", "oxygen", "blanket", "crystal", "dolphin", "eclipse", "falcon",
    "gravity", "horizon", "island", "jungle", "kingdom", "lantern", "marble",
    "nebula", "octopus", "phantom", "quicksand", "raven", "shadow", "thunder",
    "unicorn", "vortex", "whisper", "xylophone", "zealot", "abstract",
    "blizzard", "cascade", "dagger", "emerald", "fortress", "glacier", "harbor",
    "inferno", "jasmine", "kraken", "labyrinth", "mirage", "noodle", "oracle",
    "pilgrim", "quartz", "riddle", "serpent", "tundra", "vampire",
    "walrus", "anchor", "bridge", "candle", "desert", "engine", "feather",
    "goblin", "helmet", "igloo", "jigsaw", "kettle", "lemon", "muffin",
    "napkin", "orange", "pencil", "rabbit", "saddle", "trophy", "violin", "wizard",
]

STAGES = [
    "```\n  +---+\n  |   |\n      |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n      |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n  |   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|   |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n      |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n /    |\n      |\n=========```",
    "```\n  +---+\n  |   |\n  O   |\n /|\\  |\n / \\  |\n      |\n=========```",
]

MAX_WRONG = 6


def build_embed(word, guessed, wrong, title="Hangman", footer=None):
    display = " ".join(c if c in guessed else "_" for c in word)
    wrong_letters = ", ".join(sorted(l for l in guessed if l not in word)) or "None"
    remaining = MAX_WRONG - wrong

    if wrong >= MAX_WRONG:
        color = discord.Color.red()
    elif all(c in guessed for c in word):
        color = discord.Color.green()
    else:
        color = discord.Color.blurple()

    embed = discord.Embed(title=f"🪢 {title}", color=color)
    embed.add_field(name="Gallows", value=STAGES[wrong], inline=False)
    embed.add_field(name="Word", value=f"`{display}`", inline=False)
    embed.add_field(name="Wrong guesses", value=wrong_letters, inline=True)
    embed.add_field(name="Lives left", value=f"{'❤️' * remaining}{'🖤' * wrong}", inline=True)
    if footer:
        embed.set_footer(text=footer)
    return embed


class HangmanGame:
    def __init__(self, word: str, channel_id: int, starter_id: int):
        self.word = word
        self.guessed: set = set()
        self.wrong = 0
        self.over = False
        self.channel_id = channel_id
        self.starter_id = starter_id
        self.message: discord.Message = None

    def is_won(self):
        return all(c in self.guessed for c in self.word)


class HangmanCog(commands.Cog, name="Hangman"):
    def __init__(self, bot):
        self.bot = bot
        self.active: dict[int, HangmanGame] = {}

    @app_commands.command(name="hangman", description="Start a game of Hangman! Type letters in chat to guess.")
    @require_setting("games_enabled")
    async def hangman(self, interaction: discord.Interaction):
        channel_id = interaction.channel_id
        if channel_id in self.active:
            await interaction.response.send_message(
                "A game is already running in this channel! Finish it first.", ephemeral=True
            )
            return

        word = random.choice(WORDS)
        game = HangmanGame(word, channel_id, interaction.user.id)
        self.active[channel_id] = game

        embed = build_embed(word, set(), 0, footer="Just type a letter in chat to guess!")
        await interaction.response.send_message(embed=embed)
        game.message = await interaction.original_response()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        channel_id = message.channel.id
        game = self.active.get(channel_id)
        if game is None or game.over:
            return

        content = message.content.strip().lower()
        if len(content) != 1 or not content.isalpha():
            return

        letter = content

        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        if letter in game.guessed:
            try:
                note = await message.channel.send(
                    f"{message.author.mention} already guessed **{letter.upper()}**!", delete_after=3
                )
            except Exception:
                pass
            return

        game.guessed.add(letter)
        if letter not in game.word:
            game.wrong += 1

        if game.wrong >= MAX_WRONG:
            game.over = True
            del self.active[channel_id]
            embed = build_embed(game.word, game.guessed, game.wrong, title="Hangman — You Lost!")
            embed.add_field(name="The word was", value=f"**{game.word.upper()}**", inline=False)
        elif game.is_won():
            game.over = True
            del self.active[channel_id]
            embed = build_embed(game.word, game.guessed, game.wrong, title="Hangman — You Won! 🎉")
        else:
            hint = "✅ Good guess!" if letter in game.word else "❌ Wrong!"
            embed = build_embed(
                game.word, game.guessed, game.wrong,
                footer=f"{message.author.display_name} guessed '{letter.upper()}' — {hint} Type a letter to keep going."
            )

        try:
            await game.message.edit(embed=embed)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(HangmanCog(bot))
