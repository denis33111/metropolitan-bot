#!/usr/bin/env python3
"""
🔄 RESET WEBHOOK
Reset bot webhook to clear conflicts
"""

import os
import asyncio
from telegram import Bot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def reset_webhook():
    """Reset the bot's webhook"""
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        print("❌ TELEGRAM_TOKEN not found!")
        return
    
    bot = Bot(token)
    
    try:
        # Delete webhook
        await bot.delete_webhook()
        print("✅ Webhook deleted successfully")
        
        # Get bot info
        me = await bot.get_me()
        print(f"🤖 Bot: @{me.username} ({me.first_name})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(reset_webhook())
