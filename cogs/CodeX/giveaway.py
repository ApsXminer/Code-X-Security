import discord
from discord.ext import commands


class _giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    """Giveaway commands"""
  
    def help_custom(self):
		      emoji = '<:gift:1410109581534691388>'
		      label = "Giveaway Commands"
		      description = ""
		      return emoji, label, description

    @commands.group()
    async def __Giveaway__(self, ctx: commands.Context):
        """`gstart`, `gend`, `greroll` , `glist`"""