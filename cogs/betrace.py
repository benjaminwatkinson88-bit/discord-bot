import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import json
import os
import math

DATA_FILE = "data/levels.json"

HORSE_NAMES = [
    "Sir Neighs-a-Lot",
    "Glue Factory Escapee",
    "Mr. Oats",
    "Thunderhooves",
    "Sneaky Stallion",
    "Absolute Disaster",
    "Hay Fever",
    "Neighs Sheeran",
]
HORSE_EMOJIS = ["🐎", "🐴", "🦄", "🏇", "🐎", "🐴", "🐎", "🦄"]
TRACK_LENGTH = 20
LANE_PAD = 18


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data(data):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def get_xp(guild_id: int, user_id: int) -> int:
    data = load_data()
    g, u = str(guild_id), str(user_id)
    return data.get(g, {}).get(u, {}).get("xp", 0)


def add_xp(guild_id: int, user_id: int, amount: int):
    data = load_data()
    g, u = str(guild_id), str(user_id)
    if g not in data:
        data[g] = {}
    if u not in data[g]:
        data[g][u] = {"xp": 0, "level": 0}
    data[g][u]["xp"] = max(0, data[g][u]["xp"] + amount)
    data[g][u]["level"] = int(math.sqrt(data[g][u]["xp"] / 100))
    save_data(data)


def render_track(positions, names, emojis, finished):
    lines = []
    for i, (pos, name, emoji) in enumerate(zip(positions, names, emojis)):
        track = [" "] * TRACK_LENGTH
        track[min(pos, TRACK_LENGTH - 1)] = emoji
        bar = "".join(track)
        medal = ""
        if i in finished:
            place = finished.index(i) + 1
            medal = ["🥇", "🥈", "🥉"][place - 1] if place <= 3 else f"#{place}"
        label = name[:LANE_PAD].ljust(LANE_PAD)
        lines.append(f"`{label}` {bar}🏁 {medal}")
    return "\n".join(lines)


