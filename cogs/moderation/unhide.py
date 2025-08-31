import discord
from discord.ext import commands
from discord import ui

class HideUnhideView(ui.View):
    def __init__(self, channel, author, ctx):
        super().__init__(timeout=120)
        self.channel = channel
        self.author = author
        self.ctx = ctx  
        self.message = None  

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("You are not allowed to interact with this!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass

    @ui.button(label="Hide", style=discord.ButtonStyle.danger)
    async def hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.channel.set_permissions(interaction.guild.default_role, read_messages=False)
        await interaction.response.send_message(f"{self.channel.mention} has been hidden.", ephemeral=True)

        embed = discord.Embed(
            description=f"<:tabs:1348326390222557278> **Channel**: {self.channel.mention}\n<:proton:1410107307294986370> **Status**: Hidden\n<:arrow_right:1410112731796865095> **Reason:** Hide request by {self.author}",
            color=0x000000
        )
        embed.add_field(name="<:automod:1410104163513139261> **Moderator:**", value=self.ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Hidden {self.channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        await self.message.edit(embed=embed, view=self)

        for item in self.children:
            if item.label != "Delete":
                item.disabled = True
        await self.message.edit(view=self)

    @ui.button(style=discord.ButtonStyle.gray, emoji="<:delete:1348340540650950816>")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()


class Unhide(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.from_rgb(0, 0, 0)

    @commands.hybrid_command(
        name="unhide",
        help="Unhides a channel to allow the default role (@everyone) to read messages.",
        usage="unhide <channel>",
        aliases=["unhidechannel"])
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unhide_command(self, ctx, channel: discord.TextChannel = None):
        channel = channel or ctx.channel 
        if channel.permissions_for(ctx.guild.default_role).read_messages:
            embed = discord.Embed(
                description=f"**<:tabs:1348326390222557278> Channel**: {channel.mention}\n<:proton:1410107307294986370> **Status**: Already Unhidden",
                color=self.color
            )
            embed.set_author(name=f"{channel.name} is Already Unhidden", icon_url="https://cdn.discordapp.com/emojis/1294218790082711553.png")
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
            view = HideUnhideView(channel=channel, author=ctx.author, ctx=ctx)  
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            return

        await channel.set_permissions(ctx.guild.default_role, read_messages=True)

        embed = discord.Embed(
            description=f"<:tabs:1348326390222557278> **Channel**: {channel.mention}\n<:proton:1410107307294986370> **Status**: Unhidden\n<:arrow_right:1410112731796865095> **Reason:** Unhide request by {ctx.author}",
            color=self.color
        )
        embed.add_field(name="<:automod:1410104163513139261> **Moderator:**", value=ctx.author.mention, inline=False)
        embed.set_author(name=f"Successfully Unhidden {channel.name}", icon_url="https://cdn.discordapp.com/emojis/1222750301233090600.png")
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        view = HideUnhideView(channel=channel, author=ctx.author, ctx=ctx)  
        message = await ctx.send(embed=embed, view=view)
        view.message = message



 