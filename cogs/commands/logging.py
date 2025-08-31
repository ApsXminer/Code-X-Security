import discord
from discord.ext import commands
import sqlite3
import os
import asyncio
import datetime

os.makedirs("db", exist_ok=True)
DB_FILE = "db/logging.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS guild_log_settings (
                        guild_id TEXT PRIMARY KEY,
                        messages INTEGER,
                        members INTEGER,
                        channels INTEGER,
                        roles INTEGER,
                        bans INTEGER,
                        voice INTEGER,
                        moderation INTEGER,
                        configured_by TEXT,
                        config_timestamp TEXT
                    )''')
        conn.commit()

init_db()

class Logging(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_log_setups = {}

    def _get_db_connection(self):
        return sqlite3.connect(DB_FILE)

    def set_log_channel(self, guild_id, log_type, channel_id, moderator_id=None, moderator_name=None):
        with self._get_db_connection() as conn:
            c = conn.cursor()
            current_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            c.execute("INSERT OR IGNORE INTO guild_log_settings (guild_id) VALUES (?)", (str(guild_id),))
            c.execute(f"UPDATE guild_log_settings SET {log_type} = ?, configured_by = ?, config_timestamp = ? WHERE guild_id = ?",
                      (channel_id, f"{moderator_name} ({moderator_id})" if moderator_id else None, current_time, str(guild_id)))
            conn.commit()

    def get_log_channel(self, guild_id, log_type):
        with self._get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute(f"SELECT {log_type} FROM guild_log_settings WHERE guild_id = ?", (str(guild_id),))
                result = c.fetchone()
                return result[0] if result and result[0] is not None else None
            except sqlite3.OperationalError:
                return None
            
    def get_all_log_settings(self, guild_id):
        with self._get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM guild_log_settings WHERE guild_id = ?", (str(guild_id),))
            row = c.fetchone()
            if row:
                column_names = [description[0] for description in c.description]
                return dict(zip(column_names, row))
            return None
            
    def has_any_log_settings(self, guild_id):
        settings = self.get_all_log_settings(guild_id)
        if not settings:
            return False
        log_types = ["messages", "members", "channels", "roles", "bans", "voice", "moderation"]
        for log_type in log_types:
            if settings.get(log_type) is not None:
                return True
        return False

    def remove_log_channel(self, guild_id, log_type):
        with self._get_db_connection() as conn:
            c = conn.cursor()
            try:
                c.execute(f"UPDATE guild_log_settings SET {log_type} = NULL WHERE guild_id = ?", (str(guild_id),))
                conn.commit()
                return c.rowcount > 0
            except sqlite3.OperationalError:
                return False

    async def send_log(self, guild, log_type, embed):
        channel_id = self.get_log_channel(guild.id, log_type)
        if channel_id:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    print(f"Bot lacks permissions to send messages in log channel '{channel.name}' ({channel.id}) in guild '{guild.name}' ({guild.id}) for log type '{log_type}'.")
                except discord.HTTPException as e:
                    print(f"Failed to send log (type: {log_type}) in channel '{channel.name}' ({channel.id}) in guild '{guild.name}' ({guild.id}): {e}")
            else:
                print(f"Configured log channel ID {channel_id} for log type '{log_type}' in guild '{guild.name}' ({guild.id}) not found or is inaccessible.")

    def _create_log_settings_embed(self, guild_id, interaction_user=None):
        settings = self.get_all_log_settings(guild_id)
        
        embed = discord.Embed(
            title="<:icons_settings:1099577554991583292> Current Log Channel Settings",
            description="LOg SEtup HERE",
            color=discord.Color.blue()
        )
        
        log_types = ["messages", "members", "channels", "roles", "bans", "voice", "moderation"] 
        
        if settings:
            for log_type in log_types:
                channel_id = settings.get(log_type)
                if channel_id:
                    channel = self.bot.get_channel(channel_id)
                    channel_mention = channel.mention if channel else f"Deleted Channel `{channel_id}`"
                    embed.add_field(name=log_type.replace('_', ' ').capitalize(), value=channel_mention, inline=True)
                else:
                    embed.add_field(name=log_type.replace('_', ' ').capitalize(), value="*(Not Set)*", inline=True)
        else:
            embed.description = "No log channels are currently configured for this server. Use the options below to set them up."
            for log_type in log_types:
                embed.add_field(name=log_type.replace('_', ' ').capitalize(), value="*(Not Set)*", inline=True)

        if settings and settings.get("configured_by"):
            configured_by = settings.get("configured_by")
            config_timestamp_str = settings.get("config_timestamp")
            if config_timestamp_str:
                try:
                    config_timestamp = datetime.datetime.fromisoformat(config_timestamp_str)
                    embed.set_footer(text=f"Last configured by: {configured_by} at {discord.utils.format_dt(config_timestamp, 'F')}")
                except ValueError:
                    embed.set_footer(text=f"Last configured by: {configured_by}")
            else:
                embed.set_footer(text=f"Last configured by: {configured_by}")
        elif interaction_user:
            embed.set_footer(text=f"Initiated by: {interaction_user.display_name} ({interaction_user.id})")
        else:
            embed.set_footer(text="Log settings overview.")
            
        return embed

    class LogSetupView(discord.ui.View):
        def __init__(self, cog, initial_ctx):
            super().__init__(timeout=300)
            self.cog = cog
            self.initial_ctx = initial_ctx
            self.message = None

        async def on_timeout(self):
            if self.message:
                for item in self.children:
                    item.disabled = True
                try:
                    await self.message.edit(content="Log setup session timed out.", view=self)
                except discord.HTTPException:
                    pass

        @discord.ui.button(label="Manual Setup", style=discord.ButtonStyle.primary, emoji="<:icons_stagemoderator:1099577483923292260>")
        async def manual_setup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != self.initial_ctx.author:
                await interaction.response.send_message("You are not the original user who invoked this command.", ephemeral=True)
                return

            self.clear_items()
            
            log_type_options = [
                discord.SelectOption(label="Message Logs (Deleted/Edited)", value="messages", emoji="<:delete_white:1377946250049228902>"),
                discord.SelectOption(label="Member Logs (Join/Leave)", value="members", emoji="🚪"),
                discord.SelectOption(label="Channel Logs (Create/Delete/Update)", value="channels", emoji="<:x_folder2:1377946489296388147>"),
                discord.SelectOption(label="Role Logs (Create/Delete/Update)", value="roles", emoji="<:660:1372187014446710835>"),
                discord.SelectOption(label="Ban Logs (Ban/Unban)", value="bans", emoji="🔨"),
                discord.SelectOption(label="Voice Logs (Join/Leave/Move)", value="voice", emoji="🔊"),
                discord.SelectOption(label="Moderation Logs (Kicks, Webhooks, etc.)", value="moderation", emoji="👮") # Removed 'Timeouts' as it's not supported by older discord.py
            ]

            select = discord.ui.Select(
                placeholder="Select a log category to set...",
                options=log_type_options,
                min_values=1,
                max_values=1,
                custom_id="log_category_select"
            )
            select.callback = self.log_category_select_callback
            self.add_item(select)
            
            embed = self.cog._create_log_settings_embed(self.initial_ctx.guild.id, interaction.user)
            await interaction.response.edit_message(embed=embed, view=self)

        async def log_category_select_callback(self, interaction: discord.Interaction):
            if interaction.user != self.initial_ctx.author:
                await interaction.response.send_message("You are not the original user who invoked this command.", ephemeral=True)
                return

            selected_log_type = interaction.data['values'][0]
            self.cog.active_log_setups[interaction.user.id] = {"log_type": selected_log_type, "interaction_message": interaction.message}

            prompt_embed = discord.Embed(
                description=f"Please mention the channel (e.g., `#general`) or provide its ID where you want `{selected_log_type.replace('_', ' ').capitalize()}` logs to be sent.",
                color=discord.Color.yellow()
            )
            await interaction.response.send_message(embed=prompt_embed, ephemeral=False)

            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel

            try:
                response_msg = await self.cog.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                followup_msg = await interaction.followup.send("You took too long to provide a channel. Please restart the setup.", ephemeral=False)
                if interaction.user.id in self.cog.active_log_setups:
                    del self.cog.active_log_setups[interaction.user.id]
                await asyncio.sleep(5)
                await followup_msg.delete()
                return

            try:
                await response_msg.delete()
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

            channel_input = response_msg.content
            channel_obj = None

            try:
                if channel_input.startswith('<#') and channel_input.endswith('>'):
                    channel_id = int(channel_input[2:-1])
                    channel_obj = interaction.guild.get_channel(channel_id)
                else:
                    channel_obj = interaction.guild.get_channel(int(channel_input))
            except ValueError:
                pass

            if not channel_obj or not isinstance(channel_obj, discord.TextChannel):
                fail_msg = await interaction.followup.send("❌ Invalid channel provided. Please try again with a valid channel mention or ID.", ephemeral=False)
                if interaction.user.id in self.cog.active_log_setups:
                    del self.cog.active_log_setups[interaction.user.id]
                await asyncio.sleep(5)
                await fail_msg.delete()
                return

            self.cog.set_log_channel(
                interaction.guild.id, 
                selected_log_type, 
                channel_obj.id, 
                interaction.user.id, 
                interaction.user.display_name
            )
            
            success_msg = await interaction.followup.send(f"✅ Successfully updated `{selected_log_type.replace('_', ' ').capitalize()}` logs to {channel_obj.mention}.", ephemeral=False)
            
            embed = self.cog._create_log_settings_embed(interaction.guild.id, interaction.user)
            await self.message.edit(embed=embed, view=self)

            if interaction.user.id in self.cog.active_log_setups:
                del self.cog.active_log_setups[interaction.user.id]
            await asyncio.sleep(5)
            await success_msg.delete()


        @discord.ui.button(label="Auto Setup", style=discord.ButtonStyle.secondary, emoji="✨")
        async def auto_setup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != self.initial_ctx.author:
                await interaction.response.send_message("You are not the original user who invoked this command.", ephemeral=True)
                return

            self.clear_items()
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(content="Initiating automatic log setup...", embed=None, view=self)
            
            try:
                await self.cog._perform_auto_setup(self.initial_ctx, interaction.user)
                embed = self.cog._create_log_settings_embed(self.initial_ctx.guild.id, interaction.user)
                await self.message.edit(content="✅ Automatic log setup completed!", embed=embed, view=None)
            except commands.MissingPermissions:
                await self.message.edit(content="❌ I do not have sufficient permissions (Manage Channels) to perform auto-setup. Please grant them and try again.", embed=None, view=None)
            except Exception as e:
                await self.message.edit(content=f"❌ An error occurred during auto-setup: {e}", embed=None, view=None)
            finally:
                self.stop()

    @commands.command(name="setuplog")
    @commands.has_permissions(administrator=True)
    async def setuplog_interactive(self, ctx):
        if self.has_any_log_settings(ctx.guild.id):
            await ctx.send("Logs are already set up for this server. Use `$resetlog` to clear all current log settings before setting up new ones.", ephemeral=True)
            return

        # Showing "Loading Logsetup..."
        loading_message = await ctx.send("⏳ Loading Logsetup...")
        await asyncio.sleep(1) # Small delay to show the loading message

        embed = self._create_log_settings_embed(ctx.guild.id, ctx.author)
        view = self.LogSetupView(self, ctx)
        
        # Edit the loading message to show the actual setup embed and view
        await loading_message.edit(content=None, embed=embed, view=view)
        view.message = loading_message # Assign the edited message to the view for interaction

    @commands.command(name="resetlog")
    @commands.has_permissions(administrator=True)
    async def resetlog_command(self, ctx):
        with self._get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM guild_log_settings WHERE guild_id = ?", (str(ctx.guild.id),))
            conn.commit()
        await ctx.send("<:delete_white:1377946250049228902> All logging channel configurations for this server have been reset.")

    async def _perform_auto_setup(self, ctx, user):
        guild = ctx.guild
        category_name = "CODE X LOGS"
        log_channels_to_create = {
            "messages": "codex-message-logs",
            "members": "codex-member-logs",
            "channels": "codex-channel-logs",
            "roles": "codex-role-logs",
            "bans": "codex-moderation-logs", 
            "voice": "codex-voice-logs",
            "moderation": "codex-moderation-logs"
        }

        # Define permissions for the category and channels
        everyone_perms = discord.PermissionOverwrite(read_messages=False)
        bot_perms = discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)
        # admin_perms = discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True)

        everyone_role = guild.default_role

        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            try:
                category = await guild.create_category(
                    category_name,
                    overwrites={
                        everyone_role: everyone_perms,
                        guild.me: bot_perms,
                        # guild.get_role(YOUR_ADMIN_ROLE_ID): admin_perms
                    },
                    reason="Automatic log setup"
                )
            except discord.Forbidden:
                raise commands.MissingPermissions(["manage_channels"])
            except Exception as e:
                raise e

        channels_created_or_found = []
        for log_type, channel_name in log_channels_to_create.items():
            existing_channel = discord.utils.get(category.text_channels, name=channel_name)
            if not existing_channel:
                try:
                    new_channel = await guild.create_text_channel(
                        channel_name,
                        category=category,
                        overwrites={
                            everyone_role: everyone_perms,
                            guild.me: bot_perms,
                            # guild.get_role(YOUR_ADMIN_ROLE_ID): admin_perms
                        },
                        reason=f"Automatic log setup for {log_type}"
                    )
                    self.set_log_channel(guild.id, log_type, new_channel.id, user.id, user.display_name)
                    channels_created_or_found.append(new_channel.mention)
                except discord.Forbidden:
                    raise commands.MissingPermissions(["manage_channels"])
                except Exception as e:
                    print(f"Error creating channel `{channel_name}`: {e}")
                    continue
            else:
                current_overwrites = existing_channel.overwrites
                current_overwrites[everyone_role] = everyone_perms
                current_overwrites[guild.me] = bot_perms
                # current_overwrites[guild.get_role(YOUR_ADMIN_ROLE_ID)] = admin_perms
                try:
                    await existing_channel.edit(overwrites=current_overwrites)
                    self.set_log_channel(guild.id, log_type, existing_channel.id, user.id, user.display_name)
                    channels_created_or_found.append(existing_channel.mention)
                except discord.Forbidden:
                    raise commands.MissingPermissions(["manage_channels"])
                except Exception as e:
                    print(f"Error updating channel permissions for `{channel_name}`: {e}")
                    continue
        
        # The 'pass' statement that was here previously has been replaced by the above logic.

    @commands.group(name="removelog", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def removelog(self, ctx):
        await ctx.send("Please specify a log type to remove. Available types: `messages`, `members`, `channels`, `roles`, `bans`, `voice`, `moderation`, `all`.\n"
                       "Example: `!removelog messages`")

    @removelog.command(name="messages")
    @commands.has_permissions(administrator=True)
    async def removelog_messages(self, ctx):
        if self.remove_log_channel(ctx.guild.id, "messages"):
            await ctx.send("<:delete_white:1377946250049228902> Message log channel setting removed.")
        else:
            await ctx.send("ℹ️ No message log channel was set for this server.")

    @removelog.command(name="members")
    @commands.has_permissions(administrator=True)
    async def removelog_members(self, ctx):
        if self.remove_log_channel(ctx.guild.id, "members"):
            await ctx.send("<:delete_white:1377946250049228902> Member log channel setting removed.")
        else:
            await ctx.send("ℹ️ No member log channel was set for this server.")

    @removelog.command(name="channels")
    @commands.has_permissions(administrator=True)
    async def removelog_channels(self, ctx):
        if self.remove_log_channel(ctx.guild.id, "channels"):
            await ctx.send("<:delete_white:1377946250049228902> Channel log channel setting removed.")
        else:
            await ctx.send("ℹ️ No channel log channel was set for this server.")

    @removelog.command(name="roles")
    @commands.has_permissions(administrator=True)
    async def removelog_roles(self, ctx):
        if self.remove_log_channel(ctx.guild.id, "roles"):
            await ctx.send("<:delete_white:1377946250049228902> Role log channel setting removed.")
        else:
            await ctx.send("ℹ️ No role log channel was set for this server.")

    @removelog.command(name="bans")
    @commands.has_permissions(administrator=True)
    async def removelog_bans(self, ctx):
        if self.remove_log_channel(ctx.guild.id, "bans"):
            await ctx.send("<:delete_white:1377946250049228902> Ban/Unban log channel setting removed.")
        else:
            await ctx.send("ℹ️ No ban/unban log channel was set for this server.")

    @removelog.command(name="voice")
    @commands.has_permissions(administrator=True)
    async def removelog_voice(self, ctx):
        if self.remove_log_channel(ctx.guild.id, "voice"):
            await ctx.send("<:delete_white:1377946250049228902> Voice log channel setting removed.")
        else:
            await ctx.send("ℹ️ No voice log channel was set for this server.")

    @removelog.command(name="moderation")
    @commands.has_permissions(administrator=True)
    async def removelog_moderation(self, ctx):
        if self.remove_log_channel(ctx.guild.id, "moderation"):
            await ctx.send("<:delete_white:1377946250049228902> General moderation log channel setting removed.")
        else:
            await ctx.send("ℹ️ No general moderation log channel was set for this server.")

    @removelog.command(name="all")
    @commands.has_permissions(administrator=True)
    async def removelog_all(self, ctx):
        with self._get_db_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM guild_log_settings WHERE guild_id = ?", (str(ctx.guild.id),))
            conn.commit()
        await ctx.send("<:delete_white:1377946250049228902> All logging channel configurations removed for this server.")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        # Crucial check: Ensure bot is not processing its own messages or messages outside a guild
        if message.author.bot or not message.guild:
            return

        # Ensure the bot has the necessary intents to receive message content
        # For on_message_delete to provide content, Intents.message_content MUST be enabled
        # and the message must be in the bot's cache.
        # If message.content is None, it means the bot didn't have content intent or message wasn't cached.
        if message.content is None and not message.attachments:
            # If no content and no attachments, there's nothing meaningful to log
            print(f"DEBUG: Message delete event for {message.id} in {message.guild.name} had no content or attachments (missing intent/cache?).")
            return

        embed = discord.Embed(
            title="<:delete_white:1377946250049228902> Message Deleted",
            description=f"Message sent by {message.author.mention} was deleted in {message.channel.mention}.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=f"{message.author.display_name} ({message.author.id})", icon_url=message.author.display_avatar.url)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Message ID", value=f"```fix\n{message.id}```", inline=True)
        
        content = message.content if message.content else "*(No text content)*"
        if len(content) > 1000:
            content = content[:997] + "..."
        embed.add_field(name="Content", value=f"```\n{discord.utils.escape_markdown(content)}```", inline=False)

        if message.attachments:
            attachment_info = []
            for att in message.attachments:
                attachment_info.append(f"[{att.filename}]({att.url}) (`{round(att.size / 1024, 2)} KB`)")
            embed.add_field(name="Attachments", value="\n".join(attachment_info), inline=False)
        
        embed.set_footer(text=f"User ID: {message.author.id} | Channel ID: {message.channel.id}")
        await self.send_log(message.guild, "messages", embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or not before.guild or before.content == after.content:
            return

        embed = discord.Embed(
            title="✏️ Message Edited",
            description=f"Message sent by {before.author.mention} was edited in {before.channel.mention}.",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=f"{before.author.display_name} ({before.author.id})", icon_url=before.author.display_avatar.url)
        embed.add_field(name="Channel", value=before.channel.mention, inline=True)
        embed.add_field(name="Message ID", value=f"```fix\n{before.id}```", inline=True)
        embed.url = after.jump_url

        before_content = before.content if before.content else "*(No text content)*"
        if len(before_content) > 900:
            before_content = before_content[:897] + "..."
        embed.add_field(name="Old Content", value=f"```\n{discord.utils.escape_markdown(before_content)}```", inline=False)

        after_content = after.content if after.content else "*(No text content)*"
        if len(after_content) > 900:
            after_content = after_content[:897] + "..."
        embed.add_field(name="New Content", value=f"```\n{discord.utils.escape_markdown(after_content)}```", inline=False)
        
        embed.set_footer(text=f"User ID: {before.author.id} | Channel ID: {before.channel.id}")
        await self.send_log(before.guild, "messages", embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        embed = discord.Embed(
            title="✅ Member Joined",
            description=f"{member.mention} has joined the server.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=f"{member.display_name} ({member.id})", icon_url=member.display_avatar.url)
        embed.add_field(name="Account Created", value=f"{discord.utils.format_dt(member.created_at, 'F')} ({discord.utils.format_dt(member.created_at, 'R')})", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member ID: {member.id} | Current Members: {member.guild.member_count}")
        await self.send_log(member.guild, "members", embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        embed = discord.Embed(
            title="🚪 Member Left",
            description=f"{member.mention} has left the server.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=f"{member.display_name} ({member.id})", icon_url=member.display_avatar.url)
        embed.add_field(name="Joined Server", value=f"{discord.utils.format_dt(member.joined_at, 'F')} ({discord.utils.format_dt(member.joined_at, 'R')})" if member.joined_at else "*(Unknown)*", inline=False)
        
        moderator = "*(N/A)*"
        reason = "*(No reason provided)*"
        action_type = "Left"

        if member.guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
                    if entry.target.id == member.id and (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds() < 5:
                        moderator = entry.user.mention
                        reason = entry.reason or "*(No reason provided)*"
                        action_type = "Kicked"
                        break
                if action_type == "Left":
                    async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                        if entry.target.id == member.id and (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds() < 5:
                            moderator = entry.user.mention
                            reason = entry.reason or "*(No reason provided)*"
                            action_type = "Banned"
                            break
            except discord.Forbidden:
                embed.set_footer(text="Missing permissions to view audit logs for reason/moderator.")
            except Exception as e:
                print(f"Error fetching audit log for member remove: {e}")

        embed.add_field(name="Action Type", value=action_type, inline=True)
        if action_type != "Left":
            embed.add_field(name="Moderator", value=moderator, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member ID: {member.id} | Current Members: {member.guild.member_count}")
        await self.send_log(member.guild, "members", embed)


    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        if not channel.guild: return

        embed = discord.Embed(
            title="<:x_folder2:1377946489296388147> Channel Created",
            description=f"A new channel, {channel.mention}, has been created.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Name", value=channel.name, inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace("ChannelType.", "").title(), inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "*(None)*", inline=True)
        embed.add_field(name="ID", value=f"```fix\n{channel.id}```", inline=True)

        if isinstance(channel, discord.TextChannel):
            embed.add_field(name="Topic", value=channel.topic or "*(No topic)*", inline=False)
            embed.add_field(name="NSFW", value=channel.is_nsfw(), inline=True)
            embed.add_field(name="Slowmode", value=f"{channel.slowmode_delay}s", inline=True)
        elif isinstance(channel, discord.VoiceChannel):
            embed.add_field(name="User Limit", value=channel.user_limit if channel.user_limit else "*(None)*", inline=True)
            embed.add_field(name="Bitrate", value=f"{channel.bitrate / 1000}kbps", inline=True)
        
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_log(channel.guild, "channels", embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not channel.guild: return

        embed = discord.Embed(
            title="<:delete_white:1377946250049228902> Channel Deleted",
            description=f"The channel `{channel.name}` has been deleted.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Name", value=channel.name, inline=True)
        embed.add_field(name="Type", value=str(channel.type).replace("ChannelType.", "").title(), inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "*(None)*", inline=True)
        embed.add_field(name="ID", value=f"```fix\n{channel.id}```", inline=True)
        
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await self.send_log(channel.guild, "channels", embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if not before.guild: return

        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        if before.category != after.category:
            changes.append(f"**Category:** `{before.category.name if before.category else 'None'}` → `{after.category.name if after.category else 'None'}`")

        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if before.topic != after.topic:
                old_topic = before.topic or "*(No topic)*"
                new_topic = after.topic or "*(No topic)*"
                if len(old_topic) > 100: old_topic = old_topic[:97] + "..."
                if len(new_topic) > 100: new_topic = new_topic[:97] + "..."
                changes.append(f"**Topic:** ```\n{old_topic}``` → ```\n{new_topic}```")
            if before.is_nsfw() != after.is_nsfw():
                changes.append(f"**NSFW:** `{before.is_nsfw()}` → `{after.is_nsfw()}`")
            if before.slowmode_delay != after.slowmode_delay:
                changes.append(f"**Slowmode:** `{before.slowmode_delay}s` → `{after.slowmode_delay}s`")
        elif isinstance(before, discord.VoiceChannel) and isinstance(after, discord.VoiceChannel):
            if before.user_limit != after.user_limit:
                changes.append(f"**User Limit:** `{before.user_limit if before.user_limit else 'None'}` → `{after.user_limit if after.user_limit else 'None'}`")
            if before.bitrate != after.bitrate:
                changes.append(f"**Bitrate:** `{before.bitrate / 1000}kbps` → `{after.bitrate / 1000}kbps`")
            if before.rtc_region != after.rtc_region:
                changes.append(f"**Region:** `{before.rtc_region or 'Automatic'}` → `{after.rtc_region or 'Automatic'}`")

        if before.overwrites != after.overwrites:
             changes.append("**Permissions Overwrites:** Changed")

        if not changes:
            return

        embed = discord.Embed(
            title="🔧 Channel Updated",
            description=f"The channel {after.mention} has been updated.",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Channel", value=after.mention, inline=True)
        embed.add_field(name="ID", value=f"```fix\n{after.id}```", inline=True)
        embed.add_field(name="Type", value=str(after.type).replace("ChannelType.", "").title(), inline=True)
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)
        
        embed.set_footer(text=f"Channel ID: {after.id}")
        await self.send_log(before.guild, "channels", embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        embed = discord.Embed(
            title="➕ Role Created",
            description=f"A new role, {role.mention}, has been created.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Name", value=role.name, inline=True)
        embed.add_field(name="ID", value=f"```fix\n{role.id}```", inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Mentionable", value=role.mentionable, inline=True)
        embed.add_field(name="Hoisted (Display Separately)", value=role.hoist, inline=True)
        embed.add_field(name="Managed by Integration", value=role.managed, inline=True)
        
        key_permissions = []
        for perm, value in role.permissions:
            if value and perm in ["administrator", "kick_members", "ban_members", "manage_channels", "manage_roles", "manage_guild", "mention_everyone"]:
                key_permissions.append(perm.replace("_", " ").title())
        if key_permissions:
            embed.add_field(name="Key Permissions", value=", ".join(key_permissions), inline=False)
        
        embed.set_footer(text=f"Role ID: {role.id}")
        await self.send_log(role.guild, "roles", embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        embed = discord.Embed(
            title="➖ Role Deleted",
            description=f"The role `{role.name}` has been deleted.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Name", value=role.name, inline=True)
        embed.add_field(name="ID", value=f"```fix\n{role.id}```", inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.set_footer(text=f"Role ID: {role.id}")
        await self.send_log(role.guild, "roles", embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        changes = []
        if before.name != after.name:
            changes.append(f"**Name:** `{before.name}` → `{after.name}`")
        if before.color != after.color:
            changes.append(f"**Color:** `{before.color}` → `{after.color}`")
        if before.hoist != after.hoist:
            changes.append(f"**Display Separately:** `{before.hoist}` → `{after.hoist}`")
        if before.mentionable != after.mentionable:
            changes.append(f"**Mentionable:** `{before.mentionable}` → `{after.mentionable}`")
        
        if before.permissions.value != after.permissions.value:
            perm_changes = []
            for perm, value_before in before.permissions:
                value_after = getattr(after.permissions, perm)
                if value_before != value_after:
                    perm_changes.append(f"`{perm.replace('_', ' ').title()}`: `{value_before}` → `{value_after}`")
            if perm_changes:
                changes.append("**Permissions Changes:**\n" + "\n".join(perm_changes))
            else:
                 changes.append("**Permissions:** Changed")

        if not changes:
            return

        embed = discord.Embed(
            title="🛠️ Role Updated",
            description=f"The role {after.mention} has been updated.",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Role", value=after.mention, inline=True)
        embed.add_field(name="ID", value=f"```fix\n{after.id}```", inline=True)
        embed.add_field(name="Changes", value="\n".join(changes), inline=False)
        
        embed.set_footer(text=f"Role ID: {after.id}")
        await self.send_log(before.guild, "roles", embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"User {user.mention} has been banned from the server.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=f"{user} ({user.id})", icon_url=user.display_avatar.url)
        
        moderator = "*(N/A)*"
        reason = "*(No reason provided)*"
        if guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
                    if entry.target.id == user.id and (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds() < 5:
                        moderator = entry.user.mention
                        reason = entry.reason or "*(No reason provided)*"
                        break
            except discord.Forbidden:
                embed.set_footer(text="Missing permissions to view audit logs for reason/moderator.")
            except Exception as e:
                print(f"Error fetching audit log for ban: {e}")

        embed.add_field(name="Moderator", value=moderator, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        embed.set_footer(text=f"User ID: {user.id}")
        
        await self.send_log(guild, "bans", embed)
        if self.get_log_channel(guild.id, "moderation") != self.get_log_channel(guild.id, "bans"):
            await self.send_log(guild, "moderation", embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        embed = discord.Embed(
            title="⚖️ Member Unbanned",
            description=f"User {user.mention} has been unbanned from the server.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=f"{user} ({user.id})", icon_url=user.display_avatar.url)
        
        moderator = "*(N/A)*"
        reason = "*(No reason provided)*"
        if guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
                    if entry.target.id == user.id and (datetime.datetime.now(datetime.timezone.utc) - entry.created_at).total_seconds() < 5:
                        moderator = entry.user.mention
                        reason = entry.reason or "*(No reason provided)*"
                        break
            except discord.Forbidden:
                embed.set_footer(text="Missing permissions to view audit logs for reason/moderator.")
            except Exception as e:
                print(f"Error fetching audit log for unban: {e}")

        embed.add_field(name="Moderator", value=moderator, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        embed.set_footer(text=f"User ID: {user.id}")
        
        await self.send_log(guild, "bans", embed)
        if self.get_log_channel(guild.id, "moderation") != self.get_log_channel(guild.id, "bans"):
            await self.send_log(guild, "moderation", embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        embed = discord.Embed(timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.set_author(name=f"{member.display_name} ({member.id})", icon_url=member.display_avatar.url)
        embed.set_footer(text=f"Member ID: {member.id}")

        if before.channel is None and after.channel is not None:
            embed.title = "🔊 Voice Channel Joined"
            embed.description = f"{member.mention} joined voice channel {after.channel.mention}."
            embed.color = discord.Color.green()
            embed.add_field(name="Channel", value=after.channel.mention, inline=True)
            embed.add_field(name="Channel ID", value=f"```fix\n{after.channel.id}```", inline=True)
        elif before.channel is not None and after.channel is None:
            embed.title = "🔇 Voice Channel Left"
            embed.description = f"{member.mention} left voice channel {before.channel.mention}."
            embed.color = discord.Color.red()
            embed.add_field(name="Channel", value=before.channel.mention, inline=True)
            embed.add_field(name="Channel ID", value=f"```fix\n{before.channel.id}```", inline=True)
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            embed.title = "🔄 Voice Channel Moved"
            embed.description = f"{member.mention} moved from {before.channel.mention} to {after.channel.mention}."
            embed.color = discord.Color.blue()
            embed.add_field(name="From", value=before.channel.mention, inline=True)
            embed.add_field(name="To", value=after.channel.mention, inline=True)
            embed.add_field(name="From ID", value=f"```fix\n{before.channel.id}```", inline=True)
            embed.add_field(name="To ID", value=f"```fix\n{after.channel.id}```", inline=True)
        else:
            changes = []
            if before.self_mute != after.self_mute:
                changes.append(f"Self-Mute: `{before.self_mute}` → `{after.self_mute}`")
            if before.self_deaf != after.self_deaf:
                changes.append(f"Self-Deafen: `{before.self_deaf}` → `{after.self_deaf}`")
            if before.mute != after.mute:
                changes.append(f"Server Mute: `{before.mute}` → `{after.mute}`")
            if before.deaf != after.deaf:
                changes.append(f"Server Deafen: `{before.deaf}` → `{after.deaf}`")
            if before.self_stream != after.self_stream:
                changes.append(f"Streaming: `{before.self_stream}` → `{after.self_stream}`")
            if before.self_video != after.self_video:
                changes.append(f"Video: `{before.self_video}` → `{after.self_video}`")

            if not changes:
                return

            embed.title = "🎙️ Voice State Updated"
            embed.description = f"{member.mention}'s voice state updated in {after.channel.mention if after.channel else '*(No Channel)*'}."
            embed.color = discord.Color.light_grey()
            embed.add_field(name="Changes", value="\n".join(changes), inline=False)
            embed.add_field(name="Channel", value=after.channel.mention if after.channel else "*(None)*", inline=True)
            
        await self.send_log(member.guild, "voice", embed)

    @commands.Cog.listener()
    async def on_audit_log_entry(self, entry):
        guild = entry.guild
        if not guild or entry.user.bot: # Ignore bot actions
            return

        embed = None
        log_type_to_send = "moderation" # Default to moderation log

        if entry.action == discord.AuditLogAction.webhook_create:
            embed = discord.Embed(
                title="🌐 Webhook Created",
                description=f"A new webhook `{entry.target.name}` was created by {entry.user.mention}.",
                color=discord.Color.green(),
                timestamp=entry.created_at
            )
            embed.add_field(name="Webhook Name", value=entry.target.name, inline=True)
            embed.add_field(name="Webhook ID", value=f"```fix\n{entry.target.id}```", inline=True)
            embed.add_field(name="Channel", value=entry.target.channel.mention if entry.target.channel else "*(Unknown)*", inline=True)
            embed.set_footer(text=f"Moderator ID: {entry.user.id}")

        elif entry.action == discord.AuditLogAction.webhook_update:
            embed = discord.Embed(
                title="🌐 Webhook Updated",
                description=f"Webhook `{entry.target.name}` was updated by {entry.user.mention}.",
                color=discord.Color.orange(),
                timestamp=entry.created_at
            )
            embed.add_field(name="Webhook Name", value=entry.target.name, inline=True)
            embed.add_field(name="Webhook ID", value=f"```fix\n{entry.target.id}```", inline=True)
            embed.add_field(name="Channel", value=entry.target.channel.mention if entry.target.channel else "*(Unknown)*", inline=True)
            
            changes = []
            for key, value in entry.changes.items():
                changes.append(f"**{key.capitalize()}:** `{value.before}` → `{value.after}`")
            if changes:
                embed.add_field(name="Changes", value="\n".join(changes), inline=False)
            
            embed.set_footer(text=f"Moderator ID: {entry.user.id}")

        elif entry.action == discord.AuditLogAction.webhook_delete:
            embed = discord.Embed(
                title="🌐 Webhook Deleted",
                description=f"Webhook `{entry.target.name}` was deleted by {entry.user.mention}.",
                color=discord.Color.red(),
                timestamp=entry.created_at
            )
            embed.add_field(name="Webhook Name", value=entry.target.name, inline=True)
            embed.add_field(name="Webhook ID", value=f"```fix\n{entry.target.id}```", inline=True)
            embed.set_footer(text=f"Moderator ID: {entry.user.id}")
        
        # Add other moderation actions here if they don't have dedicated listeners
        # For example, if you want to log kicks specifically here (though on_member_remove tries)
        # if entry.action == discord.AuditLogAction.kick:
        #     # This would be a fallback if on_member_remove didn't catch it or for extra detail
        #     pass

        if embed:
            await self.send_log(guild, log_type_to_send, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # This listener has been updated to remove checks for 'timed_out'
        # which is not present in older discord.py versions.
        # As a result, native Discord timeouts cannot be logged with older versions.
        
        # Check for other member updates that might be relevant if desired,
        # e.g., role changes.
        # Example: Logging role changes
        if before.roles != after.roles:
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]

            if added_roles or removed_roles:
                embed = discord.Embed(
                    title="👤 Member Roles Updated",
                    description=f"Roles for {after.mention} have been updated.",
                    color=discord.Color.blue(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                embed.set_author(name=f"{after.display_name} ({after.id})", icon_url=after.display_avatar.url)
                if added_roles:
                    embed.add_field(name="Roles Added", value=", ".join([role.mention for role in added_roles]), inline=False)
                if removed_roles:
                    embed.add_field(name="Roles Removed", value=", ".join([role.mention for role in removed_roles]), inline=False)
                embed.set_footer(text=f"User ID: {after.id}")
                await self.send_log(after.guild, "members", embed) # Or 'moderation' depending on preference

        # Other potential updates (e.g., nickname changes, activity status) could be added here
        if before.nick != after.nick:
            embed = discord.Embed(
                title="📝 Member Nickname Updated",
                description=f"{after.mention}'s nickname was updated.",
                color=discord.Color.light_grey(),
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.set_author(name=f"{after.display_name} ({after.id})", icon_url=after.display_avatar.url)
            embed.add_field(name="Old Nickname", value=before.nick or "*(None)*", inline=True)
            embed.add_field(name="New Nickname", value=after.nick or "*(None)*", inline=True)
            embed.set_footer(text=f"User ID: {after.id}")
            await self.send_log(after.guild, "members", embed) # Or 'moderation'