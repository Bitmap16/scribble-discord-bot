"""
Action Handler for Scribble Discord Bot
Handles Discord actions like timeouts, bans, nicknames, DMs, voice channels, and image search
"""

import os
import aiohttp
import asyncio
import discord
import json
import logging
import os
import random
import shlex
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz

class ActionHandler:
    def __init__(self, bot, config):
        self.bot = bot
        self.config = config
        self.logger = logging.getLogger('ActionHandler')
        
        # Action tracking for safety
        self.action_history = []
        
    def parse_action_args(self, action_string: str) -> tuple[str, List[str]]:
        """Parse action string into action type and arguments, handling quoted strings"""
        try:
            # Use shlex to properly handle quoted strings
            parts = shlex.split(action_string.strip())
            if not parts:
                return "", []
            
            action_type = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            return action_type, args
        except ValueError as e:
            self.logger.error(f"Error parsing action string '{action_string}': {e}")
            # Fallback to simple split if shlex fails
            parts = action_string.strip().split()
            if not parts:
                return "", []
            action_type = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []
            return action_type, args
        
    async def execute_action(self, action_string: str, channel: discord.TextChannel, requester: discord.Member):
        """Parse and execute an action command"""
        self.logger.info(f"Executing action: {action_string}")
        
        # Parse action with proper quoted string handling
        action_type, args = self.parse_action_args(action_string)
        
        if not action_type:
            return
            
        # Check if action is enabled
        if not self.is_action_enabled(action_type):
            await channel.send("-# *sowwy, that action is disabled... uwu*")
            return
            
        # Check rate limits
        if not self.check_action_rate_limit():
            await channel.send("-# *I'm doing too many things at once! Need to slow down... uwu*")
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
            await channel.send("-# *oopsie! Something went wrong while trying to do that... sowwy! uwu*")
            
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
            await channel.send("-# *confused* I need a username and time! Like 'timeout \"username\" 5' uwu")
            return
            
        # First argument is the username (could be quoted)
        username = args[0]
        try:
            minutes = int(args[1])
        except ValueError:
            await channel.send("-# *scratches head* That doesn't look like a number for minutes... uwu")
            return
            
        # Safety check
        max_timeout = self.config.get('safety.max_timeout_minutes', 60)
        if minutes > max_timeout:
            minutes = max_timeout
            await channel.send(f"-# *nervously* That's too long! I'll make it {minutes} minutes instead... uwu")
            
        # Find user
        member = await self.find_member(channel.guild, username)
        if not member:
            await channel.send(f"-# *looks around confused* I can't find anyone named '{username}'... uwu")
            return
            
        # Check if user is protected
        if self.is_protected_user(member):
            await channel.send("-# *shakes head* I can't timeout that person! They're too important... uwu")
            return
            
        try:
            timeout_until = datetime.now() + timedelta(minutes=minutes)
            await member.timeout(timeout_until, reason=f"Timeout by Scribble (requested by {requester.display_name})")
            await channel.send(f"-# *apologetically* Sowwy {member.display_name}, you're in timeout for {minutes} minutes... uwu")
            
        except discord.Forbidden:
            await channel.send("-# *sad scribble noises* I don't have permission to timeout people... uwu")
        except discord.HTTPException as e:
            await channel.send(f"-# *confused* Something went wrong: {e}... uwu")
            
    async def handle_ban(self, args, channel, requester):
        """Handle ban action"""
        if not args:
            await channel.send("-# *nervously* I need a username to ban... but are you sure? That's really serious! uwu")
            return
            
        username = args[0]
        
        # Find user
        member = await self.find_member(channel.guild, username)
        if not member:
            await channel.send(f"-# *looks around* I can't find anyone named '{username}'... maybe that's for the best? uwu")
            return
            
        # Check if user is protected
        if self.is_protected_user(member):
            await channel.send("-# *shakes head frantically* NO NO NO! I can't ban that person! They're way too important! uwu")
            return
            
        try:
            await member.ban(reason=f"Ban by Scribble (requested by {requester.display_name})")
            await channel.send(f"-# *very sadly* I... I banned {member.display_name}... I hope they come back someday... *sniffles* uwu")
            
        except discord.Forbidden:
            await channel.send("-# *relieved sigh* Actually, I don't have permission to ban people... maybe that's good? uwu")
        except discord.HTTPException as e:
            await channel.send(f"-# *confused* Something went wrong: {e}... uwu")
            
    async def handle_nickname(self, args, channel, requester):
        """Handle nickname change action"""
        if len(args) < 2:
            await channel.send("-# *tilts head* I need a username and a new nickname! Like 'nickname \"username\" \"new nickname\"' uwu")
            return
            
        username = args[0]
        new_nickname = args[1]
        
        # Find user
        member = await self.find_member(channel.guild, username)
        if not member:
            await channel.send(f"-# *looks confused* I can't find anyone named '{username}'... uwu")
            return
            
        # Check if user is protected
        if self.is_protected_user(member):
            await channel.send("-# *nervously* I probably shouldn't change their nickname... they're important! uwu")
            return
            
        try:
            old_name = member.display_name
            await member.edit(nick=new_nickname, reason=f"Nickname change by Scribble (requested by {requester.display_name})")
            await channel.send(f"-# *proudly* I changed {old_name}'s nickname to '{new_nickname}'! Do you like it? uwu")
            
        except discord.Forbidden:
            await channel.send("-# *sad* I don't have permission to change nicknames... uwu")
        except discord.HTTPException as e:
            await channel.send(f"-# *confused* Something went wrong: {e}... uwu")
            
    async def handle_dm(self, args, channel, requester):
        """Handle direct message action"""
        if len(args) < 2:
            await channel.send("-# *confused* I need a username and a message to send! Like 'dm \"username\" \"message\"' uwu")
            return
            
        username = args[0]
        message = args[1]
        
        # Find user
        member = await self.find_member(channel.guild, username)
        if not member:
            await channel.send(f"-# *looks around* I can't find anyone named '{username}'... uwu")
            return
            
        try:
            await member.send(f"{message}")
            await channel.send(f"-# I sent a message to {member.display_name}! uwu")
            
        except discord.Forbidden:
            await channel.send(f"-# {member.display_name} has their DMs closed... I can't message them... uwu")
        except discord.HTTPException as e:
            await channel.send(f"-# *confused* Something went wrong: {e}... uwu")
            
    async def handle_voice_join(self, args, channel, requester):
        """Handle voice channel join action"""
        if not args:
            await channel.send("-# *confused* Which voice channel should I join? uwu")
            return
            
        channel_name = args[0]
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
            
        # Check if bot has permission to join the voice channel
        if not voice_channel.permissions_for(channel.guild.me).connect:
            await channel.send("*sadly* I don't have permission to join that voice channel... uwu")
            return
            
        if not voice_channel.permissions_for(channel.guild.me).speak:
            await channel.send("*worried* I can join but I can't speak in that voice channel... uwu")
            return
            
        # Get voice settings from config at the beginning
        voice_config = self.config.get('voice', {})
        
        try:
            # Check if already connected to a voice channel
            if channel.guild.voice_client and channel.guild.voice_client.is_connected():
                # If already in the same channel, just extend the time
                if channel.guild.voice_client.channel == voice_channel:
                    await channel.send(f"*happy* I'm already in {voice_channel.name}! I'll stay for {minutes} more minutes! uwu")
                    
                    # Create background task for auto-disconnect
                    async def auto_disconnect():
                        await asyncio.sleep(minutes * 60)
                        await self.bot.sound_manager.leave_voice_channel(channel.guild.id)
                        await channel.send("*waves* Time's up! Leaving the voice channel now! uwu")
                    
                    # Start the background task without blocking
                    asyncio.create_task(auto_disconnect())
                    return
                else:
                    # Disconnect from current channel first
                    self.logger.info(f"Disconnecting from current voice channel to join {voice_channel.name}")
                    await channel.guild.voice_client.disconnect()
                    # Get disconnect delay from config
                    disconnect_delay = voice_config.get('disconnect_delay_seconds', 1)
                    await asyncio.sleep(disconnect_delay)  # Give it a moment to disconnect
                
            # Use the proven working approach from vc_abduction.py
            self.logger.info("Joining voice channel with audio playback...")
            self.logger.info(f"Voice channel: {voice_channel.name} (ID: {voice_channel.id})")
            self.logger.info(f"Guild: {voice_channel.guild.name} (ID: {voice_channel.guild.id})")
            
            try:
                # Simple connection like the working script with Voice Gateway v4
                self.logger.info("Attempting voice connection...")
                connection_timeout = voice_config.get('connection_timeout_seconds', 20.0)
                voice_client = await voice_channel.connect(timeout=connection_timeout, self_deaf=True, self_mute=False)
                
                if voice_client is None:
                    raise Exception("Failed to connect to the voice channel.")
                
                self.logger.info(f"Successfully joined {voice_channel.name}")
                await channel.send(f"*excitedly* I joined {voice_channel.name}! I'll play some cute sounds for {minutes} minutes! uwu")
                
                # Define the after_playing callback with random intervals
                async def after_playing(error):
                    if error:
                        self.logger.error(f"Error during audio playback: {error}")
                    
                    # Check if we should play another sound or disconnect
                    if voice_client.is_connected():
                        # Get voice settings from config
                        voice_config = self.config.get('voice', {})
                        random_sound_chance = voice_config.get('random_sound_chance', 70) / 100.0
                        min_interval = voice_config.get('min_interval_seconds', 30)
                        max_interval = voice_config.get('max_interval_seconds', 120)
                        
                        # Random chance to play another sound
                        if random.random() < random_sound_chance:
                            # Random interval between min and max seconds
                            interval = random.randint(min_interval, max_interval)
                            self.logger.info(f"Will play another sound in {interval} seconds")
                            
                            # Schedule next sound
                            async def play_next_sound():
                                await asyncio.sleep(interval)
                                
                                if voice_client.is_connected():
                                    # Get all available sound files again
                                    sounds_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sounds')
                                    sound_files = []
                                    if os.path.exists(sounds_dir):
                                        for filename in os.listdir(sounds_dir):
                                            if any(filename.lower().endswith(fmt) for fmt in supported_formats):
                                                sound_files.append(filename)
                                    
                                    if sound_files:
                                        # Pick a random sound file
                                        random_sound = random.choice(sound_files)
                                        sound_path = os.path.join(sounds_dir, random_sound)
                                        
                                        self.logger.info(f"Playing random sound: {random_sound}")
                                        source = discord.FFmpegPCMAudio(sound_path)
                                        voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                                            after_playing(e), voice_client.loop
                                        ))
                                    else:
                                        # No more sounds, disconnect
                                        await voice_client.disconnect()
                                        await channel.send("*waves* No more sounds! Leaving the voice channel now! uwu")
                                else:
                                    # Voice client disconnected, don't play more sounds
                                    pass
                            
                            # Start the next sound task
                            asyncio.create_task(play_next_sound())
                        else:
                            # Disconnect chance after this sound
                            disconnect_chance = voice_config.get('disconnect_chance', 30) / 100.0
                            if random.random() < disconnect_chance:
                                await voice_client.disconnect()
                                await channel.send("*waves* Sound finished! Leaving the voice channel now! uwu")
                            else:
                                # Continue playing more sounds
                                async def continue_playing():
                                    await asyncio.sleep(interval)
                                    if voice_client.is_connected():
                                        # Get all available sound files again
                                        sounds_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sounds')
                                        sound_files = []
                                        if os.path.exists(sounds_dir):
                                            for filename in os.listdir(sounds_dir):
                                                if any(filename.lower().endswith(fmt) for fmt in supported_formats):
                                                    sound_files.append(filename)
                                        
                                        if sound_files:
                                            # Pick a random sound file
                                            random_sound = random.choice(sound_files)
                                            sound_path = os.path.join(sounds_dir, random_sound)
                                            
                                            self.logger.info(f"Playing random sound: {random_sound}")
                                            source = discord.FFmpegPCMAudio(sound_path)
                                            voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                                                after_playing(e), voice_client.loop
                                            ))
                                        else:
                                            # No more sounds, disconnect
                                            await voice_client.disconnect()
                                            await channel.send("*waves* No more sounds! Leaving the voice channel now! uwu")
                                    else:
                                        # Voice client disconnected, don't play more sounds
                                        pass
                                
                                # Start the continue playing task
                                asyncio.create_task(continue_playing())
                
                # Also set a maximum time limit
                async def max_time_disconnect():
                    await asyncio.sleep(minutes * 60)
                    if voice_client.is_connected():
                        await voice_client.disconnect()
                        await channel.send("*waves* Time's up! Leaving the voice channel now! uwu")
                
                # Start the maximum time task
                asyncio.create_task(max_time_disconnect())
                
                # Get all available sound files
                sounds_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sounds')
                sound_files = []
                if os.path.exists(sounds_dir):
                    # Get supported formats from config
                    voice_config = self.config.get('voice', {})
                    supported_formats = voice_config.get('supported_formats', ['.mp3', '.wav', '.ogg', '.m4a'])
                    
                    for filename in os.listdir(sounds_dir):
                        if any(filename.lower().endswith(fmt) for fmt in supported_formats):
                            sound_files.append(filename)
                
                if sound_files:
                    # Pick a random sound file
                    random_sound = random.choice(sound_files)
                    sound_path = os.path.join(sounds_dir, random_sound)
                    
                    self.logger.info(f"Playing random sound: {random_sound}")
                    source = discord.FFmpegPCMAudio(sound_path)
                    voice_client.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(
                        after_playing(e), voice_client.loop
                    ))
                else:
                    self.logger.warning("No sound files found in sounds directory")
                    # Still disconnect after the timeout even if no sound
                    async def timeout_disconnect():
                        await asyncio.sleep(minutes * 60)
                        if voice_client.is_connected():
                            await voice_client.disconnect()
                            await channel.send("*waves* Time's up! Leaving the voice channel now! uwu")
                    asyncio.create_task(timeout_disconnect())
                
            except Exception as e:
                self.logger.error(f"Error joining voice channel: {e}")
                await channel.send(f"*sadly* I couldn't join the voice channel... sowwy! uwu")
                
        except discord.ClientException:
            await channel.send("*confused* I'm already connected to a voice channel... uwu")
        except discord.opus.OpusNotLoaded:
            await channel.send("*technical difficulties* Voice isn't working properly... sowwy! uwu")
        except Exception as e:
            await channel.send(f"*confused* I couldn't join the voice channel: {e}... uwu")
            
    async def handle_image_search(self, args, channel):
        """Handle image search and posting of multiple images"""
        if not args:
            await channel.send("*confused* What kind of image should I look for? uwu")
            return
            
        search_query = args[0]
        max_images = self.config.get('google_images.max_images_to_post', 5)  # Default max 5 images
        
        # Randomly select how many images to post (1 to max_images)
        num_images = random.randint(1, max_images)
        
        try:
            # Get multiple random image URLs
            image_urls = await self.search_images(search_query, count=num_images)
            
            if not image_urls:
                await channel.send(f"*sadly* I couldn't find any images for '{search_query}'... sowwy! uwu")
                return
                
            # Post each image in a separate message
            for url in image_urls:
                try:
                    await channel.send(url)
                    # Small delay between posts to avoid rate limiting
                    voice_config = self.config.get('voice', {})
                    image_delay = voice_config.get('image_post_delay_seconds', 0.5)
                    await asyncio.sleep(image_delay)
                except Exception as e:
                    self.logger.error(f"Error posting image: {e}")
                    continue
                
        except Exception as e:
            self.logger.error(f"Error searching for images: {e}")
            await channel.send("*confused* Something went wrong while looking for images... uwu")
            
    async def search_images(self, query: str, count: int = 1) -> List[str]:
        """Search for multiple images using Google Custom Search API, restricted to safe sites if configured
        
        Args:
            query: The search query string
            count: Number of unique images to return (up to max_results)
            
        Returns:
            List of image URLs, or empty list if no results or error
        """
        api_key = os.getenv('GOOGLE_API_KEY') or self.config.get('google_images.api_key')
        search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID') or self.config.get('google_images.search_engine_id')
        
        if not api_key or not search_engine_id or api_key == "YOUR_GOOGLE_API_KEY_HERE":
            self.logger.warning("Google Images API not configured")
            return []
            
        # Get safe sites from config if available
        safe_sites = self.config.get('google_images.safe_sites', [])
        max_results = self.config.get('google_images.max_results', 10)
        
        # Get safe search setting from config (default: 'active')
        safe_search = self.config.get('google_images.safe_search', 'active')
        
        # Build the search query
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,  # The base search query
            'searchType': 'image',
            'num': min(max_results, 10),  # Google API max is 10 per request
            'safe': safe_search,  # 'active' or 'off' from config
            'imgSize': 'large',  # Prefer larger images
            'imgType': 'photo',  # Prefer photos over icons/clipart
            'rights': 'cc_publicdomain,cc_attribute,cc_sharealike'  # Try to get more permissive content
        }
        
        # If we have safe sites, add them as site search parameters
        if safe_sites:
            # Google's API allows multiple site parameters, which acts as an OR condition
            for site in safe_sites:
                params[f'siteSearch'] = site
                params['siteSearchFilter'] = 'i'  # 'i' means include these sites only
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])
                        if items:
                            # Randomly select up to 'count' unique images
                            selected_items = random.sample(items, min(len(items), count))
                            return [item['link'] for item in selected_items]
        except Exception as e:
            self.logger.error(f"Google Images API error: {e}")
            
        return []
        
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
