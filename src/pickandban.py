import json
import uuid
from discord import ui, Member, Interaction, Embed, SelectOption, Colour
import os
import discord
from dotenv import load_dotenv
from log_webhook import WebhookLogger

load_dotenv()
logger = WebhookLogger(os.getenv("WEBHOOK"))


class PickandBan:

    def __init__(
        self,
        rep_a: Member,
        rep_b: Member,
        interaction: Interaction,
        tournamentstage: int,
    ):
        self.uid = uuid.uuid4()
        self.map_pool = None
        self.rep_a = rep_a
        self.rep_b = rep_b
        self.rep_a_msg = None
        self.rep_b_msg = None
        self.rep_a_view = None
        self.rep_b_view = None
        self.team_a, self.team_b = map(self.get_clantag, (rep_a.nick, rep_b.nick))
        self.interaction = interaction
        self.embed = PBEmbed(
            title=f"{self.team_a} vs {self.team_b}", description=self.uid
        )
        self.banned_maps = {self.team_a: None, self.team_b: None}
        self.picked_maps = {self.team_a: [], self.team_b: []}
        self.banned_ships = {self.team_a: [], self.team_b: []}
        self.stage = 0
        self.tournamentstage = tournamentstage

    async def update_embed(self):
        if all(self.banned_maps.values()):  # Checks if both teams have banned maps
            value = "\n".join(
                f"{map_name} **{team}**" for team, map_name in self.banned_maps.items()
            )
            edit_embeds(self.embed, "Banned Maps", value)
            mp = MapPickSelect(self)
            if self.stage == 0:
                self.rep_a_view = await self.rep_a.send(
                    content="Pick a Map", view=ui.View().add_item(mp)
                )
                self.stage = 1
        picked_map = ""
        for maps in self.picked_maps.values():
            picked_map += "".join(
                f'{i["map"]}, {i["spawn"]}\n' if "spawn" in i else f'{i["map"]}\n'
                for i in maps
                if "map" in i
            )
        edit_embeds(self.embed, "Picked Maps", picked_map)
        banned_ships_str = "None"
        if all(
            len(ships) >= self.tournamentstage for ships in self.banned_ships.values()
        ):  # len of ship has to be variable later
            banned_ships_str = "\n".join(
                f"**{team}**: {', '.join(ships)}"
                for team, ships in self.banned_ships.items()
            )
            self.embed.color = Colour.brand_green()
        edit_embeds(self.embed, "Banned Ships", banned_ships_str)
        await self.interaction.edit_original_response(embed=self.embed)
        await self.rep_a_msg.edit(embed=self.embed)
        await self.rep_b_msg.edit(embed=self.embed)

    async def start_rep_conversation(self):
        view = MapbanView(self)

        self.rep_a_msg = await self.rep_a.send(embed=self.embed)
        self.rep_b_msg = await self.rep_b.send(embed=self.embed)
        self.rep_a_view = await self.rep_a.send(content="Please ban a Map", view=view)
        self.rep_b_view = await self.rep_b.send(content="Please ban a Map", view=view)

    def get_clantag(self, rep_name: str):
        return rep_name.split("[")[1].split("]")[0]


def edit_embeds(embed: Embed, field_name, new_value):
    a = [x for x in embed.fields if x.name == field_name][0]
    index = embed.fields.index(a)
    embed.remove_field(index)
    a.value = new_value
    embed.insert_field_at(index, name=a.name, value=a.value, inline=a.inline)


class MapbanSelect(ui.Select):

    def __init__(self, pb: PickandBan):
        # created out of map json
        options = []
        # Load map pool from JSON file
        with open("mappool.json", "r") as f:
            maps = json.load(f)
            for i in maps:
                options.append(SelectOption(label=i, value=i))
        super().__init__(options=options)
        self.pb = pb

    async def callback(self, interaction: Interaction):
        if interaction.user.name == self.pb.rep_a.name:
            self.pb.banned_maps[self.pb.team_a] = self.values[0]
            await self.pb.rep_a_view.delete()
        if interaction.user.name == self.pb.rep_b.name:
            self.pb.banned_maps[self.pb.team_b] = self.values[0]
            await self.pb.rep_b_view.delete()
        await self.pb.update_embed()
        await interaction.response.send_message(f"You banned {self.values[0]}")


