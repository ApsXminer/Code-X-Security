import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
import sqlite3
import os
import asyncio
from typing import Optional, Tuple

class TicketSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "db/ticket.db"
        os.makedirs("db", exist_ok=True)
        self.setup_db()

    def help_custom(self):
        return '<:ticket:1410111142491066418>', 'Ticket System', 'An advanced support ticket management system.'

    async def cog_load(self):
        self.bot.add_view(TicketButtonView())
        self.bot.add_view(TicketManageView(None))

    def setup_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            category_id INTEGER,
            log_channel_id INTEGER,
            staff_role_id INTEGER
        )""")
        c.execute("""
        CREATE TABLE IF NOT EXISTS active_tickets (
            channel_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            guild_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ticket_type TEXT
        )""")
        conn.commit()
        conn.close()

    def get_config(self, guild_id: int) -> Optional[Tuple[int, int, int]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT category_id, log_channel_id, staff_role_id FROM guild_config WHERE guild_id = ?", (guild_id,))
        result = c.fetchone()
        conn.close()
        return result

    def add_active_ticket(self, channel_id: int, user_id: int, guild_id: int, ticket_type: str = "general") -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO active_tickets (channel_id, user_id, guild_id, ticket_type) VALUES (?, ?, ?, ?)",
                 (channel_id, user_id, guild_id, ticket_type))
        conn.commit()
        conn.close()

    def remove_active_ticket(self, channel_id: int) -> None:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM active_tickets WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()

    def has_active_ticket(self, user_id: int, guild_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT channel_id FROM active_tickets WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        result = c.fetchone()
        conn.close()
        return bool(result)

    def get_ticket_stats(self, guild_id: int) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM active_tickets WHERE guild_id = ?", (guild_id,))
        active_count = c.fetchone()[0]
        c.execute("SELECT ticket_type, COUNT(*) FROM active_tickets WHERE guild_id = ? GROUP BY ticket_type", (guild_id,))
        type_stats = dict(c.fetchall())
        conn.close()
        return {"active_tickets": active_count, "by_type": type_stats}

    @commands.hybrid_command(name="setticket", description="Set up the ticket system configuration.")
    @commands.has_permissions(administrator=True)
    async def setticket(self, ctx, category: discord.CategoryChannel, log_channel: discord.TextChannel, staff_role: discord.Role):
        try:
            bot_perms = category.permissions_for(ctx.guild.me)
            if not (bot_perms.manage_channels and bot_perms.manage_permissions):
                embed = discord.Embed(title="<:cross:1410121962189095003> Permission Error", description="I need `Manage Channels` and `Manage Permissions` in the ticket category.", color=0xff0000)
                return await ctx.send(embed=embed, ephemeral=True)
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO guild_config (guild_id, category_id, log_channel_id, staff_role_id) VALUES (?, ?, ?, ?)", (ctx.guild.id, category.id, log_channel.id, staff_role.id))
            conn.commit()
            embed = discord.Embed(title="<:tick:1410118593089372242> Ticket System Configured", description=f"**Configuration saved successfully!**\n\n**Category:** {category.mention}\n**Log Channel:** {log_channel.mention}\n**Staff Role:** {staff_role.mention}\n\nUse `/ticket` to create a ticket panel.", color=0x00ff00)
            await ctx.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="<:cross:1410121962189095003> Configuration Error", description=f"Failed to save configuration: {str(e)}", color=0xff0000)
            await ctx.send(embed=embed, ephemeral=True)
        finally:
            if 'conn' in locals() and conn:
                conn.close()

    @commands.hybrid_command(name="ticketconfig", description="Show current ticket configuration and statistics.")
    async def ticketconfig(self, ctx):
        config = self.get_config(ctx.guild.id)
        if not config:
            embed = discord.Embed(title="<:cross:1410121962189095003> Not Configured", description="Ticket system is not configured. Use `/setticket` to set it up.", color=0xff0000)
            return await ctx.send(embed=embed, ephemeral=True)
        stats = self.get_ticket_stats(ctx.guild.id)
        embed = discord.Embed(title="🎫 Ticket System Configuration", color=0x5865F2)
        embed.add_field(name="📂 Category", value=f"<#{config[0]}>", inline=True)
        embed.add_field(name="📋 Log Channel", value=f"<#{config[1]}>", inline=True)
        embed.add_field(name="👥 Staff Role", value=f"<@&{config[2]}>", inline=True)
        embed.add_field(name="📊 Active Tickets", value=f"`{stats['active_tickets']}`", inline=True)
        if stats['by_type']:
            type_breakdown = "\n".join([f"**{t.title()}:** `{c}`" for t, c in stats['by_type'].items()])
            embed.add_field(name="📈 By Type", value=type_breakdown, inline=True)
        embed.set_footer(text="Use /ticket to create a ticket panel")
        await ctx.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(name="ticket", description="Create a ticket panel.")
    @commands.has_permissions(administrator=True)
    async def ticket(self, ctx):
        config = self.get_config(ctx.guild.id)
        if not config:
            embed = discord.Embed(title="<:cross:1410121962189095003> Not Configured", description="Ticket system is not configured. Use `/setticket` first.", color=0xff0000)
            return await ctx.send(embed=embed, ephemeral=True)
        embed = discord.Embed(title="🎫 Support Tickets", description="Click the button below to create a support ticket. Our staff will assist you as soon as possible.", color=0x5865F2)
        embed.set_image(url='https://i.imgur.com/FoI5ITb.png')
        await ctx.send(embed=embed, view=TicketButtonView())

class TicketButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="persistent:ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        cog = interaction.client.get_cog("TicketSetup")
        if cog.has_active_ticket(interaction.user.id, interaction.guild.id):
            embed = discord.Embed(title="<:alert:1410119045444927538> Active Ticket", description="You already have an active ticket. Please use your existing ticket or close it before creating a new one.", color=0xffa500)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.response.send_message(view=ReasonSelectView(), ephemeral=True)

class ReasonSelectView(View):
    def __init__(self):
        super().__init__(timeout=180)

    @discord.ui.select(
        placeholder="Select a support category...",
        options=[
            discord.SelectOption(label="Purchase Support", value="purchase", emoji="🛒", description="For billing, payments, and purchase issues."),
            discord.SelectOption(label="Technical Help", value="technical", emoji="🛠️", description="For bug reports and technical problems."),
            discord.SelectOption(label="Report Issues", value="report", emoji="🚫", description="To report rule violations or abuse."),
            discord.SelectOption(label="Suggestions", value="suggestions", emoji="💡", description="For feature requests and improvements."),
            discord.SelectOption(label="General Support", value="general", emoji="❓", description="For any other questions or general help."),
        ])
    async def select_callback(self, interaction: discord.Interaction, select: Select):
        cog = interaction.client.get_cog("TicketSetup")
        config = cog.get_config(interaction.guild.id)
        if not config:
            embed = discord.Embed(title="<:cross:1410121962189095003> Configuration Error", description="The ticket system is not configured properly. Please contact an administrator.", color=0xff0000)
            return await interaction.response.edit_message(embed=embed, view=None)
        category_id, log_channel_id, staff_role_id = config
        category = interaction.guild.get_channel(category_id)
        log_channel = interaction.guild.get_channel(log_channel_id)
        staff_role = interaction.guild.get_role(staff_role_id)
        if not all([category, log_channel, staff_role]):
            embed = discord.Embed(title="<:cross:1410121962189095003> Configuration Invalid", description="Some components of the ticket system are missing. Please contact an administrator.", color=0xff0000)
            return await interaction.response.edit_message(embed=embed, view=None)
        ticket_type = select.values[0]
        channel_name = f"{ticket_type}-{interaction.user.name}"
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True, embed_links=True),
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True, read_message_history=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        try:
            ticket_channel = await category.create_text_channel(name=channel_name, overwrites=overwrites, reason=f"Ticket created by {interaction.user} for {ticket_type}")
        except discord.HTTPException as e:
            embed = discord.Embed(title="<:cross:1410121962189095003> Creation Failed", description=f"Failed to create ticket channel: {str(e)}", color=0xff0000)
            return await interaction.response.edit_message(embed=embed, view=None)
        cog.add_active_ticket(ticket_channel.id, interaction.user.id, interaction.guild.id, ticket_type)
        embed = discord.Embed(title="<:tick:1410118593089372242> Ticket Created", description=f"Your ticket has been created at {ticket_channel.mention}", color=0x00ff00)
        await interaction.response.edit_message(embed=embed, view=None)
        welcome_embed = discord.Embed(title=f"{ticket_type.title()} Support", description=f"Hello {interaction.user.mention}, please describe your issue in detail. The {staff_role.mention} team will assist you shortly.", color=0x5865F2)
        welcome_embed.set_footer(text=f"Ticket opened at {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        await ticket_channel.send(f"{interaction.user.mention} {staff_role.mention}", embed=welcome_embed, view=TicketManageView(interaction.user))
        log_embed = discord.Embed(title="📋 New Ticket Created", color=0x5865F2, timestamp=discord.utils.utcnow())
        log_embed.add_field(name="👤 User", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
        log_embed.add_field(name="🏷️ Type", value=ticket_type.title(), inline=True)
        log_embed.add_field(name="📂 Channel", value=ticket_channel.mention, inline=True)
        await log_channel.send(embed=log_embed)

class TicketManageView(View):
    def __init__(self, ticket_owner):
        super().__init__(timeout=None)
        self.ticket_owner = ticket_owner

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, emoji="🔐", custom_id="persistent:close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        cog = interaction.client.get_cog("TicketSetup")
        config = cog.get_config(interaction.guild.id)
        staff_role = interaction.guild.get_role(config[2]) if config else None
        is_staff = staff_role and staff_role in interaction.user.roles
        if interaction.user == self.ticket_owner or is_staff or interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("This ticket will be closed in 5 seconds.", ephemeral=True)
            await asyncio.sleep(5)
            cog.remove_active_ticket(interaction.channel.id)
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
            log_channel = interaction.guild.get_channel(config[1]) if config else None
            if log_channel:
                log_embed = discord.Embed(title="🔐 Ticket Closed", color=0xff0000, timestamp=discord.utils.utcnow())
                log_embed.add_field(name="📂 Channel", value=f"`{interaction.channel.name}`", inline=True)
                log_embed.add_field(name="👤 Closed by", value=f"{interaction.user.mention}", inline=True)
                log_embed.add_field(name="👥 Ticket Owner", value=f"{self.ticket_owner.mention if self.ticket_owner else 'Unknown'}", inline=True)
                await log_channel.send(embed=log_embed)
        else:
            embed = discord.Embed(title="<:cross:1410121962189095003> Access Denied", description="You don't have permission to close this ticket.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Call Staff", style=discord.ButtonStyle.secondary, emoji="🔔", custom_id="persistent:call_staff")
    async def call_staff(self, interaction: discord.Interaction, button: Button):
        cog = interaction.client.get_cog("TicketSetup")
        config = cog.get_config(interaction.guild.id)
        if not config:
            embed = discord.Embed(title="<:cross:1410121962189095003> Configuration Error", description="Ticket system is not properly configured.", color=0xff0000)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        staff_role = interaction.guild.get_role(config[2])
        if not staff_role:
            embed = discord.Embed(title="<:cross:1410121962189095003> Staff Role Not Found", description="The configured staff role could not be found.", color=0xff0000)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.channel.send(f"🔔 {staff_role.mention}, assistance has been requested by {interaction.user.mention}.")
        await interaction.response.send_message("Staff have been notified.", ephemeral=True)

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.success, emoji="➕", custom_id="persistent:add_user")
    async def add_user(self, interaction: discord.Interaction, button: Button):
        cog = interaction.client.get_cog("TicketSetup")
        config = cog.get_config(interaction.guild.id)
        staff_role = interaction.guild.get_role(config[2]) if config else None
        is_staff = staff_role and staff_role in interaction.user.roles
        if interaction.user == self.ticket_owner or is_staff or interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_modal(UserModal(interaction.channel))
        else:
            embed = discord.Embed(title="<:cross:1410121962189095003> Access Denied", description="Only staff or the ticket owner can add users.", color=0xff0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)

class UserModal(Modal):
    def __init__(self, channel):
        super().__init__(title="Add User to Ticket")
        self.channel = channel
        self.user_input = TextInput(label="User ID or Mention", placeholder="Enter the User ID or mention them here", required=True)
        self.add_item(self.user_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_str = self.user_input.value.strip()
        try:
            user_id = int(user_str.strip('<@!>'))
            user = interaction.guild.get_member(user_id)
        except ValueError:
            user = discord.utils.get(interaction.guild.members, name=user_str)
        if not user:
            embed = discord.Embed(title="<:cross:1410121962189095003> User Not Found", description="Could not find the specified user.", color=0xff0000)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.channel.set_permissions(user, view_channel=True, send_messages=True, read_message_history=True)
        embed = discord.Embed(title="<:tick:1410118593089372242> User Added", description=f"{user.mention} has been added to this ticket.", color=0x00ff00)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(TicketSetup(bot))