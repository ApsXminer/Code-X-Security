import discord
from discord.ext import commands
import aiosqlite
import asyncio
import os
import re
import google.generativeai as genai
from groq import Groq, APIError

from utils.Tools import *

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = 'db/aichat.db'

        self.aichat_prodia = "You are an advanced AI chatbot named CodeX, designed for security and assistance. You are helpful, respectful, and harmless. You should avoid any content that is discriminatory, hateful, or promotes illegal activities. Focus on providing accurate and safe information. Keep your responses concise and helpful."

        genai.configure(api_key=os.getenv("GEMINI_API_KEY") or "AIzaSyD22w5ckQLcECAfS7QDoJ4lwV_0WCvEWfU")
        self.gemini_model = genai.GenerativeModel('gemini-pro')

        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY") or "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")
        self.groq_model = "llama3-8b-8192" 
        self.bot.loop.create_task(self.create_ai_chat_table())

    async def create_ai_chat_table(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS aichat_settings (
                    guild_id INTEGER PRIMARY KEY,
                    channel_id INTEGER NOT NULL
                )
            ''')
            await db.commit()

    async def _clean_response(self, text, guild=None):
        text = text.replace('@everyone', 'everyone').replace('@here', 'here')

        if guild:
            def replace_user_ping(match):
                user_id = int(match.group(1))
                member = guild.get_member(user_id)
                if member:
                    return f'@{member.display_name}'
                return f'@{user_id}'
            text = re.sub(r'<@!?(\d+)>', replace_user_ping, text)

        text = re.sub(r'https?://\S+|www\.\S+|discord\.gg/\S+', '[link removed]', text)

        return text

    def help_custom(self):
        return '<:robot:894567890123456789>', 'AI Chat', 'Commands for AI chat setup and interaction.'

    @commands.group(name='aichat', invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def aichat(self, ctx):
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
            ctx.command.reset_cooldown(ctx)

    @aichat.command(name='setup')  # type: ignore
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def setup_aichat(self, ctx, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT channel_id FROM aichat_settings WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()

            if row:
                existing_channel_id = row[0]
                if existing_channel_id != channel.id:
                    existing_channel = ctx.guild.get_channel(existing_channel_id)
                    embed = discord.Embed(
                        title="<:alert:1410119045444927538> AI Chat Already Setup",
                        description=f"AI chat is already configured in {existing_channel.mention if existing_channel else 'an unknown channel'}.\n"
                                    f"Please use `{ctx.prefix}aichat reset` before setting up a new channel.",
                        color=0x000000
                    )
                    await ctx.reply(embed=embed)
                    return
            
            await db.execute(
                'REPLACE INTO aichat_settings (guild_id, channel_id) VALUES (?, ?)',
                (ctx.guild.id, channel.id)
            )
            await db.commit()

        embed = discord.Embed(
            title="<:tick:1410118593089372242> AI Chat Setup Complete",
            description=f"AI chat has been set up in {channel.mention}.",
            color=0x000000
        )
        embed.set_footer(text="The AI will now respond to messages in this channel.")
        await ctx.reply(embed=embed)

    @aichat.command(name='reset', aliases=["remove"])  # type: ignore
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(administrator=True)
    async def reset_aichat(self, ctx):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT channel_id FROM aichat_settings WHERE guild_id = ?', (ctx.guild.id,)) as cursor:
                row = await cursor.fetchone()

            if not row:
                embed = discord.Embed(
                    title="<:cross:1410121962189095003> Error",
                    description="AI chat is not currently set up in this guild.",
                    color=0x000000
                )
                await ctx.reply(embed=embed)
                return

            await db.execute('DELETE FROM aichat_settings WHERE guild_id = ?', (ctx.guild.id,))
            await db.commit()

        embed = discord.Embed(
            title="<:tick:1410118593089372242> AI Chat Reset",
            description="AI chat settings have been reset for this guild. The AI will no longer respond here.",
            color=0x000000
        )
        await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT channel_id FROM aichat_settings WHERE guild_id = ?', (message.guild.id,)) as cursor:
                row = await cursor.fetchone()

        if not row or row[0] != message.channel.id:
            return

        async with message.channel.typing():
            response_text = None
            
            try:
                chat_session = self.gemini_model.start_chat(history=[
                    {"role": "user", "parts": [self.aichat_prodia]},
                    {"role": "model", "parts": ["Understood. I will now respond as CodeX, providing concise, helpful, and safe information without pinging, sending links, or promoting harmful content."]},
                ])
                # Use asyncio to properly handle the Gemini API call
                gemini_response = chat_session.send_message(message.content)
                response_text = gemini_response.text
                
            except Exception as e:
                print(f"Gemini API issue encountered. Falling back to Groq. Error: {type(e).__name__}") 

                try:
                    groq_chat_completion = self.groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": self.aichat_prodia},
                            {"role": "user", "content": message.content},
                        ],
                        model=self.groq_model,
                        temperature=0.7,
                        max_tokens=1024,
                        top_p=1,
                        stop=None,
                        stream=False,
                    )
                    response_text = groq_chat_completion.choices[0].message.content
                except APIError as e:
                    print(f"Groq API error encountered. Check Groq API key and service status. Error: {type(e).__name__}")
                except Exception as e:
                    print(f"An unexpected error occurred with Groq fallback. Error: {type(e).__name__}")

            if response_text:
                cleaned_response = await self._clean_response(response_text, message.guild)

                if len(cleaned_response) > 2000:
                    for chunk in [cleaned_response[i:i+2000] for i in range(0, len(cleaned_response), 2000)]:
                        try:
                            await message.reply(chunk)
                        except discord.Forbidden:
                            print("Bot encountered a Discord permissions error during AI chat operation (chunked).")
                            break
                        except discord.HTTPException:
                            print("Discord HTTP exception during AI chat operation (chunked).")
                            break
                else:
                    try:
                        await message.reply(cleaned_response)
                    except discord.Forbidden:
                        print("Bot encountered a Discord permissions error during AI chat operation.")
                    except discord.HTTPException:
                        print("Discord HTTP exception during AI chat operation.")

async def setup(bot):
    await bot.add_cog(AIChat(bot))
