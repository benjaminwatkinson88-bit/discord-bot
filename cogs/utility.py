import discord
from discord import app_commands
from discord.ext import commands

CLIENT_ID = 1508226029825818704
PERMISSIONS = 134335552


class VoteButton(discord.ui.Button):
    def __init__(self, index: int, option: str, emoji: str):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label=f"{emoji} {option[:50]}",
            row=0
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: PollView = self.view
        user_id = interaction.user.id
        already_here = user_id in view.votes[self.index]
        for voters in view.votes.values():
            voters.discard(user_id)
        if not already_here:
            view.votes[self.index].add(user_id)
        await interaction.response.edit_message(embed=view.get_embed(), view=view)


class PollView(discord.ui.View):
    def __init__(self, question: str, options: list):
        super().__init__(timeout=86400)
        self.question = question
        self.options = options
        self.votes = {i: set() for i in range(len(options))}
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        for i, option in enumerate(options):
            self.add_item(VoteButton(i, option, emojis[i]))

    def get_embed(self) -> discord.Embed:
        total = sum(len(v) for v in self.votes.values())
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        embed = discord.Embed(title=f"📊 {self.question}", color=discord.Color.blurple())
        for i, option in enumerate(self.options):
            count = len(self.votes[i])
            pct = round((count / total * 100) if total > 0 else 0)
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            embed.add_field(
                name=f"{emojis[i]} {option}",
                value=f"`{bar}` {count} vote(s) ({pct}%)",
                inline=False
            )
        embed.set_footer(text=f"Total votes: {total} · Click a button to vote, click again to remove")
        return embed


class UtilityCog(commands.Cog, name="Utility"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="invite", description="Get the link to add this bot to your server!")
    async def invite(self, interaction: discord.Interaction):
        url = (
            f"https://discord.com/oauth2/authorize"
            f"?client_id={CLIENT_ID}"
            f"&permissions={PERMISSIONS}"
            f"&scope=bot%20applications.commands"
        )
        embed = discord.Embed(
            title="➕ Add Me to Your Server!",
            description=f"[**Click here to invite the bot**]({url})\n\nMake sure to grant all requested permissions so the title system and AI features work properly.",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Thanks for using the bot!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create a poll with up to 4 options.")
    @app_commands.describe(
        question="The poll question",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
    )
    async def poll(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: str = None,
        option4: str = None,
    ):
        options = [o for o in [option1, option2, option3, option4] if o]
        view = PollView(question, options)
        await interaction.response.send_message(
            embed=view.get_embed(),
            view=view
        )

    @app_commands.command(name="serverinfo", description="View information about this server.")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title=f"📋 {guild.name}", color=discord.Color.blurple())

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)

        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Members", value=f"{guild.member_count:,}", inline=True)
        embed.add_field(name="Roles", value=str(len(guild.roles) - 1), inline=True)
        embed.add_field(name="Text Channels", value=str(text_channels), inline=True)
        embed.add_field(name="Voice Channels", value=str(voice_channels), inline=True)
        embed.add_field(name="Boosts", value=f"{guild.premium_subscription_count} (Tier {guild.premium_tier})", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="Server ID", value=str(guild.id), inline=True)

        if guild.banner:
            embed.set_image(url=guild.banner.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="View information about a user.")
    @app_commands.describe(member="The member to look up (defaults to you)")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user

        roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
        roles_text = " ".join(roles[:10]) + (f" +{len(roles) - 10} more" if len(roles) > 10 else "") if roles else "None"

        embed = discord.Embed(title=f"👤 {member.display_name}", color=member.color or discord.Color.blurple())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member), inline=True)
        embed.add_field(name="ID", value=str(member.id), inline=True)
        embed.add_field(name="Bot", value="Yes" if member.bot else "No", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:D>", inline=True)
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention if member.top_role.name != "@everyone" else "None", inline=True)
        embed.add_field(name=f"Roles ({len(roles)})", value=roles_text, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="View someone's avatar in full size.")
    @app_commands.describe(member="The member whose avatar to show (defaults to you)")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        avatar_url = member.display_avatar.url

        embed = discord.Embed(title=f"🖼️ {member.display_name}'s Avatar", color=discord.Color.blurple())
        embed.set_image(url=avatar_url)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open in browser", url=avatar_url, style=discord.ButtonStyle.link))
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="announce", description="[Admin] Send a formatted announcement to a channel.")
    @app_commands.describe(
        channel="The channel to send to",
        title="Announcement title",
        message="The announcement message",
        ping="Optional role to ping",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        message: str,
        ping: discord.Role = None,
    ):
        embed = discord.Embed(
            title=f"📢 {title}",
            description=message,
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Announced by {interaction.user.display_name}")

        content = ping.mention if ping else ""
        await channel.send(content=content, embed=embed)
        await interaction.response.send_message(
            f"✅ Announcement sent to {channel.mention}!", ephemeral=True
        )

    @announce.error
    async def announce_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You need **Administrator** permission to use this command.", ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
