from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional
import discord
from discord.ext import commands
from discord import Interaction, ButtonStyle


class Paginator(discord.ui.View):
    def __init__(self, ctx: commands.Context | Interaction, pages_list: list[discord.Embed]):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.pages = pages_list
        self.current_page = 0
        self.message: Optional[discord.Message] = None

        self.clear_items()
        self.fill_items()

    def fill_items(self) -> None:
        """Adds navigation buttons dynamically based on the number of pages."""
        if len(self.pages) > 1:
            self.add_item(self.first_page_button)
            self.add_item(self.previous_page_button)
            self.add_item(self.stop_button)
            self.add_item(self.next_page_button)
            self.add_item(self.last_page_button)

    async def update_page(self, interaction: discord.Interaction) -> None:
        """Updates the embed to the current page."""
        embed = self.pages[self.current_page]
        self.first_page_button.disabled = self.current_page == 0
        self.previous_page_button.disabled = self.current_page == 0
        self.next_page_button.disabled = self.current_page == len(self.pages) - 1
        self.last_page_button.disabled = self.current_page == len(self.pages) - 1

        if interaction.response.is_done():
            await self.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Ensures only the command invoker can interact with the pagination."""
        if isinstance(self.ctx, Interaction):
            if interaction.user and interaction.user.id == self.ctx.user.id:
                return True
        elif interaction.user and interaction.user.id == self.ctx.author.id:
            return True

        await interaction.response.send_message("You cannot control this paginator!", ephemeral=True)
        return False

    async def on_timeout(self) -> None:
        """Disables buttons when the pagination times out."""
        if self.message:
            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    child.disabled = True
            await self.message.edit(view=self)

    async def paginate(self, content: Optional[str] = None, ephemeral: bool = False) -> None:
        """Sends the paginator message and initializes the pagination session."""
        embed = self.pages[0]
        self.first_page_button.disabled = True
        self.previous_page_button.disabled = True
        if len(self.pages) == 1:
            self.next_page_button.disabled = True
            self.last_page_button.disabled = True

        if isinstance(self.ctx, Interaction):
            self.message = await self.ctx.response.send_message(embed=embed, view=self, ephemeral=ephemeral)
        else:
            self.message = await self.ctx.send(embed=embed, view=self, ephemeral=ephemeral)

    @discord.ui.button(emoji="⏪", style=ButtonStyle.secondary)
    async def first_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Navigates to the first page."""
        self.current_page = 0
        await self.update_page(interaction)

    @discord.ui.button(emoji="◀️", style=ButtonStyle.secondary)
    async def previous_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Goes back one page."""
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_page(interaction)

    @discord.ui.button(emoji="🔲", style=ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stops the pagination session and deletes the message."""
        await interaction.response.defer()
        await self.message.delete()
        self.stop()

    @discord.ui.button(emoji="▶️", style=ButtonStyle.secondary)
    async def next_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Goes forward one page."""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_page(interaction)

    @discord.ui.button(emoji="⏩", style=ButtonStyle.secondary)
    async def last_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Goes to the last page."""
        self.current_page = len(self.pages) - 1
        await self.update_page(interaction)
