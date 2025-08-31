import discord
from discord.ext import commands
import datetime

class Suggestion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # This is the channel where suggestions will be sent
        self.suggestion_channel_id = 1385212499946901526

    async def send_suggestion_embed(self, ctx, suggestion_content):
        """
        Helper function to send a suggestion embed to the designated channel.
        """
        channel = self.bot.get_channel(self.suggestion_channel_id)
        if channel:
            embed = discord.Embed(
                title="New Suggestion!",
                description=suggestion_content,
                color=discord.Color.blue()
            )
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else discord.Embed.Empty)
            embed.set_footer(text=f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            message = await channel.send(embed=embed)
            # Add reactions for voting
            await message.add_reaction('⬆️')  # Up arrow
            await message.add_reaction('⬇️')  # Green checkmark (for approval/implementation)
        else:
            print(f"Error: Could not find the suggestion channel with ID {self.suggestion_channel_id}.")
            await ctx.send(f"I couldn't find the designated suggestion channel. Please contact an admin.")

    @commands.hybrid_command(
        name="suggest",
        aliases=["suggestion"], # Allows both $suggest and $suggestion
        usage='suggest <your suggestion>',
        description='Submit a suggestion for the bot or server.',
        help='Submit a suggestion to the development team or server staff.',
        with_app_command=True # Enables it as a slash command too
    )
    @commands.cooldown(1, 60, commands.BucketType.user) # Cooldown: 1 use per user per 60 seconds
    async def suggest(self, ctx, *, suggestion_content: str):
        """
        Sends a suggestion to the designated suggestion channel.
        """
        await self.send_suggestion_embed(ctx, suggestion_content)
        await ctx.send("<:3742:1363545422752383240> Thanks for your suggestion! We will review it soon.")

async def setup(bot):
    await bot.add_cog(Suggestion(bot))