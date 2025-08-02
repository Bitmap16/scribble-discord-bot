"""
Sound Manager for Scribble Discord Bot
Handles playing furry sounds during voice calls
"""

import asyncio
import random
import logging
import os
from typing import Optional, List
import discord
from discord import FFmpegPCMAudio

class SoundManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('SoundManager')
        
        # Sound settings
        self.sounds_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sounds')
        voice_config = config.get('voice', {})
        self.sound_interval_min = voice_config.get('min_interval_seconds', 30)  # Min time between sounds
        self.sound_interval_max = voice_config.get('max_interval_seconds', 120)  # Max time between sounds
        self.sound_volume = voice_config.get('volume', 0.3)  # Volume level (0.0 to 1.0)
        self.enabled = voice_config.get('enabled', True)
        
        # Check if FFmpeg is available
        self.ffmpeg_available = self.check_ffmpeg()
        if not self.ffmpeg_available:
            self.logger.warning("FFmpeg not found! Sound playback will not work. Please install FFmpeg.")
            self.enabled = False
        
        # Active voice clients and their sound tasks
        self.active_voice_clients = {}  # {guild_id: {'client': voice_client, 'task': task}}
        
        # Load available sounds
        self.available_sounds = self.load_sounds()
        
    def load_sounds(self) -> List[str]:
        """Load available sound files from the sounds directory"""
        sounds = []
        if not os.path.exists(self.sounds_dir):
            self.logger.warning(f"Sounds directory not found: {self.sounds_dir}")
            return sounds
            
        try:
            for filename in os.listdir(self.sounds_dir):
                if filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                    sounds.append(filename)
            self.logger.info(f"Loaded {len(sounds)} sound files: {sounds}")
        except Exception as e:
            self.logger.error(f"Error loading sounds: {e}")
            
        return sounds
        
    def check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available on the system"""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return False
        
    async def join_voice_channel(self, voice_channel: discord.VoiceChannel) -> bool:
        """Join a voice channel and start the sound loop"""
        if not self.enabled:
            self.logger.info("Sound system is disabled")
            return False
            
        if not self.available_sounds:
            self.logger.warning("No sound files available")
            return False
            
        self.logger.info(f"Sound system enabled with {len(self.available_sounds)} sounds available")
        self.logger.info(f"Available sounds: {self.available_sounds}")
            
        try:
            # Check if already connected to this guild
            if voice_channel.guild.id in self.active_voice_clients:
                self.logger.info(f"Already connected to guild {voice_channel.guild.id}")
                return True
                
            # Simple connection like the working script
            self.logger.info(f"Connecting to voice channel {voice_channel.name}")
            voice_client = await voice_channel.connect()
            
            if voice_client is None:
                self.logger.error("Failed to connect to voice channel")
                return False
                
            # Start sound loop task
            sound_task = asyncio.create_task(self.sound_loop(voice_client, voice_channel.guild.id))
            
            # Store the voice client and task
            self.active_voice_clients[voice_channel.guild.id] = {
                'client': voice_client,
                'task': sound_task
            }
            
            self.logger.info(f"Successfully joined voice channel {voice_channel.name} and started sound loop")
            return True
            
        except Exception as e:
            self.logger.error(f"Error joining voice channel: {e}")
            return False
            
    async def leave_voice_channel(self, guild_id: int):
        """Leave a voice channel and stop the sound loop"""
        if guild_id not in self.active_voice_clients:
            self.logger.debug(f"Not connected to guild {guild_id}")
            return
            
        try:
            # Cancel the sound task
            task_info = self.active_voice_clients[guild_id]
            if not task_info['task'].done():
                task_info['task'].cancel()
                try:
                    await task_info['task']
                except asyncio.CancelledError:
                    pass  # Expected when cancelling
            
            # Disconnect from voice
            if task_info['client'].is_connected():
                try:
                    await task_info['client'].disconnect()
                except Exception as e:
                    self.logger.warning(f"Error disconnecting voice client: {e}")
                
            # Remove from active clients
            del self.active_voice_clients[guild_id]
            
            self.logger.info(f"Successfully left voice channel for guild {guild_id}")
            
        except Exception as e:
            self.logger.error(f"Error leaving voice channel for guild {guild_id}: {e}")
            # Clean up anyway
            if guild_id in self.active_voice_clients:
                del self.active_voice_clients[guild_id]
            
    async def sound_loop(self, voice_client: discord.VoiceClient, guild_id: int):
        """Main loop for playing sounds at random intervals"""
        self.logger.info(f"Starting sound loop for guild {guild_id}")
        
        # Wait a bit before playing the first sound
        await asyncio.sleep(3)
        
        while voice_client.is_connected() and guild_id in self.active_voice_clients:
            try:
                # Check if still connected and active
                if not voice_client.is_connected():
                    self.logger.info(f"Voice client disconnected for guild {guild_id}")
                    break
                    
                if guild_id not in self.active_voice_clients:
                    self.logger.info(f"Sound loop removed for guild {guild_id}")
                    break
                    
                # Wait for random interval
                interval = random.randint(self.sound_interval_min, self.sound_interval_max)
                self.logger.info(f"Waiting {interval} seconds before next sound")
                await asyncio.sleep(interval)
                
                # Double-check connection after waiting
                if not voice_client.is_connected():
                    self.logger.info(f"Voice client disconnected during wait for guild {guild_id}")
                    break
                    
                if guild_id not in self.active_voice_clients:
                    self.logger.info(f"Sound loop removed during wait for guild {guild_id}")
                    break
                    
                # Play a random sound
                await self.play_random_sound(voice_client)
                
            except asyncio.CancelledError:
                self.logger.info(f"Sound loop cancelled for guild {guild_id}")
                break
            except Exception as e:
                self.logger.error(f"Error in sound loop for guild {guild_id}: {e}")
                await asyncio.sleep(10)  # Wait before retrying
                
        # Cleanup when loop ends
        if guild_id in self.active_voice_clients:
            self.logger.info(f"Cleaning up sound loop for guild {guild_id}")
            del self.active_voice_clients[guild_id]
                
    async def play_random_sound(self, voice_client: discord.VoiceClient):
        """Play a random sound from the available sounds"""
        if not self.available_sounds:
            self.logger.warning("No sounds available to play")
            return
            
        if voice_client.is_playing():
            self.logger.debug("Voice client is already playing, skipping")
            return
            
        try:
            # Select random sound
            sound_file = random.choice(self.available_sounds)
            sound_path = os.path.join(self.sounds_dir, sound_file)
            
            self.logger.info(f"Attempting to play sound: {sound_file}")
            
            # Check if file exists
            if not os.path.exists(sound_path):
                self.logger.error(f"Sound file not found: {sound_path}")
                return
                
            # Create audio source using discord.FFmpegPCMAudio directly
            audio_source = discord.FFmpegPCMAudio(sound_path)
            
            # Play the sound with after callback for cleanup
            def after_playing(error):
                if error:
                    self.logger.error(f"Error during sound playback: {error}")
                else:
                    self.logger.info(f"Finished playing sound: {sound_file}")
            
            voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(
                self._handle_sound_complete(e), voice_client.loop
            ))
            
            self.logger.info(f"Successfully started playing sound: {sound_file}")
            
        except Exception as e:
            self.logger.error(f"Error playing sound: {e}")
            # Don't disconnect on sound error, just log it
            
    async def _handle_sound_complete(self, error):
        """Handle sound playback completion"""
        if error:
            self.logger.error(f"Error during sound playback: {error}")
        else:
            self.logger.debug("Sound playback completed successfully")
            
    async def play_specific_sound(self, voice_client: discord.VoiceClient, sound_name: str):
        """Play a specific sound by name"""
        if not self.available_sounds:
            return False
            
        try:
            # Find the sound file
            sound_file = None
            for filename in self.available_sounds:
                if sound_name.lower() in filename.lower():
                    sound_file = filename
                    break
                    
            if not sound_file:
                self.logger.warning(f"Sound not found: {sound_name}")
                return False
                
            sound_path = os.path.join(self.sounds_dir, sound_file)
            
            # Stop current audio if playing
            if voice_client.is_playing():
                voice_client.stop()
                
            # Create audio source and play
            audio_source = discord.FFmpegPCMAudio(sound_path)
            voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(
                self._handle_sound_complete(e), voice_client.loop
            ))
            
            self.logger.info(f"Playing specific sound: {sound_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error playing specific sound: {e}")
            return False
            
    def get_available_sounds(self) -> List[str]:
        """Get list of available sound names"""
        return [os.path.splitext(sound)[0] for sound in self.available_sounds]
        
    def reload_sounds(self):
        """Reload sounds from the sounds directory"""
        self.available_sounds = self.load_sounds()
        
    def is_connected(self, guild_id: int) -> bool:
        """Check if connected to a voice channel in the given guild"""
        return guild_id in self.active_voice_clients and self.active_voice_clients[guild_id]['client'].is_connected() 