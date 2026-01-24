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

# Referee role ID
REFEREE_ROLE_ID = 1375423331720757289


def check_referee_role(interaction: discord.Interaction) -> bool:
    """Check if user has referee role or is admin."""
    if not interaction.guild:
        return False
    
    # interaction.user should already be a Member in guild context
    member = interaction.user
    if not hasattr(member, 'roles'):
        # Fallback: fetch member if needed
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False
    
    # Allow if user has referee role or admin permissions
    has_referee_role = any(role.id == REFEREE_ROLE_ID for role in member.roles)
    has_admin = member.guild_permissions.manage_guild
    
    return has_referee_role or has_admin


class Blarry(discord.ext.commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents, command_prefix="?")
        self.pick_bans = []
        self.active_tournaments = {}  # guild_id -> tournament_id mapping

    async def setup_hook(self):
        # Option 1: Guild-specific sync (instant, for development)
        guild_id = os.getenv("DEV_GUILD_ID")  # Add to .env: DEV_GUILD_ID=your_server_id
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"Commands synced to guild {guild_id} (instant)")
        
        # Option 2: Global sync (takes up to 1 hour to propagate)
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


def load_tournament_config():
    """Load tournament configuration from JSON file."""
    import json
    config_file = "tournament_config.json"
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return json.load(f)
    return {"tournaments": []}


async def tournament_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function for tournament selection."""
    config = load_tournament_config()
    tournaments = config.get("tournaments", [])
    return [
        app_commands.Choice(name=t["name"], value=t["id"])
        for t in tournaments
        if current.lower() in t["name"].lower() or current.lower() in t["id"].lower()
    ][:25]  # Discord limit


async def stage_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """Autocomplete function for stage selection based on selected tournament."""
    # Try to get tournament_id from namespace
    tournament_id = interaction.namespace.tournament_id if hasattr(interaction, 'namespace') else None
    
    # If no tournament_id specified, use active tournament for this guild
    if not tournament_id and interaction.guild_id:
        tournament_id = client.active_tournaments.get(interaction.guild_id)
    
    if not tournament_id:
        return []
    
    config = load_tournament_config()
    tournament = next((t for t in config["tournaments"] if t["id"] == tournament_id), None)
    
    if not tournament:
        return []
    
    stages = tournament.get("stages", {})
    return [
        app_commands.Choice(name=stage_name, value=stage_name)
        for stage_name in stages.keys()
        if current.lower() in stage_name.lower()
    ][:25]


@client.tree.command()
@app_commands.describe(
    rep_a="Team Captain A", 
    rep_b="Team Captain B", 
    stage_name="Stage of the Tournament",
    tournament_id="Tournament to use (optional, uses active tournament if not specified)"
)
@app_commands.autocomplete(tournament_id=tournament_autocomplete, stage_name=stage_autocomplete)
async def pick_ban(
    interaction: discord.Interaction,
    rep_a: discord.Member,
    rep_b: discord.Member,
    stage_name: str,
    tournament_id: str = None,
):
    # Check referee role
    if not check_referee_role(interaction):
        await interaction.response.send_message(
            "❌ You need the Referee role to use this command.",
            ephemeral=True
        )
        return
    
    if check_rep_format(rep_a, rep_b):
        await interaction.response.send_message(
            "At least one teamleader is missing a [Clantag]", ephemeral=True
        )
        return
    
    # Use active tournament if no tournament_id specified
    if not tournament_id:
        tournament_id = client.active_tournaments.get(interaction.guild_id)
        if not tournament_id:
            await interaction.response.send_message(
                "❌ No active tournament set!\n"
                "Admin must use `/set_active_tournament` first, or specify `tournament_id` parameter.",
                ephemeral=True
            )
            return
    
    try:
        pb = PickandBan(rep_a, rep_b, interaction, tournament_id, stage_name)
        client.add_pb(pb)
        await asyncio.gather(
            pb.start_rep_conversation(),
            interaction.response.send_message("Pick&Ban started", embed=pb.embed),
            logger.log(f"Pick&Ban started by {interaction.user} between {rep_a.nick} and {rep_b.nick} - Tournament: {tournament_id}, Stage: {stage_name}")
        )
    except ValueError as e:
        await interaction.response.send_message(f"Error: {str(e)}", ephemeral=True)
        await logger.log(f"Pick&Ban creation error: {e}")
    


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
@app_commands.describe(tournament_id="Tournament to set as active for this server")
@app_commands.autocomplete(tournament_id=tournament_autocomplete)
async def set_active_tournament(interaction: discord.Interaction, tournament_id: str):
    """Set the active tournament for this server (Admin only)"""
    config = load_tournament_config()
    tournament = next((t for t in config["tournaments"] if t["id"] == tournament_id), None)
    
    if not tournament:
        await interaction.response.send_message(f"❌ Tournament `{tournament_id}` not found!", ephemeral=True)
        return
    
    client.active_tournaments[interaction.guild_id] = tournament_id
    await interaction.response.send_message(
        f"✅ Active tournament set to: **{tournament['name']}** (`{tournament_id}`)\n"
        f"Referees can now use `/pick_ban` without specifying tournament_id.",
        ephemeral=True
    )
    await logger.log(f"Active tournament set to {tournament_id} in guild {interaction.guild.name} by {interaction.user}")


@client.tree.command()
@app_commands.describe(uuid="UUID of the Pick&Ban session to remove")
async def remove_pb(interaction: discord.Interaction, uuid: str):
    """Remove an active Pick&Ban session"""
    # Check referee role
    if not check_referee_role(interaction):
        await interaction.response.send_message(
            "❌ You need the Referee role to use this command.",
            ephemeral=True
        )
        return
    
    await client.remove_pb(uuid)
    await interaction.response.send_message("✅ Pick&Ban session deleted")


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
