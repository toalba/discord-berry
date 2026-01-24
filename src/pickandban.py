import json
import uuid
from discord import ui, Member, Interaction, Embed, SelectOption, Colour
import os
import discord
from dotenv import load_dotenv
from log_webhook import WebhookLogger
import asyncio
import random
import datetime
load_dotenv()
logger = WebhookLogger(os.getenv("WEBHOOK"))

def load_tournament_config():
    """Load tournament configuration from JSON file."""
    config_file = "tournament_config.json"
    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            return json.load(f)
    # Fallback to default config
    return {"tournaments": [{"id": "default", "name": "Default", "mappool": [], "stages": {}}]}

def get_tournament_by_id(tournament_id):
    """Get a specific tournament configuration by ID."""
    config = load_tournament_config()
    return next((t for t in config["tournaments"] if t["id"] == tournament_id), None)

# Load map pool once at module level (fallback for compatibility)
if os.path.exists("mappool.json"):
    with open("mappool.json", "r") as f:
        MAP_POOL = json.load(f)
else:
    MAP_POOL = []


class PickandBan:

    def __init__(
        self,
        rep_a: Member,
        rep_b: Member,
        interaction: Interaction,
        tournament_id: str,
        stage_name: str,
    ):
        self.uid = uuid.uuid4()
        
        # Load tournament configuration
        self.tournament = get_tournament_by_id(tournament_id)
        if not self.tournament:
            raise ValueError(f"Tournament {tournament_id} not found")
        
        if stage_name not in self.tournament["stages"]:
            raise ValueError(f"Stage {stage_name} not found in tournament {tournament_id}")
        
        self.stage_config = self.tournament["stages"][stage_name]
        self.stage_name = stage_name
        self.map_pool = self.tournament["mappool"]
        
        self.rep_a = rep_a
        self.rep_b = rep_b
        self.rep_a_msg = None
        self.rep_b_msg = None
        self.rep_a_view = None
        self.rep_b_view = None
        self.team_a, self.team_b = map(self.get_clantag, (rep_a.nick, rep_b.nick))
        self.interaction = interaction
        self.embed = PBEmbed(
            title=f"{self.team_a} vs {self.team_b}", 
            description=f"{self.uid}\n**Stage:** {stage_name}",
            ship_bans=self.stage_config["ship_bans"]
        )
        self.banned_maps = {self.team_a: [], self.team_b: []}
        self.picked_maps = {self.team_a: [], self.team_b: []}
        self.banned_ships = {self.team_a: [], self.team_b: []}
        self.stage = 0
        self.current_picker = self.rep_a.id
        self.decider_map = ""

    async def update_embed(self):
        # Handle Map Bans
        map_bans_required = self.stage_config["map_bans"]
        if map_bans_required > 0 and all(len(bans) >= map_bans_required for bans in self.banned_maps.values()):
            value = "\n".join(
                f"{', '.join(map_list)} **{team}**" for team, map_list in self.banned_maps.items() if map_list
            )
            edit_embeds(self.embed, "Banned Maps", value if value else "None")
            if self.stage == 0:
                mp = MapPickSelect(self)
                view = MapSelectView(mp)
                try:
                    self.rep_a_view = await self.rep_a.send(content="Pick a Map", view=view)
                except discord.HTTPException as e:
                    await logger.log(f"Error sending view to {self.rep_a.nick}: {e}")
                self.stage = 1
        
        # Handle Map Picks
        picked_map = ""
        for maps in self.picked_maps.values():
            picked_map += "".join(
                f'{i["map"]}, {i["spawn"]}\n' if "spawn" in i else f'{i["map"]}\n'
                for i in maps
                if "map" in i
            )
        picked_map = picked_map + self.decider_map if self.decider_map else picked_map
        edit_embeds(self.embed, "Picked Maps", picked_map if picked_map else "None")
        
        # Handle Ship Bans
        ship_bans_required = self.stage_config["ship_bans"]
        banned_ships_str = "None"
        if ship_bans_required > 0 and all(
            len(ships) >= ship_bans_required for ships in self.banned_ships.values()
        ):
            banned_ships_str = "\n".join(
                f"**{team}**: {', '.join(ships)}"
                for team, ships in self.banned_ships.items()
            )
            self.embed.color = Colour.brand_green()
            remove_embeds(self.embed, "Time until")
        
        if ship_bans_required > 0:
            edit_embeds(self.embed, "Banned Ships", banned_ships_str)
        
        # Use gather with return_exceptions to prevent one failure from breaking all updates
        results = await asyncio.gather(
            self.interaction.edit_original_response(embed=self.embed),
            self.rep_a_msg.edit(embed=self.embed),
            self.rep_b_msg.edit(embed=self.embed),
            return_exceptions=True
        )
        
        # Log any errors that occurred
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                target = ["interaction", "rep_a_msg", "rep_b_msg"][i]
                await logger.log(f"Error updating {target} embed in {self.uid}: {result}")

    async def start_rep_conversation(self):
        try:
            map_bans_required = self.stage_config["map_bans"]
            
            # If no map bans required, start with map picks
            if map_bans_required == 0:
                mp = MapPickSelect(self)
                view = MapSelectView(mp)
                # Send messages concurrently for better performance
                results = await asyncio.gather(
                    self.rep_a.send(embed=self.embed),
                    self.rep_b.send(embed=self.embed),
                    self.rep_a.send(content="Pick a Map", view=view),
                    return_exceptions=True
                )
                
                if not isinstance(results[0], Exception):
                    self.rep_a_msg = results[0]
                else:
                    await logger.log(f"Error sending embed to rep_a: {results[0]}")
                    
                if not isinstance(results[1], Exception):
                    self.rep_b_msg = results[1]
                else:
                    await logger.log(f"Error sending embed to rep_b: {results[1]}")
                    
                if not isinstance(results[2], Exception):
                    self.rep_a_view = results[2]
                else:
                    await logger.log(f"Error sending view to rep_a: {results[2]}")

            else:
                # Map bans required
                view = MapbanView(self)
                # Send messages concurrently for better performance
                results = await asyncio.gather(
                    self.rep_a.send(embed=self.embed),
                    self.rep_b.send(embed=self.embed),
                    self.rep_a.send(content="Please ban a Map", view=view),
                    self.rep_b.send(content="Please ban a Map", view=view),
                    return_exceptions=True
                )
                
                if not isinstance(results[0], Exception):
                    self.rep_a_msg = results[0]
                else:
                    await logger.log(f"Error sending embed to rep_a: {results[0]}")
                    
                if not isinstance(results[1], Exception):
                    self.rep_b_msg = results[1]
                else:
                    await logger.log(f"Error sending embed to rep_b: {results[1]}")
                    
                if not isinstance(results[2], Exception):
                    self.rep_a_view = results[2]
                else:
                    await logger.log(f"Error sending ban view to rep_a: {results[2]}")
                    
                if not isinstance(results[3], Exception):
                    self.rep_b_view = results[3]
                else:
                    await logger.log(f"Error sending ban view to rep_b: {results[3]}")
                    
        except Exception as e:
            await logger.log(f"Unexpected error in start_rep_conversation: {e}")

    

    def get_clantag(self, rep_name: str):
        return rep_name.split("[")[1].split("]")[0]
    
    def add_decider(self):
        tiebreaker_maps = self.stage_config.get("tiebreaker_maps", ["Riposte", "Ocean", "Shards"])
        available_maps = [m for m in tiebreaker_maps if m not in [item for sublist in self.banned_maps.values() for item in sublist]]
        if not available_maps:
            available_maps = tiebreaker_maps  # Fallback if all banned
        random_map = random.choice(available_maps)
        self.decider_map += f"**Decider Map**\n{random_map}, Alpha **({self.team_a})**\n"
        if self.stage_config["ship_bans"] == 0:
            self.embed.color = Colour.brand_green()


