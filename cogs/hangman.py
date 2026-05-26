import discord
from discord import app_commands
from discord.ext import commands
import random

WORDS = [
    "python", "discord", "elephant", "umbrella", "jazz", "rhythm", "sphinx",
    "volcano", "oxygen", "blanket", "crystal", "dolphin", "eclipse", "falcon",
    "gravity", "horizon", "island", "jungle", "kingdom", "lantern", "marble",
    "nebula", "octopus", "phantom", "quicksand", "raven", "shadow", "thunder",
    "unicorn", "vortex", "whisper", "xylophone", "yellow", "zealot", "abstract",
    "blizzard", "cascade", "dagger", "emerald", "fortress", "glacier", "harbor",
    "inferno", "jasmine", "kraken", "labyrinth", "mirage", "noodle", "oracle",
    "pilgrim", "quartz", "riddle", "serpent", "tundra", "uplift", "vampire",
    "walrus", "xenon", "yonder", "zigzag", "anchor", "bridge", "candle",
    "desert", "engine", "feather", "goblin", "helmet", "igloo", "jigsaw",
    "kettle", "lemon", "muffin", "napkin", "orange", "pencil", "rabbit",
    "saddle", "trophy", "urchin", "violin", "wizard", "zipper",
]

STAGES = [
    (
        "```\n"
        "  +---+\n"
        "  |   |\n"
        "      |\n"
        "      |\n"
        "      |\n"
        "      |\n"
        "=========```"
    ),
    (
        "```\n"
        "  +---+\n"
        "  |   |\n"
        "  O   |\n"
        "      |\n"
        "      |\n"
        "      |\n"
        "=========```"
    ),
    (
        "```\n"
        "  +---+\n"
        "  |   |\n"
        "  O   |\n"
        "  |   |\n"
        "      |\n"
        "      |\n"
        "=========```"
    ),
    (
        "```\n"
        "  +---+\n"
        "  |   |\n"
        "  O   |\n"
        " /|   |\n"
        "      |\n"
        "      |\n"
        "=========```"
    ),
    (
        "```\n"
        "  +---+\n"
        "  |   |\n"
        "  O   |\n"
        " /|\\  |\n"
        "      |\n"
        "      |\n"
        "=========```"
    ),
    (
        "```\n"
        "  +---+\n"
        "  |   |\n"
        "  O   |\n"
        " /|\\  |\n"
        " /    |\n"
        "      |\n"
        "=========```"
    ),
    (
        "```\n"
        "  +---+\n"
        "  |   |\n"
        "  O   |\n"
        " /|\\  |\n"
        " / \\  |\n"
        "      |\n"
        "=========```"
    ),
]

MAX_WRONG = 6


def build_embed(word: str, guessed: set, wrong: int, title: str = "Hangman") -> discord.Embed:
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
    return embed


class GuessModal(discord.ui.Modal, title="Guess a Letter"):
    letter = discord.ui.TextInput(
        label="Enter a single letter",
        min_length=1,
        max_length=1,
        placeholder="e.g. A",
    )

    def __init__(self, view: "HangmanView"):
        super().__init__()
        self.game_view = view

    async def on_submit(self, interaction: discord.Interaction):
        await self.game_view.process_guess(interaction, self.letter.value.lower())


class HangmanView(discord.ui.View):
    def __init__(self, word: str):
        super().__init__(timeout=300)
        self.word = word
        self.guessed: set = set()
        self.wrong = 0
        self.over = False

    def is_won(self) -> bool:
        return all(c in self.guessed for c in self.word)

    async def process_guess(self, interaction: discord.Interaction, letter: str):
        if self.over:
            await interaction.response.send_message("This game is already over!", ephemeral=True)
            return

        if not letter.isalpha():
            await interaction.response.send_message("Please enter a letter (A–Z).", ephemeral=True)
            return

        if letter in self.guessed:
            await interaction.response.send_message(f"You already guessed **{letter.upper()}**!", ephemeral=True)
            return

        self.guessed.add(letter)
        if letter not in self.word:
            self.wrong += 1

        if self.wrong >= MAX_WRONG:
            self.over = True
            self._disable_buttons()
            embed = build_embed(self.word, self.guessed, self.wrong, title="Hangman — You Lost!")
            embed.add_field(name="The word was", value=f"**{self.word.upper()}**", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)

        elif self.is_won():
            self.over = True
            self._disable_buttons()
            embed = build_embed(self.word, self.guessed, self.wrong, title="Hangman — You Won!")
            await interaction.response.edit_message(embed=embed, view=self)

        else:
            embed = build_embed(self.word, self.guessed, self.wrong)
            await interaction.response.edit_message(embed=embed, view=self)

    def _disable_buttons(self):
        for item in self.children:
            item.disabled = True

    @discord.ui.button(label="Guess a Letter", style=discord.ButtonStyle.primary, emoji="🔤")
    async def guess_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.over:
            await interaction.response.send_message("This game is already over!", ephemeral=True)
            return
        await interaction.response.send_modal(GuessModal(self))

    @discord.ui.button(label="Give Up", style=discord.ButtonStyle.danger, emoji="🏳️")
    async def giveup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.over:
            await interaction.response.send_message("This game is already over!", ephemeral=True)
            return
        self.over = True
        self.wrong = MAX_WRONG
        self._disable_buttons()
        embed = build_embed(self.word, self.guessed, self.wrong, title="Hangman — Gave Up!")
        embed.add_field(name="The word was", value=f"**{self.word.upper()}**", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        self.over = True
        self._disable_buttons()


class HangmanCog(commands.Cog, name="Hangman"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hangman", description="Start a game of Hangman!")
    async def hangman(self, interaction: discord.Interaction):
        word = random.choice(WORDS)
        view = HangmanView(word)
        embed = build_embed(word, set(), 0)
        embed.set_footer(text="Click 'Guess a Letter' to open the input. You have 6 lives.")
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(HangmanCog(bot))
