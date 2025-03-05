# This example requires the 'message_content' intent.

import discord
import json
import random
from discord import ui
from discord import app_commands
from discord.ext import commands
import uuid

import os
from dotenv import load_dotenv
load_dotenv() 

MY_GUILD = discord.Object(id=os.getenv('DC-GUILD'))  # replace with your guild id


class Blarry(discord.ext.commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents, command_prefix = "?")
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
            print('Pick&Ban removed succesfully')

intents = discord.Intents.default()
intents.message_content = True
client = Blarry(intents=intents)



@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('?berry'):
        await message.channel.send('Hey I am Berry')


@client.tree.command()
#@app_commands.checks.has_role(1013754809494556673)
@app_commands.describe(
    rep_a='Team Captain A',
    rep_b='Team Captain B'
)
async def pick_ban(interaction: discord.Interaction, rep_a: discord.Member, rep_b: discord.Member):
    select = ui.Select(options=[discord.SelectOption(label='P&B')])
    pb = PickandBan(rep_a,rep_b, interaction)
    client.add_pb(pb)
    await pb.start_rep_conversation()
    await interaction.response.send_message(embed=pb.embed)

@client.tree.command()
#@app_commands.checks.has_role(1013754809494556673)
async def remove_pb(interaction: discord.Interaction, uuid: str):
    await client.remove_pb(uuid)
    await interaction.response.send_message('Deleted')

@pick_ban.error
async def pick_ban_error(interaction: discord.Interaction, error):
    await interaction.response.send_message('You are not blue enough to do this')


class PickandBan():

    def __init__(self,rep_a: discord.Member ,rep_b: discord.Member, interaction: discord.Interaction):
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
        self.embed = PBEmbed(title=f'{self.team_a} vs {self.team_b}',description=self.uid)
        self.banned_maps = {
            self.team_a: None,
            self.team_b: None
        }
        self.picked_maps = {
            self.team_a: [],
            self.team_b: []
        }
        self.banned_ships = {
            self.team_a: [],
            self.team_b: []
        }
        self.stage = 0

    async def update_embed(self):
        print(self.banned_maps)
        print(self.picked_maps)
        if all(self.banned_maps.values()):  # Checks if both teams have banned maps
            value = '\n'.join(f'{map_name} **{team}**' for team, map_name in self.banned_maps.items())
            edit_embeds(self.embed,'Banned Maps', value)
            mp = MapPickSelect(self)
            if self.stage == 0:
                self.rep_a_view = await self.rep_a.send(content='Pick a Map',view=ui.View().add_item(mp))
                self.stage=1
        picked_map=''
        for maps in self.picked_maps.values():
            picked_map += "".join(f'{i["map"]}, {i["spawn"]}\n' if "spawn" in i else f'{i["map"]}\n' for i in maps if "map" in i)
        edit_embeds(self.embed,'Picked Maps', picked_map)
        banned_ships_str = 'None'
        if all(len(ships) >= 2 for ships in self.banned_ships.values()):
            banned_ships_str = "\n".join(f"**{team}**: {', '.join(ships)}" for team, ships in self.banned_ships.items())
            self.embed.color = discord.Colour.brand_green()
        edit_embeds(self.embed,'Banned Ships', banned_ships_str)
        await self.interaction.edit_original_response(embed=self.embed)
        await self.rep_a_msg.edit(embed=self.embed)
        await self.rep_b_msg.edit(embed=self.embed)



    async def start_rep_conversation(self):
        view = MapbanView(self)

        self.rep_a_msg = await self.rep_a.send(embed=self.embed)
        self.rep_b_msg = await self.rep_b.send(embed=self.embed)
        self.rep_a_view = await self.rep_a.send(content='Please ban a Map',view=view)
        self.rep_b_view = await self.rep_b.send(content='Please ban a Map',view=view)
        

    def get_clantag(self, rep_name: str):
        return rep_name.split("[")[1].split(']')[0]

def edit_embeds(embed: discord.Embed, field_name, new_value):
        a = [x for x in embed.fields if x.name==field_name][0]
        index = embed.fields.index(a)
        embed.remove_field(index)
        a.value =  new_value
        embed.insert_field_at(index,name=a.name,value=a.value,inline=a.inline)


class MapbanSelect(ui.Select):

    def __init__(self, pb: PickandBan):
        # created out of map json
        options=[
            discord.SelectOption(label='Ocean',),
            discord.SelectOption(label='Sleeper')
        ]
        super().__init__(options=options)
        self.pb = pb
        

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.name == self.pb.rep_a.name:
            self.pb.banned_maps[self.pb.team_a] = self.values[0]
            await self.pb.rep_a_view.delete()
        if interaction.user.name == self.pb.rep_b.name:
            self.pb.banned_maps[self.pb.team_b] = self.values[0]
            await self.pb.rep_b_view.delete()
        await self.pb.update_embed()
        await interaction.response.send_message(f'You banned {self.values[0]}')

