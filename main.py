#!/usr/bin/env python3
"""
Scribble Discord Bot - Main Entry Point
Run this file to start the bot
"""

import sys
import os

# Add src directory to path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from bot import main

if __name__ == "__main__":
    main()
