#!/usr/bin/env python3
"""
🧪 BOT HEALTH TEST SCRIPT
Tests basic bot functionality and health checks
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_basic_functionality():
    """Test basic bot functionality"""
    try:
        logger.info("🧪 Testing basic bot functionality...")
        
        # Test environment variables
        bot_token = os.getenv('BOT_TOKEN')
        spreadsheet_id = os.getenv('SPREADSHEET_ID')
        google_creds = os.getenv('GOOGLE_CREDENTIALS_JSON')
        
        if not bot_token:
            logger.error("❌ BOT_TOKEN not found")
            return False
        else:
            logger.info("✅ BOT_TOKEN found")
            
        if not spreadsheet_id:
            logger.error("❌ SPREADSHEET_ID not found")
            return False
        else:
            logger.info("✅ SPREADSHEET_ID found")
            
        if not google_creds:
            logger.error("❌ GOOGLE_CREDENTIALS_JSON not found")
            return False
        else:
            logger.info("✅ GOOGLE_CREDENTIALS_JSON found")
        
        # Test imports
        try:
            from src.services.sheets_service import GoogleSheetsService
            from src.services.location_service import LocationService
            logger.info("✅ Service imports successful")
        except Exception as e:
            logger.error(f"❌ Service import failed: {e}")
            return False
        
        # Test service initialization
        try:
            sheets_service = GoogleSheetsService(spreadsheet_id)
            location_service = LocationService()
            logger.info("✅ Services initialized successfully")
        except Exception as e:
            logger.error(f"❌ Service initialization failed: {e}")
            return False
        
        logger.info("✅ All basic functionality tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed with error: {e}")
        return False

async def test_health_endpoints():
    """Test health check endpoints"""
    try:
        logger.info("🏥 Testing health endpoints...")
        
        # Import the health check function
        from attendance_bot import health_check, shutdown_handler
        
        # Create a mock request object
        class MockRequest:
            def __init__(self):
                self.app = {}
        
        mock_request = MockRequest()
        
        # Test health check
        try:
            health_response = await health_check(mock_request)
            logger.info(f"✅ Health check response: {health_response}")
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return False
        
        logger.info("✅ Health endpoint tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Health endpoint test failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("🚀 Starting bot health tests...")
    
    # Test basic functionality
    basic_ok = await test_basic_functionality()
    
    # Test health endpoints
    health_ok = await test_health_endpoints()
    
    # Summary
    if basic_ok and health_ok:
        logger.info("🎉 All tests passed! Bot is ready for production.")
        return True
    else:
        logger.error("❌ Some tests failed. Please fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
