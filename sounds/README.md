# Scribble Sound Files

This directory contains sound files that Scribble will play randomly during voice calls.

## Supported Formats
- `.mp3`
- `.wav` 
- `.ogg`
- `.m4a`

## How It Works
- Scribble will automatically play sounds at random intervals (30-120 seconds by default)
- Sounds are played randomly from all available files in this directory
- The sound system is controlled by the bot, not the AI

## Adding Sound Files
1. Place your sound files in this directory
2. Use descriptive names like `purr.mp3`, `meow.wav`, `chirp.ogg`
3. Keep files reasonably sized (under 10MB recommended)
4. Use short sounds (1-5 seconds) for best effect

## Configuration
Sound settings can be adjusted in `config/settings.json`:

```json
"sounds": {
  "enabled": true,
  "interval_min_seconds": 30,
  "interval_max_seconds": 120,
  "volume": 0.3
}
```

## Admin Commands
- `!scribble sounds` - Show sound system status
- `!scribble sounds_toggle` - Enable/disable sound system
- `!scribble sounds_reload` - Reload sound files (use after adding new files)

## Example Sound Ideas
- Cute animal noises (purrs, meows, chirps)
- Furry character sounds
- Soft squeaks or squeals
- Gentle growls or rumbles
- Happy noises or giggles

Remember: Scribble is innocent and easily influenced, so keep the sounds cute and friendly! uwu 