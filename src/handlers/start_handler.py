#!/usr/bin/env python3
"""
🚀 START COMMAND HANDLER
Handles /start command with registration or check-in flow
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import logging

logger = logging.getLogger(__name__)

# Conversation states
ASKING_NAME, ASKING_PHONE = range(2)

class StartHandler:
    """Handles the /start command flow"""
    
    def __init__(self, worker_service):
        self.worker_service = worker_service
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - check if worker exists and route accordingly"""
        user = update.effective_user
        telegram_id = user.id
        
        logger.info(f"User {telegram_id} ({user.first_name}) started the bot")
        
        # Check if worker already exists
        worker_exists = await self.worker_service.check_worker_exists(telegram_id)
        
        if worker_exists:
            # Existing worker - go to check-in flow
            await self.handle_checkin_flow(update, context)
            return ConversationHandler.END
        else:
            # New worker - start registration flow
            return await self.handle_registration_flow(update, context)
    
    async def handle_registration_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new worker registration - ask for name"""
        user = update.effective_user
        
        welcome_message = f"""
Χαίρετε! 👋

Παρακαλώ για να κάνετε εγγραφή γράψτε ονομα και επώνυμο:
        """
        
        await update.message.reply_text(welcome_message)
        
        # Store user data for registration
        context.user_data['registration'] = {
            'telegram_id': user.id
        }
        
        return ASKING_NAME
    
    async def handle_name_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle name input and ask for phone"""
        name = update.message.text.strip()
        
        if len(name) < 2:
            await update.message.reply_text("❌ Το όνομα πρέπει να έχει τουλάχιστον 2 χαρακτήρες. Δοκιμάστε ξανά:")
            return ASKING_NAME
        
        # Store name and ask for phone
        context.user_data['registration']['name'] = name
        
        phone_message = """
✅ Όνομα αποθηκεύθηκε!

Τώρα παρακαλώ γράψτε το τηλέφωνό σας:
        """
        
        await update.message.reply_text(phone_message)
        return ASKING_PHONE
    
    async def handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle phone input and complete registration"""
        phone = update.message.text.strip()
        
        if len(phone) < 8:
            await update.message.reply_text("❌ Το τηλέφωνο πρέπει να έχει τουλάχιστον 8 ψηφία. Δοκιμάστε ξανά:")
            return ASKING_PHONE
        
        # Get registration data
        reg_data = context.user_data['registration']
        telegram_id = reg_data['telegram_id']
        name = reg_data['name']
        
        # Register the worker
        success = await self.worker_service.register_worker(telegram_id, name, phone)
        
        if success:
            success_message = f"""
🎉 **Εγγραφή ολοκληρώθηκε επιτυχώς!**

**Στοιχεία:**
👤 Όνομα: {name}
📱 Τηλέφωνο: {phone}
🆔 Telegram ID: {telegram_id}

Τώρα μπορείτε να χρησιμοποιήσετε το bot για check-in/check-out!
            """
            
            await update.message.reply_text(success_message, parse_mode='Markdown')
            
            # Clear registration data
            context.user_data.pop('registration', None)
            
            # Go to check-in flow
            await self.handle_checkin_flow(update, context)
            
        else:
            error_message = """
❌ Σφάλμα κατά την εγγραφή!

Παρακαλώ δοκιμάστε ξανά ή επικοινωνήστε με την ομάδα admin.
            """
            
            await update.message.reply_text(error_message)
        
        return ConversationHandler.END
    
    async def handle_checkin_flow(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle existing worker check-in flow"""
        # TODO: Implement check-in/out flow
        checkin_message = """
✅ **Καλώς ήρθατε!**

Είστε ήδη εγγεγραμμένος στο σύστημα.

🚧 Η λειτουργία check-in/check-out θα είναι διαθέσιμη σύντομα!
        """
        
        await update.message.reply_text(checkin_message, parse_mode='Markdown')
    
    async def cancel_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel registration process"""
        await update.message.reply_text("❌ Η εγγραφή ακυρώθηκε.")
        
        # Clear registration data
        context.user_data.pop('registration', None)
        
        return ConversationHandler.END
