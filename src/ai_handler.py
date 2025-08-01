"""
AI Handler for Scribble Discord Bot
Manages interactions with OpenAI API for main responses, profiling, and memory updates
"""

import openai
import json
import logging
import os

# Determine project root (parent of src directory)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
from datetime import datetime
import os
from typing import Dict, List, Optional

class AIHandler:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger('AIHandler')
        
        # Initialize OpenAI client
        api_key = os.getenv('OPENAI_API_KEY') or config.get('openai.api_key')
        if not api_key or api_key == "YOUR_OPENAI_API_KEY_HERE":
            self.logger.error("OpenAI API key not found!")
            self.client = None
        else:
            self.client = openai.OpenAI(api_key=api_key)
            
        # Directory with prompt templates
        self.prompts_dir = os.path.join(ROOT_DIR, 'config', 'prompts')

        # Load character prompt
        self.character_prompt = self.load_character_prompt()

        # Load prompt templates
        self.main_template = self.load_prompt_template('main_prompt.txt')
        self.memory_template = self.load_prompt_template('memory_prompt.txt')
        self.profiler_template = self.load_prompt_template('profiler_prompt.txt')
            
    def load_prompt_template(self, filename: str) -> str:
        """Helper to load prompt template from config/prompts directory"""
        path = os.path.join(self.prompts_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            self.logger.error(f"Prompt template '{filename}' not found in {self.prompts_dir}!")
            return ""

    def load_character_prompt(self) -> str:
        """Load character prompt from file"""
        prompt_path = os.path.join(ROOT_DIR, 'config', 'prompt.txt')
        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            self.logger.error("Character prompt file not found!")
            return "You are Scribble, a friendly Discord bot."
            
    async def get_main_response(self, context: Dict) -> Optional[Dict]:
        """Get main AI response for conversation"""
        if not self.client:
            return None
            
        try:
            # Prepare context for AI
            messages_text = self.format_messages(context['messages'])
            memories_text = self.format_memories(context['memories'])
            dossier_text = self.format_dossier(context['dossier'], context['messages'])
            
            # Build prompt
            voice_channels_text = ", ".join(context.get('voice_channels', [])) if context.get('voice_channels') else "None available"
        
            system_prompt = self.main_template.format(
                character_prompt=self.character_prompt,
                guild_name=context['guild_name'],
                channel_name=context['channel_name'],
                voice_channels_text=voice_channels_text,
                memories_text=memories_text,
                dossier_text=dossier_text,
                messages_text=messages_text
            )

            response = self.client.chat.completions.create(
                model=self.config.get('openai.main_model', 'gpt-4o'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Please respond to the recent messages as Scribble."}
                ],
                max_tokens=self.config.get('openai.max_tokens.main', 500),
                temperature=self.config.get('openai.temperature.main', 0.8)
            )
            
            content = response.choices[0].message.content.strip()
            
            # Try to parse JSON response, handling markdown code blocks
            try:
                # First try direct JSON parsing
                return json.loads(content)
            except json.JSONDecodeError:
                # Check if it's wrapped in markdown code blocks
                if '```json' in content and '```' in content:
                    # Extract JSON from code blocks
                    start = content.find('```json') + 7
                    end = content.rfind('```')
                    if start < end:
                        json_content = content[start:end].strip()
                        try:
                            return json.loads(json_content)
                        except json.JSONDecodeError:
                            pass
                
                # If still can't parse, treat as plain message
                return {"message": content, "action": "none"}
                
        except Exception as e:
            self.logger.error(f"Error getting main AI response: {e}")
            return None
            
    async def update_dossier(self, context: Dict) -> Optional[Dict]:
        """Update user dossier using profiler AI"""
        if not self.client:
            return None
            
        try:
            # Get current dossier
            current_dossier = context['dossier']
            
            # Extract users from recent messages
            users_in_messages = {}
            for msg in context['messages']:
                user_id = msg['id']
                if user_id not in users_in_messages:
                    users_in_messages[user_id] = {
                        'name': msg['name'],
                        'messages': []
                    }
                users_in_messages[user_id]['messages'].append(msg['message'])
                
            # Build profiler prompt
            messages_text = self.format_messages(context['messages'])
            
            system_prompt = self.profiler_template.format(
                messages_text=messages_text,
                current_dossier=json.dumps(current_dossier, indent=2)
            )

            response = self.client.chat.completions.create(
                model=self.config.get('openai.profiler_model', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Please update the user dossier based on the recent messages."}
                ],
                max_tokens=self.config.get('openai.max_tokens.profiler', 200),
                temperature=self.config.get('openai.temperature.profiler', 0.3)
            )
            
            content = response.choices[0].message.content.strip()
            
            def _extract_json(text:str):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    # Attempt to extract from ```json code blocks
                    # ```json fenced block
                    if '```json' in text and '```' in text:
                        start = text.find('```json') + 7
                        end = text.rfind('```')
                        if start < end:
                            segment = text[start:end].strip()
                            try:
                                return json.loads(segment)
                            except json.JSONDecodeError:
                                pass
                    # generic ``` fenced block
                    if '```' in text:
                        start = text.find('```') + 3
                        end = text.rfind('```')
                        if start < end:
                            segment = text[start:end].strip()
                            try:
                                return json.loads(segment)
                            except json.JSONDecodeError:
                                pass
                    return None

            updated_data = _extract_json(content)
            if not updated_data:
                self.logger.error("Failed to parse dossier update response")
                return None

            # Add timestamp metadata
            updated_data['last_updated'] = datetime.now().astimezone().isoformat()
            updated_data['total_users'] = len(updated_data.get('users', {}))
            return updated_data
                
        except Exception as e:
            self.logger.error(f"Error updating dossier: {e}")
            return None
            
    async def update_memories(self, context: Dict, response: Dict) -> Optional[Dict]:
        """Update memories using memory AI"""
        if not self.client:
            self.logger.error("OpenAI client not available")
            return None
            
        try:
            self.logger.info("Memory AI: Starting memory update")
            self.logger.debug(f"Context keys: {list(context.keys())}")
            self.logger.debug(f"Response: {response}")
            current_memories = context['memories']
            messages_text = self.format_messages(context['messages'][-5:])  # Last 5 messages
            
            # Format current memories properly for the prompt
            current_memories_text = self.format_memories(current_memories)
            
            system_prompt = self.memory_template.format(
                messages_text=messages_text,
                response_message=response.get('message', ''),
                response_action=response.get('action', 'none'),
                current_memories=current_memories_text
            )

            ai_response = self.client.chat.completions.create(
                model=self.config.get('openai.memory_model', 'gpt-3.5-turbo'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "Please update Scribble's memories based on this interaction."}
                ],
                max_tokens=self.config.get('openai.max_tokens.memory', 300),
                temperature=self.config.get('openai.temperature.memory', 0.5)
            )
            
            content = ai_response.choices[0].message.content.strip()
            
            # Log the raw response for debugging
            self.logger.debug(f"Memory AI raw response: {content}")
            
            # Simplified JSON parsing
            memory_update = None
            
            try:
                # First try direct JSON parsing
                memory_update = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract from markdown code blocks
                if '```json' in content and '```' in content:
                    start = content.find('```json') + 7
                    end = content.rfind('```')
                    if start < end:
                        json_content = content[start:end].strip()
                        try:
                            memory_update = json.loads(json_content)
                        except json.JSONDecodeError:
                            pass
                elif '```' in content:
                    start = content.find('```') + 3
                    end = content.rfind('```')
                    if start < end:
                        json_content = content[start:end].strip()
                        try:
                            memory_update = json.loads(json_content)
                        except json.JSONDecodeError:
                            pass
            
            if not memory_update:
                self.logger.error(f"Failed to parse memory update response. Raw content: {repr(content)}")
                self.logger.error(f"Content length: {len(content)}")
                self.logger.error(f"First 100 chars: {repr(content[:100])}")
                self.logger.error(f"Last 100 chars: {repr(content[-100:])}")
                
                # Fallback: create a simple memory based on the response
                try:
                    response_message = response.get('message', '')
                    if response_message:
                        # Extract a simple memory from the response
                        simple_memory = f"I responded to someone with: {response_message[:50]}..."
                        if len(response_message) > 50:
                            simple_memory += "..."
                        
                        # Add to existing memories
                        updated_memories = current_memories + [simple_memory]
                        
                        # Limit memory count
                        max_memories = self.config.get('character.max_memory_entries', 100)
                        if len(updated_memories) > max_memories:
                            updated_memories = updated_memories[-max_memories:]
                        
                        self.logger.info(f"Created fallback memory: {simple_memory}")
                        return {
                            'memories': updated_memories,
                            'last_updated': datetime.now().isoformat(),
                            'total_entries': len(updated_memories)
                        }
                except Exception as fallback_error:
                    self.logger.error(f"Fallback memory creation also failed: {fallback_error}")
                
                return None
            
            # Use the AI's updated memories (it should return the complete list)
            updated_memories = memory_update.get('memories', [])
            
            self.logger.info(f"Successfully parsed memory update: {len(updated_memories)} memories")
            self.logger.debug(f"Memory update structure: {memory_update}")
            
            # Ensure we have a list
            if not isinstance(updated_memories, list):
                self.logger.error(f"Expected memories to be a list, got: {type(updated_memories)}")
                return None
            
            # Limit memory count as a safety measure
            max_memories = self.config.get('character.max_memory_entries', 100)
            if len(updated_memories) > max_memories:
                updated_memories = updated_memories[-max_memories:]
                
            return {
                'memories': updated_memories,
                'last_updated': datetime.now().isoformat(),
                'total_entries': len(updated_memories)
            }
                
        except Exception as e:
            self.logger.error(f"Error updating memories: {e}")
            return None
            
    def format_messages(self, messages: List[Dict]) -> str:
        """Format messages for AI consumption"""
        formatted = []
        for msg in messages:
            formatted.append(f"[{msg['time']}] {msg['name']}: {msg['message']}")
        return "\n".join(formatted)
        
    def format_memories(self, memories: List[str]) -> str:
        """Format memories for AI consumption"""
        if not memories:
            return "No memories yet."
        return "\n".join(f"- {memory}" for memory in memories[-20:])  # Last 20 memories
        
    def format_dossier(self, dossier: Dict, messages: List[Dict]) -> str:
        """Format user dossier for AI consumption"""
        if not dossier:
            return "No user profiles yet."
            
        # Only include users from recent messages
        relevant_users = set(msg['id'] for msg in messages)
        formatted = []
        
        for user_id, profile in dossier.items():
            if user_id in relevant_users:
                formatted.append(f"{profile.get('name', 'Unknown')}: {profile.get('profile', 'No profile')}")
                
        return "\n".join(formatted) if formatted else "No relevant user profiles."