def edit_embeds(embed: Embed, field_name, new_value):
    a = [x for x in embed.fields if x.name == field_name][0]
    index = embed.fields.index(a)
    embed.remove_field(index)
    a.value = new_value
    embed.insert_field_at(index, name=a.name, value=a.value, inline=a.inline)

def remove_embeds(embed: Embed, field_name):
    a = [x for x in embed.fields if x.name == field_name][0]
    index = embed.fields.index(a)
    embed.remove_field(index)


class MapSelectView(ui.View):
    def __init__(self, select: ui.Select, timeout=60000):
        super().__init__(timeout=timeout)
        self.add_item(select)


class MapbanSelect(ui.Select):

    def __init__(self, pb: PickandBan):
        options = [SelectOption(label=i, value=i) for i in pb.map_pool]
        super().__init__(options=options)
        self.pb = pb

    async def callback(self, interaction: Interaction):
        if interaction.user.id == self.pb.rep_a.id:
            self.pb.banned_maps[self.pb.team_a].append(self.values[0])
            try:
                await self.pb.rep_a_view.delete()
            except discord.NotFound:
                pass  # Message already deleted
            except discord.HTTPException as e:
                await logger.log(f"Error deleting rep_a_view: {e}")
        elif interaction.user.id == self.pb.rep_b.id:
            self.pb.banned_maps[self.pb.team_b].append(self.values[0])
            try:
                await self.pb.rep_b_view.delete()
            except discord.NotFound:
                pass  # Message already deleted
            except discord.HTTPException as e:
                await logger.log(f"Error deleting rep_b_view: {e}")

        await self.pb.update_embed()
        await interaction.response.send_message(f"You banned {self.values[0]}")