class MapPickSelect(ui.Select):

    def __init__(self, pb: PickandBan):

        # created out of map json - banned maps
        options=[
            discord.SelectOption(label='North'),
            discord.SelectOption(label='Hotspot'),
            discord.SelectOption(label='Ripost')

        ]
        super().__init__(options=options)
        self.pb = pb
        

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.name == self.pb.rep_a.name:
            self.pb.picked_maps[self.pb.team_a].append({'map': self.values[0]})
            await self.pb.rep_a_view.delete()
            await interaction.response.send_message(f'You picked {self.values[0]}')
            sp = SpawnSelect(self.pb,self.values[0])
            self.pb.rep_b_view = await self.pb.rep_b.send(content=sp.msg,view=ui.View().add_item(sp))
        if interaction.user.name == self.pb.rep_b.name:
            self.pb.picked_maps[self.pb.team_b].append({'map': self.values[0]})
            await self.pb.rep_b_view.delete()
            await interaction.response.send_message(f'You picked {self.values[0]}')
            sp = SpawnSelect(self.pb,self.values[0])
            self.pb.rep_a_view = await self.pb.rep_a.send(content=sp.msg,view=ui.View().add_item(sp))
        await self.pb.update_embed()

class SpawnSelect(ui.Select):
    
    def __init__(self, pb: PickandBan, map: str):

        # created out of map json - banned maps
        self.msg = f"Enemy picked: {map}"
        options=[
            discord.SelectOption(label='Alpha'),
            discord.SelectOption(label='Bravo'),
        ]
        super().__init__(options=options)
        self.pb = pb
        

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.name == self.pb.rep_a.name:
            self.pb.picked_maps[self.pb.team_b][-1].update({'spawn': f'{self.values[0]} **({self.pb.team_a})**'})
            await self.pb.rep_a_view.delete()
            await interaction.response.send_message(f'You picked {self.values[0]}')
            if not len(self.pb.picked_maps[self.pb.team_a]) + len(self.pb.picked_maps[self.pb.team_b]) >= 2:
                mp = MapPickSelect(self.pb)
                self.pb.rep_a_view = await self.pb.rep_a.send(content='Pick a Map',view=ui.View().add_item(mp))
        if interaction.user.name == self.pb.rep_b.name:
            self.pb.picked_maps[self.pb.team_a][-1].update({'spawn': f'{self.values[0]} **({self.pb.team_b})**'})
            await self.pb.rep_b_view.delete()
            await interaction.response.send_message(f'You picked {self.values[0]}')
            if not len(self.pb.picked_maps[self.pb.team_a]) + len(self.pb.picked_maps[self.pb.team_b]) >= 2:
                mp = MapPickSelect(self.pb)
                self.pb.rep_b_view = await self.pb.rep_b.send(content='Pick a Map',view=ui.View().add_item(mp))
        if len(self.pb.picked_maps[self.pb.team_a]) + len(self.pb.picked_maps[self.pb.team_b]) >= 2:
                mpa = ShipbanSelect(self.pb)
                self.pb.rep_a_view = await self.pb.rep_a.send(content='Ban a Ship',view=ui.View().add_item(mpa))
                mpb = ShipbanSelect(self.pb)
                self.pb.rep_b_view = await self.pb.rep_b.send(content='Ban a Ship',view=ui.View().add_item(mpb))
        await self.pb.update_embed()

class ShipbanSelect(ui.Select):

    def __init__(self, pb: PickandBan):
        # created out of map json
        options=[
            discord.SelectOption(label='Kleber',),
            discord.SelectOption(label='Marseille'),
            discord.SelectOption(label='Tard'),

        ]
        super().__init__(options=options)
        self.pb = pb
        

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.name == self.pb.rep_a.name:
            self.pb.banned_ships[self.pb.team_a].append(self.values[0])
            await self.pb.rep_a_view.delete()
            await interaction.response.send_message(f'You banned {self.values[0]}')
            if not len(self.pb.banned_ships[self.pb.team_a]) >= 2:
                mp = ShipbanSelect(self.pb)
                self.pb.rep_a_view = await self.pb.rep_a.send(content='Ban a Ship',view=ui.View().add_item(mp))
        if interaction.user.name == self.pb.rep_b.name:
            self.pb.banned_ships[self.pb.team_b].append(self.values[0])
            await self.pb.rep_b_view.delete()
            await interaction.response.send_message(f'You banned {self.values[0]}')
            if not len(self.pb.banned_ships[self.pb.team_b]) >= 2:
                mp = ShipbanSelect(self.pb)
                self.pb.rep_b_view = await self.pb.rep_b.send(content='Ban a Ship',view=ui.View().add_item(mp))
        await self.pb.update_embed()

class MapbanView(ui.View):

    def __init__(self, pb: PickandBan):
        super().__init__()
        self.add_item(MapbanSelect(pb))

class PBEmbed(discord.Embed):

    def __init__(self, *, colour = None, color = discord.Colour.dark_blue(), title = None, type = 'rich', url = None, description = None, timestamp = None):
        super().__init__(colour=colour, color=color, title=title, type=type, url=url, description=description, timestamp=timestamp)
        self.add_field(name='Banned Maps',value=None, inline=False)
        self.add_field(name='Picked Maps',value=None, inline=False)
        self.add_field(name='Banned Ships',value=None, inline=False)




client.run(os.getenv('TOKEN'))


# Add point system for berry sticker