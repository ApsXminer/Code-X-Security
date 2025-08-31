import discord
from discord.ext import commands
import asyncio

class React(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        for owner in self.bot.owner_ids:
            if f"<@{owner}>" in message.content:
                try:
                    if owner == 1383706658315960330:
                        
                        emojis = [
                            "<a:Crown:1410121588824866916>",
                            "<a:Diamond:1410121535326388234>",
                            "<:owner:1410176722476990525>",
                            "<:devs:1410123972044918925>"
                        ]
                        for emoji in emojis:
                            await message.add_reaction(emoji)
                    else:
                        
                        await message.add_reaction("<a:Crown:1410121588824866916>")
                except discord.errors.RateLimited as e:
                    await asyncio.sleep(e.retry_after)
                    await message.add_reaction("<a:Crown:1410121588824866916>")
                except Exception as e:
                    print(f"An unexpected error occurred Auto react owner mention: {e}")
