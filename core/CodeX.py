from __future__ import annotations
from discord.ext import commands
import discord
import aiohttp
import json
import jishaku
import asyncio
import typing
from typing import List
import aiosqlite
from utils.config import OWNER_IDS
from utils import getConfig, updateConfig
from .Context import Context
from discord.ext import commands, tasks
from colorama import Fore, Style, init
import importlib
import inspect

init(autoreset=True)

extensions: List[str] = [
    "cogs"
]

class CodeX(commands.AutoShardedBot):

    def __init__(self, *arg, **kwargs):
        intents = discord.Intents.all()
        intents.presences = True
        intents.members = True
        super().__init__(command_prefix=self.get_prefix,
                         case_insensitive=True,
                         intents=intents,
                         status=discord.Status.do_not_disturb,
                         strip_after_prefix=True,
                         owner_ids=OWNER_IDS,
                         allowed_mentions=discord.AllowedMentions(
                             everyone=False, replied_user=False, roles=False),
                         sync_commands_debug=True,
                         sync_commands=True,
                         shard_count=2)

    async def setup_hook(self):
        await self.load_extensions() 

    async def load_extensions(self):
        for extension in extensions:
            try:
                await self.load_extension(extension) 
            except Exception as e:
                print(
                    f"{Fore.RED}{Style.BRIGHT}Failed to load extension {extension}. {e}"
                )

    async def on_connect(self):
        await self.change_presence(status=discord.Status.do_not_disturb,
                                   activity=discord.Activity(
                                       type=discord.ActivityType.playing,
                                       name='$help | $inv'))

    async def send_raw(self, channel_id: int, content: str,
                       **kwargs) -> typing.Optional[discord.Message]:
        await self.http.send_message(channel_id, content, **kwargs)

    async def invoke_help_command(self, ctx: Context) -> None:
        """Invoke the help command or default help command if help extensions is not loaded."""
        return await ctx.send_help(ctx.command)

    async def fetch_message_by_channel(
            self, channel: discord.TextChannel,
            messageID: int) -> typing.Optional[discord.Message]:
        async for msg in channel.history(
                limit=1,
                before=discord.Object(messageID + 1),
                after=discord.Object(messageID - 1),
        ):
            return msg

    async def get_prefix(self, message: discord.Message):
        if message.guild:
            guild_id = message.guild.id
            async with aiosqlite.connect('db/np.db') as db:
                async with db.execute("SELECT id FROM np WHERE id = ?", (message.author.id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        data = await getConfig(guild_id)
                        prefix = data["prefix"]
                        # Np user
                        return commands.when_mentioned_or(prefix, '')(self, message)
                    else:
                        # non np
                        data = await getConfig(guild_id)
                        prefix = data["prefix"]
                        return commands.when_mentioned_or(prefix)(self, message)
        else:
            async with aiosqlite.connect('db/np.db') as db:
                async with db.execute("SELECT id FROM np WHERE id = ?", (message.author.id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        #NO user (Dms)
                        return commands.when_mentioned_or('$', '')(self, message)
                    else:
                        #Non Np user (DMs)
                        return commands.when_mentioned_or('')(self, message)


    async def on_message_edit(self, before, after):
        ctx: Context = await self.get_context(after, cls=Context)
        if before.content != after.content:
            if after.guild is None or after.author.bot:
                return
            if ctx.command is None:
                return
            if type(ctx.channel) == "public_thread":
                return
            await self.invoke(ctx)
        else:
            return



def setup_bot():
    intents = discord.Intents.all()
    bot = CodeX(intents=intents)
    return bot