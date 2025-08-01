"""
Utility classes for Scribble Discord Bot
Handles configuration management and data persistence
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

class ConfigManager:
    """Manages bot configuration from settings.json"""
    
    def __init__(self, config_path: str = 'config/settings.json'):
        self.config_path = config_path
        self.config = {}
        self.logger = logging.getLogger('ConfigManager')
        self.load_config()
        
    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            self.logger.info("Configuration loaded successfully")
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {self.config_path}")
            self.config = {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            self.config = {}
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'discord.bot_token')"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        
    def save_config(self):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info("Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")

class DataManager:
    """Manages persistent data files (memories, dossier, blacklist)"""
    
    def __init__(self):
        self.logger = logging.getLogger('DataManager')
        
        # File paths
        self.memories_path = 'data/memories.json'
        self.dossier_path = 'data/dossier.json'
        self.blacklist_path = 'config/blacklist.txt'
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
    def load_memories(self) -> Dict:
        """Load memories from file"""
        try:
            with open(self.memories_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning("Memories file not found, creating new one")
            default_memories = {
                "memories": [
                    "I was just promoted to chancellor of Tiny Ninos! I'm so excited but also nervous about doing a good job.",
                    "Everyone seems really nice here, I hope I can make lots of friends!",
                    "I have these new powers but I'm not really sure how to use them properly... I hope someone can help me learn!"
                ],
                "last_updated": datetime.now().isoformat(),
                "total_entries": 3
            }
            self.save_memories(default_memories)
            return default_memories
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing memories file: {e}")
            return {"memories": [], "last_updated": datetime.now().isoformat(), "total_entries": 0}
            
    def save_memories(self, memories_data: Dict):
        """Save memories to file"""
        try:
            memories_data['last_updated'] = datetime.now().isoformat()
            with open(self.memories_path, 'w', encoding='utf-8') as f:
                json.dump(memories_data, f, indent=2, ensure_ascii=False)
            self.logger.debug("Memories saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving memories: {e}")
            
    def load_dossier(self) -> Dict:
        """Load user dossier from file"""
        try:
            with open(self.dossier_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.warning("Dossier file not found, creating new one")
            default_dossier = {
                "users": {},
                "last_updated": datetime.now().isoformat(),
                "total_users": 0
            }
            self.save_dossier(default_dossier)
            return default_dossier
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing dossier file: {e}")
            return {"users": {}, "last_updated": datetime.now().isoformat(), "total_users": 0}
            
    def save_dossier(self, dossier_data: Dict):
        """Save user dossier to file"""
        try:
            dossier_data['last_updated'] = datetime.now().isoformat()
            dossier_data['total_users'] = len(dossier_data.get('users', {}))
            with open(self.dossier_path, 'w', encoding='utf-8') as f:
                json.dump(dossier_data, f, indent=2, ensure_ascii=False)
            self.logger.debug("Dossier saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving dossier: {e}")
            
    def load_blacklist(self) -> List[str]:
        """Load channel blacklist from file"""
        try:
            with open(self.blacklist_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Filter out comments and empty lines
            blacklist = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    blacklist.append(line)
                    
            return blacklist
        except FileNotFoundError:
            self.logger.warning("Blacklist file not found, creating default")
            default_blacklist = [
                "audit-log",
                "mod-log", 
                "bot-commands",
                "admin-only",
                "staff-chat"
            ]
            self.save_blacklist(default_blacklist)
            return default_blacklist
        except Exception as e:
            self.logger.error(f"Error loading blacklist: {e}")
            return []
            
    def save_blacklist(self, blacklist: List[str]):
        """Save channel blacklist to file"""
        try:
            os.makedirs(os.path.dirname(self.blacklist_path), exist_ok=True)
            with open(self.blacklist_path, 'w', encoding='utf-8') as f:
                f.write("# Channels where Scribble should not respond\n")
                f.write("# Add channel names or IDs, one per line\n")
                f.write("# Lines starting with # are comments\n\n")
                for channel in blacklist:
                    f.write(f"{channel}\n")
            self.logger.debug("Blacklist saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving blacklist: {e}")
            
    def add_to_blacklist(self, channel: str):
        """Add a channel to the blacklist"""
        blacklist = self.load_blacklist()
        if channel not in blacklist:
            blacklist.append(channel)
            self.save_blacklist(blacklist)
            self.logger.info(f"Added {channel} to blacklist")
            
    def remove_from_blacklist(self, channel: str):
        """Remove a channel from the blacklist"""
        blacklist = self.load_blacklist()
        if channel in blacklist:
            blacklist.remove(channel)
            self.save_blacklist(blacklist)
            self.logger.info(f"Removed {channel} from blacklist")
            
    def cleanup_old_memories(self, max_entries: int = 100):
        """Clean up old memories if there are too many"""
        memories_data = self.load_memories()
        memories = memories_data.get('memories', [])
        
        if len(memories) > max_entries:
            # Keep the most recent memories
            memories_data['memories'] = memories[-max_entries:]
            self.save_memories(memories_data)
            self.logger.info(f"Cleaned up memories, kept {max_entries} most recent entries")
            
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Get a specific user's profile from dossier"""
        dossier = self.load_dossier()
        return dossier.get('users', {}).get(user_id)
        
    def update_user_profile(self, user_id: str, name: str, profile: str):
        """Update a specific user's profile in dossier"""
        dossier = self.load_dossier()
        
        if 'users' not in dossier:
            dossier['users'] = {}
            
        dossier['users'][user_id] = {
            'name': name,
            'profile': profile,
            'last_seen': datetime.now().isoformat()
        }
        
        self.save_dossier(dossier)
        self.logger.debug(f"Updated profile for user {name} ({user_id})")
        
    def add_memory(self, memory: str):
        """Add a single memory"""
        memories_data = self.load_memories()
        memories_data['memories'].append(memory)
        self.save_memories(memories_data)
        self.logger.debug(f"Added memory: {memory[:50]}...")
        
    def get_stats(self) -> Dict:
        """Get statistics about stored data"""
        memories_data = self.load_memories()
        dossier_data = self.load_dossier()
        blacklist = self.load_blacklist()
        
        return {
            'total_memories': len(memories_data.get('memories', [])),
            'total_users': len(dossier_data.get('users', {})),
            'blacklisted_channels': len(blacklist),
            'last_memory_update': memories_data.get('last_updated', 'Never'),
            'last_dossier_update': dossier_data.get('last_updated', 'Never')
        }
