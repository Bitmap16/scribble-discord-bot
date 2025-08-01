# This is a bunch of AI slop, feel free to ignore...

# 🐾 Scribble Discord Bot

A naive, innocent furry Discord bot powered by AI that serves as the "chancellor" of your Discord server. Scribble uses multiple AI models to provide natural conversations, maintain user profiles, and perform various Discord actions.

## 🌟 Features

- **Natural AI Conversations**: Powered by GPT-4o with a unique naive, furry personality
- **Smart Activation**: Responds when mentioned with 85% fuzzy name matching
- **Wake Word System**: Say the wake word to start a conversation that lasts until timeout
- **User Profiling**: Automatically builds profiles of server members using AI
- **Memory System**: Maintains persistent memories of interactions
- **Moderation Actions**: Timeout, ban, nickname changes, and DMs
- **Voice Channel Integration**: Can join and leave voice channels
- **Image Search**: Finds and posts images from Google Images
- **Highly Configurable**: Extensive settings and safety controls

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- OpenAI API Key
- Google Custom Search API (optional, for image search)

### 2. Installation

```bash
# Clone or download the project
cd scribble

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 3. Configuration

1. **Edit `.env` file** with your API keys:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here  # Optional
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id_here  # Optional
```

2. **Configure settings** in `config/settings.json`:
   - Adjust AI model settings
   - Set safety limits
   - Configure character behavior
   - Add admin/protected user IDs

3. **Customize character** in `config/prompt.txt`:
   - Modify Scribble's personality
   - Adjust speech patterns
   - Change behavior guidelines

4. **Set channel blacklist** in `config/blacklist.txt`:
   - Add channels where Scribble shouldn't respond
   - One channel name/ID per line

### 4. Run the Bot

```bash
python main.py
```

## 🎭 Character

**Scribble** is a white, fluffy furry character (no specific species) who:
- Is extremely naive and innocent
- Gets easily influenced by others
- Speaks in a mix of normal, lolcat, and furry-speak
- Is very apologetic when making mistakes
- Recently became "chancellor" of the server
- Has moderation powers but isn't sure how to use them

## 🛠️ Available Actions

Scribble can perform these actions when mentioned:

- `timeout [username] [minutes]` - Timeout a user
- `ban [username]` - Ban a user (use carefully!)
- `nickname [username] [new_nickname]` - Change someone's nickname
- `dm [username] [message]` - Send a direct message
- `vcjoin [channel_name] [minutes]` - Join a voice channel
- `image [description]` - Search and post an image

## 🔔 Wake Word System

Scribble now supports a wake word system for more natural conversations:

1. **Say the wake word** (default: "scribble") to start a conversation
2. **Keep chatting** - Scribble will respond to all messages in the channel
3. **Automatic timeout** - After 10 minutes of inactivity, the conversation ends
4. **Say the wake word again** to restart the conversation

### Configuration
- `wake_word`: The word to activate conversation mode (default: "scribble")
- `conversation_timeout_minutes`: Minutes of inactivity before timeout (default: 10)
- `enable_wake_word_mode`: Enable/disable the wake word system (default: true)

### Admin Commands
- `!scribble wakeword` - Show wake word system status
- `!scribble wakeword_toggle` - Enable/disable wake word mode
- `!scribble wakeword_set [word]` - Change the wake word
- `!scribble timeout_set [minutes]` - Change conversation timeout
- `!scribble fix_memories` - Fix and validate memory data
- `!scribble clear_memories` - Reset all memories to default

## 📁 Project Structure

```
scribble/
├── config/
│   ├── settings.json      # Main configuration
│   ├── prompt.txt         # Character prompt
│   └── blacklist.txt      # Blacklisted channels
├── data/
│   ├── memories.json      # Bot memories
│   └── dossier.json       # User profiles
├── src/
│   ├── bot.py            # Main bot logic
│   ├── ai_handler.py     # AI integrations
│   ├── actions.py        # Discord actions
│   └── utils.py          # Utilities
├── logs/                 # Log files
├── main.py              # Entry point
├── requirements.txt     # Dependencies
└── .env                 # Environment variables
```

## ⚙️ Configuration Options

### Discord Settings
- `activation_threshold`: Fuzzy matching threshold (0.85 = 85%)
- `message_history_count`: Messages to include in context (20)
- `command_cooldown_seconds`: Cooldown between responses (3)
- `max_actions_per_hour`: Action rate limit (10)

### Response Settings
- `name_closeness_threshold`: Fuzzy name matching threshold (85%)
- `random_response_chance`: Chance to respond randomly (100%)
- `wake_word`: Word to activate conversation mode ("scribble")
- `conversation_timeout_minutes`: Minutes before conversation ends (10)
- `enable_wake_word_mode`: Enable wake word system (true)

### AI Settings
- `main_model`: Primary conversation model (gpt-4o)
- `profiler_model`: User profiling model (gpt-3.5-turbo)
- `memory_model`: Memory update model (gpt-3.5-turbo)
- `max_tokens`: Token limits for each model
- `temperature`: Creativity settings for each model

### Safety Settings
- `admin_user_ids`: Protected admin users
- `protected_user_ids`: Users immune to actions
- `max_timeout_minutes`: Maximum timeout duration (60)
- `enable_bans/timeouts/nicknames`: Toggle action types

## 🔧 Advanced Usage

### Custom Prompts
Edit `config/prompt.txt` to customize Scribble's personality, speech patterns, and behavior guidelines.

### Memory Management
- Memories are automatically managed and cleaned up
- Robust error handling with fallback mechanisms
- Automatic validation and corruption repair
- Manual editing possible in `data/memories.json`
- Configurable memory limits in settings
- Admin commands for memory maintenance

### User Profiles
- Automatically generated based on message analysis
- Stored in `data/dossier.json`
- Can be manually edited if needed

### Logging
- Configurable log levels in settings
- Logs stored in `logs/scribble.log`
- AI call logging can be enabled/disabled

## 🛡️ Safety Features

- **Rate Limiting**: Prevents spam and abuse
- **Protected Users**: Admins and specified users are immune to actions
- **Action Limits**: Maximum timeouts, hourly action limits
- **Channel Blacklisting**: Exclude sensitive channels
- **Permission Checks**: Respects Discord permissions

## 🔍 Troubleshooting

### Common Issues

1. **Bot doesn't respond**
   - Check if channel is blacklisted
   - Verify name matching threshold
   - Check rate limiting

2. **Actions don't work**
   - Verify bot permissions in Discord
   - Check safety settings
   - Ensure user isn't protected

3. **AI responses are weird**
   - Check API keys and quotas
   - Adjust temperature settings
   - Review character prompt

4. **Memory/profile issues**
   - Use `!scribble fix_memories` to repair corrupted data
   - Use `!scribble clear_memories` to reset if needed
   - Check file permissions in `data/` folder
   - Verify JSON file format
   - Check disk space

### Getting Help

1. Check the logs in `logs/scribble.log`
2. Verify all configuration files are valid JSON
3. Test API keys independently
4. Check Discord bot permissions

## 📝 License

This project is open source. Feel free to modify and adapt for your server!

## 🎉 Contributing

Want to improve Scribble? Feel free to:
- Add new actions
- Improve AI prompts
- Enhance safety features
- Fix bugs and issues

---

*Made with ❤️ for the Tiny Ninos Discord community! uwu*
