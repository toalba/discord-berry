from discord import Webhook
import aiohttp


class WebhookLogger:

    def __init__(self, url):
        self.url = url

    async def log(self, msg):
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(self.url, session=session)
            await webhook.send(
                msg,
                username="Berryhook",
                avatar_url="https://cdn.discordapp.com/attachments/1131166133471420476/1344715401417986131/Blueberry_sticker3.png?ex=67c9d44f&is=67c882cf&hm=fe280d81e847fca00354c3ca94d292e401ebd014f29b2ee63d9f6b091ef7e828&",
            )
