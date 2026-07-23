import discord
from discord import app_commands
from discord.ext import commands


FUN_COMMANDS_1 = [
    ("`/tictactoe @user`", "Tic Tac Toe"),
    ("`/rate <thing>`", "Rate anything"),
    ("`/compare <a> <b>`", "Head-to-head comparison"),
    ("`/8ball <question>`", "Magic 8 ball"),
    ("`/roll [sides]`", "Roll a dice"),
    ("`/joke`", "Random joke"),
    ("`/roast @user`", "AI roast"),
    ("`/wyr`", "Would You Rather"),
    ("`/ship @user1 @user2`", "Love compatibility"),
    ("`/trivia`", "AI trivia question"),
    ("`/fact`", "Random fun fact"),
    ("`/rps <choice>`", "Rock Paper Scissors"),
    ("`/massping @user`", "Spam ping a user until stopped"),
    ("`/massprotect`", "Toggle mass ping protection on yourself"),
]

FUN_COMMANDS_2 = [
    ("`/riddle`", "AI riddle with reveal button"),
    ("`/advice <situation>`", "AI advice"),
    ("`/mock <text>`", "SpongeBob mock text"),
    ("`/emojify <text>`", "Emoji letters"),
    ("`/topic`", "Conversation starter"),
    ("`/horoscope <sign>`", "AI horoscope"),
    ("`/debate <statement>`", "AI argues opposite"),
    ("`/fortune`", "Fortune cookie"),
    ("`/compliment @user`", "Compliment someone"),
    ("`/pickup`", "Cheesy pickup line"),
    ("`/wouldyou <question>`", "Bot answers anything"),
    ("`/story <prompt>`", "AI short story"),
]

GAME_COMMANDS = [
    ("`/hangman`", "Hangman — type letters in chat"),
    ("`/horsle`", "Wordle but the answer is always HORSE"),
    ("`/racestart`", "Animated horse race with XP betting"),
    ("`/gamble <amount>`", "Pick from 5 gambling games"),
]

PUBLIC_UTILITY_COMMANDS = [
    ("`/rank [@user]`", "Check XP level and rank"),
    ("`/leaderboard`", "Top members by XP"),
    ("`/invite`", "Add this bot to your server"),
    ("`/poll <question> <opt1> <opt2>`", "Live voting poll"),
    ("`/serverinfo`", "Server info"),
    ("`/userinfo [@user]`", "User info"),
    ("`/avatar [@user]`", "Full-size avatar"),
    ("`/personality`", "View the bot's AI personality"),
]

ADMIN_COMMANDS = [
    ("`/setpersonality <text>`", "Change the bot's AI personality"),
    ("`/setpersonality2 <text>`", "Set the second self-talk personality"),
    ("`/selftalk on/off`", "Toggle the bot talking to itself"),
    ("`/selftalkinfinity on/off`", "Toggle infinite self-talk (no turn limit)"),
    ("`/channel [#channel]`", "Set a channel the bot replies to all messages in"),
    ("`/givexp @user <amount>`", "Give XP to a member"),
    ("`/resetxp @user`", "Reset a member's XP to zero"),
    ("`/checkgroq`", "Test whether the Groq AI key is working"),
    ("`/settitleall`", "Set titles for all members by role"),
    ("`/settitle @user`", "Set a member's title"),
    ("`/removetitle @user`", "Remove a member's title"),
    ("`/autoemoji on/off`", "Toggle AI auto-emoji for roles"),
    ("`/titlekeywords`", "View keyword → emoji mappings"),
    ("`/addkeyword <keyword> <emoji>`", "Add a keyword mapping"),
    ("`/removekeyword <keyword>`", "Remove a keyword mapping"),
    ("`/announce <#ch> <title> <msg>`", "Send a formatted announcement"),
]


def fmt(commands):
    return "\n".join(f"{cmd} — {desc}" for cmd, desc in commands)


class HelpCog(commands.Cog, name="Help"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all available commands.")
    async def help(self, interaction: discord.Interaction):
        is_admin = (
            interaction.user.guild_permissions.administrator
            if interaction.guild else False
        )

        embed = discord.Embed(
            title="📖 Command Help",
            description=(
                f"Hey **{interaction.user.display_name}**! Here's what I can do.\n"
                f"Ping me or use the AI channel to chat with the bot!"
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(name="🎉 Fun Commands", value=fmt(FUN_COMMANDS_1), inline=False)
        embed.add_field(name="🎉 More Fun Commands", value=fmt(FUN_COMMANDS_2), inline=False)
        embed.add_field(name="🎮 Games", value=fmt(GAME_COMMANDS), inline=False)
        embed.add_field(name="🔧 Utility", value=fmt(PUBLIC_UTILITY_COMMANDS), inline=False)

        if is_admin:
            embed.add_field(name="🔒 Admin Commands", value=fmt(ADMIN_COMMANDS), inline=False)

        embed.set_footer(
            text="Admin commands only visible to administrators." if not is_admin
            else "You have administrator access — all commands shown."
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
