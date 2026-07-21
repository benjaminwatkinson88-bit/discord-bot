import discord
from discord import app_commands
from discord.ext import commands
import random
import hashlib
import asyncio
from cogs.settings_cog import require_setting


SLOT_SYMBOLS = ['🍒', '🍋', '🍊', '🍇', '🍓', '💎', '7️⃣']
SLOT_WEIGHTS = [30, 25, 20, 15, 5, 3, 2]

EIGHT_BALL_RESPONSES = [
    "It is certain.", "It is decidedly so.", "Without a doubt.",
    "Yes, definitely.", "You may rely on it.", "As I see it, yes.",
    "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.",
    "Outlook not so good.", "Very doubtful.",
]

JOKES = [
    "Why don't scientists trust atoms? Because they make up everything!",
    "Why did the scarecrow win an award? He was outstanding in his field!",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why can't you give Elsa a balloon? Because she'll let it go.",
    "What do you call a fish without eyes? A fsh.",
    "Why did the bicycle fall over? Because it was two-tired.",
    "I'm reading a book about anti-gravity. It's impossible to put down.",
    "Did you hear about the claustrophobic astronaut? He just needed a little space.",
    "Why don't eggs tell jokes? They'd crack each other up.",
    "What do you call cheese that isn't yours? Nacho cheese.",
    "Why did the math book look so sad? Because it had too many problems.",
    "What do you call a sleeping dinosaur? A dino-snore.",
    "Why can't a nose be 12 inches long? Because then it would be a foot.",
    "I used to hate facial hair, but then it grew on me.",
    "What do you call a fake noodle? An impasta.",
]


class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        if interaction.user.id not in [view.player1.id, view.player2.id]:
            await interaction.response.send_message("You're not part of this game!", ephemeral=True)
            return
        if interaction.user.id != view.current_player.id:
            await interaction.response.send_message(
                f"It's not your turn! Waiting for {view.current_player.mention}.", ephemeral=True
            )
            return
        if view.board[self.y][self.x] != 0:
            await interaction.response.send_message("That spot is already taken!", ephemeral=True)
            return
        if view.current_player.id == view.player1.id:
            self.label = "❌"
            self.style = discord.ButtonStyle.danger
            view.board[self.y][self.x] = 1
            view.current_player = view.player2
        else:
            self.label = "⭕"
            self.style = discord.ButtonStyle.success
            view.board[self.y][self.x] = 2
            view.current_player = view.player1
        self.disabled = True
        winner = view.check_winner()
        if winner == 1:
            content = f"❌ **{view.player1.display_name}** wins! GG!"
            for child in view.children:
                child.disabled = True
            view.stop()
        elif winner == 2:
            content = f"⭕ **{view.player2.display_name}** wins! GG!"
            for child in view.children:
                child.disabled = True
            view.stop()
        elif winner == -1:
            content = "It's a **draw**! Neither wins."
            for child in view.children:
                child.disabled = True
            view.stop()
        else:
            content = (
                f"Tic Tac Toe | ❌ {view.player1.display_name} vs ⭕ {view.player2.display_name}\n"
                f"It's **{view.current_player.display_name}**'s turn!"
            )
        await interaction.response.edit_message(content=content, view=view)


class TicTacToeView(discord.ui.View):
    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=300)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_winner(self):
        b = self.board
        for row in b:
            if row[0] == row[1] == row[2] != 0:
                return row[0]
        for col in range(3):
            if b[0][col] == b[1][col] == b[2][col] != 0:
                return b[0][col]
        if b[0][0] == b[1][1] == b[2][2] != 0:
            return b[0][0]
        if b[0][2] == b[1][1] == b[2][0] != 0:
            return b[0][2]
        if all(b[y][x] != 0 for y in range(3) for x in range(3)):
            return -1
        return None


def consistent_number(seed: str, low: int, high: int) -> int:
    h = int(hashlib.md5(seed.lower().strip().encode()).hexdigest(), 16)
    return low + (h % (high - low + 1))


