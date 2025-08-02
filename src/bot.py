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
import random
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
from dotenv import load_dotenv

from ai_handler import AIHandler
from actions import ActionHandler
from sound_manager import SoundManager
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
        self.sound_manager = SoundManager(self.config)
        
        # Rate limiting
        self.last_response = {}
        self.action_count = {}
        
        # Wake word conversation tracking
        self.active_conversations = {}  # {channel_id: {'last_activity': datetime, 'active': bool}}
        self.wake_word = self.config.get('response.wake_word', 'scribble').lower()
        self.conversation_timeout = self.config.get('response.conversation_timeout_minutes', 10)
        self.wake_word_mode_enabled = self.config.get('response.enable_wake_word_mode', True)
        
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
        logging.getLogger('discord').setLevel(logging.INFO)  # Increased from WARNING to INFO
        logging.getLogger('httpx').setLevel(logging.INFO)    # Increased from WARNING to INFO
        logging.getLogger('openai').setLevel(logging.DEBUG)  # Add OpenAI debug logging
        
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
            
        # Check for conversation timeout
        await self.check_conversation_timeout(message.channel.id)
        
        # If this is a DM, always respond
        if isinstance(message.channel, discord.DMChannel) or message.guild is None:
            should_respond = True
        else:
            # Check if channel is blacklisted
            if self.is_blacklisted_channel(message.channel):
                return
                
            # Check if wake word mode is enabled
            if self.wake_word_mode_enabled:
                # Check if conversation is already active
                if self.is_conversation_active(message.channel.id):
                    should_respond = True
                    # Update activity timestamp
                    self.update_conversation_activity(message.channel.id)
                else:
                    # Check for wake word to start conversation
                    should_respond = self.should_respond(message.content)
                    if should_respond:
                        # Activate conversation when wake word is detected
                        self.activate_conversation(message.channel.id)
            else:
                # Fall back to original behavior
                should_respond = self.should_respond(message.content)
        
        # If not explicitly mentioned, check for random response
        if not should_respond and self.is_random_response_channel(message.channel):
            # Roll a d10 (1-10) and check against the configured chance (default 10%)
            random_chance = self.config.get('response.random_response_chance', 10)
            if random.randint(1, 10) <= (random_chance / 10):
                should_respond = True
                self.logger.info(f"Random response triggered (rolled {random.randint(1, 10)} <= {random_chance/10})")
            
        if not should_respond:
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
        """Check if channel is blacklisted (always False for DMs)"""
        import discord
        if isinstance(channel, discord.DMChannel):
            return False
        blacklist = self.data_manager.load_blacklist()
        return (
            channel.name in blacklist or 
            str(channel.id) in blacklist or
            any(word in channel.name.lower() for word in blacklist if not word.startswith('#'))
        )
        
    def is_random_response_channel(self, channel):
        """Check if random responses are enabled for this channel"""
        # Use the same blacklist as regular messages
        return not self.is_blacklisted_channel(channel)
        
    def should_respond(self, content):
        """Check if message should trigger a response using fuzzy matching or wake word"""
        # Check if wake word mode is enabled
        if self.wake_word_mode_enabled:
            # Check for exact wake word match
            if self.wake_word in content.lower():
                self.logger.info(f"Wake word '{self.wake_word}' detected in message")
                return True
        
        # Fall back to fuzzy name matching
        bot_name = self.config.get('character.name', 'Scribble').lower()
        # Use the new config path for name matching threshold (0-100)
        threshold = self.config.get('response.name_closeness_threshold', 85) / 100.0
        
        words = content.lower().split()
        for word in words:
            # Remove common punctuation
            clean_word = word.strip('.,!?;:"()[]{}')
            similarity = fuzz.ratio(clean_word, bot_name) / 100.0
            if similarity >= threshold:
                self.logger.info(f"Matched name: {clean_word} with similarity {similarity*100:.1f}% >= {threshold*100}%")
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
        
    async def check_conversation_timeout(self, channel_id):
        """Check if conversation has timed out and deactivate if needed"""
        if not self.wake_word_mode_enabled:
            return
            
        if channel_id in self.active_conversations:
            conversation = self.active_conversations[channel_id]
            if conversation['active']:
                now = datetime.now()
                timeout_delta = timedelta(minutes=self.conversation_timeout)
                
                if now - conversation['last_activity'] > timeout_delta:
                    conversation['active'] = False
                    self.logger.info(f"Conversation timed out in channel {channel_id} after {self.conversation_timeout} minutes of inactivity")
                    
    def activate_conversation(self, channel_id):
        """Activate conversation mode for a channel"""
        if not self.wake_word_mode_enabled:
            return
            
        now = datetime.now()
        self.active_conversations[channel_id] = {
            'last_activity': now,
            'active': True
        }
        self.logger.info(f"Conversation activated in channel {channel_id}")
        
    def update_conversation_activity(self, channel_id):
        """Update the last activity time for a conversation"""
        if not self.wake_word_mode_enabled:
            return
            
        if channel_id in self.active_conversations:
            self.active_conversations[channel_id]['last_activity'] = datetime.now()
        else:
            # If conversation doesn't exist, create it
            self.activate_conversation(channel_id)
            
    def is_conversation_active(self, channel_id):
        """Check if conversation is currently active in a channel"""
        if not self.wake_word_mode_enabled:
            return False
            
        return channel_id in self.active_conversations and self.active_conversations[channel_id]['active']
        
    async def process_message(self, message):
        """Process a message that should trigger a response"""
        channel_label = message.channel.name if hasattr(message.channel, 'name') else 'DM'
        self.logger.info(f"=== Processing message from {message.author.name} in #{channel_label} ===")
        self.logger.info(f"Message: {message.content}")
        
        # Collect context
        context = await self.collect_context(message)
        
        # Store context for debug commands
        self._last_context = context
        
        # Update user dossier
        await self.update_user_dossier(context)
        
        # Get AI response
        response = await self.ai_handler.get_main_response(context)
        
        if not response:
            await message.channel.send("*confused scribble noises* uwu")
            return
            
        # Log full context and response for debugging
        # Log the message being responded to
        self.logger.info(f"Responding to: {message.author.display_name}: {message.content}")
        # Print clean response to terminal if enabled
        if self.config.get('debug.log_to_terminal', True):
            print(f"\n🤖 Scribble's Response:")
            print(f"📝 Message: {response.get('message', 'None')}")
            if response.get('action') and response['action'] != 'none':
                print(f"⚡ Action: {response.get('action', 'none')}")
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
                'time': msg.created_at.astimezone().strftime('%H:%M')
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
        
        # Get voice channels if in a guild
        voice_channels = []
        if message.guild:
            voice_channels = [vc.name for vc in message.guild.voice_channels]
        
        return {
            'messages': messages,
            'memories': memories.get('memories', []),
            'memories_data': memories,  # Pass the full memories data structure
            'dossier': dossier.get('users', {}),
            'channel_name': message.channel.name if hasattr(message.channel, 'name') else 'DM',
            'guild_name': message.guild.name if message.guild else 'DM',
            'voice_channels': voice_channels
        }
        
    async def update_user_dossier(self, context):
        """Update user dossier using profiler AI"""
        try:
            self.logger.info("Starting dossier update...")
            updated_dossier = await self.ai_handler.update_dossier(context)
            if updated_dossier:
                self.logger.info(f"Dossier update successful, saving {len(updated_dossier.get('users', {}))} users")
                self.data_manager.save_dossier(updated_dossier)
            else:
                self.logger.warning("Dossier update returned None, keeping existing dossier")
        except Exception as e:
            self.logger.error(f"Error updating dossier: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
    async def update_memories(self, context, response):
        """Update memories using memory AI"""
        try:
            self.logger.info("Starting memory update...")
            updated_memories = await self.ai_handler.update_memories(context, response)
            if updated_memories:
                self.logger.info(f"Memory update successful, saving {len(updated_memories.get('memories', []))} memories")
                self.data_manager.save_memories(updated_memories)
            else:
                # Fallback: keep existing memories if AI update fails
                self.logger.warning("Memory update failed, keeping existing memories")
                current_memories = self.data_manager.load_memories()
                if current_memories and current_memories.get('memories'):
                    # Just update the timestamp to show we tried
                    current_memories['last_updated'] = datetime.now().isoformat()
                    self.data_manager.save_memories(current_memories)
        except Exception as e:
            self.logger.error(f"Error updating memories: {e}")
            # Fallback: keep existing memories
            try:
                current_memories = self.data_manager.load_memories()
                if current_memories and current_memories.get('memories'):
                    current_memories['last_updated'] = datetime.now().isoformat()
                    self.data_manager.save_memories(current_memories)
            except Exception as fallback_error:
                self.logger.error(f"Fallback memory save also failed: {fallback_error}")
            

                
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
                
            current = self.config.get('debug.log_to_terminal', False)
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
            terminal_logging = self.config.get('debug.log_to_terminal', False)
            
            embed = discord.Embed(
                title="🔧 Scribble Debug Status",
                color=0x87CEEB  # Sky blue
            )
            
            embed.add_field(name="Raw Output", value="✅ Enabled" if raw_output else "❌ Disabled", inline=True)
            embed.add_field(name="Terminal Logging", value="✅ Enabled" if terminal_logging else "❌ Disabled", inline=True)
            
            embed.set_footer(text="Commands: !scribble raw, terminal, status, show_prompt, memories • uwu")
            
            await ctx.send(embed=embed)

        @self.command(name='memories')
        async def show_memories(ctx):
            """Show current memories (admin only)"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can see memories, sowwy! uwu")
                return
            
            memories_data = self.data_manager.load_memories()
            memories = memories_data.get('memories', [])
            
            if not memories:
                await ctx.send("📝 **Memories:** No memories yet!")
                return
            
            # Format memories for display
            memory_text = "\n".join(f"• {memory}" for memory in memories[-10:])  # Show last 10
            
            embed = discord.Embed(
                title="🧠 Scribble's Memories",
                description=memory_text,
                color=0x87CEEB
            )
            
            embed.add_field(name="Total Memories", value=str(len(memories)), inline=True)
            embed.add_field(name="Last Updated", value=memories_data.get('last_updated', 'Unknown'), inline=True)
            
            await ctx.send(embed=embed)

        @self.command(name='test_memory')
        async def test_memory_update(ctx):
            """Test memory update function (admin only)"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can test memory updates, sowwy! uwu")
                return
            
            if not hasattr(self, '_last_context'):
                await ctx.send("❌ No recent message context available. Send a message first!")
                return
            
            # Create a test response
            test_response = {
                "message": "This is a test response for memory update",
                "action": "none"
            }
            
            try:
                await self.update_memories(self._last_context, test_response)
                await ctx.send("✅ Memory update test completed! Check logs for details.")
            except Exception as e:
                await ctx.send(f"❌ Memory update test failed: {e}")

        @self.command(name='fix_memories')
        async def fix_memories(ctx):
            """Fix and validate memory data (admin only)"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can fix memories, sowwy! uwu")
                return
            
            try:
                # Load and validate memories
                memories_data = self.data_manager.load_memories()
                validated_memories = self.data_manager.validate_memories(memories_data)
                
                # Clean up if needed
                max_memories = self.config.get('character.max_memory_entries', 100)
                if len(validated_memories['memories']) > max_memories:
                    self.data_manager.cleanup_old_memories(max_memories)
                    validated_memories = self.data_manager.load_memories()
                
                # Save the fixed memories
                self.data_manager.save_memories(validated_memories)
                
                embed = discord.Embed(
                    title="🔧 Memory Fix Results",
                    color=0x87CEEB
                )
                
                embed.add_field(name="Total Memories", value=str(len(validated_memories['memories'])), inline=True)
                embed.add_field(name="Last Updated", value=validated_memories.get('last_updated', 'Unknown'), inline=True)
                embed.add_field(name="Status", value="✅ Fixed and validated", inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Memory fix failed: {e}")

        @self.command(name='clear_memories')
        async def clear_memories(ctx):
            """Clear all memories (admin only)"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can clear memories, sowwy! uwu")
                return
            
            try:
                # Create fresh memory data
                fresh_memories = {
                    "memories": [
                        "I was just promoted to chancellor of Tiny Ninos! I'm so excited but also nervous about doing a good job.",
                        "Everyone seems really nice here, I hope I can make lots of friends!",
                        "I have these new powers but I'm not really sure how to use them properly... I hope someone can help me learn!"
                    ],
                    "last_updated": datetime.now().isoformat(),
                    "total_entries": 3
                }
                
                self.data_manager.save_memories(fresh_memories)
                
                embed = discord.Embed(
                    title="🧹 Memories Cleared",
                    description="All memories have been reset to default values.",
                    color=0x87CEEB
                )
                
                embed.add_field(name="New Memories", value=str(len(fresh_memories['memories'])), inline=True)
                embed.add_field(name="Status", value="✅ Reset complete", inline=True)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Memory clear failed: {e}")

        @self.command(name='show_prompt')
        async def show_openai_prompt(ctx):
            """Show what's being sent to OpenAI for the last message"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can use debug commands, sowwy! uwu")
                return
            
            # Get the last message context
            if not hasattr(self, '_last_context'):
                await ctx.send("❌ No recent message context available. Send a message first!")
                return
            
            context = self._last_context
            
            # Format the prompt like it's sent to OpenAI
            messages_text = self.ai_handler.format_messages(context['messages'])
            memories_text = self.ai_handler.format_memories(context['memories'])
            dossier_text = self.ai_handler.format_dossier(context['dossier'], context['messages'])
            voice_channels_text = ", ".join(context.get('voice_channels', [])) if context.get('voice_channels') else "None available"
            
            system_prompt = self.ai_handler.main_template.format(
                character_prompt=self.ai_handler.character_prompt,
                guild_name=context['guild_name'],
                channel_name=context['channel_name'],
                voice_channels_text=voice_channels_text,
                memories_text=memories_text,
                dossier_text=dossier_text,
                messages_text=messages_text
            )
            
            # Create the full prompt that gets sent to OpenAI
            full_prompt = f"**System Message:**\n```\n{system_prompt}\n```\n\n**User Message:**\n```\nPlease respond to the recent messages as Scribble.\n```"
            
            # Split into chunks if too long
            if len(full_prompt) > 1900:
                chunks = [full_prompt[i:i+1900] for i in range(0, len(full_prompt), 1900)]
                for i, chunk in enumerate(chunks):
                    await ctx.send(f"**OpenAI Prompt (Part {i+1}/{len(chunks)}):**\n{chunk}")
            else:
                await ctx.send(f"**OpenAI Prompt:**\n{full_prompt}")

        @self.command(name='wakeword')
        async def show_wake_word_status(ctx):
            """Show current wake word system status"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can see wake word status, sowwy! uwu")
                return
            
            embed = discord.Embed(
                title="🔔 Wake Word System Status",
                color=0x87CEEB
            )
            
            embed.add_field(name="Wake Word Mode", value="✅ Enabled" if self.wake_word_mode_enabled else "❌ Disabled", inline=True)
            embed.add_field(name="Wake Word", value=f"`{self.wake_word}`", inline=True)
            embed.add_field(name="Timeout", value=f"{self.conversation_timeout} minutes", inline=True)
            
            # Show active conversations
            active_count = sum(1 for conv in self.active_conversations.values() if conv['active'])
            embed.add_field(name="Active Conversations", value=str(active_count), inline=True)
            
            embed.set_footer(text="Commands: !scribble wakeword, wakeword_toggle, wakeword_set, timeout_set • uwu")
            
            await ctx.send(embed=embed)

        @self.command(name='wakeword_toggle')
        async def toggle_wake_word_mode(ctx):
            """Toggle wake word mode on/off"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can toggle wake word mode, sowwy! uwu")
                return
            
            self.wake_word_mode_enabled = not self.wake_word_mode_enabled
            self.config.set('response.enable_wake_word_mode', self.wake_word_mode_enabled)
            
            status = "enabled" if self.wake_word_mode_enabled else "disabled"
            await ctx.send(f"🔔 Wake word mode {status}! {'Users can now say the wake word to start conversations!' if self.wake_word_mode_enabled else 'Back to normal response mode!'} uwu")

        @self.command(name='wakeword_set')
        async def set_wake_word(ctx, *, new_wake_word):
            """Set a new wake word"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can change the wake word, sowwy! uwu")
                return
            
            if not new_wake_word or len(new_wake_word.strip()) == 0:
                await ctx.send("❌ Please provide a valid wake word!")
                return
            
            self.wake_word = new_wake_word.lower().strip()
            self.config.set('response.wake_word', self.wake_word)
            
            await ctx.send(f"🔔 Wake word changed to `{self.wake_word}`! Users can now say this to start conversations! uwu")

        @self.command(name='timeout_set')
        async def set_conversation_timeout(ctx, minutes: int):
            """Set conversation timeout in minutes"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can change the timeout, sowwy! uwu")
                return
            
            if minutes < 1 or minutes > 1440:  # Between 1 minute and 24 hours
                await ctx.send("❌ Timeout must be between 1 and 1440 minutes!")
                return
            
            self.conversation_timeout = minutes
            self.config.set('response.conversation_timeout_minutes', minutes)
            
            await ctx.send(f"⏰ Conversation timeout set to {minutes} minutes! Conversations will end after {minutes} minutes of inactivity! uwu")

        @self.command(name='sounds')
        async def show_sound_status(ctx):
            """Show current sound system status"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can see sound status, sowwy! uwu")
                return
            
            embed = discord.Embed(
                title="🔊 Sound System Status",
                color=0x87CEEB
            )
            
            embed.add_field(name="Sound System", value="✅ Enabled" if self.sound_manager.enabled else "❌ Disabled", inline=True)
            embed.add_field(name="Available Sounds", value=str(len(self.sound_manager.available_sounds)), inline=True)
            embed.add_field(name="Sound Interval", value=f"{self.sound_manager.sound_interval_min}-{self.sound_manager.sound_interval_max}s", inline=True)
            
            # Show active voice connections
            active_connections = sum(1 for guild_id in self.sound_manager.active_voice_clients.keys())
            embed.add_field(name="Active Voice Connections", value=str(active_connections), inline=True)
            
            # List available sounds
            if self.sound_manager.available_sounds:
                sound_list = ", ".join(self.sound_manager.get_available_sounds()[:5])  # Show first 5
                if len(self.sound_manager.available_sounds) > 5:
                    sound_list += f" and {len(self.sound_manager.available_sounds) - 5} more..."
                embed.add_field(name="Available Sounds", value=sound_list, inline=False)
            else:
                embed.add_field(name="Available Sounds", value="No sound files found in sounds/ directory", inline=False)
            
            embed.set_footer(text="Commands: !scribble sounds, sounds_toggle, sounds_reload • uwu")
            
            await ctx.send(embed=embed)

        @self.command(name='sounds_toggle')
        async def toggle_sound_system(ctx):
            """Toggle sound system on/off"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can toggle sound system, sowwy! uwu")
                return
            
            self.sound_manager.enabled = not self.sound_manager.enabled
            self.config.set('sounds.enabled', self.sound_manager.enabled)
            
            status = "enabled" if self.sound_manager.enabled else "disabled"
            await ctx.send(f"🔊 Sound system {status}! {'Scribble will now make cute sounds in voice channels!' if self.sound_manager.enabled else 'Sound system is now disabled!'} uwu")

        @self.command(name='sounds_reload')
        async def reload_sounds(ctx):
            """Reload sound files from the sounds directory"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can reload sounds, sowwy! uwu")
                return
            
            old_count = len(self.sound_manager.available_sounds)
            self.sound_manager.reload_sounds()
            new_count = len(self.sound_manager.available_sounds)
            
            await ctx.send(f"🔊 Reloaded sounds! Found {new_count} sound files (was {old_count})! uwu")

        @self.command(name='test_dossier')
        async def test_dossier_update(ctx):
            """Test the dossier update system"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can test dossier updates, sowwy! uwu")
                return
            
            try:
                # Create a test context
                test_context = {
                    'messages': [
                        {
                            'name': ctx.author.display_name,
                            'id': str(ctx.author.id),
                            'message': 'This is a test message to update my dossier!',
                            'time': datetime.now().strftime('%H:%M')
                        }
                    ],
                    'dossier': self.data_manager.load_dossier().get('users', {})
                }
                
                await ctx.send("🔄 Testing dossier update system...")
                
                # Test the dossier update
                updated_dossier = await self.ai_handler.update_dossier(test_context)
                
                if updated_dossier:
                    await ctx.send(f"✅ Dossier update successful! Updated {len(updated_dossier.get('users', {}))} users")
                    # Save the updated dossier
                    self.data_manager.save_dossier(updated_dossier)
                else:
                    await ctx.send("❌ Dossier update failed - check logs for details")
                    
            except Exception as e:
                await ctx.send(f"❌ Error testing dossier: {e}")
                self.logger.error(f"Error in test_dossier_update: {e}")

        @self.command(name='show_dossier')
        async def show_dossier(ctx):
            """Show the current user dossier"""
            if not self.is_admin(ctx.author):
                await ctx.send("*shakes head* Only admins can see the dossier, sowwy! uwu")
                return
            
            try:
                dossier = self.data_manager.load_dossier()
                users = dossier.get('users', {})
                
                if not users:
                    await ctx.send("📋 No users in dossier yet!")
                    return
                
                embed = discord.Embed(
                    title="📋 User Dossier",
                    color=0x87CEEB
                )
                
                for user_id, user_data in users.items():
                    name = user_data.get('name', 'Unknown')
                    profile = user_data.get('profile', 'No profile')
                    last_seen = user_data.get('last_seen', 'Unknown')
                    
                    # Truncate profile if too long
                    if len(profile) > 200:
                        profile = profile[:200] + "..."
                    
                    embed.add_field(
                        name=f"👤 {name}",
                        value=f"**Profile:** {profile}\n**Last Seen:** {last_seen}",
                        inline=False
                    )
                
                embed.set_footer(text=f"Total Users: {len(users)} • Last Updated: {dossier.get('last_updated', 'Unknown')}")
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ Error showing dossier: {e}")
                self.logger.error(f"Error in show_dossier: {e}")
            
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