class MapPickSelect(ui.Select):

    def __init__(self, pb: PickandBan):
        # Filter out all banned maps from both teams
        banned = set(pb.banned_maps[pb.team_a] + pb.banned_maps[pb.team_b])
        options = [
            SelectOption(label=i, value=i)
            for i in pb.map_pool
            if i not in banned
        ]
        super().__init__(options=options)
        self.pb = pb

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.pb.current_picker:
            await interaction.response.send_message("It's not your turn to pick a map.", ephemeral=True)
            return

        if interaction.user.id == self.pb.rep_a.id:
            self.pb.picked_maps[self.pb.team_a].append({"map": self.values[0]})
            try:
                await self.pb.rep_a_view.delete()
            except (discord.NotFound, discord.HTTPException) as e:
                await logger.log(f"Error deleting rep_a_view in MapPick: {e}")
            
            await interaction.response.send_message(f"You picked {self.values[0]}")
            await logger.log(
                f"{self.pb.uid}: {self.pb.team_a} picked {self.pb.picked_maps[self.pb.team_a]}"
            )
            self.pb.current_picker = self.pb.rep_b.id  # Now rep B picks spawn
            sp = SpawnSelect(self.pb, self.values[0])
            view = MapSelectView(sp)
            try:
                self.pb.rep_b_view = await self.pb.rep_b.send(content=sp.msg, view=view)
            except discord.HTTPException as e:
                await logger.log(f"Error sending spawn select to rep_b: {e}")

        elif interaction.user.id == self.pb.rep_b.id:
            self.pb.picked_maps[self.pb.team_b].append({"map": self.values[0]})
            try:
                await self.pb.rep_b_view.delete()
            except (discord.NotFound, discord.HTTPException) as e:
                await logger.log(f"Error deleting rep_b_view in MapPick: {e}")
            
            await interaction.response.send_message(f"You picked {self.values[0]}")
            await logger.log(
                f"{self.pb.uid}: {self.pb.team_b} picked {self.pb.picked_maps[self.pb.team_b]}"
            )
            self.pb.current_picker = self.pb.rep_a.id  # Now rep A picks spawn
            sp = SpawnSelect(self.pb, self.values[0])
            view = MapSelectView(sp)
            try:
                self.pb.rep_a_view = await self.pb.rep_a.send(content=sp.msg, view=view)
            except discord.HTTPException as e:
                await logger.log(f"Error sending spawn select to rep_a: {e}")

        await self.pb.update_embed()