class FunCog(commands.Cog, name="Fun"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="tictactoe", description="Challenge someone to a game of Tic Tac Toe!")
    @app_commands.describe(opponent="The person you want to challenge")
    @require_setting("games_enabled")
    async def tictactoe(self, interaction: discord.Interaction, opponent: discord.Member):
        if opponent.bot:
            await interaction.response.send_message("You can't challenge a bot!", ephemeral=True)
            return
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("You can't play against yourself!", ephemeral=True)
            return
        view = TicTacToeView(interaction.user, opponent)
        await interaction.response.send_message(
            f"Tic Tac Toe | ❌ {interaction.user.display_name} vs ⭕ {opponent.display_name}\n"
            f"It's **{interaction.user.display_name}**'s turn!",
            view=view
        )

    @app_commands.command(name="rate", description="Get a consistent rating for anything!")
    @app_commands.describe(prompt="What do you want to rate?")
    @require_setting("fun_commands")
    async def rate(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        rating = consistent_number(prompt, 1, 10)
        if rating <= 3:
            color = discord.Color.red()
            star = "🔴"
        elif rating <= 6:
            color = discord.Color.orange()
            star = "🟠"
        else:
            color = discord.Color.green()
            star = "🟢"
        bar = "█" * rating + "░" * (10 - rating)
        ai_cog = self.bot.get_cog("AI")
        description = ""
        if ai_cog:
            try:
                guild_id = interaction.guild.id if interaction.guild else None
                description = await ai_cog.quick_ai(
                    f"Write a single short, witty, and unique sentence rating '{prompt}' a {rating}/10. "
                    f"Match the tone to the score — brutal if 1-3, lukewarm if 4-6, glowing if 7-10.",
                    guild_id=guild_id
                )
            except Exception:
                pass
        embed = discord.Embed(title=f"{star} Rating: {prompt}", color=color)
        embed.add_field(name="Score", value=f"`{bar}` **{rating} / 10**", inline=False)
        if description:
            embed.add_field(name="Verdict", value=description, inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="compare", description="Compare two things and see who wins!")
    @app_commands.describe(thing1="First thing", thing2="Second thing")
    @require_setting("fun_commands")
    async def compare(self, interaction: discord.Interaction, thing1: str, thing2: str):
        await interaction.response.defer()
        score1 = consistent_number(f"{thing1.lower()}_vs_{thing2.lower()}_score1", 10, 99)
        score2 = consistent_number(f"{thing1.lower()}_vs_{thing2.lower()}_score2", 10, 99)
        if score1 == score2:
            score2 += 1
        if score1 > score2:
            winner, loser, win_score, lose_score = thing1, thing2, score1, score2
        else:
            winner, loser, win_score, lose_score = thing2, thing1, score2, score1
        ai_cog = self.bot.get_cog("AI")
        verdict = f"{winner} simply outclasses {loser} in every way imaginable."
        if ai_cog:
            try:
                verdict = await ai_cog.quick_ai(
                    f"In one short, witty, funny sentence: explain why {winner} beats {loser}. Be creative and humorous."
                )
            except Exception:
                pass
        embed = discord.Embed(title="⚔️ Head-to-Head Comparison", color=discord.Color.purple())
        embed.add_field(name=f"🥇 {winner}", value=f"Score: **{win_score}**", inline=True)
        embed.add_field(name=f"🥈 {loser}", value=f"Score: **{lose_score}**", inline=True)
        embed.add_field(name="Verdict", value=verdict, inline=False)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="8ball", description="Ask the magic 8 ball a question!")
    @app_commands.describe(question="Your question for the 8 ball")
    @require_setting("fun_commands")
    async def eightball(self, interaction: discord.Interaction, question: str):
        response = random.choice(EIGHT_BALL_RESPONSES)
        if response in EIGHT_BALL_RESPONSES[:10]:
            color = discord.Color.green()
            icon = "✅"
        elif response in EIGHT_BALL_RESPONSES[10:15]:
            color = discord.Color.yellow()
            icon = "🤷"
        else:
            color = discord.Color.red()
            icon = "❌"
        embed = discord.Embed(title="🎱 Magic 8 Ball", color=color)
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=f"{icon} {response}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roll", description="Roll a dice!")
    @app_commands.describe(sides="Number of sides on the dice (default: 6)")
    @require_setting("fun_commands")
    async def roll(self, interaction: discord.Interaction, sides: int = 6):
        if sides < 2:
            await interaction.response.send_message("A dice needs at least 2 sides!", ephemeral=True)
            return
        if sides > 1000000:
            await interaction.response.send_message("That's way too many sides!", ephemeral=True)
            return
        result = random.randint(1, sides)
        embed = discord.Embed(
            title="🎲 Dice Roll",
            description=f"Rolling a **d{sides}**...\n\nYou rolled: **{result}**",
            color=discord.Color.blue()
        )
        if result == sides:
            embed.set_footer(text="Maximum roll! Lucky!")
        elif result == 1:
            embed.set_footer(text="Minimum roll. Ouch.")
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="joke", description="Hear a random joke!")
    @require_setting("fun_commands")
    async def joke(self, interaction: discord.Interaction):
        joke_text = random.choice(JOKES)
        embed = discord.Embed(title="😂 Random Joke", description=joke_text, color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="roast", description="Get an AI roast of someone!")
    @app_commands.describe(target="Who do you want to roast?")
    @require_setting("fun_commands")
    async def roast(self, interaction: discord.Interaction, target: discord.Member):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            roast_text = await ai_cog.quick_ai(
                f"Write a single, witty, playful roast for someone named {target.display_name}. "
                f"Keep it funny and lighthearted, not mean-spirited. One or two sentences max."
            )
        except Exception as e:
            await interaction.followup.send(f"Couldn't roast them this time: {e}")
            return
        embed = discord.Embed(title=f"🔥 Roasting {target.display_name}", description=roast_text, color=discord.Color.red())
        embed.set_footer(text=f"Requested by {interaction.user.display_name} | All in good fun!")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="wyr", description="Get a Would You Rather question!")
    @require_setting("fun_commands")
    async def wyr(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            question = await ai_cog.quick_ai(
                "Generate a single interesting and fun 'Would You Rather' question. "
                "Format it as: 'Would you rather [option A] or [option B]?' — just the question, nothing else."
            )
        except Exception as e:
            await interaction.followup.send(f"Couldn't generate a question: {e}")
            return
        embed = discord.Embed(title="🤔 Would You Rather?", description=question, color=discord.Color.blurple())
        embed.set_footer(text="Discuss in the chat!")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ship", description="Check the love compatibility between two people!")
    @app_commands.describe(person1="First person", person2="Second person")
    @require_setting("fun_commands")
    async def ship(self, interaction: discord.Interaction, person1: discord.Member, person2: discord.Member):
        ids = sorted([person1.id, person2.id])
        seed = f"ship_{ids[0]}_{ids[1]}"
        percentage = consistent_number(seed, 0, 100)
        if percentage >= 90:
            verdict, bar_color = "💞 Soulmates! Made for each other.", "💗"
        elif percentage >= 70:
            verdict, bar_color = "💕 Great chemistry! This could work.", "❤️"
        elif percentage >= 50:
            verdict, bar_color = "💛 Some sparks, but needs work.", "💛"
        elif percentage >= 30:
            verdict, bar_color = "💔 Hmm... it's complicated.", "🧡"
        else:
            verdict, bar_color = "💀 Yikes. Just friends at best.", "🖤"
        bar_filled = round(percentage / 10)
        bar = bar_color * bar_filled + "⬜" * (10 - bar_filled)
        ship_name = person1.display_name[:len(person1.display_name)//2] + person2.display_name[len(person2.display_name)//2:]
        embed = discord.Embed(title=f"💘 {person1.display_name} + {person2.display_name}", color=discord.Color.pink())
        embed.add_field(name="Ship Name", value=f"**{ship_name}**", inline=False)
        embed.add_field(name="Compatibility", value=f"{bar} **{percentage}%**", inline=False)
        embed.add_field(name="Verdict", value=verdict, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="trivia", description="Get a random trivia question!")
    @require_setting("fun_commands")
    async def trivia(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            response = await ai_cog.quick_ai(
                "Generate a fun trivia question and its answer. "
                "Format it EXACTLY like this:\n"
                "QUESTION: [your question here]\n"
                "ANSWER: [the answer here]"
            )
            lines = response.strip().split("\n")
            question = next((l.replace("QUESTION:", "").strip() for l in lines if l.startswith("QUESTION:")), "Unknown question")
            answer = next((l.replace("ANSWER:", "").strip() for l in lines if l.startswith("ANSWER:")), "Unknown answer")
        except Exception as e:
            await interaction.followup.send(f"Couldn't fetch a trivia question: {e}")
            return
        embed = discord.Embed(title="🧠 Trivia Time!", color=discord.Color.teal())
        embed.add_field(name="Question", value=question, inline=False)
        embed.set_footer(text="Reply with your answer! The answer will be revealed in 15 seconds.")
        msg = await interaction.followup.send(embed=embed)
        await asyncio.sleep(15)
        embed.add_field(name="Answer", value=f"||{answer}||", inline=False)
        embed.set_footer(text="Times up! How did you do?")
        await msg.edit(embed=embed)

    @app_commands.command(name="fact", description="Get a random fun fact!")
    @require_setting("fun_commands")
    async def fact(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            fact_text = await ai_cog.quick_ai(
                "Share one interesting, surprising, and true fun fact. "
                "Keep it to 1-2 sentences. Don't say 'Did you know' — just state the fact."
            )
        except Exception as e:
            await interaction.followup.send(f"Couldn't fetch a fact: {e}")
            return
        embed = discord.Embed(title="💡 Fun Fact", description=fact_text, color=discord.Color.blue())
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rps", description="Play Rock, Paper, Scissors against the bot!")
    @app_commands.describe(choice="Your choice: rock, paper, or scissors")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Rock 🪨", value="rock"),
        app_commands.Choice(name="Paper 📄", value="paper"),
        app_commands.Choice(name="Scissors ✂️", value="scissors"),
    ])
    @require_setting("games_enabled")
    async def rps(self, interaction: discord.Interaction, choice: app_commands.Choice[str]):
        bot_choice = random.choice(["rock", "paper", "scissors"])
        icons = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}
        player = choice.value
        outcomes = {("rock", "scissors"): "win", ("paper", "rock"): "win", ("scissors", "paper"): "win"}
        if player == bot_choice:
            result, color = "It's a **tie**! Great minds think alike.", discord.Color.yellow()
        elif outcomes.get((player, bot_choice)):
            result, color = "You **win**! Well played! 🎉", discord.Color.green()
        else:
            result, color = "You **lose**! Better luck next time. 😈", discord.Color.red()
        embed = discord.Embed(title="🎮 Rock, Paper, Scissors", color=color)
        embed.add_field(name="Your Pick", value=f"{icons[player]} {player.capitalize()}", inline=True)
        embed.add_field(name="Bot's Pick", value=f"{icons[bot_choice]} {bot_choice.capitalize()}", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(FunCog(bot))
