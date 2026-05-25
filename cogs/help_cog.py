import discord
from discord import app_commands
from discord.ext import commands


PUBLIC_FUN_COMMANDS = [
    ("`/slots`", "Pull the slot machine lever and try your luck!"),
    ("`/tictactoe @user`", "Challenge someone to Tic Tac Toe"),
    ("`/rate <prompt>`", "Get a rating for anything"),
    ("`/compare <thing1> <thing2>`", "See who or what wins in a head-to-head"),
    ("`/8ball <question>`", "Ask the magic 8 ball"),
    ("`/roll [sides]`", "Roll a dice (default: d6)"),
    ("`/coinflip`", "Flip a coin — heads or tails?"),
    ("`/joke`", "Hear a random joke"),
    ("`/roast @user`", "Get an AI roast of someone"),
    ("`/wyr`", "Get a Would You Rather question"),
    ("`/ship @user1 @user2`", "Check love compatibility between two people"),
    ("`/trivia`", "AI trivia question (answer revealed in 15s)"),
    ("`/fact`", "Get a random fun fact"),
    ("`/rps <choice>`", "Play Rock, Paper, Scissors against the bot"),
    ("`/riddle`", "Get an AI riddle with a reveal button"),
    ("`/advice <situation>`", "Get AI advice on any situation"),
    ("`/mock <text>`", "SpongeBob mocking meme text"),
    ("`/emojify <text>`", "Turn your text into emoji letters"),
    ("`/topic`", "Get a random conversation topic"),
    ("`/horoscope <sign>`", "Get your AI-generated horoscope"),
    ("`/debate <statement>`", "The AI argues the opposite of your statement"),
]

PUBLIC_AI_COMMANDS = [
    ("`/story <prompt>`", "Generate an AI story based on your prompt"),
    ("`/personality`", "See the bot's current AI personality"),
]

PUBLIC_UTILITY_COMMANDS = [
    ("`/invite`", "Get the link to add this bot to your server"),
    ("`/poll <question> <opt1> <opt2> ...`", "Create a live voting poll"),
    ("`/serverinfo`", "View info about this server"),
    ("`/userinfo [@user]`", "View info about a user"),
    ("`/avatar [@user]`", "View someone's avatar in full size"),
    ("`/rank [@user]`", "Check your XP level and server rank"),
    ("`/leaderboard`", "See the top members by XP"),
]

ADMIN_COMMANDS = [
    ("`/settitleall`", "Set titles for all members based on their roles"),
    ("`/settitle @user`", "Set the title for a specific member"),
    ("`/removetitle @user`", "Remove the title from a specific member"),
    ("`/autoemoji on/off`", "Toggle AI auto-emoji for roles with no keyword match"),
    ("`/titlekeywords`", "View current keyword → emoji mappings"),
    ("`/addkeyword <keyword> <emoji>`", "Add a custom role keyword mapping"),
    ("`/removekeyword <keyword>`", "Remove a keyword mapping"),
    ("`/setpersonality <text>`", "Change the bot's AI personality for this server"),
    ("`/channel [#channel]`", "Set a channel the bot replies to all messages in"),
    ("`/announce <#channel> <title> <message>`", "Send a formatted announcement"),
    ("`/givexp @user <amount>`", "Give XP to a member"),
    ("`/resetxp @user`", "Reset a member's XP to zero"),
]

OTHER_COMMANDS = [
    ("`/help`", "Show this help menu"),
]


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all available commands.")
    async def help(self, interaction: discord.Interaction):
        is_admin = (
            interaction.user.guild_permissions.administrator
            if interaction.guild
            else False
        )

        embed = discord.Embed(
            title="📖 Command Help",
            description=(
                f"Hey **{interaction.user.display_name}**! Here's what I can do.\n"
                f"Ping me directly to chat with the AI!"
            ),
            color=discord.Color.blurple()
        )

        fun_text = "\n".join(f"{cmd} — {desc}" for cmd, desc in PUBLIC_FUN_COMMANDS)
        embed.add_field(name="🎉 Fun Commands", value=fun_text, inline=False)

        ai_text = "\n".join(f"{cmd} — {desc}" for cmd, desc in PUBLIC_AI_COMMANDS)
        embed.add_field(name="🤖 AI Commands", value=ai_text, inline=False)

        util_text = "\n".join(f"{cmd} — {desc}" for cmd, desc in PUBLIC_UTILITY_COMMANDS)
        embed.add_field(name="🔧 Utility", value=util_text, inline=False)

        if is_admin:
            admin_text = "\n".join(f"{cmd} — {desc}" for cmd, desc in ADMIN_COMMANDS)
            embed.add_field(name="🔒 Admin Commands", value=admin_text, inline=False)

        other_text = "\n".join(f"{cmd} — {desc}" for cmd, desc in OTHER_COMMANDS)
        embed.add_field(name="ℹ️ Other", value=other_text, inline=False)

        embed.set_footer(
            text="Admin commands are only visible to administrators."
            if not is_admin
            else "You have administrator access — all commands are shown."
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
