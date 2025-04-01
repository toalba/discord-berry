class ShipbanSelect(ui.Select):

    def __init__(self, pb: PickandBan):
        # created out of map json
        options=[
            SelectOption(label='Kleber',),
            SelectOption(label='Marseille'),
            SelectOption(label='Tard'),

        ]
        super().__init__(options=options)
        self.pb = pb
        

    async def callback(self, interaction: Interaction):
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