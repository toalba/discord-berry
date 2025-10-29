# This example requires the 'message_content' intent.

import discord
from discord.ext import commands
from discord import app_commands
from pickandban import PickandBan, ShipbanView
from log_webhook import WebhookLogger
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

logger = WebhookLogger(os.getenv("WEBHOOK"))


class Blarry(discord.ext.commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents, command_prefix="?")
        self.pick_bans = []

    async def setup_hook(self):
        # Sync commands globally to work on all servers
        # Note: Global command sync can take up to 1 hour to propagate
        await self.tree.sync()
        print("Commands synced globally")

    def add_pb(self, pb):
        self.pick_bans.append(pb)

    async def remove_pb(self, pb_uid):
        pb = next((obj for obj in self.pick_bans if str(obj.uid) == pb_uid), None)
        if pb is not None:
            # Use gather with return_exceptions to delete all messages even if some fail
            delete_tasks = []
            if pb.rep_a_msg:
                delete_tasks.append(pb.rep_a_msg.delete())
            if pb.rep_a_view:
                delete_tasks.append(pb.rep_a_view.delete())
            if pb.rep_b_msg:
                delete_tasks.append(pb.rep_b_msg.delete())
            if pb.rep_b_view:
                delete_tasks.append(pb.rep_b_view.delete())
            delete_tasks.append(pb.interaction.delete_original_response())
            
            results = await asyncio.gather(*delete_tasks, return_exceptions=True)
            
            # Log any deletion errors
            for i, result in enumerate(results):
                if isinstance(result, Exception) and not isinstance(result, discord.NotFound):
                    await logger.log(f"Error deleting message in remove_pb: {result}")
            
            self.pick_bans.remove(pb)
            await logger.log(
                f"Pick&Ban removed by {pb.interaction.user} between {pb.rep_a.nick} and {pb.rep_b.nick}"
            )
            del pb
        else:
            await logger.log(f"Pick&Ban not found for uuid {pb_uid}")


intents = discord.Intents.default()
intents.message_content = True
client = Blarry(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")
    await logger.log(f"We have logged in as {client.user}")


async def cleanup():
    """Cleanup function to close resources properly on shutdown."""
    print("Starting cleanup...")
    
    # Close all active pick&ban sessions
    for pb in client.pick_bans[:]:  # Copy list to avoid modification during iteration
        try:
            await client.remove_pb(str(pb.uid))
        except Exception as e:
            print(f"Error cleaning up pick&ban {pb.uid}: {e}")
    
    # Close webhook logger session
    try:
        await logger.close()
    except Exception as e:
        print(f"Error closing logger: {e}")
    
    print("Cleanup complete.")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("?berry"):
        await message.channel.send("Hey I am Berry")


def check_rep_format(rep_a: discord.Member, rep_b: discord.Member) -> bool:
    try:
        rep_a.nick.split("[")[1].split("]")[0]  # type: ignore
        rep_b.nick.split("[")[1].split("]")[0]  # type: ignore
    except:
        return True
    return False


@client.tree.command()
@app_commands.default_permissions(manage_guild=True)
@app_commands.describe(
    rep_a="Team Captain A", rep_b="Team Captain B", stage="Stage of the Tournament"
)
@app_commands.choices(
    stage=[
        app_commands.Choice(name="Group Stage", value=2),
        app_commands.Choice(name="KO Stage", value=3),
    ]
)
async def pick_ban(
    interaction: discord.Interaction,
    rep_a: discord.Member,
    rep_b: discord.Member,
    stage: app_commands.Choice[int],
):
    if check_rep_format(rep_a, rep_b):
        await interaction.response.send_message(
            "At least one teamleader is missing a [Clantag]"
        )
        return
    pb = PickandBan(rep_a, rep_b, interaction, stage.value)
    client.add_pb(pb)
    await asyncio.gather(
        pb.start_rep_conversation(),
        interaction.response.send_message("Pick&Ban started", embed=pb.embed),
        logger.log(f"Pick&Ban started by {interaction.user} between {rep_a.nick} and {rep_b.nick}")
    )
    


@pick_ban.error
async def pick_ban_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need 'Manage Server' permission to use this command", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while processing the command", ephemeral=True)
    await logger.log(
        f"Error: {error} \n User: {interaction.user} \n Command: {interaction.command.name} \n Guild: {interaction.guild.name} \n Channel: {interaction.channel.name}"  # type: ignore
    )


@client.tree.command()
@app_commands.default_permissions(manage_guild=True)
async def remove_pb(interaction: discord.Interaction, uuid: str):
    await client.remove_pb(uuid)
    await interaction.response.send_message("Deleted")


@remove_pb.error
async def remove_pb_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need 'Manage Server' permission to use this command", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while processing the command", ephemeral=True)
    await logger.log(
        f"Error: {error} \n User: {interaction.user} \n Command: {interaction.command.name} \n Guild: {interaction.guild.name} \n Channel: {interaction.channel.name}"  # type: ignore
    )


# Run bot with proper cleanup
try:
    client.run(os.getenv("TOKEN"))
except KeyboardInterrupt:
    print("Bot shutdown requested...")
finally:
    # Run cleanup in the event loop
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(cleanup())
    else:
        loop.run_until_complete(cleanup())
