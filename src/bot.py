# This example requires the 'message_content' intent.

import discord
from discord.ext import commands
from discord import app_commands
from pickandban import PickandBan, ShipbanView
from log_webhook import WebhookLogger

import os
from dotenv import load_dotenv

load_dotenv()

MY_GUILD = discord.Object(id=os.getenv("DC-GUILD"))  # replace with your guild id
logger = WebhookLogger(os.getenv("WEBHOOK"))


class Blarry(discord.ext.commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents, command_prefix="?")
        self.pick_bans = []

    async def setup_hook(self):
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

    def add_pb(self, pb):
        self.pick_bans.append(pb)

    async def remove_pb(self, pb_uid):
        pb = next((obj for obj in self.pick_bans if str(obj.uid) == pb_uid), None)
        if pb is not None:
            await pb.rep_a_msg.delete()
            await pb.rep_a_view.delete()
            await pb.rep_b_msg.delete()
            await pb.rep_b_view.delete()
            await pb.interaction.delete_original_response()
            self.pick_bans.remove(pb)
            del pb
            print("Pick&Ban removed succesfully")


intents = discord.Intents.default()
intents.message_content = True
client = Blarry(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    await logger.log(f"We have logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("?berry"):
        await message.channel.send("Hey I am Berry")


def check_rep_format(rep_a: discord.Member, rep_b: discord.Member) -> bool:
    try:
        rep_a.nick.split("[")[1].split("]")[0]
        rep_b.nick.split("[")[1].split("]")[0]
    except:
        return True
    return False


@client.tree.command()
# @app_commands.checks.has_role(1013754809494556673)
@app_commands.describe(
    rep_a="Team Captain A", rep_b="Team Captain B", stage="Stage of the Tournament"
)
@app_commands.choices(
    stage=[
        app_commands.Choice(name="2nd Group Stage", value=1),
        app_commands.Choice(name="KO Stage", value=2),
        app_commands.Choice(name="Finals", value=3),
    ]
)
async def pick_ban(
    interaction: discord.Interaction,
    rep_a: discord.Member,
    rep_b: discord.Member,
    stage: app_commands.Choice[int]
):
    if check_rep_format(rep_a, rep_b):
        await interaction.response.send_message(
            "At least one teamleader is missing a [Clantag]"
        )
        return
    pb = PickandBan(rep_a, rep_b, interaction, stage.value)
    client.add_pb(pb)
    await pb.start_rep_conversation()
    await interaction.response.send_message("Pick&Ban started", embed=pb.embed)
    await logger.log(
        f"Pick&Ban started by {interaction.user} between {rep_a.nick} and {rep_b.nick}"
    )


@pick_ban.error
async def pick_ban_error(interaction: discord.Interaction, error):
    await interaction.response.send_message("You are not blue enough to do this")
    await logger.log(
        f"Error: {error} \n User: {interaction.user} \n Command: {interaction.command.name} \n Guild: {interaction.guild.name} \n Channel: {interaction.channel.name}"
    )


@client.tree.command()
# @app_commands.checks.has_role(1013754809494556673)
async def remove_pb(interaction: discord.Interaction, uuid: str):
    await client.remove_pb(uuid)
    await interaction.response.send_message("Deleted")


@client.tree.command()
async def test(
    interaction: discord.Interaction, rep_a: discord.Member, rep_b: discord.Member
):
    pb = PickandBan(rep_a, rep_b, interaction, stage=1)  # Default stage value set to 1
    pb.rep_a_view = await pb.rep_a.send(content="Start Ship ban", view=ShipbanView(pb))
    await interaction.response.send_message("Pick&Ban started", ephemeral=True)
    await logger.log(
        f"Pick&Ban started by {interaction.user} between {rep_a.nick} and {rep_b.nick}"
    )


client.run(os.getenv("TOKEN"))
