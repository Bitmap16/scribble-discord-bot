#!/usr/bin/env python3
"""
Test script to debug image search functionality
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src directory to path
sys.path.append('src')

from actions import ActionHandler
from utils import ConfigManager

async def test_image_search():
    """Test the image search functionality"""
    print("🔍 Testing image search functionality...")
    
    # Load config
    config = ConfigManager()
    
    # Create a mock bot object (we only need it for the ActionHandler init)
    class MockBot:
        pass
    
    bot = MockBot()
    action_handler = ActionHandler(bot, config)
    
    # Test the search_image method directly
    print("\n📋 Environment variables:")
    api_key = os.getenv('GOOGLE_API_KEY')
    search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
    
    print(f"GOOGLE_API_KEY: {'✅ Set' if api_key and api_key != 'YOUR_GOOGLE_API_KEY_HERE' else '❌ Not set or placeholder'}")
    print(f"GOOGLE_SEARCH_ENGINE_ID: {'✅ Set' if search_engine_id and search_engine_id != 'YOUR_SEARCH_ENGINE_ID_HERE' else '❌ Not set or placeholder'}")
    
    if api_key:
        print(f"API Key (first 10 chars): {api_key[:10]}...")
    if search_engine_id:
        print(f"Search Engine ID: {search_engine_id}")
    
    # Test image search with detailed debugging
    print("\n🖼️ Testing image search for 'cute yorkie'...")
    
    # Test the API call manually first
    import aiohttp
    import json
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': search_engine_id,
        'q': "cute yorkie",
        'searchType': 'image',
        'num': 10,
        'safe': 'active'  # Must be either 'active' or 'off'
    }
    
    print(f"\n🌐 Making API call to: {url}")
    print(f"📋 Parameters: {dict(params)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                print(f"\n📡 Response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API call successful!")
                    print(f"📊 Response keys: {list(data.keys())}")
                    
                    items = data.get('items', [])
                    print(f"🖼️ Found {len(items)} images")
                    
                    if items:
                        first_image = items[0]['link']
                        print(f"🎯 First image URL: {first_image}")
                    else:
                        print("❌ No images in response")
                        if 'error' in data:
                            print(f"🚨 API Error: {data['error']}")
                else:
                    error_text = await response.text()
                    print(f"❌ API call failed: {response.status}")
                    print(f"📄 Error response: {error_text}")
                    
    except Exception as e:
        print(f"❌ Exception during API call: {e}")
        import traceback
        traceback.print_exc()
    
    # Now test the action handler method
    print("\n🔧 Testing ActionHandler.search_image method...")
    try:
        result = await action_handler.search_image("cute yorkie")
        if result:
            print(f"✅ ActionHandler success! Found image URL: {result}")
        else:
            print("❌ ActionHandler failed! No image URL returned")
    except Exception as e:
        print(f"❌ ActionHandler error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_image_search())