class SpawnSelect(ui.Select):

    def __init__(self, pb: PickandBan, map: str):
        self.msg = f"Enemy picked: {map}"
        options = [
            SelectOption(label="Alpha"),
            SelectOption(label="Bravo"),
        ]
        super().__init__(options=options)
        self.pb = pb

    async def callback(self, interaction: Interaction):
        if interaction.user.id not in [self.pb.rep_a.id, self.pb.rep_b.id]:
            return

        if interaction.user.id == self.pb.rep_b.id and len(self.pb.picked_maps[self.pb.team_a]) > len(self.pb.picked_maps[self.pb.team_b]):
            self.pb.picked_maps[self.pb.team_a][-1].update(
                {"spawn": f"{self.values[0]} **({self.pb.team_b})**"}
            )
            try:
                await self.pb.rep_b_view.delete()
            except (discord.NotFound, discord.HTTPException) as e:
                await logger.log(f"Error deleting rep_b_view in SpawnSelect: {e}")
        elif interaction.user.id == self.pb.rep_a.id and len(self.pb.picked_maps[self.pb.team_b]) >= len(self.pb.picked_maps[self.pb.team_a]):
            self.pb.picked_maps[self.pb.team_b][-1].update(
                {"spawn": f"{self.values[0]} **({self.pb.team_a})**"}
            )
            try:
                await self.pb.rep_a_view.delete()
            except (discord.NotFound, discord.HTTPException) as e:
                await logger.log(f"Error deleting rep_a_view in SpawnSelect: {e}")
        else:
            await interaction.response.send_message("It's not your turn to pick spawn.", ephemeral=True)
            return

        await interaction.response.send_message(f"You picked {self.values[0]}")

        total_picks = len(self.pb.picked_maps[self.pb.team_a]) + len(self.pb.picked_maps[self.pb.team_b])
        map_picks_required = self.pb.stage_config["map_picks"] * 2  # 2 teams
        
        if total_picks < map_picks_required:
            next_picker = self.pb.rep_b if interaction.user.id == self.pb.rep_b.id else self.pb.rep_a
            next_picker_id = next_picker.id
            self.pb.current_picker = next_picker_id
            mp = MapPickSelect(self.pb)
            view = MapSelectView(mp)
            next_view_attr = "rep_b_view" if interaction.user.id == self.pb.rep_b.id else "rep_a_view"
            try:
                setattr(self.pb, next_view_attr, await next_picker.send(content="Pick a Map", view=view))
            except discord.HTTPException as e:
                await logger.log(f"Error sending map pick to {next_picker.nick}: {e}")
        else:
            # All map picks done
            if self.pb.stage_config.get("has_tiebreaker", False):
                self.pb.add_decider()
            
            ship_bans_required = self.pb.stage_config["ship_bans"]
            if ship_bans_required == 0:
                self.pb.embed.color = Colour.brand_green()
                await self.pb.update_embed()
                return
            
            view_a = ShipbanView(self.pb)
            view_b = ShipbanView(self.pb)
            try:
                self.pb.rep_a_view = await self.pb.rep_a.send(content="Ban a Ship", view=view_a)
            except discord.HTTPException as e:
                await logger.log(f"Error sending ship ban view to rep_a: {e}")
            try:
                self.pb.rep_b_view = await self.pb.rep_b.send(content="Ban a Ship", view=view_b)
            except discord.HTTPException as e:
                await logger.log(f"Error sending ship ban view to rep_b: {e}")

        await self.pb.update_embed()



class ShipbanModal(ui.Modal):

    def __init__(self, pb: PickandBan):
        super().__init__(title="Ship Ban")
        self.pb = pb
        ship_bans_required = pb.stage_config["ship_bans"]
        for i in range(ship_bans_required):
            self.add_item(
                ui.TextInput(label=f"Ship {i+1}", placeholder="Enter Ship Name")
            )

    async def on_submit(self, interaction: Interaction):
        try:
            team = self.pb.team_a if interaction.user.id == self.pb.rep_a.id else self.pb.team_b
            for i in self.children:
                self.pb.banned_ships[team].append(i.value)
            if interaction.user.id == self.pb.rep_a.id:
                try:
                    await self.pb.rep_a_view.delete()
                except (discord.NotFound, discord.HTTPException) as e:
                    await logger.log(f"Error deleting rep_a_view in ShipbanModal: {e}")
            else:
                try:
                    await self.pb.rep_b_view.delete()
                except (discord.NotFound, discord.HTTPException) as e:
                    await logger.log(f"Error deleting rep_b_view in ShipbanModal: {e}")
            await logger.log(f"{self.pb.uid}: {team} banned {self.pb.banned_ships[team]}")
            await interaction.response.send_message(f"You banned {self.pb.banned_ships}")
            await self.pb.update_embed()
        except Exception as e:
            await logger.log(f"Error in ShipbanModal: {e}")


class ShipbanView(ui.View):
    def __init__(self, pb: PickandBan):
        super().__init__(timeout=60000)
        self.pb = pb

    @ui.button(
        label="Ban Ship",
        style=discord.ButtonStyle.primary,
    )
    async def callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.send_modal(ShipbanModal(self.pb))


class MapbanView(ui.View):

    def __init__(self, pb: PickandBan):
        super().__init__(timeout=60000)
        self.add_item(MapbanSelect(pb))


class PBEmbed(Embed):

    def __init__(
        self,
        *,
        colour=None,
        color=Colour.dark_blue(),
        title=None,
        type="rich",
        url=None,
        description=None,
        timestamp=None,
        ship_bans=0,
    ):
        
        super().__init__(
            colour=colour,
            color=color,
            title=title,
            type=type,
            url=url,
            description=description,
            timestamp=timestamp,
        )
        timer = datetime.datetime.now() + datetime.timedelta(minutes=10)
        timer = discord.utils.format_dt(timer, style="R")
        self.add_field(name="Time until", value=timer, inline=False)
        self.add_field(name="Banned Maps", value=None, inline=False)
        self.add_field(name="Picked Maps", value=None, inline=False)
        if ship_bans > 0:
            self.add_field(name="Banned Ships", value=None, inline=False)
        self.set_footer(text="Enterprise I Bot by Rias_prpr")
