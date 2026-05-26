import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio

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
FINISH = "🏁"
LANE_PAD = 18


def render_race(positions: list[int], names: list[str], emojis: list[str], finished: list[int]) -> str:
    lines = []
    for i, (pos, name, emoji) in enumerate(zip(positions, names, emojis)):
        track = [" "] * TRACK_LENGTH
        horse_pos = min(pos, TRACK_LENGTH - 1)
        track[horse_pos] = emoji
        bar = "".join(track)
        medal = ""
        if i in finished:
            place = finished.index(i) + 1
            medal = ["🥇", "🥈", "🥉"][place - 1] if place <= 3 else f"#{place}"
        label = name[:LANE_PAD].ljust(LANE_PAD)
        lines.append(f"`{label}` {bar}{FINISH} {medal}")
    return "\n".join(lines)


class HorsleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=15)
        self.ready = False

    @discord.ui.button(label="🚦 Start Race Now!", style=discord.ButtonStyle.success)
    async def start_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.ready = True
        button.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class HorsleCog(commands.Cog, name="Horsle"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="racestart", description="Watch chaotic horse racing in real time!")
    async def racestart(self, interaction: discord.Interaction):
        count = random.randint(4, 6)
        names = random.sample(HORSE_NAMES, count)
        emojis = HORSE_EMOJIS[:count]
        positions = [0] * count
        finished = []

        view = HorsleView()

        embed = discord.Embed(
            title="🏟️ Horse Race — Starting Soon!",
            description=(
                "The horses are lining up at the gate...\n\n"
                + render_race(positions, names, emojis, finished)
                + "\n\n*Race begins in 10 seconds or click the button!*"
            ),
            color=discord.Color.yellow(),
        )
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        # Wait up to 10s or until button pressed
        await asyncio.wait_for(
            asyncio.shield(asyncio.get_event_loop().run_in_executor(None, lambda: None)),
            timeout=0
        ) if False else None

        try:
            await asyncio.wait_for(view.wait(), timeout=10)
        except asyncio.TimeoutError:
            pass

        # Disable the view
        for item in view.children:
            item.disabled = True

        # Race loop
        tick = 0
        while len(finished) < count:
            tick += 1
            for i in range(count):
                if i in finished:
                    continue
                # Random step: 0, 1, or 2 spaces
                move = random.choices([0, 1, 2], weights=[20, 55, 25])[0]
                positions[i] += move
                if positions[i] >= TRACK_LENGTH - 1:
                    positions[i] = TRACK_LENGTH - 1
                    if i not in finished:
                        finished.append(i)

            desc = render_race(positions, names, emojis, finished)

            if len(finished) == count:
                winner = names[finished[0]]
                embed = discord.Embed(
                    title="🏆 Horse Race — Race Over!",
                    description=desc + f"\n\n🥇 **{winner}** wins!",
                    color=discord.Color.gold(),
                )
            else:
                embed = discord.Embed(
                    title=f"🏟️ Horse Race — Lap {tick}",
                    description=desc,
                    color=discord.Color.blurple(),
                )

            try:
                await msg.edit(embed=embed, view=view)
            except Exception:
                pass

            if len(finished) < count:
                await asyncio.sleep(1.2)

        # Final podium
        podium = "\n".join(
            f"{['🥇','🥈','🥉'][i] if i < 3 else f'#{i+1}'} {names[finished[i]]}"
            for i in range(len(finished))
        )
        embed.add_field(name="Final Standings", value=podium, inline=False)
        try:
            await msg.edit(embed=embed, view=view)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(HorsleCog(bot))
