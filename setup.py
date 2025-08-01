#!/usr/bin/env python3
"""
Setup script for Scribble Discord Bot
Helps with initial configuration and dependency installation
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies!")
        return False

def setup_environment():
    """Setup environment file"""
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    if env_path.exists():
        print("✅ .env file already exists")
        return True
        
    if example_path.exists():
        print("\n🔧 Creating .env file from template...")
        with open(example_path, 'r') as src, open(env_path, 'w') as dst:
            dst.write(src.read())
        print("✅ .env file created! Please edit it with your API keys.")
        return True
    else:
        print("❌ .env.example file not found!")
        return False

def check_directories():
    """Ensure all required directories exist"""
    directories = ['config', 'data', 'logs', 'src']
    
    print("\n📁 Checking directories...")
    for directory in directories:
        path = Path(directory)
        if path.exists():
            print(f"✅ {directory}/ exists")
        else:
            path.mkdir(exist_ok=True)
            print(f"✅ Created {directory}/")
    return True

def validate_config_files():
    """Validate configuration files"""
    print("\n⚙️ Validating configuration files...")
    
    # Check settings.json
    settings_path = Path("config/settings.json")
    if settings_path.exists():
        try:
            with open(settings_path, 'r') as f:
                json.load(f)
            print("✅ config/settings.json is valid")
        except json.JSONDecodeError as e:
            print(f"❌ config/settings.json has invalid JSON: {e}")
            return False
    else:
        print("❌ config/settings.json not found!")
        return False
    
    # Check other required files
    required_files = [
        "config/prompt.txt",
        "config/blacklist.txt",
        "data/memories.json",
        "data/dossier.json"
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} not found!")
            return False
    
    return True

def check_api_keys():
    """Check if API keys are configured"""
    print("\n🔑 Checking API configuration...")
    
    # Check .env file
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found!")
        return False
    
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    # Check for placeholder values
    if "your_discord_bot_token_here" in env_content.lower():
        print("⚠️  Discord bot token not configured in .env")
    else:
        print("✅ Discord bot token appears to be set")
    
    if "your_openai_api_key_here" in env_content.lower():
        print("⚠️  OpenAI API key not configured in .env")
    else:
        print("✅ OpenAI API key appears to be set")
    
    if "your_google_api_key_here" in env_content.lower():
        print("⚠️  Google API key not configured (optional for image search)")
    else:
        print("✅ Google API key appears to be set")
    
    return True

def print_next_steps():
    """Print next steps for the user"""
    print("\n🎉 Setup complete! Next steps:")
    print("\n1. Configure your API keys in .env:")
    print("   - Get Discord bot token from https://discord.com/developers/applications")
    print("   - Get OpenAI API key from https://platform.openai.com/api-keys")
    print("   - (Optional) Get Google API key for image search")
    
    print("\n2. Customize your bot in config/:")
    print("   - Edit settings.json for behavior and limits")
    print("   - Modify prompt.txt to change Scribble's personality")
    print("   - Update blacklist.txt with channels to avoid")
    
    print("\n3. Invite your bot to Discord:")
    print("   - Go to Discord Developer Portal")
    print("   - Generate invite link with necessary permissions")
    print("   - Required permissions: Send Messages, Manage Messages, Timeout Members, etc.")
    
    print("\n4. Run the bot:")
    print("   python main.py")
    
    print("\n📚 Read README.md for detailed configuration options!")

def main():
    """Main setup function"""
    print("🐾 Scribble Discord Bot Setup")
    print("=" * 40)
    
    success = True
    
    # Run all setup steps
    success &= check_python_version()
    success &= check_directories()
    success &= validate_config_files()
    success &= setup_environment()
    success &= install_dependencies()
    success &= check_api_keys()
    
    if success:
        print("\n✅ Setup completed successfully!")
        print_next_steps()
    else:
        print("\n❌ Setup encountered some issues. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
