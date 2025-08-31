import discord
from discord.ext import commands


class _ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    """Ticket commands"""
  
    def help_custom(self):
        emoji = '<:ticket:1410111142491066418>'
        label = "Ticket System"
        description = "Advanced support ticket management"
        return emoji, label, description

    @commands.group()
    async def __Ticket__(self, ctx: commands.Context):
        """`ticket` - Advanced ticket management system\n\n__**Setup Commands**__\n`setticket <category> <log_channel> <staff_role>` - Configure the ticket system\n`ticketconfig` - View current ticket configuration\n`ticket` - Create ticket panel with buttons\n\n__**Features**__\n🎫 Interactive ticket creation\n🔧 Multiple ticket reasons (Buy, Help, Report)\n📝 Automatic logging system\n🏷️ Smart channel naming with prefixes\n🔒 Advanced permission management\n👥 Staff role integration\n📊 Ticket tracking and management\n🔔 Staff notification system\n\n__**Ticket Types**__\n💸 **Buy** - Purchase support and billing\n🛠️ **Help** - General support and assistance\n🚫 **Report** - Bug reports and issues\n\n__**Management**__\n✅ One-click ticket closure\n🔔 Staff call button\n📋 Detailed logging with timestamps\n🔐 Permission-based access control\n\n**Note:** Requires administrator permissions to set up. Staff can manage tickets based on assigned roles."""