class BetButton(discord.ui.Button):
    def __init__(self, horse_index: int, horse_name: str, bet_amount: int, view: "BetView"):
        super().__init__(
            label=horse_name[:20],
            style=discord.ButtonStyle.secondary,
            custom_id=f"bet_{horse_index}",
            row=horse_index // 3,
        )
        self.horse_index = horse_index
        self.horse_name = horse_name
        self.bet_amount = bet_amount
        self.bet_view = view

    async def callback(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        guild_id = interaction.guild.id

        if user_id in self.bet_view.bets:
            old_horse = self.bet_view.bets[user_id][0]
            if old_horse == self.horse_index:
                await interaction.response.send_message(
                    f"You already bet on **{self.horse_name}**!", ephemeral=True
                )
                return
            # Refund old bet, move to new horse
            add_xp(guild_id, user_id, self.bet_amount)

        current_xp = get_xp(guild_id, user_id)
        if current_xp < self.bet_amount:
            await interaction.response.send_message(
                f"You need **{self.bet_amount:,} XP** to bet but only have **{current_xp:,} XP**.",
                ephemeral=True,
            )
            return

        add_xp(guild_id, user_id, -self.bet_amount)
        self.bet_view.bets[user_id] = (self.horse_index, self.bet_amount, interaction.user.display_name)

        bets_text = self.bet_view.format_bets()
        embed = interaction.message.embeds[0]
        if len(embed.fields) > 0:
            embed.set_field_at(0, name="Current Bets", value=bets_text, inline=False)
        else:
            embed.add_field(name="Current Bets", value=bets_text, inline=False)

        await interaction.response.edit_message(embed=embed, view=self.bet_view)
        await interaction.followup.send(
            f"🎰 You bet **{self.bet_amount:,} XP** on **{self.horse_name}**!", ephemeral=True
        )


class StartButton(discord.ui.Button):
    def __init__(self, bet_view: "BetView"):
        super().__init__(label="🚦 Start Race!", style=discord.ButtonStyle.success, row=3)
        self.bet_view = bet_view

    async def callback(self, interaction: discord.Interaction):
        if not self.bet_view.bets:
            await interaction.response.send_message("At least one person must place a bet first!", ephemeral=True)
            return
        await interaction.response.defer()
        self.bet_view.started = True
        self.bet_view.stop()


class BetView(discord.ui.View):
    def __init__(self, names: list, bet_amount: int):
        super().__init__(timeout=30)
        self.bets: dict = {}
        self.started = False

        for i, name in enumerate(names):
            self.add_item(BetButton(i, name, bet_amount, self))
        self.add_item(StartButton(self))

    def format_bets(self) -> str:
        if not self.bets:
            return "*No bets yet*"
        lines = []
        from collections import defaultdict
        grouped = defaultdict(list)
        for uid, (horse_idx, amount, name) in self.bets.items():
            grouped[horse_idx].append(name)
        for idx, bettors in grouped.items():
            lines.append(f"🐎 Bettor(s) on horse #{idx + 1}: {', '.join(bettors)}")
        return "\n".join(lines)


class BetraceCog(commands.Cog, name="Betrace"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="betrace", description="Bet XP on a horse race! Win big or lose it all.")
    @app_commands.describe(amount="XP to bet (minimum 50)")
    async def betrace(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("This command only works in a server.", ephemeral=True)
            return

        amount = random.randint(50, 200)

        count = random.randint(4, 6)
        names = random.sample(HORSE_NAMES, count)
        emojis = HORSE_EMOJIS[:count]

        view = BetView(names, amount)

        horses_list = "\n".join(f"{emojis[i]} **{name}**" for i, name in enumerate(names))
        embed = discord.Embed(
            title="🎰 Horse Race Betting",
            description=(
                f"**Bet:** {amount:,} XP each\n"
                f"**Payout:** 2× your bet if your horse wins\n\n"
                f"{horses_list}\n\n"
                f"*Click a horse to bet! Race starts in 30s or when someone clicks Start.*"
            ),
            color=discord.Color.yellow(),
        )
        embed.add_field(name="Current Bets", value="*No bets yet*", inline=False)

        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        try:
            await asyncio.wait_for(view.wait(), timeout=30)
        except asyncio.TimeoutError:
            pass

        for item in view.children:
            item.disabled = True

        if not view.bets:
            embed.description = "Nobody bet — race cancelled."
            embed.color = discord.Color.grayed()
            await msg.edit(embed=embed, view=view)
            return

        # Run the race
        positions = [0] * count
        finished = []
        tick = 0

        while len(finished) < count:
            tick += 1
            for i in range(count):
                if i in finished:
                    continue
                move = random.choices([0, 1, 2], weights=[20, 55, 25])[0]
                positions[i] += move
                if positions[i] >= TRACK_LENGTH - 1:
                    positions[i] = TRACK_LENGTH - 1
                    if i not in finished:
                        finished.append(i)

            desc = render_track(positions, names, emojis, finished)
            if len(finished) == count:
                winner_name = names[finished[0]]
                race_embed = discord.Embed(
                    title="🏆 Race Over!",
                    description=desc + f"\n\n🥇 **{winner_name}** wins!",
                    color=discord.Color.gold(),
                )
            else:
                race_embed = discord.Embed(
                    title=f"🏟️ Racing — Lap {tick}",
                    description=desc,
                    color=discord.Color.blurple(),
                )

            try:
                await msg.edit(embed=race_embed, view=view)
            except Exception:
                pass

            if len(finished) < count:
                await asyncio.sleep(1.2)

        # Pay out winners
        winning_horse = finished[0]
        winner_name = names[winning_horse]
        payouts = []
        losers = []

        for uid, (horse_idx, bet_amt, display_name) in view.bets.items():
            if horse_idx == winning_horse:
                payout = bet_amt * 2
                add_xp(interaction.guild.id, uid, payout)
                payouts.append(f"🎉 **{display_name}** +{payout:,} XP")
            else:
                losers.append(f"💸 **{display_name}** -{bet_amt:,} XP")

        result_lines = payouts + losers
        race_embed.add_field(
            name="Betting Results",
            value="\n".join(result_lines) if result_lines else "No payouts.",
            inline=False,
        )
        try:
            await msg.edit(embed=race_embed, view=view)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(BetraceCog(bot))
