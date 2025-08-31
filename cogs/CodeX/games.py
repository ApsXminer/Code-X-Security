import discord
from discord.ext import commands

class _games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    """Games commands"""
  
    def help_custom(self):
		      emoji = '<:games:1410106989668729012>'
		      label = "Games Commands"
		      description = ""
		      return emoji, label, description

    @commands.group()
    async def __Games__(self, ctx: commands.Context):
        """`blackjack` , `chess` , `tic-tac-toe` , `country-guesser` , `rps` , `lights-out` , `wordle` , `2048` , `memory-game` , `number-slider` , `battleship` , `connect-four` , `slots`"""