class MapPickSelect(ui.Select):

    def __init__(self, pb: PickandBan):

        # created out of map json - banned maps#
        options = []
        # Load map pool from JSON file
        with open("mappool.json", "r") as f:
            maps = json.load(f)
            for i in maps:
                if i != pb.banned_maps[pb.team_a] and i != pb.banned_maps[pb.team_b]:
                    options.append(SelectOption(label=i, value=i))
        super().__init__(options=options)
        self.pb = pb

    async def callback(self, interaction: Interaction):
        if interaction.user.name == self.pb.rep_a.name:
            self.pb.picked_maps[self.pb.team_a].append({"map": self.values[0]})
            await self.pb.rep_a_view.delete()
            await interaction.response.send_message(f"You picked {self.values[0]}")
            await logger.log(
                f"{self.pb.uid}: {self.pb.team_a} picked {self.pb.picked_maps[self.pb.team_a]}"
            )
            sp = SpawnSelect(self.pb, self.values[0])
            self.pb.rep_b_view = await self.pb.rep_b.send(
                content=sp.msg, view=ui.View().add_item(sp)
            )
        if interaction.user.name == self.pb.rep_b.name:
            self.pb.picked_maps[self.pb.team_b].append({"map": self.values[0]})
            await self.pb.rep_b_view.delete()
            await interaction.response.send_message(f"You picked {self.values[0]}")
            await logger.log(
                f"{self.pb.uid}: {self.pb.team_b} picked {self.pb.picked_maps[self.pb.team_b]}"
            )
            sp = SpawnSelect(self.pb, self.values[0])
            self.pb.rep_a_view = await self.pb.rep_a.send(
                content=sp.msg, view=ui.View().add_item(sp)
            )
        await self.pb.update_embed()


class SpawnSelect(ui.Select):

    def __init__(self, pb: PickandBan, map: str):

        # created out of map json - banned maps
        self.msg = f"Enemy picked: {map}"
        options = [
            SelectOption(label="Alpha"),
            SelectOption(label="Bravo"),
        ]
        super().__init__(options=options)
        self.pb = pb

    async def callback(self, interaction: Interaction):
        if interaction.user.name == self.pb.rep_a.name:
            self.pb.picked_maps[self.pb.team_b][-1].update(
                {"spawn": f"{self.values[0]} **({self.pb.team_a})**"}
            )
            await self.pb.rep_a_view.delete()
            await interaction.response.send_message(f"You picked {self.values[0]}")
            if (
                not len(self.pb.picked_maps[self.pb.team_a])
                + len(self.pb.picked_maps[self.pb.team_b])
                >= 2
            ):
                mp = MapPickSelect(self.pb)
                self.pb.rep_a_view = await self.pb.rep_a.send(
                    content="Pick a Map", view=ui.View().add_item(mp)
                )
        if interaction.user.name == self.pb.rep_b.name:
            self.pb.picked_maps[self.pb.team_a][-1].update(
                {"spawn": f"{self.values[0]} **({self.pb.team_b})**"}
            )
            await self.pb.rep_b_view.delete()
            await interaction.response.send_message(f"You picked {self.values[0]}")
            if (
                not len(self.pb.picked_maps[self.pb.team_a])
                + len(self.pb.picked_maps[self.pb.team_b])
                >= 2
            ):
                mp = MapPickSelect(self.pb)
                self.pb.rep_b_view = await self.pb.rep_b.send(
                    content="Pick a Map", view=ui.View().add_item(mp)
                )
        if (
            len(self.pb.picked_maps[self.pb.team_a])
            + len(self.pb.picked_maps[self.pb.team_b])
            >= 2
        ):
            # Randomly selected decider map with a has alpha spawn
            mpa = ShipbanView(self.pb)
            self.pb.rep_a_view = await self.pb.rep_a.send(
                content="Ban a Ship", view=mpa
            )
            mpb = ShipbanView(self.pb)
            self.pb.rep_b_view = await self.pb.rep_b.send(
                content="Ban a Ship", view=mpb
            )
        await self.pb.update_embed()


class ShipbanModal(ui.Modal):

    def __init__(self, pb: PickandBan):
        super().__init__(title="Ship Ban")
        self.pb = pb
        for i in range(self.pb.tournamentstage):
            self.add_item(
                ui.TextInput(label=f"Ship {i+1}", placeholder="Enter Ship Name")
            )

    async def on_submit(self, interaction: Interaction):
        if interaction.user.name == self.pb.rep_a.name:
            for i in self.children:
                self.pb.banned_ships[self.pb.team_a].append(i.value)
            await self.pb.rep_a_view.delete()
            await logger.log(
                f"{self.pb.uid}: {self.pb.team_a} banned {self.pb.banned_ships[self.pb.team_a]}"
            )
        if interaction.user.name == self.pb.rep_b.name:
            for i in self.children:
                self.pb.banned_ships[self.pb.team_b].append(i.value)
            await self.pb.rep_b_view.delete()
            await logger.log(
                f"{self.pb.uid}: {self.pb.team_b} banned {self.pb.banned_ships[self.pb.team_b]}"
            )
        await interaction.response.send_message(f"You banned {self.pb.banned_ships}")
        await self.pb.update_embed()


class ShipbanView(ui.View):
    def __init__(self, pb: PickandBan):
        super().__init__()
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
        super().__init__()
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
        self.add_field(name="Banned Maps", value=None, inline=False)
        self.add_field(name="Picked Maps", value=None, inline=False)
        self.add_field(name="Banned Ships", value=None, inline=False)
        self.set_footer(text="Enterprise I Bot by Rias_prpr")
