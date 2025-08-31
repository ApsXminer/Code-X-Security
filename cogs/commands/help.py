import discord
from discord.ext import commands
from discord import app_commands, Interaction
from difflib import get_close_matches
from contextlib import suppress
from core import Context
from core.CodeX import CodeX
from core.Cog import Cog
from utils.Tools import getConfig
from itertools import chain
import json
from utils import help as vhelp
from utils import Paginator, DescriptionEmbedPaginator, FieldPagePaginator, TextPaginator
import asyncio
from utils.config import serverLink
from utils.Tools import *

color = 0x000000
client = CodeX()

class HelpCommand(commands.HelpCommand):

  async def send_ignore_message(self, ctx, ignore_type: str):

    if ignore_type == "channel":
      await ctx.reply(f"This channel is ignored.", mention_author=False)
    elif ignore_type == "command":
      await ctx.reply(f"{ctx.author.mention} This Command, Channel, or You have been ignored here.", delete_after=6)
    elif ignore_type == "user":
      await ctx.reply(f"You are ignored.", mention_author=False)


  async def on_help_command_error(self, ctx, error):
    errors = [
      commands.CommandOnCooldown, commands.CommandNotFound,
      discord.HTTPException, commands.CommandInvokeError
    ]
    if not type(error) in errors:
      await self.context.reply(f"Unknown Error Occurred\n{error.original}",
                               mention_author=False)
    else:
      if type(error) == commands.CommandOnCooldown:
        return

    return await super().on_help_command_error(ctx, error)

  
  async def command_not_found(self, string: str) -> None:
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
        return

    if not check_ignore:
        await self.send_ignore_message(ctx, "command")
        return

    cmds = (str(cmd) for cmd in self.context.bot.walk_commands())
    matches = get_close_matches(string, cmds)

    embed = discord.Embed(
        title="",
        description=f"Command not found with the name `{string}`.",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1275364856631005256.png")
    embed.set_author(name="Command Not Found", icon_url=self.context.bot.user.avatar.url)
    embed.set_footer(text=f"Requested By {ctx.author}",
                       icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    if matches:
        match_list = "\n".join([f"{index}. `{match}`" for index, match in enumerate(matches, start=1)])
        embed.add_field(name="Did you mean:", value=match_list, inline=True)

    await ctx.reply(embed=embed)

  
  async def send_bot_help(self, mapping):
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
      return

    if not check_ignore:
      await self.send_ignore_message(ctx, "command")
      return

    
    embed = discord.Embed(description="<a:loading:1410098840765206659> **Generating Help module...**", color=color)
    ok = await self.context.reply(embed=embed)          
    data = await getConfig(self.context.guild.id)
    prefix = data["prefix"]
    filtered = await self.filter_commands(self.context.bot.walk_commands(),
                                              sort=True)
    slash = len([
  cmd for cmd in self.context.bot.tree.get_commands() 
  if isinstance(cmd, app_commands.Command)
])
    
    embed = discord.Embed(
      title="", color=0x000000)

    embed.add_field(name=f"<a:dot:1410099793983967332> **Server Prefix:** `{prefix}`", value= f"<a:dot:1410099793983967332>** Total Commands:** **{len(set(self.context.bot.walk_commands()))}**\n**<a:dot:1410099793983967332> Type `{prefix}help` To get Started**\n<a:dot:1410099793983967332> **[Get CodeX](https://dsc.gg/codex-security)** | **[Support](https://discord.gg/pndSM8wrmS)**\n\n",inline=False)

    embed.add_field(name="<:star:1410101217186549800> __**My Features**__", value=">>> \n <:mod:1410101927773212753> Security\n <:setting_tool:1410102296062201856> Utility\n <:circle2:1410102626129023017> Media\n <:earth:1410103243903864922> General \n <:automod2:1410103561425256539> Automoderation\n <:automod:1410104163513139261> Moderation\n <:music:1410105787698774139> Music\n <:mail1:1410106158949077064> Server & Setup ",inline=True)
    embed.add_field(name="<:star:1410101217186549800> __**My Modules**__", value=">>> \n <:hallow:1410106550391144518> Fun & AI \n <:games:1410106989668729012> Games\n <:proton:1410107307294986370> Ignore\n <:mic:1410107989666304052> Voice & InVC\n <:msg:1410109102167822476> Welcome\n <:gift:1410109581534691388> Giveaway\n <:snow1:1410110069667922010> Logging\n <:ticket:1410111142491066418> Ticket",inline=True)
    embed.set_footer(
      text=f"Requested By {self.context.author}",
      icon_url=self.context.author.avatar.url if self.context.author.avatar else self.context.author.default_avatar.url
    )
    embed.set_author(name=self.context.author, icon_url=self.context.author.avatar.url if self.context.author.avatar else self.context.author.default_avatar.url)
    embed.set_thumbnail(url=self.context.bot.user.avatar.url)
    embed.set_image(url="https://media.discordapp.net/attachments/1376132308419219486/1376453971170033787/a_0480347842c791592b4563ce7edc6030.gif?ex=68356228&is=683410a8&hm=fe5a65d43d13ec28c60949d244b4c0e6358d06461771af91fc44f01b35260bdf&=&width=287&height=161")

    #embed.timestamp = discord.utils.utcnow()
    view = vhelp.View(mapping=mapping,
                          ctx=self.context,
                          homeembed=embed,
                          ui=2)
    await asyncio.sleep(0.5)
    await ok.edit(embed=embed,view=view)
  
  async def send_command_help(self, command):
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
      return

    if not check_ignore:
      await self.send_ignore_message(ctx, "command")
      return
    
    codex = f">>> {command.help}" if command.help else '>>> No Help Provided...'
    embed = discord.Embed(
        description=
        f"""```xml
<[] = optional | ‹› = required\nDon't type these while using Commands>```\n{codex}""",
        color=color)
    alias = ' | '.join(command.aliases)

    embed.add_field(name="**Aliases**",
                      value=f"{alias}" if command.aliases else "No Aliases",
                      inline=False)
    embed.add_field(name="**Usage**",
                      value=f"`{self.context.prefix}{command.signature}`\n")
    embed.set_author(name=f"{command.qualified_name.title()} Command",
                       icon_url=self.context.bot.user.display_avatar.url)
    await self.context.reply(embed=embed, mention_author=False)

  def get_command_signature(self, command: commands.Command) -> str:
    parent = command.full_parent_name
    if len(command.aliases) > 0:
      aliases = ' | '.join(command.aliases)
      fmt = f'[{command.name} | {aliases}]'
      if parent:
        fmt = f'{parent}'
      alias = f'[{command.name} | {aliases}]'
    else:
      alias = command.name if not parent else f'{parent} {command.name}'
    return f'{alias} {command.signature}'

  def common_command_formatting(self, embed_like, command):
    embed_like.title = self.get_command_signature(command)
    if command.description:
      embed_like.description = f'{command.description}\n\n{command.help}'
    else:
      embed_like.description = command.help or 'No help found...'

  async def send_group_help(self, group):
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
        return

    if not check_ignore:
        await self.send_ignore_message(ctx, "command")
        return

    entries = [
        (
            f"➜ `{self.context.prefix}{cmd.qualified_name}`\n",
            f"{cmd.short_doc if cmd.short_doc else ''}\n\u200b"
        )
        for cmd in group.commands
    ]

    count = len(group.commands)

    embeds = FieldPagePaginator(
        entries=entries,
        title=f"{group.qualified_name.title()} [{count}]",
        description="< > Duty | [ ] Optional\n",
        per_page=4
    ).get_pages()

    paginator = Paginator(ctx, embeds)
    await paginator.paginate()
    
  async def send_cog_help(self, cog):
    ctx = self.context
    check_ignore = await ignore_check().predicate(ctx)
    check_blacklist = await blacklist_check().predicate(ctx)

    if not check_blacklist:
      return

    if not check_ignore:
      await self.send_ignore_message(ctx, "command")
      return


    entries = [(
      f"➜ `{self.context.prefix}{cmd.qualified_name}`",
      f"{cmd.short_doc if cmd.short_doc else ''}"
      f"\n\u200b",
    ) for cmd in cog.get_commands()]
    embeds = FieldPagePaginator(
      entries=entries,
      title=f"{cog.qualified_name.title()} ({len(cog.get_commands())})",
      description="< > Duty | [ ] Optional\n\n",
      color=color,
      per_page=4).get_pages()
    paginator = Paginator(ctx, embeds)
    await paginator.paginate()


class Help(Cog, name="help"):

  def __init__(self, client: CodeX):
    self._original_help_command = client.help_command
    attributes = {
      'name':
      "help",
      'aliases': ['h','codex', 'Ansh'],
      'cooldown':
      commands.CooldownMapping.from_cooldown(1, 5, commands.BucketType.user),
      'help':
      'Shows help about bot, a command or a category'
    }
    client.help_command = HelpCommand(command_attrs=attributes)
    client.help_command.cog = self

  async def cog_unload(self):
    self.help_command = self._original_help_command