import discord
from discord import app_commands
from discord.ext import commands
from cogs.settings_cog import require_setting

ANSWER = "horse"
MAX_GUESSES = 6

GREEN = "🟩"
YELLOW = "🟨"
GRAY = "⬛"


def score_guess(guess: str, answer: str) -> list[str]:
    result = [GRAY] * 5
    answer_chars = list(answer)
    guess_chars = list(guess)

    # First pass: correct position
    for i in range(5):
        if guess_chars[i] == answer_chars[i]:
            result[i] = GREEN
            answer_chars[i] = None
            guess_chars[i] = None

    # Second pass: wrong position
    for i in range(5):
        if guess_chars[i] is None:
            continue
        if guess_chars[i] in answer_chars:
            result[i] = YELLOW
            answer_chars[answer_chars.index(guess_chars[i])] = None

    return result


def build_embed(rows: list[str], guesses_left: int, won: bool = False, lost: bool = False) -> discord.Embed:
    if won:
        color = discord.Color.green()
        title = "🐴 Horsle — You got it!"
    elif lost:
        color = discord.Color.red()
        title = "🐴 Horsle — Game Over!"
    else:
        color = discord.Color.blurple()
        title = "🐴 Horsle"

    board = "\n".join(rows) if rows else "*(no guesses yet)*"
    empty = MAX_GUESSES - len(rows)
    if empty > 0 and not won and not lost:
        board += "\n" + "\n".join(["⬜⬜⬜⬜⬜"] * empty)

    embed = discord.Embed(title=title, color=color)
    embed.add_field(name="Board", value=board, inline=False)

    if not won and not lost:
        embed.set_footer(text=f"{guesses_left} guess{'es' if guesses_left != 1 else ''} left — type a 5-letter word in chat!")
    elif lost:
        embed.set_footer(text=f"The word was: HORSE. It was right there the whole time.")

    return embed


class HorsleGame:
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.rows: list[str] = []
        self.over = False
        self.message: discord.Message = None

    @property
    def guesses_left(self):
        return MAX_GUESSES - len(self.rows)


class HorsleGameCog(commands.Cog, name="HorsleGame"):
    def __init__(self, bot):
        self.bot = bot
        self.active: dict[int, HorsleGame] = {}

    @app_commands.command(name="horsle", description="Horsle — Wordle, but the answer is always HORSE.")
    @require_setting("games_enabled")
    async def horsle(self, interaction: discord.Interaction):
        channel_id = interaction.channel_id
        if channel_id in self.active:
            await interaction.response.send_message(
                "A Horsle game is already running here! Guess or give up first.", ephemeral=True
            )
            return

        game = HorsleGame(channel_id)
        self.active[channel_id] = game

        embed = build_embed([], MAX_GUESSES)
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
        if len(content) != 5 or not content.isalpha():
            return

        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        guess = content
        tiles = score_guess(guess, ANSWER)
        row = "".join(tiles) + f"  `{guess.upper()}`"
        game.rows.append(row)

        won = guess == ANSWER
        lost = not won and game.guesses_left == 0

        if won or lost:
            game.over = True
            del self.active[channel_id]

        embed = build_embed(game.rows, game.guesses_left, won=won, lost=lost)

        if won:
            num = len(game.rows)
            embed.description = f"{message.author.mention} got it in **{num}** guess{'es' if num != 1 else ''}!"
        elif lost:
            embed.description = f"{message.author.mention} has been eliminated from the gene pool."

        try:
            await game.message.edit(embed=embed)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(HorsleGameCog(bot))
