import discord
from discord.ext import commands
import aiosqlite
import os
import time
from typing import Optional
from utils.Tools import *

black1 = 0
black2 = 0
black3 = 0

DB_PATH = "db/afk.db"

class BasicView(discord.ui.View):
    def __init__(self, ctx: commands.Context, timeout: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.ctx = ctx

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(embed=discord.Embed(description=f"Only **{self.ctx.author}** can use this command. Use {self.ctx.prefix}**{self.ctx.command}** to run the command", color=self.ctx.author.color), ephemeral=True)
            return False
        return True

class OnOrOff(BasicView):
    def __init__(self, ctx: commands.Context):
        super().__init__(ctx, timeout=None)
        self.value = None

    @discord.ui.button(label="DM me", emoji="<:tick:1410118593089372242>", custom_id='Yes', style=discord.ButtonStyle.green)
    async def dare(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = 'Yes'
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Don't DM", emoji="<:cross:1410121962189095003>", custom_id='No', style=discord.ButtonStyle.danger)
    async def truth(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = 'No'
        await interaction.response.defer()
        self.stop()

class afk(commands.Cog):

    def __init__(self, client, *args, **kwargs):
        self.client = client
        self.client.loop.create_task(self.initialize_db())

    async def initialize_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS afk (
                    user_id INTEGER PRIMARY KEY,
                    AFK TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    time INTEGER NOT NULL,
                    mentions INTEGER NOT NULL,
                    dm TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS afk_guild (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            await db.commit()

    async def cog_after_invoke(self, ctx):
        ctx.command.reset_cooldown(ctx)

    async def update_data(self, user, guild_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO afk (user_id, AFK, reason, time, mentions, dm) VALUES (?, 'False', 'None', 0, 0, 'False')", (user.id,))
            await db.execute("INSERT OR IGNORE INTO afk_guild (user_id, guild_id) VALUES (?, ?)", (user.id, guild_id))
            await db.commit()

    async def time_formatter(self, seconds: float):
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        tmp = ((str(days) + " days, ") if days else "") + \
              ((str(hours) + " hours, ") if hours else "") + \
              ((str(minutes) + " minutes, ") if minutes else "") + \
              ((str(seconds) + " seconds, ") if seconds else "")
        return tmp[:-2]

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if message.author.bot:
                return

            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("SELECT AFK, time, mentions, reason FROM afk WHERE user_id = ?", (message.author.id,))
                afk_data = await cursor.fetchone()
                await cursor.close()

                if afk_data and afk_data[0] == 'True':
                    cursor = await db.execute("SELECT guild_id FROM afk_guild WHERE user_id = ?", (message.author.id,))
                    guild_ids = [row[0] for row in await cursor.fetchall()]
                    await cursor.close()

                    if message.guild.id in guild_ids:
                        meth = int(time.time()) - int(afk_data[1])
                        been_afk_for = await self.time_formatter(meth)
                        mentionz = afk_data[2]
                        await db.execute("UPDATE afk SET AFK = 'False', reason = 'None' WHERE user_id = ?", (message.author.id,))
                        await db.execute("DELETE FROM afk_guild WHERE user_id = ? AND guild_id = ?", (message.author.id, message.guild.id))
                        await db.commit()
                        wlbat = discord.Embed(title=f'{message.author.display_name} Welcome Back!',
                                              description=f'I removed your AFK\nTotal Mentions: **{mentionz}**\nAFK Timing: **{been_afk_for}**', color=0x0c0606)
                        try:
                            await message.reply(embed=wlbat)
                        except discord.Forbidden:
                            print(f"(AFK module) Missing permissions to send messages in channel: {message.channel.id}")

            if message.mentions:
                async with aiosqlite.connect(DB_PATH) as db:
                    for user_mention in message.mentions:
                        cursor = await db.execute("SELECT AFK, reason, time, mentions, dm FROM afk WHERE user_id = ?", (user_mention.id,))
                        afk_data = await cursor.fetchone()
                        await cursor.close()

                        if afk_data and afk_data[0] == 'True':
                            cursor = await db.execute("SELECT guild_id FROM afk_guild WHERE user_id = ?", (user_mention.id,))
                            guild_ids = [row[0] for row in await cursor.fetchall()]
                            await cursor.close()

                            if message.guild.id in guild_ids:
                                reason = afk_data[1]
                                ok = afk_data[2]
                                wl = discord.Embed(description=f'**<@{user_mention.id}>** went AFK <t:{ok}:R> for the following reason:\n**{reason}**', color=0x0c0606)
                                try:
                                    await message.reply(embed=wl)
                                except discord.Forbidden:
                                    print(f"(AFK module) Missing permissions to send messages to user: {user_mention.id}")

                                new_mentions = afk_data[3] + 1
                                await db.execute("UPDATE afk SET mentions = ? WHERE user_id = ?", (new_mentions, user_mention.id))
                                await db.commit()

                                embed = discord.Embed(description=f'You were mentioned in **{message.guild.name}** by **{message.author}**', color=discord.Color.from_rgb(black1, black2, black3))
                                embed.add_field(name="Total mentions:", value=new_mentions, inline=False)
                                embed.add_field(name="Message:", value=message.content, inline=False)
                                embed.add_field(name="Jump Message:", value=f"[Jump to message]({message.jump_url})", inline=False)

                                if afk_data[4] == 'True':
                                    try:
                                        await user_mention.send(embed=embed)
                                    except discord.Forbidden:
                                        print(f"(AFK module) Missing permissions to send DMs to user: {user_mention.id}")

            if not message.author.bot:
                await self.update_data(message.author, message.guild.id)
        except Exception as e:
            print(f"Ignoring exception in on_message: {e}")

    @commands.hybrid_command(description="Shows an AFK status when you're mentioned")
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def afk(self, ctx, *, reason=None):
        if not reason:
            reason = "I am afk :)"

        if any(invite in reason.lower() for invite in ['discord.gg', 'gg/']):
            emd = discord.Embed(description="<:alert:1410119045444927538> | You can't advertise Serve Invite in the AFK reason", color=0x0c0606)
            return await ctx.send(embed=emd)

        view = OnOrOff(ctx)
        em = discord.Embed(description="Should I DM you on mentions?", color=0x000000)
        try:
            em.set_author(name=str(ctx.author), icon_url=ctx.author.avatar.url)
        except:
            em.set_author(name=str(ctx.author))
        test = await ctx.reply(embed=em, view=view)
        await view.wait()

        async with aiosqlite.connect(DB_PATH) as db:
            if not view.value:
                return await test.edit(content="Timed Out, please try again.", view=None)
            dm_status = 'True' if view.value == 'Yes' else 'False'

            await db.execute("INSERT OR REPLACE INTO afk (user_id, AFK, reason, time, mentions, dm) VALUES (?, 'True', ?, ?, 0, ?)", 
                             (ctx.author.id, reason, int(time.time()),dm_status))
            await db.commit()
            await db.execute("INSERT OR IGNORE INTO afk_guild (user_id, guild_id) VALUES (?, ?)", (ctx.author.id, ctx.guild.id))
            await db.commit()

            await test.delete()
            af = discord.Embed(title='<:tick:1410118593089372242> Success', 
                 description=f'{ctx.author.mention}, You are now marked as AFK due to: **{reason}**', 
                 color=0x000000)
            await ctx.reply(embed=af)

 
