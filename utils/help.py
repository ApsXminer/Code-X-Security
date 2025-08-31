import discord
import functools
from utils.Tools import *


class Dropdown(discord.ui.Select):

    def __init__(self, ctx, options):
        super().__init__(placeholder="Start With CodeX Security",
                         min_values=1,
                         max_values=1,
                         options=options)
        self.invoker = ctx.author

    async def callback(self, interaction: discord.Interaction):
        if self.invoker == interaction.user:
            index = self.view.find_index_from_select(self.values[0])
            if not index:
                index = 0
            await self.view.set_page(index, interaction)
        else:
            await interaction.response.send_message(
                "Uh oh! That message doesn't belong to you. You must run this command to interact with it.", ephemeral=True)


class Button(discord.ui.Button):

    def __init__(self, command, ctx, label, style: discord.ButtonStyle, emoji=None, args=None):
        disable = False
        if args == -1 or args == 0:
            disable = True
        super().__init__(label=label, style=style, emoji=emoji, disabled=disable)
        self.command = command
        self.invoker = ctx.author
        self.args = args

    async def callback(self, interaction: discord.Interaction):
        if self.invoker == interaction.user:
            if self.args or self.args == 0:
                func = functools.partial(self.command, self.args, interaction)
                await func()
            else:
                await self.command(interaction)
        else:
            await interaction.response.send_message(
                "Uh oh! That message doesn't belong to you. You must run this command to interact with it.", ephemeral=True)


class View(discord.ui.View):

    def __init__(self, mapping: dict, ctx: discord.ext.commands.context.Context, homeembed: discord.embeds.Embed, ui: int):
        super().__init__(timeout=None)
        self.mapping, self.ctx, self.home = mapping, ctx, homeembed
        self.index, self.buttons = 0, None

        self.options, self.embeds, self.total_pages = self.gen_embeds()

        if ui == 0:
            self.add_item(Dropdown(ctx=self.ctx, options=self.options))
        elif ui == 1:
            self.buttons = self.add_buttons()
        else:
            self.buttons = self.add_buttons()
            self.add_item(Dropdown(ctx=self.ctx, options=self.options))

    def add_buttons(self):
        self.homeB = Button(label="", style=discord.ButtonStyle.secondary, emoji="<:arrow_left1:1368997542712574033>", command=self.set_page, args=0, ctx=self.ctx)
        self.backB = Button(label="", style=discord.ButtonStyle.secondary, emoji="<:arrow_left:1410112774696206417>", command=self.to_page, args=-1, ctx=self.ctx)
        self.quitB = Button(label="", style=discord.ButtonStyle.danger, emoji="<:delete:1348340540650950816>", command=self.quit, ctx=self.ctx)
        self.nextB = Button(label="", style=discord.ButtonStyle.secondary, emoji="<:arrow_right:1410112731796865095>", command=self.to_page, args=1, ctx=self.ctx)
        self.lastB = Button(label="", style=discord.ButtonStyle.secondary, emoji="<:arrow_right1:1368997540334141562>", command=self.set_last_page, ctx=self.ctx)

        buttons = [self.homeB, self.backB, self.quitB, self.nextB, self.lastB]
        for button in buttons:
            self.add_item(button)
        return buttons

    def find_index_from_select(self, value):
        i = 0
        for cog in self.get_cogs():
            if "help_custom" in dir(cog):
                _, label, _ = cog.help_custom()
                if label == value:
                    return i + 1
                i += 1

    def get_cogs(self):
        return list(self.mapping.keys())

    def gen_embeds(self):
        options, embeds = [], []
        total_pages = 0

        options.append(
            discord.SelectOption(label="Home",
                                 emoji='<:home:1348326486511325256>', description=""))
        embeds.append(self.home)
        total_pages += 1

        for cog in self.get_cogs():
            if "help_custom" in dir(cog):
                emoji, label, description = cog.help_custom()
                options.append(discord.SelectOption(label=label, emoji=emoji, description=description))
                embed = discord.Embed(title=f"{emoji} {label}",
                                      color=0x000000)

                for command in cog.get_commands():
                    params = ""
                    for param in command.clean_params:
                        params += f" <{param}>"
                    embed.add_field(name=f"{command.name}{params}",
                                    value=f"{command.help}\n\u200b",
                                    inline=False)

                embeds.append(embed)
                total_pages += 1

        self.home.set_footer(text=f" • Help page 1/{total_pages} | Requested by: {self.ctx.author.display_name}",
                             icon_url=f"{self.ctx.bot.user.avatar.url}")

        return options, embeds, total_pages

    async def quit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()

    async def to_page(self, page: int, interaction: discord.Interaction):
        if not self.index + page < 0 or not self.index + page > len(self.options):
            await self.set_index(page)
            embed = self.embeds[self.index]
            embed.set_footer(text=f" • Help page {self.index + 1}/{self.total_pages} | Requested by: {self.ctx.author.display_name}",
                             icon_url=f"{self.ctx.bot.user.avatar.url}")
            await interaction.response.edit_message(embed=embed, view=self)

    async def set_page(self, page: int, interaction: discord.Interaction):
        self.index = page
        await self.to_page(0, interaction)

    async def set_index(self, page):
        self.index += page
        if self.buttons:
            for button in self.buttons[0:-1]:
                button.disabled = False
            if self.index == 0:
                self.backB.disabled = True
            elif self.index == len(self.options) - 1:
                self.nextB.disabled = True

    async def set_last_page(self, interaction: discord.Interaction):
        await self.set_page(len(self.options) - 1, interaction)
