"""
AI Handler for Scribble Discord Bot
Manages interactions with OpenAI API for main responses, profiling, and memory updates
"""

import openai
import json
import logging
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
            
        # Load character prompt
        self.character_prompt = self.load_character_prompt()
        
    def load_character_prompt(self) -> str:
        """Load character prompt from file"""
        try:
            with open('config/prompt.txt', 'r', encoding='utf-8') as f:
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
            system_prompt = f"""{self.character_prompt}

CURRENT CONTEXT:
Server: {context['guild_name']}
Channel: #{context['channel_name']}

MEMORIES:
{memories_text}

USER DOSSIER:
{dossier_text}

RECENT MESSAGES:
{messages_text}

Remember to respond as Scribble and format your response as JSON with 'message' and 'action' fields."""

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
            
            system_prompt = f"""You are a profiler AI that analyzes Discord messages to create user profiles.

Based on the recent messages, update the user dossier with relevant information about each user.
Focus on:
- Personality traits
- Interests and hobbies
- Communication style
- Pronouns (if mentioned)
- Relationships with other users
- Any notable behaviors

Keep profiles concise but informative. Only include information that can be reasonably inferred from the messages.

RECENT MESSAGES:
{messages_text}

CURRENT DOSSIER:
{json.dumps(current_dossier, indent=2)}

Respond with a JSON object containing the updated dossier in the format:
{{
  "users": {{
    "user_id": {{
      "name": "display_name",
      "profile": "updated profile text",
      "last_seen": "timestamp"
    }}
  }}
}}"""

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
            
            try:
                updated_data = json.loads(content)
                # Add timestamp
                updated_data['last_updated'] = datetime.now().isoformat()
                updated_data['total_users'] = len(updated_data.get('users', {}))
                return updated_data
            except json.JSONDecodeError:
                self.logger.error("Failed to parse dossier update response")
                return None
                
        except Exception as e:
            self.logger.error(f"Error updating dossier: {e}")
            return None
            
    async def update_memories(self, context: Dict, response: Dict) -> Optional[Dict]:
        """Update memories using memory AI"""
        if not self.client:
            return None
            
        try:
            current_memories = context['memories']
            messages_text = self.format_messages(context['messages'][-5:])  # Last 5 messages
            
            system_prompt = f"""You are Scribble's memory AI. You help Scribble remember important interactions and experiences.

Based on the recent conversation and Scribble's response, update Scribble's memories.
Write memories in first person from Scribble's perspective.
Focus on:
- Important interactions with users
- Actions Scribble took and why
- Things Scribble learned about users
- Emotional moments or significant events
- Mistakes Scribble made

Keep memories concise and in character. Limit to the most important additions.

RECENT CONVERSATION:
{messages_text}

SCRIBBLE'S RESPONSE:
Message: {response.get('message', '')}
Action: {response.get('action', 'none')}

CURRENT MEMORIES:
{json.dumps(current_memories, indent=2)}

Respond with a JSON object containing updated memories:
{{
  "memories": ["memory1", "memory2", ...]
}}

Only include the most relevant new memories (1-3 entries max per interaction)."""

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
            
            try:
                memory_update = json.loads(content)
                
                # Combine with existing memories
                all_memories = current_memories + memory_update.get('memories', [])
                
                # Limit memory count
                max_memories = self.config.get('character.max_memory_entries', 100)
                if len(all_memories) > max_memories:
                    all_memories = all_memories[-max_memories:]
                    
                return {
                    'memories': all_memories,
                    'last_updated': datetime.now().isoformat(),
                    'total_entries': len(all_memories)
                }
            except json.JSONDecodeError:
                self.logger.error("Failed to parse memory update response")
                return None
                
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
