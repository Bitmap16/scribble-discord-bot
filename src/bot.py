#!/usr/bin/env python3
"""
Scribble Discord Bot - Main Bot File
A naive, innocent furry character bot with AI integration
"""

import discord
from discord.ext import commands
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
from dotenv import load_dotenv

from ai_handler import AIHandler
from actions import ActionHandler
from utils import ConfigManager, DataManager

# Load environment variables
load_dotenv()

class ScribbleBot(commands.Bot):
    def __init__(self):
        # Load configuration
        self.config = ConfigManager()
        self.data_manager = DataManager()
        
        # Initialize bot with intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!scribble ',
            intents=intents,
            help_command=None
        )
        
        # Add admin commands
        self.add_admin_commands()
        
        # Initialize handlers
        self.ai_handler = AIHandler(self.config)
        self.action_handler = ActionHandler(self, self.config)
        
        # Rate limiting
        self.last_response = {}
        self.action_count = {}
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_level = getattr(logging, self.config.get('logging.level', 'WARNING'))  # Default to WARNING instead of INFO
        log_file = self.config.get('logging.log_file', 'logs/scribble.log')
        
        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Configure root logger
        logging.basicConfig(level=log_level)
        
        # Set up file handler with detailed logging
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        
        # Set up console handler with minimal logging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        
        # Configure the root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        root_logger.handlers = []  # Remove any existing handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Set specific log levels for noisy loggers
        logging.getLogger('discord').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        
        # Create our bot logger
        self.logger = logging.getLogger('ScribbleBot')
        self.logger.setLevel(log_level)
        
    async def on_ready(self):
        """Called when bot is ready"""
        self.logger.info(f'{self.user} has connected to Discord!')
        self.logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set configurable status
        status_message = self.config.get('character.status_message', 'over Tiny Ninos as chancellor! uwu')
        status_type = self.config.get('character.status_type', 'watching')
        
        # Map status type string to Discord ActivityType
        activity_types = {
            'playing': discord.ActivityType.playing,
            'streaming': discord.ActivityType.streaming,
            'listening': discord.ActivityType.listening,
            'watching': discord.ActivityType.watching,
            'competing': discord.ActivityType.competing
        }
        
        activity_type = activity_types.get(status_type.lower(), discord.ActivityType.watching)
        
        await self.change_presence(
            activity=discord.Activity(
                type=activity_type,
                name=status_message
            )
        )
        
    async def on_message(self, message):
        """Handle incoming messages"""
        # Ignore bot messages
        if message.author.bot:
            return
            
        # Check if channel is blacklisted
        if self.is_blacklisted_channel(message.channel):
            return
            
        # Check for activation (name mention with fuzzy matching)
        if not self.should_respond(message.content):
            return
            
        # Rate limiting check
        if not self.check_rate_limit(message.author.id):
            return
            
        try:
            await self.process_message(message)
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            await message.channel.send("*sowwy, I made an oopsie! Something went wrong... uwu*")
            
    def is_blacklisted_channel(self, channel):
        """Check if channel is blacklisted"""
        blacklist = self.data_manager.load_blacklist()
        return (
            channel.name in blacklist or 
            str(channel.id) in blacklist or
            any(word in channel.name.lower() for word in blacklist if not word.startswith('#'))
        )
        
    def should_respond(self, content):
        """Check if message should trigger a response using fuzzy matching"""
        bot_name = self.config.get('character.name', 'Scribble').lower()
        threshold = self.config.get('discord.activation_threshold', 0.85)
        
        words = content.lower().split()
        for word in words:
            # Remove common punctuation
            clean_word = word.strip('.,!?;:"()[]{}')
            similarity = fuzz.ratio(clean_word, bot_name) / 100.0
            if similarity >= threshold:
                return True
        return False
        
    def check_rate_limit(self, user_id):
        """Check if user is rate limited"""
        now = datetime.now()
        cooldown = self.config.get('discord.command_cooldown_seconds', 3)
        
        if user_id in self.last_response:
            if (now - self.last_response[user_id]).seconds < cooldown:
                return False
                
        self.last_response[user_id] = now
        return True
        
    async def process_message(self, message):
        """Process a message that should trigger a response"""
        self.logger.info(f"Processing message from {message.author.name}: {message.content}")
        
        # Collect context
        context = await self.collect_context(message)
        
        # Update user dossier
        await self.update_user_dossier(context)
        
        # Get AI response
        response = await self.ai_handler.get_main_response(context)
        
        if not response:
            await message.channel.send("*confused scribble noises* uwu")
            return
            
        # Log raw response for debugging
        self.logger.info(f"Raw AI Response: {json.dumps(response, indent=2)}")
        
        # Also print to terminal if enabled
        if self.config.get('debug.log_to_terminal', True):
            print(f"\n🤖 RAW AI RESPONSE:")
            print(f"📝 Message: {response.get('message', 'None')}")
            print(f"⚡ Action: {response.get('action', 'none')}")
            print(f"📋 Full JSON: {json.dumps(response, indent=2)}")
            print("-" * 50)
        
        # Send message response (raw JSON or plain text)
        if response.get('message'):
            raw_output = self.config.get('debug.raw_output', False)
            
            if raw_output:
                # Send raw JSON for debugging
                json_str = json.dumps(response, indent=2)
                await message.channel.send(f"```json\n{json_str}\n```")
            else:
                # Send plain text message (like original)
                await message.channel.send(response['message'])
            
        # Execute action if specified
        if response.get('action') and response['action'] != 'none':
            await self.action_handler.execute_action(
                response['action'], 
                message.channel, 
                message.author
            )
            
        # Update memories
        await self.update_memories(context, response)
        
    async def collect_context(self, message):
        """Collect context for AI processing"""
        # Get message history
        messages = []
        history_count = self.config.get('discord.message_history_count', 20)
        
        async for msg in message.channel.history(limit=history_count + 1):
            if msg.id == message.id:
                continue
                
            messages.append({
                'name': msg.author.display_name,
                'id': str(msg.author.id),
                'message': msg.content,
                'time': msg.created_at.strftime('%H:%M')
            })
            
        messages.reverse()  # Chronological order
        
        # Add the triggering message
        messages.append({
            'name': message.author.display_name,
            'id': str(message.author.id),
            'message': message.content,
            'time': message.created_at.strftime('%H:%M')
        })
        
        # Load memories and dossier
        memories = self.data_manager.load_memories()
        dossier = self.data_manager.load_dossier()
        
        return {
            'messages': messages,
            'memories': memories.get('memories', []),
            'dossier': dossier.get('users', {}),
            'channel_name': message.channel.name,
            'guild_name': message.guild.name if message.guild else 'DM'
        }
        
    async def update_user_dossier(self, context):
        """Update user dossier using profiler AI"""
        try:
            updated_dossier = await self.ai_handler.update_dossier(context)
            if updated_dossier:
                self.data_manager.save_dossier(updated_dossier)
        except Exception as e:
            self.logger.error(f"Error updating dossier: {e}")
            
    async def update_memories(self, context, response):
        """Update memories using memory AI"""
        try:
            updated_memories = await self.ai_handler.update_memories(context, response)
            if updated_memories:
                self.data_manager.save_memories(updated_memories)
        except Exception as e:
            self.logger.error(f"Error updating memories: {e}")
            

                
    def add_admin_commands(self):
        """Add admin commands for debugging and configuration"""
        
        @self.command(name='raw')
        async def toggle_raw_output(ctx):
            """Toggle raw JSON output for debugging"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can use debug commands, sowwy! uwu")
                return
                
            current = self.config.get('debug.raw_output', False)
            self.config.set('debug.raw_output', not current)
            
            status = "enabled" if not current else "disabled"
            await ctx.send(f"🔧 Raw output {status}! {'JSON mode activated!' if not current else 'Plain text mode activated!'} uwu")
            

        @self.command(name='terminal')
        async def toggle_terminal_logging(ctx):
            """Toggle terminal logging of raw responses"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can use debug commands, sowwy! uwu")
                return
                
            current = self.config.get('debug.log_to_terminal', True)
            self.config.set('debug.log_to_terminal', not current)
            
            status = "enabled" if not current else "disabled"
            await ctx.send(f"🖥️ Terminal logging {status}! {'Raw responses will show in console!' if not current else 'Console output disabled!'} uwu")
            
        @self.command(name='status')
        async def show_debug_status(ctx):
            """Show current debug settings"""
            if not self.is_admin(ctx.author):
                await ctx.send("*tilts head* Only admins can see debug status, sowwy! uwu")
                return
                
            raw_output = self.config.get('debug.raw_output', False)
            terminal_logging = self.config.get('debug.log_to_terminal', True)
            
            embed = discord.Embed(
                title="🔧 Scribble Debug Status",
                color=0x87CEEB  # Sky blue
            )
            
            embed.add_field(name="Raw Output", value="✅ Enabled" if raw_output else "❌ Disabled", inline=True)
            embed.add_field(name="Terminal Logging", value="✅ Enabled" if terminal_logging else "❌ Disabled", inline=True)
            
            embed.set_footer(text="Commands: !scribble raw, terminal, status • uwu")
            
            await ctx.send(embed=embed)
            
    def is_admin(self, user):
        """Check if user is an admin"""
        admin_ids = self.config.get('safety.admin_user_ids', [])
        return (
            str(user.id) in admin_ids or
            user.guild_permissions.administrator or
            user.guild_permissions.manage_guild
        )

def main():
    """Main function to run the bot"""
    bot = ScribbleBot()
    
    # Get token from environment or config
    token = os.getenv('DISCORD_BOT_TOKEN') or bot.config.get('discord.bot_token')
    
    if not token or token == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("❌ Discord bot token not found!")
        print("Please set DISCORD_BOT_TOKEN in your .env file or config/settings.json")
        return
        
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Invalid Discord bot token!")
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    main()
