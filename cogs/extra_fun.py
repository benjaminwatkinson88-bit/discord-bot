import discord
from discord import app_commands
from discord.ext import commands
import random
from cogs.settings_cog import require_setting


def mock_text(text: str) -> str:
    result = []
    upper = False
    for char in text:
        if char.isalpha():
            result.append(char.upper() if upper else char.lower())
            upper = not upper
        else:
            result.append(char)
    return "".join(result)


def emojify_text(text: str) -> str:
    digit_map = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    parts = []
    for char in text.lower():
        if "a" <= char <= "z":
            parts.append(chr(0x1F1E6 + ord(char) - ord("a")) + "\u200b")
        elif char == " ":
            parts.append("   ")
        elif char.isdigit():
            parts.append(digit_map[int(char)])
        elif char == "!":
            parts.append("❗")
        elif char == "?":
            parts.append("❓")
        elif char == "+":
            parts.append("➕")
        elif char == "-":
            parts.append("➖")
        else:
            parts.append(char)
    return "".join(parts)


class RiddleView(discord.ui.View):
    def __init__(self, answer: str):
        super().__init__(timeout=300)
        self.answer = answer

    @discord.ui.button(label="🔍 Reveal Answer", style=discord.ButtonStyle.primary)
    async def reveal(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        button.label = "✅ Revealed"
        embed = interaction.message.embeds[0]
        embed.add_field(name="💡 Answer", value=self.answer, inline=False)
        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=self)


