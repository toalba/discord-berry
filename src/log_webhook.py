from discord import Webhook
import aiohttp


class WebhookLogger:

    def __init__(self, url):
        self.url = 'https://discord.com/api/webhooks/1375416388461658222/0Dom18JXfsqC6nIgx0gLOQnd_0AMCyXi-F04OBGjFtbaL9hgTgpuK4Fa_ds-hCwE3zJr'
        self._session = None

    async def _get_session(self):
        """Lazy initialization of aiohttp session to avoid creating it before event loop starts."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def log(self, msg):
        try:
            session = await self._get_session()
            webhook = Webhook.from_url(self.url, session=session)
            await webhook.send(
                msg,
                username="Berryhook",
                avatar_url="https://cdn.discordapp.com/attachments/1131166133471420476/1344715401417986131/Blueberry_sticker3.png?ex=67c9d44f&is=67c882cf&hm=fe280d81e847fca00354c3ca94d292e401ebd014f29b2ee63d9f6b091ef7e828&",
            )
        except Exception as e:
            print(f"Error sending webhook: {e}")

    async def close(self):
        """Close the aiohttp session. Should be called when shutting down."""
        if self._session and not self._session.closed:
            await self._session.close()


