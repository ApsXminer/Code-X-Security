from __future__ import annotations
import os
from utils.config import BotName
from discord.ext import commands
from discord.ext.commands import Context, Paginator as CmdPaginator
from typing import Any, List


class FieldPagePaginator:
    def __init__(self, entries: list[tuple[Any, Any]], *, per_page: int = 10, inline: bool = False, **kwargs):
        self.entries = entries
        self.per_page = per_page
        self.inline = inline
        self.embed = discord.Embed(
            title=kwargs.get('title'),
            description=kwargs.get('description'),
            color=0x000000
        )

    def get_pages(self):
        pages_list = []
        for i in range(0, len(self.entries), self.per_page):
            embed = self.embed.copy()
            embed.clear_fields()
            for key, value in self.entries[i:i + self.per_page]:
                embed.add_field(name=key, value=value, inline=self.inline)

            total_pages = len(self.entries) // self.per_page + (1 if len(self.entries) % self.per_page else 0)
            if total_pages > 1:
                embed.set_footer(
                    text=f'• Page {i // self.per_page + 1}/{total_pages} | CodeX Development™',
                    icon_url="https://cdn.discordapp.com/avatars/1368423803440468060/a_f061e6472786781e23bac32fa8d0a667.png?width=115&height=115"
                )
            pages_list.append(embed)
        return pages_list


class TextPaginator:
    def __init__(self, text, *, prefix='```', suffix='```', max_size=2000):
        self.pages = []
        paginator = CmdPaginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        for line in text.split('\n'):
            paginator.add_line(line)
        self.pages = paginator.pages

    def get_pages(self):
        return [discord.Embed(description=page) for page in self.pages]


class DescriptionEmbedPaginator:
    def __init__(self, entries: list[Any], *, per_page: int = 10, **kwargs):
        self.entries = entries
        self.per_page = per_page
        self.embed = discord.Embed(title=kwargs.get('title'), color=0x000000)

    def get_pages(self):
        pages_list = []
        for i in range(0, len(self.entries), self.per_page):
            embed = self.embed.copy()
            embed.description = '\n'.join(self.entries[i:i + self.per_page])

            total_pages = len(self.entries) // self.per_page + (1 if len(self.entries) % self.per_page else 0)
            if total_pages > 1:
                embed.set_footer(
                    text=f'• Page {i // self.per_page + 1}/{total_pages} | CodeX Development™',
                    icon_url="https://cdn.discordapp.com/avatars/1368423803440468060/a_f061e6472786781e23bac32fa8d0a667.png?width=115&height=115"
                )
            pages_list.append(embed)
        return pages_list
