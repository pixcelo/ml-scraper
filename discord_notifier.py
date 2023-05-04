from discord_webhook import DiscordWebhook

class DiscordNotifier:
    def __init__(self, config):
        self.webhook_url = config.get("discord", "webhook_url")

    def notify(self, message):
        webhook = DiscordWebhook(url=self.webhook_url, content=message)
        webhook.execute()
