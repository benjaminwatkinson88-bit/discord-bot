import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import json
import os
import math
from cogs.settings_cog import require_setting, get_setting

DATA_FILE = "data/levels.json"

HORSE_NAMES = [
    "Sir Neighs-a-Lot",
    "Glue Factory Escapee",
    "Mr. Oats",
    "Thunderhooves",
    "Sneaky Stallion",
    "Absolute Disaster",
]
HORSE_EMOJIS = ["🐎", "🐴", "🦄", "🏇", "🐎", "🐴"]
TRACK_LENGTH = 20
LANE_PAD = 18
BET_AMOUNT = 100


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


def get_xp(guild_id, user_id):
    data = load_data()
    return data.get(str(guild_id), {}).get(str(user_id), {}).get("xp", 0)


def change_xp(guild_id, user_id, amount):
    data = load_data()
    g, u = str(guild_id), str(user_id)
    if g not in data:
        data[g] = {}
    if u not in data[g]:
        data[g][u] = {"xp": 0, "level": 0}
    data[g][u]["xp"] = max(0, data[g][u]["xp"] + amount)
    data[g][u]["level"] = int(math.sqrt(data[g][u]["xp"] / 100))
    save_data(data)


def render_race(positions, names, emojis, finished):
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


class RaceView(discord.ui.View):
    def __init__(self, names: list, guild_id: int):
        super().__init__(timeout=20)
        self.names = names
        self.guild_id = guild_id
        self.bets: dict = {}   # user_id -> horse_index
        self.started = False
        for i, name in enumerate(names):
            self.add_item(HorseBetButton(i, name, self))
        self.add_item(StartButton(self))

    def bet_summary(self):
        if not self.bets:
            return "*No bets yet — click a horse to bet 100 XP!*"
        from collections import defaultdict
        grouped = defaultdict(list)
        for uid, (horse_idx, uname) in self.bets.items():
            grouped[horse_idx].append(uname)
        lines = []
        for idx, bettors in sorted(grouped.items()):
            lines.append(f"{HORSE_EMOJIS[idx]} **{self.names[idx]}**: {', '.join(bettors)}")
        return "\n".join(lines)


class HorseBetButton(discord.ui.Button):
    def __init__(self, index: int, name: str, race_view: RaceView):
        super().__init__(
            label=name[:20],
            style=discord.ButtonStyle.secondary,
            row=index // 3,
        )
        self.index = index
        self.race_view = race_view

    async def callback(self, interaction: discord.Interaction):
        uid = interaction.user.id
        guild_id = interaction.guild_id

        if not get_setting(guild_id, "gambling_enabled"):
            await interaction.response.send_message("❌ Gambling is disabled in this server.", ephemeral=True)
            return

        if self.race_view.started:
            await interaction.response.send_message("Race already started!", ephemeral=True)
            return

        if uid in self.race_view.bets:
            old_idx, _ = self.race_view.bets[uid]
            if old_idx == self.index:
                await interaction.response.send_message(
                    f"You already bet on **{self.label}**!", ephemeral=True
                )
                return
            # Refund old bet and switch
            change_xp(guild_id, uid, BET_AMOUNT)

        xp = get_xp(guild_id, uid)
        if xp < BET_AMOUNT:
            await interaction.response.send_message(
                f"You need **{BET_AMOUNT} XP** to bet but only have **{xp:,} XP**.",
                ephemeral=True,
            )
            return

        change_xp(guild_id, uid, -BET_AMOUNT)
        self.race_view.bets[uid] = (self.index, interaction.user.display_name)

        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="💰 Bets", value=self.race_view.bet_summary(), inline=False)
        await interaction.response.edit_message(embed=embed, view=self.race_view)
        await interaction.followup.send(
            f"🎰 Bet **{BET_AMOUNT} XP** on **{self.label}**! Win = **{BET_AMOUNT * 2} XP** back.",
            ephemeral=True,
        )


class StartButton(discord.ui.Button):
    def __init__(self, race_view: RaceView):
        super().__init__(label="🚦 Start Race!", style=discord.ButtonStyle.success, row=2)
        self.race_view = race_view

    async def callback(self, interaction: discord.Interaction):
        self.race_view.started = True
        self.disabled = True
        await interaction.response.edit_message(view=self.race_view)
        self.race_view.stop()


class HorsleCog(commands.Cog, name="Horsle"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="racestart", description="Start a horse race! Bet 100 XP before the race begins.")
    @require_setting("games_enabled")
    async def racestart(self, interaction: discord.Interaction):
        count = random.randint(4, 6)
        names = random.sample(HORSE_NAMES, count)
        emojis = HORSE_EMOJIS[:count]
        positions = [0] * count
        finished = []

        guild_id = interaction.guild_id or 0
        view = RaceView(names, guild_id)

        horses_list = "\n".join(f"{emojis[i]} **{name}**" for i, name in enumerate(names))
        embed = discord.Embed(
            title="🏟️ Horse Race — Place Your Bets!",
            description=(
                f"{horses_list}\n\n"
                f"*Click a horse to bet **{BET_AMOUNT} XP** on it. "
                f"Winners get **{BET_AMOUNT * 2} XP** back.*\n"
                f"*Race starts in 20s or click Start Race!*"
            ),
            color=discord.Color.yellow(),
        )
        embed.add_field(name="💰 Bets", value=view.bet_summary(), inline=False)

        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        try:
            await asyncio.wait_for(view.wait(), timeout=20)
        except asyncio.TimeoutError:
            pass

        for item in view.children:
            item.disabled = True

        # Race loop
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

            desc = render_race(positions, names, emojis, finished)

            if len(finished) == count:
                winner = names[finished[0]]
                race_embed = discord.Embed(
                    title="🏆 Race Over!",
                    description=desc + f"\n\n🥇 **{winner}** wins!",
                    color=discord.Color.gold(),
                )
            else:
                race_embed = discord.Embed(
                    title=f"🏟️ Racing...",
                    description=desc,
                    color=discord.Color.blurple(),
                )

            try:
                await msg.edit(embed=race_embed, view=view)
            except Exception:
                pass

            if len(finished) < count:
                await asyncio.sleep(1.2)

        # Pay out bets
        winning_horse = finished[0]
        payouts = []
        losses = []
        for uid, (horse_idx, display_name) in view.bets.items():
            if horse_idx == winning_horse:
                change_xp(guild_id, uid, BET_AMOUNT * 2)
                payouts.append(f"🎉 **{display_name}** +{BET_AMOUNT * 2:,} XP")
            else:
                losses.append(f"💸 **{display_name}** -{BET_AMOUNT:,} XP")

        if payouts or losses:
            result_text = "\n".join(payouts + losses)
            race_embed.add_field(name="Bet Results", value=result_text, inline=False)

        podium = "\n".join(
            f"{['🥇','🥈','🥉'][i] if i < 3 else f'#{i+1}'} {names[finished[i]]}"
            for i in range(len(finished))
        )
        race_embed.add_field(name="Final Standings", value=podium, inline=False)

        try:
            await msg.edit(embed=race_embed, view=view)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(HorsleCog(bot))