class ExtraFunCog(commands.Cog, name="ExtraFun"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="riddle", description="Get an AI-generated riddle — can you solve it?")
    @require_setting("fun_commands")
    async def riddle(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            response = await ai_cog.quick_ai(
                "Create a clever riddle. Format it EXACTLY like this:\n"
                "RIDDLE: [the riddle here]\n"
                "ANSWER: [the answer here]",
                system="You are a riddle master. Reply only in the exact format requested."
            )
            lines = response.strip().split("\n")
            riddle_text = next((l.replace("RIDDLE:", "").strip() for l in lines if l.startswith("RIDDLE:")), None)
            answer_text = next((l.replace("ANSWER:", "").strip() for l in lines if l.startswith("ANSWER:")), None)
            if not riddle_text or not answer_text:
                await interaction.followup.send("Couldn't parse the riddle. Try again!")
                return
        except Exception as e:
            await interaction.followup.send(f"Couldn't generate a riddle: {e}")
            return
        embed = discord.Embed(title="🧩 Riddle Time!", description=riddle_text, color=discord.Color.purple())
        embed.set_footer(text="Think you know the answer? Click reveal when you're ready!")
        await interaction.followup.send(embed=embed, view=RiddleView(answer_text))

    @app_commands.command(name="advice", description="Get AI advice on any situation.")
    @app_commands.describe(situation="What do you need advice on?")
    @require_setting("fun_commands")
    async def advice(self, interaction: discord.Interaction, situation: str):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            advice_text = await ai_cog.quick_ai(
                f"Give thoughtful, genuine, and practical advice for this situation: {situation}. "
                f"Keep it concise — 2 to 4 sentences.",
                system="You are a wise and empathetic advisor. Give real, grounded advice."
            )
        except Exception as e:
            await interaction.followup.send(f"Couldn't generate advice: {e}")
            return
        embed = discord.Embed(title="💬 Advice", color=discord.Color.teal())
        embed.add_field(name="Your situation", value=f"> {situation}", inline=False)
        embed.add_field(name="Advice", value=advice_text, inline=False)
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="mock", description="Turn text into the SpongeBob mocking meme.")
    @app_commands.describe(text="The text to mock")
    @require_setting("fun_commands")
    async def mock(self, interaction: discord.Interaction, text: str):
        mocked = mock_text(text)
        embed = discord.Embed(
            title="🧽 mOcKeD",
            description=f"**Input:** {text}\n**Output:** {mocked}",
            color=discord.Color.yellow()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="emojify", description="Turn your text into emoji letters!")
    @app_commands.describe(text="The text to emojify (letters and numbers only)")
    @require_setting("fun_commands")
    async def emojify(self, interaction: discord.Interaction, text: str):
        if len(text) > 30:
            await interaction.response.send_message(
                "Keep it under 30 characters — longer text gets too wide!", ephemeral=True
            )
            return
        result = emojify_text(text)
        embed = discord.Embed(title="🔤 Emojified", description=result, color=discord.Color.blurple())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="topic", description="Get a random conversation topic to break the silence!")
    @require_setting("fun_commands")
    async def topic(self, interaction: discord.Interaction):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            topic_text = await ai_cog.quick_ai(
                "Give me one interesting, fun, and open-ended conversation starter topic or question. "
                "It should spark genuine discussion. Just the topic/question — no intro, no explanation.",
                system="You are a conversation facilitator. Reply with a single creative topic or question."
            )
        except Exception as e:
            await interaction.followup.send(f"Couldn't get a topic: {e}")
            return
        embed = discord.Embed(title="💬 Conversation Topic", description=topic_text, color=discord.Color.green())
        embed.set_footer(text="Discuss away!")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="horoscope", description="Get your AI-generated horoscope!")
    @app_commands.describe(sign="Your star sign")
    @app_commands.choices(sign=[
        app_commands.Choice(name="♈ Aries", value="Aries"),
        app_commands.Choice(name="♉ Taurus", value="Taurus"),
        app_commands.Choice(name="♊ Gemini", value="Gemini"),
        app_commands.Choice(name="♋ Cancer", value="Cancer"),
        app_commands.Choice(name="♌ Leo", value="Leo"),
        app_commands.Choice(name="♍ Virgo", value="Virgo"),
        app_commands.Choice(name="♎ Libra", value="Libra"),
        app_commands.Choice(name="♏ Scorpio", value="Scorpio"),
        app_commands.Choice(name="♐ Sagittarius", value="Sagittarius"),
        app_commands.Choice(name="♑ Capricorn", value="Capricorn"),
        app_commands.Choice(name="♒ Aquarius", value="Aquarius"),
        app_commands.Choice(name="♓ Pisces", value="Pisces"),
    ])
    @require_setting("fun_commands")
    async def horoscope(self, interaction: discord.Interaction, sign: app_commands.Choice[str]):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            reading = await ai_cog.quick_ai(
                f"Write a fun, dramatic, and slightly over-the-top daily horoscope for {sign.value}. "
                f"Include predictions about love, work, and luck. Keep it to 3 short paragraphs. Be theatrical.",
                system="You are a dramatic mystical astrologer. Be theatrical and fun."
            )
        except Exception as e:
            await interaction.followup.send(f"The stars aren't speaking today: {e}")
            return
        embed = discord.Embed(title=f"🔮 {sign.value} Horoscope", description=reading, color=discord.Color.purple())
        embed.set_footer(text="For entertainment purposes only ✨")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="debate", description="Pick a side — the AI will argue the opposite!")
    @app_commands.describe(statement="A statement or opinion for the bot to debate against")
    @require_setting("fun_commands")
    async def debate(self, interaction: discord.Interaction, statement: str):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            counter = await ai_cog.quick_ai(
                f"The user says: '{statement}'. Argue confidently and cleverly against this position. "
                f"Give a compelling 2-3 sentence counterargument. Be assertive but not rude.",
                system="You are a skilled debater who always argues the opposite side of any statement."
            )
        except Exception as e:
            await interaction.followup.send(f"Couldn't start the debate: {e}")
            return
        embed = discord.Embed(title="⚖️ Debate", color=discord.Color.orange())
        embed.add_field(name="Your position", value=f"> {statement}", inline=False)
        embed.add_field(name="Bot's counter-argument", value=counter, inline=False)
        embed.set_footer(text="Do you agree? Disagree? Discuss!")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="fortune", description="Crack open a fortune cookie!")
    @require_setting("fun_commands")
    async def fortune(self, interaction: discord.Interaction):
        fortunes = [
            "A beautiful, smart, and loving person will be coming into your life.",
            "A dubious friend may be an enemy in camouflage.",
            "All the effort you are making will ultimately pay off.",
            "Be not afraid of growing slowly; be afraid only of standing still.",
            "Curious, restless, and inventive — you will go far.",
            "Do not be afraid to take that big step.",
            "Every flower blooms in its own sweet time.",
            "Fortune favors the bold.",
            "Good news will come to you by mail. (Probably spam though.)",
            "Hard work pays off in the future; laziness pays off now.",
            "Help! I am being held prisoner in a fortune cookie factory.",
            "If you think nobody cares if you're alive, try missing a couple of car payments.",
            "It's not a bug — it's a feature.",
            "Laughter is the shock absorber that eases the blows of life.",
            "Nothing is impossible to a willing heart.",
            "Opportunities multiply as they are seized.",
            "Someone is thinking of you right now. Could be nice. Could be weird.",
            "The best time to plant a tree was 20 years ago. The second best time is now.",
            "The fortune you seek is in another cookie.",
            "You are not a failure. You are a draft.",
            "Your soulmate is probably within a 5-mile radius.",
            "Your talents will be recognised and rewarded.",
        ]
        fortune_text = random.choice(fortunes)
        embed = discord.Embed(title="🥠 Fortune Cookie", description=f"*{fortune_text}*", color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="compliment", description="Compliment someone!")
    @app_commands.describe(member="Who do you want to compliment?")
    @require_setting("fun_commands")
    async def compliment(self, interaction: discord.Interaction, member: discord.Member):
        compliments = [
            "has the energy of someone who actually reads the terms and conditions.",
            "could make a grumpy cat smile.",
            "is the human equivalent of a perfectly timed high five.",
            "radiates main character energy.",
            "is statistically the coolest person in this server.",
            "makes every room a little less terrible.",
            "is built different — in the best way.",
            "has an aura that just makes people want to be around them.",
            "is someone the world didn't deserve but got lucky with anyway.",
            "is proof that some people are just built better.",
            "has never once sent a bad vibe into the universe.",
            "is the reason this server has a pulse.",
        ]
        line = random.choice(compliments)
        embed = discord.Embed(description=f"💖 {member.mention} {line}", color=discord.Color.pink())
        embed.set_footer(text=f"Compliment delivered by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pickup", description="Get a devastatingly cheesy pickup line.")
    @require_setting("fun_commands")
    async def pickup(self, interaction: discord.Interaction):
        lines = [
            "Are you a parking ticket? Because you've got 'fine' written all over you.",
            "Are you a bank loan? Because you have my interest.",
            "Are you a campfire? Because you're hot and I want s'more.",
            "Are you a keyboard? Because you're just my type.",
            "Are you a magician? Because whenever I look at you, everyone else disappears.",
            "Are you made of copper and tellurium? Because you're CuTe.",
            "Are you wi-fi? Because I'm feeling a connection.",
            "Did it hurt? When you fell from the vending machine? Because you're a snack.",
            "Do you like science? Because I've got chemistry with you.",
            "Do you play Minecraft? Because I'd dig you.",
            "I must be a snowflake, because I've fallen for you.",
            "I'm not a photographer, but I can picture us together.",
            "Is your name Google? Because you have everything I've been searching for.",
            "My love for you is like dividing by zero — it cannot be defined.",
            "Roses are red, violets are blue, I'm not that good at poems, nice shoes.",
            "You must be a broom, because you swept me off my feet.",
        ]
        embed = discord.Embed(
            title="💘 Pickup Line",
            description=random.choice(lines),
            color=discord.Color.from_rgb(255, 105, 180),
        )
        embed.set_footer(text="Use responsibly. Results may vary.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="wouldyou", description="Ask the bot an impossible question and get an answer.")
    @app_commands.describe(question="Your impossible 'Would you rather' or 'Would you ever' question")
    @require_setting("fun_commands")
    async def wouldyou(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()
        ai_cog = self.bot.get_cog("AI")
        if not ai_cog:
            await interaction.followup.send("AI is not available right now.")
            return
        try:
            answer = await ai_cog.quick_ai(
                f"Answer this question as yourself (a Discord bot with a personality): '{question}'. "
                f"Give a funny, committed 1-2 sentence answer. Pick a side — no fence sitting.",
                system="You are a bold, opinionated Discord bot who always commits to an answer with humor."
            )
        except Exception as e:
            await interaction.followup.send(f"Couldn't answer: {e}")
            return
        embed = discord.Embed(color=discord.Color.purple())
        embed.add_field(name="❓ The Question", value=f"> {question}", inline=False)
        embed.add_field(name="🤖 My Answer", value=answer, inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ExtraFunCog(bot))
