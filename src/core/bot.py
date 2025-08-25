#!/usr/bin/env python3
"""
🤖 METROPOLITAN BOT CORE
Main bot class with registration and check-in flows
"""

from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
import logging
import os

# Import services and handlers
from src.services.sheets_service import GoogleSheetsService
from src.services.worker_service import WorkerService
from src.handlers.start_handler import StartHandler, ASKING_NAME, ASKING_PHONE

logger = logging.getLogger(__name__)

class MetropolitanBot:
    """Main bot class for Metropolitan attendance system"""
    
    def __init__(self, token: str):
        self.token = token
        self.app = Application.builder().token(token).build()
        
        # Initialize services
        spreadsheet_id = os.getenv('SPREADSHEET_ID', 'default_sheet_id')
        self.sheets_service = GoogleSheetsService(spreadsheet_id)
        self.worker_service = WorkerService(self.sheets_service)
        
        # Initialize handlers
        self.start_handler = StartHandler(self.worker_service)
        
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up all command handlers"""
        
        # Start command with conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start_handler.handle_start)],
            states={
                ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.start_handler.handle_name_input)],
                ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.start_handler.handle_phone_input)]
            },
            fallbacks=[CommandHandler("cancel", self.start_handler.cancel_registration)]
        )
        
        self.app.add_handler(conv_handler)
        
        # Add error handler
        self.app.add_error_handler(self.error_handler)
        
        logger.info("✅ All handlers set up successfully")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
        
        if update and hasattr(update, 'message'):
            await update.message.reply_text(
                "❌ Σφάλμα! Παρακαλώ δοκιμάστε ξανά ή επικοινωνήστε με την ομάδα admin."
            )
    
    async def run_polling(self):
        """Run the bot with polling"""
        logger.info("🤖 Starting Metropolitan Bot...")
        
        # Start the application
        await self.app.initialize()
        await self.app.start()
        
        # Run polling in a way that doesn't get cancelled
        logger.info("✅ Bot is now running and listening for messages...")
        await self.app.run_polling(allowed_updates=["message", "callback_query"])
        
        # Cleanup
        await self.app.stop()
        await self.app.shutdown()
