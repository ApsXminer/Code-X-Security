import os
import asyncio
import traceback
from datetime import datetime
import aiohttp
import discord
from discord.ext import commands
from core import Context
from core.Cog import Cog
from core.CodeX import CodeX
from utils.Tools import *
from utils.config import *

import jishaku
import cogs 

os.environ["JISHAKU_NO_DM_TRACEBACK"] = "False"
os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

client = CodeX()
tree = client.tree
TOKEN = os.getenv("TOKEN")

@client.event
async def on_ready():
    await client.wait_until_ready()
    
    print("""CodeX""")
    print("Loaded & Online!")
    print(f"Logged in as: {client.user}")
    print(f"Connected to: {len(client.guilds)} guilds")
    print(f"Connected to: {len(client.users)} users")
    try:
        synced = await client.tree.sync()
        all_commands = list(client.commands)
        print(f"Synced Total {len(all_commands)} Client Commands and {len(synced)} Slash Commands")
    except Exception as e:
        print(e)

@client.event
async def on_command_completion(context: commands.Context) -> None:
    if context.author.id in OWNER_IDS:
        return

    full_command_name = context.command.qualified_name
    split = full_command_name.split("\n")
    executed_command = str(split[0])
    async with aiohttp.ClientSession() as session:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)

        if context.guild is not None:
            try:
                embed = discord.Embed(color=0x000000)
                avatar_url = context.author.avatar.url if context.author.avatar else context.author.default_avatar.url
                embed.set_author(
                    name=f"Executed {executed_command} Command By : {context.author}",
                    icon_url=avatar_url
                )
                embed.set_thumbnail(url=avatar_url)
                embed.add_field(name="<:arrow_right:1410112731796865095> Command Name :",
                                value=f"{executed_command}",
                                inline=False)
                embed.add_field(
                    name="<:arrow_right:1410112731796865095> Command Executed By :",
                    value=f"{context.author} | ID: [{context.author.id}](https://discord.com/users/{context.author.id})",
                    inline=False)
                embed.add_field(
                    name="<:arrow_right:1410112731796865095> Command Executed In :",
                    value=f"{context.guild.name} | ID: [{context.guild.id}](https://discord.com/guilds/{context.guild.id})",
                    inline=False)
                embed.add_field(
                    name="<:arrow_right:1410112731796865095> Command Executed In Channel :",
                    value=f"{context.channel.name} | ID: [{context.channel.id}](https://discord.com/channels/{context.guild.id}/{context.channel.id})",
                    inline=False)

                embed.timestamp = discord.utils.utcnow()
                embed.set_footer(text="CodeX Security ❤️",icon_url=client.user.display_avatar.url)

                
                await webhook.send(embed=embed)
            except Exception as e:
                print(f'Command failed: {e}')
                traceback.print_exc()
        else:
            try:
                embed1 = discord.Embed(color=0x000000)
                avatar_url = context.author.avatar.url if context.author.avatar else context.author.default_avatar.url
                embed1.set_author(
                    name=f"Executed {executed_command} Command By : {context.author}",
                    icon_url=avatar_url
                )
                embed1.set_thumbnail(url=avatar_url)
                embed1.add_field(name="<:arrow_right:1410112731796865095> Command Name :",
                                 value=f"{executed_command}",
                                 inline=False)
                embed1.add_field(
                    name="<:arrow_right:1410112731796865095> Command Executed By :",
                    value=f"{context.author} | ID: [{context.author.id}](https://discord.com/users/{context.author.id})",
                    inline=False)
                embed1.set_footer(text=f"Powered by Code X Security",
                                  icon_url=client.user.display_avatar.url)
                print("Sending embed1 to webhook...")
                await webhook.send(embed=embed1)
                print("Embed1 sent successfully.")
            except Exception as e:
                print(f'Command failed: {e}')
                traceback.print_exc()





async def main():
    async with client:
        os.system("clear")
        os.system("cls")
        
        # Display ASCII art
        print(""" ██████╗ ██████╗ ██████╗ ███████╗    ██╗  ██╗    ██╗   ██╗███████╗██████╗ ███████╗███████╗
██╔════╝██╔═══██╗██╔══██╗██╔════╝    ╚██╗██╔╝    ██║   ██║██╔════╝██╔══██╗██╔════╝██╔════╝
██║     ██║   ██║██║  ██║█████╗       ╚███╔╝     ██║   ██║█████╗  ██████╔╝███████╗█████╗  
██║     ██║   ██║██║  ██║██╔══╝       ██╔██╗     ╚██╗ ██╔╝██╔══╝  ██╔══██╗╚════██║██╔══╝  
╚██████╗╚██████╔╝██████╔╝███████╗    ██╔╝ ██╗     ╚████╔╝ ███████╗██║  ██║███████║███████╗
 ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝    ╚═╝  ╚═╝      ╚═══╝  ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝
                                                                                          
""")
        
        print("Loading extensions...")
        await client.load_extension("jishaku")
        await client.load_extension("status")
        await client.load_extension('cogs.commands.suggestion')
        
        print("Starting Discord bot...")
        await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
