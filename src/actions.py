"""
Action Handler for Scribble Discord Bot
Handles Discord actions like timeouts, bans, nicknames, DMs, voice channels, and image search
"""

import os
import logging
import asyncio
import aiohttp
import random
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import discord
from fuzzywuzzy import fuzz

class ActionHandler:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.logger = logging.getLogger('ActionHandler')
        
        # Action tracking for safety
        self.action_history = []
        
    async def execute_action(self, action_string: str, channel: discord.TextChannel, requester: discord.Member):
        """Parse and execute an action command"""
        self.logger.info(f"Executing action: {action_string}")
        
        # Parse action
        parts = action_string.strip().split()
        if not parts:
            return
            
        action_type = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        # Check if action is enabled
        if not self.is_action_enabled(action_type):
            await channel.send("*sowwy, that action is disabled... uwu*")
            return
            
        # Check rate limits
        if not self.check_action_rate_limit():
            await channel.send("*I'm doing too many things at once! Need to slow down... uwu*")
            return
            
        try:
            # Execute specific action
            if action_type == "timeout":
                await self.handle_timeout(args, channel, requester)
            elif action_type == "ban":
                await self.handle_ban(args, channel, requester)
            elif action_type == "nickname":
                await self.handle_nickname(args, channel, requester)
            elif action_type == "dm":
                await self.handle_dm(args, channel, requester)
            elif action_type == "vcjoin":
                await self.handle_voice_join(args, channel, requester)
            elif action_type == "image":
                await self.handle_image_search(args, channel)
            else:
                await channel.send(f"*confused scribble noises* I don't know how to do '{action_type}'... uwu")
                
        except Exception as e:
            self.logger.error(f"Error executing action {action_type}: {e}")
            await channel.send("*oopsie! Something went wrong while trying to do that... sowwy! uwu*")
            
    def is_action_enabled(self, action_type: str) -> bool:
        """Check if an action type is enabled in config"""
        safety_config = self.config.get('safety', {})
        
        action_map = {
            'timeout': 'enable_timeouts',
            'ban': 'enable_bans',
            'nickname': 'enable_nicknames',
            'dm': True,  # DMs always enabled
            'vcjoin': True,  # Voice join always enabled
            'image': True   # Image search always enabled
        }
        
        if action_type not in action_map:
            return False
            
        setting = action_map[action_type]
        if isinstance(setting, bool):
            return setting
            
        return safety_config.get(setting, True)
        
    def check_action_rate_limit(self) -> bool:
        """Check if we're within action rate limits"""
        max_actions = self.config.get('discord.max_actions_per_hour', 10)
        now = datetime.now()
        
        # Remove old actions (older than 1 hour)
        self.action_history = [
            action_time for action_time in self.action_history 
            if (now - action_time).seconds < 3600
        ]
        
        if len(self.action_history) >= max_actions:
            return False
            
        self.action_history.append(now)
        return True
        
    async def handle_timeout(self, args, channel, requester):
        """Handle timeout action"""
        if len(args) < 2:
            await channel.send("*confused* I need a username and time! Like 'timeout username 5' uwu")
            return
            
        username = args[0].strip('"\'')
        try:
            minutes = int(args[1])
        except ValueError:
            await channel.send("*scratches head* That doesn't look like a number for minutes... uwu")
            return
            
        # Safety check
        max_timeout = self.config.get('safety.max_timeout_minutes', 60)
        if minutes > max_timeout:
            minutes = max_timeout
            await channel.send(f"*nervously* That's too long! I'll make it {minutes} minutes instead... uwu")
            
        # Find user
        member = await self.find_member(channel.guild, username)
        if not member:
            await channel.send(f"*looks around confused* I can't find anyone named '{username}'... uwu")
            return
            
        # Check if user is protected
        if self.is_protected_user(member):
            await channel.send("*shakes head* I can't timeout that person! They're too important... uwu")
            return
            
        try:
            timeout_until = datetime.now() + timedelta(minutes=minutes)
            await member.timeout(timeout_until, reason=f"Timeout by Scribble (requested by {requester.display_name})")
            await channel.send(f"*apologetically* Sowwy {member.display_name}, you're in timeout for {minutes} minutes... uwu")
            
        except discord.Forbidden:
            await channel.send("*sad scribble noises* I don't have permission to timeout people... uwu")
        except discord.HTTPException as e:
            await channel.send(f"*confused* Something went wrong: {e}... uwu")
            
    async def handle_ban(self, args, channel, requester):
        """Handle ban action"""
        if not args:
            await channel.send("*nervously* I need a username to ban... but are you sure? That's really serious! uwu")
            return
            
        username = args[0].strip('"\'')
        
        # Find user
        member = await self.find_member(channel.guild, username)
        if not member:
            await channel.send(f"*looks around* I can't find anyone named '{username}'... maybe that's for the best? uwu")
            return
            
        # Check if user is protected
        if self.is_protected_user(member):
            await channel.send("*shakes head frantically* NO NO NO! I can't ban that person! They're way too important! uwu")
            return
            
        try:
            await member.ban(reason=f"Ban by Scribble (requested by {requester.display_name})")
            await channel.send(f"*very sadly* I... I banned {member.display_name}... I hope they come back someday... *sniffles* uwu")
            
        except discord.Forbidden:
            await channel.send("*relieved sigh* Actually, I don't have permission to ban people... maybe that's good? uwu")
        except discord.HTTPException as e:
            await channel.send(f"*confused* Something went wrong: {e}... uwu")
            
    async def handle_nickname(self, args, channel, requester):
        """Handle nickname change action"""
        if len(args) < 2:
            await channel.send("*tilts head* I need a username and a new nickname! uwu")
            return
            
        username = args[0].strip('"\'')
        new_nickname = " ".join(args[1:]).strip('"\'')
        
        # Find user
        member = await self.find_member(channel.guild, username)
        if not member:
            await channel.send(f"*looks confused* I can't find anyone named '{username}'... uwu")
            return
            
        # Check if user is protected
        if self.is_protected_user(member):
            await channel.send("*nervously* I probably shouldn't change their nickname... they're important! uwu")
            return
            
        try:
            old_name = member.display_name
            await member.edit(nick=new_nickname, reason=f"Nickname change by Scribble (requested by {requester.display_name})")
            await channel.send(f"*proudly* I changed {old_name}'s nickname to '{new_nickname}'! Do you like it? uwu")
            
        except discord.Forbidden:
            await channel.send("*sad* I don't have permission to change nicknames... uwu")
        except discord.HTTPException as e:
            await channel.send(f"*confused* Something went wrong: {e}... uwu")
            
    async def handle_dm(self, args, channel, requester):
        """Handle direct message action"""
        if len(args) < 2:
            await channel.send("*confused* I need a username and a message to send! uwu")
            return
            
        username = args[0].strip('"\'')
        message = " ".join(args[1:]).strip('"\'')
        
        # Find user
        member = await self.find_member(channel.guild, username)
        if not member:
            await channel.send(f"*looks around* I can't find anyone named '{username}'... uwu")
            return
            
        try:
            await member.send(f"Hi! Scribble here! Someone asked me to tell you: {message} uwu")
            await channel.send(f"*happily* I sent a message to {member.display_name}! uwu")
            
        except discord.Forbidden:
            await channel.send(f"*sadly* {member.display_name} has their DMs closed... I can't message them... uwu")
        except discord.HTTPException as e:
            await channel.send(f"*confused* Something went wrong: {e}... uwu")
            
    async def handle_voice_join(self, args, channel, requester):
        """Handle voice channel join action"""
        if not args:
            await channel.send("*confused* Which voice channel should I join? uwu")
            return
            
        channel_name = args[0].strip('"\'')
        minutes = 5  # Default
        
        if len(args) > 1:
            try:
                minutes = int(args[1])
                minutes = min(minutes, 30)  # Max 30 minutes
            except ValueError:
                pass
                
        # Find voice channel
        voice_channel = None
        for vc in channel.guild.voice_channels:
            if channel_name.lower() in vc.name.lower():
                voice_channel = vc
                break
                
        if not voice_channel:
            await channel.send(f"*looks confused* I can't find a voice channel called '{channel_name}'... uwu")
            return
            
        try:
            # Check if already connected
            if channel.guild.voice_client:
                await channel.guild.voice_client.disconnect()
                
            voice_client = await voice_channel.connect()
            await channel.send(f"*excitedly* I joined {voice_channel.name}! I'll stay for {minutes} minutes! uwu")
            
            # Create background task for auto-disconnect
            async def auto_disconnect():
                await asyncio.sleep(minutes * 60)
                if voice_client.is_connected():
                    await voice_client.disconnect()
                    await channel.send("*waves* Time's up! Leaving the voice channel now! uwu")
            
            # Start the background task without blocking
            asyncio.create_task(auto_disconnect())
                
        except discord.ClientException:
            await channel.send("*confused* I'm already connected to a voice channel... uwu")
        except discord.opus.OpusNotLoaded:
            await channel.send("*technical difficulties* Voice isn't working properly... sowwy! uwu")
        except Exception as e:
            await channel.send(f"*confused* I couldn't join the voice channel: {e}... uwu")
            
    async def handle_image_search(self, args, channel):
        """Handle image search and posting"""
        if not args:
            await channel.send("*confused* What kind of image should I look for? uwu")
            return
            
        search_query = " ".join(args).strip('"\'')
        
        try:
            image_url = await self.search_image(search_query)
            if image_url:
                # Send the raw image URL directly
                await channel.send(image_url)
            else:
                # Only send a message if no image is found
                await channel.send(f"*sadly* I couldn't find any images for '{search_query}'... sowwy! uwu")
                
        except Exception as e:
            self.logger.error(f"Error searching for image: {e}")
            await channel.send("*confused* Something went wrong while looking for images... uwu")
            
    async def search_image(self, query: str) -> Optional[str]:
        """Search for an image using Google Custom Search API"""
        api_key = os.getenv('GOOGLE_API_KEY') or self.config.get('google_images.api_key')
        search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID') or self.config.get('google_images.search_engine_id')
        
        if not api_key or not search_engine_id or api_key == "YOUR_GOOGLE_API_KEY_HERE":
            self.logger.warning("Google Images API not configured")
            return None
            
        # Add random 4-digit number to make results more diverse
        random_suffix = random.randint(1000, 9999)
        search_query = f"{query} {random_suffix}"
            
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': search_query,
            'searchType': 'image',
            'num': self.config.get('google_images.max_results', 10),
            'safe': 'active'  # Must be either 'active' or 'off'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])
                        if items:
                            # Return first result
                            return items[0]['link']
        except Exception as e:
            self.logger.error(f"Google Images API error: {e}")
            
        return None
        
    async def find_member(self, guild: discord.Guild, username: str) -> Optional[discord.Member]:
        """Find a member by username, display name, or mention"""
        username = username.lower().strip('<@!>')
        
        # Try by ID first (if it's a mention)
        if username.isdigit():
            member = guild.get_member(int(username))
            if member:
                return member
                
        # Try by exact username or display name
        for member in guild.members:
            if (member.name.lower() == username or 
                member.display_name.lower() == username):
                return member
                
        # Try partial match
        for member in guild.members:
            if (username in member.name.lower() or 
                username in member.display_name.lower()):
                return member
                
        return None
        
    def is_protected_user(self, member: discord.Member) -> bool:
        """Check if a user is protected from actions"""
        protected_ids = self.config.get('safety.protected_user_ids', [])
        admin_ids = self.config.get('safety.admin_user_ids', [])
        
        # Check if user is in protected lists
        if str(member.id) in protected_ids or str(member.id) in admin_ids:
            return True
            
        # Check if user has admin permissions
        if member.guild_permissions.administrator:
            return True
            
        # Check if user is bot owner
        if member.guild_permissions.manage_guild:
            return True
            
        return False
