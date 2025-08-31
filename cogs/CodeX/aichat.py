import discord
from discord.ext import commands


class _aichat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    """AI Chat commands"""
  
    def help_custom(self):
        emoji = '<:robot:894567890123456789>'
        label = "AI Chat Commands"
        description = "AI-powered chat assistance system"
        return emoji, label, description

    @commands.group()
    async def __AIChat__(self, ctx: commands.Context):
        """`aichat` - AI Chat system management\n\n__**Setup Commands**__\n`aichat setup [channel]` - Set up AI chat in a channel\n`aichat reset` - Remove AI chat from the guild\n\n__**Features**__\n✨ Powered by Google Gemini AI\n🔄 Automatic fallback to Groq API\n🛡️ Built-in safety filters\n💬 Natural conversation support\n🚫 Link and mention protection\n\n__**Usage**__\nOnce set up, the AI will automatically respond to all messages in the designated channel with intelligent, helpful responses while maintaining safety standards."""