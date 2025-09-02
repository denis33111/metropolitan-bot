#!/usr/bin/env python3
"""
🤖 WORKING METROPOLITAN BOT
Simple bot that actually works - with Google Sheets integration and attendance buttons
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler, ContextTypes
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from src.services.sheets_service import GoogleSheetsService
from src.services.location_service import LocationService
import aiohttp
from aiohttp import web
import psutil
import time
import signal

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
ASKING_NAME, ASKING_PHONE = range(2)

def load_config():
    """Load all configuration in one place"""
    config = {
        'bot_token': os.getenv('BOT_TOKEN'),
        'spreadsheet_id': os.getenv('SPREADSHEET_ID'),
        'google_credentials': os.getenv('GOOGLE_CREDENTIALS_JSON')
    }
    
    # Validate required values
    if not config['bot_token']:
        raise ValueError("BOT_TOKEN not found in environment variables!")
    if not config['spreadsheet_id']:
        raise ValueError("SPREADSHEET_ID not found in environment variables!")
    
    return config

# Global variables for pending actions
pending_actions = {}

# Add cleanup mechanism for pending actions
async def cleanup_expired_actions():
    """Clean up expired pending actions to prevent memory leaks"""
    global pending_actions
    current_time = datetime.now()
    expired_keys = []
    
    for user_id, action_data in pending_actions.items():
        # Remove actions older than 30 minutes
        if (current_time - action_data['timestamp']).total_seconds() > 1800:
            expired_keys.append(user_id)
    
    for key in expired_keys:
        del pending_actions[key]
    
    if expired_keys:
        logger.info(f"🧹 Cleaned up {len(expired_keys)} expired pending actions")
    
    return len(expired_keys)

async def monitor_memory_usage():
    """Monitor memory usage and log warnings"""
    try:
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            logger.warning(f"⚠️ High memory usage: {memory.percent:.1f}%")
        if memory.percent > 90:
            logger.error(f"🚨 Critical memory usage: {memory.percent:.1f}%")
            
        # Log memory stats periodically
        logger.info(f"📊 Memory: {memory.percent:.1f}% used, {memory.available / 1024 / 1024 / 1024:.1f}GB available")
        
    except Exception as e:
        logger.error(f"❌ Error monitoring memory: {e}")

# Add periodic cleanup task
async def periodic_cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Periodic task to clean up expired actions and monitor resources"""
    try:
        # Clean up expired actions
        cleaned_count = await cleanup_expired_actions()
        
        # Monitor memory usage
        await monitor_memory_usage()
        
        # Log current pending actions count
        global pending_actions
        logger.info(f"📊 Current pending actions: {len(pending_actions)}")
        
    except Exception as e:
        logger.error(f"❌ Error in periodic cleanup: {e}")

def create_smart_keyboard(worker_name: str, current_status: str) -> ReplyKeyboardMarkup:
    """Create smart keyboard based on current attendance status"""
    
    if current_status == 'CHECKED_IN':
        # Worker is checked in, show only check-out button
        keyboard = [
            [KeyboardButton("🚪 Check Out")],
            [KeyboardButton("📅 Πρόγραμμα"), KeyboardButton("📞 Contact")]
        ]
    elif current_status == 'COMPLETE':
        # Worker completed today, show only check-in button
        keyboard = [
            [KeyboardButton("✅ Check In")],
            [KeyboardButton("📅 Πρόγραμμα"), KeyboardButton("📞 Contact")]
        ]
    else:
        # Worker not checked in today, show only check-in button
        keyboard = [
            [KeyboardButton("✅ Check In")],
            [KeyboardButton("📅 Πρόγραμμα"), KeyboardButton("📞 Contact")]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start_command(update: Update, context):
    """Handle /start command"""
    # Get services from context
    sheets_service = context.bot_data.get('sheets_service')
    location_service = context.bot_data.get('location_service')
    
    user = update.effective_user
    
    # Check if worker already exists
    existing_worker = await sheets_service.find_worker_by_telegram_id(user.id)
    
    if existing_worker:
        # Existing worker - show smart keyboard based on current status
        worker_name = existing_worker['name']
        
        # Get current attendance status
        attendance_status = await sheets_service.get_worker_attendance_status(worker_name)
        current_status = attendance_status['status']
        
        # Create smart keyboard based on current status
        smart_keyboard = create_smart_keyboard(worker_name, current_status)
        
        # Show welcome message with smart keyboard
        welcome_msg = f"""
✅ **Καλώς ήρθατε, {worker_name}!**

Είστε ήδη εγγεγραμμένος στο σύστημα.

**Χρησιμοποιήστε τα κουμπιά κάτω από το πεδίο εισαγωγής:**
        """
        
        # Send message with smart keyboard
        await update.message.reply_text(welcome_msg, parse_mode='Markdown', reply_markup=smart_keyboard)
        
        return ConversationHandler.END
    else:
        # New worker - start registration flow
        await update.message.reply_text("Χαίρετε! 👋\n\nΠαρακαλώ για να κάνετε εγγραφή γράψτε ονομα και επώνυμο:")
        
        # Store user data for registration
        context.user_data['registration'] = {'telegram_id': user.id}
        
        return ASKING_NAME

async def handle_name(update: Update, context):
    """Handle name input"""
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

async def handle_phone(update: Update, context):
    """Handle phone input"""
    phone = update.message.text.strip()
    
    if len(phone) < 8:
        await update.message.reply_text("❌ Το τηλέφωνο πρέπει να έχει τουλάχιστον 8 ψηφία. Δοκιμάστε ξανά:")
        return ASKING_PHONE
    
    # Get registration data
    reg_data = context.user_data['registration']
    telegram_id = reg_data['telegram_id']
    name = reg_data['name']
    
    # Get sheets service from context
    sheets_service = context.bot_data.get('sheets_service')
    if not sheets_service:
        await update.message.reply_text("❌ Σφάλμα: Δεν μπορεί να βρεθεί η υπηρεσία Google Sheets.")
        return ConversationHandler.END
    
    # Get services from context
    sheets_service = context.bot_data.get('sheets_service')
    
    # Add worker to Google Sheets
    success = await sheets_service.add_worker(telegram_id, name, phone)
    
    if success:
        success_msg = "✅ Η εγγραφή σας ολοκληρώθηκε!"
        
        await update.message.reply_text(success_msg)
        
        # Clear data
        context.user_data.pop('registration', None)
        
        # Show attendance menu for new worker
        # Create smart keyboard for new worker (not checked in)
        smart_keyboard = create_smart_keyboard(name, 'NOT_CHECKED_IN')
        
        menu_msg = f"""
🎉 **Καλώς ήρθατε στο σύστημα, {name}!**

Τώρα μπορείτε να χρησιμοποιήσετε το bot για check-in/check-out!

**Χρησιμοποιήστε τα κουμπιά κάτω από το πεδίο εισαγωγής:**
        """
        
        # Send message with smart keyboard
        await update.message.reply_text(menu_msg, parse_mode='Markdown', reply_markup=smart_keyboard)
        
    else:
        error_msg = """
❌ Σφάλμα κατά την εγγραφή!

Δεν ήταν δυνατή η αποθήκευση στο Google Sheets.
Παρακαλώ δοκιμάστε ξανά ή επικοινωνήστε με την ομάδα admin.
        """
        
        await update.message.reply_text(error_msg)
    
    return ConversationHandler.END

async def cancel_registration(update: Update, context):
    """Cancel registration"""
    await update.message.reply_text("❌ Η εγγραφή ακυρώθηκε.")
    context.user_data.pop('registration', None)
    return ConversationHandler.END

# LEGACY FUNCTIONS - REMOVED (were causing duplicate messages)
# These functions are no longer used - all check-in/check-out flows now use persistent keyboard
# async def handle_button_callback() - REMOVED
# async def handle_checkin() - REMOVED  
# async def handle_checkout() - REMOVED

async def handle_schedule_request(query, context, worker_name: str):
    """Handle weekly schedule request"""
    try:
        from datetime import datetime, timedelta
        
        # Get current date and format for sheets (Greece timezone)
        import pytz
        greece_tz = pytz.timezone('Europe/Athens')
        today = datetime.now(greece_tz)
        # Fix date format for macOS compatibility
        try:
            current_date = today.strftime("%-m/%-d/%Y")  # Format: 7/18/2025
        except ValueError:
            current_date = today.strftime("%m/%d/%Y")  # Format: 07/18/2025
        
        # Get worker's telegram ID to find their schedule
        user = query.from_user
        
        # Get sheets_service from the bot context
        sheets_service = context.bot_data.get('sheets_service')
        if not sheets_service:
            await query.edit_message_text("❌ Σφάλμα: Δεν είναι διαθέσιμη η υπηρεσία Google Sheets.")
            return
        
        # Get worker info
        existing_worker = await sheets_service.find_worker_by_telegram_id(user.id)
        if not existing_worker:
            await query.edit_message_text("❌ Δεν είστε εγγεγραμμένος στο σύστημα.")
            return
        
        # Get current week schedule
        current_week_schedule = await sheets_service.get_weekly_schedule(str(user.id), current_date)
        
        # Get next week schedule using intelligent B3-based detection
        worker_name = existing_worker['name']
        next_week_schedule = await sheets_service.get_intelligent_next_week_schedule(current_date, worker_name)
        
        # Create smart keyboard based on current status
        attendance_status = await sheets_service.get_worker_attendance_status(worker_name)
        current_status = attendance_status['status']
        smart_keyboard = create_smart_keyboard(worker_name, current_status)
        
        # Format current week schedule with improved design
        current_week_text = ""
        if current_week_schedule:
            current_week_text = "**📅 ΤΡΕΧΟΥΣΑ ΕΒΔΟΜΑΔΑ**\n"
            current_week_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_names_gr = ['Δευτέρα', 'Τρίτη', 'Τετάρτη', 'Πέμπτη', 'Παρασκευή', 'Σάββατο', 'Κυριακή']
            
            for i, day in enumerate(days):
                # Always show all 7 days, regardless of data availability
                if day in current_week_schedule and current_week_schedule[day]:
                    schedule = current_week_schedule[day]
                    if schedule and schedule.strip():
                        if schedule.strip().upper() in ['REST', 'OFF']:
                            current_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule}\n"
                        else:
                            # Check if it's today
                            today_name = today.strftime("%A")
                            if day == today_name:
                                current_week_text += f"🎯 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule} _(Σήμερα)_\n"
                            else:
                                current_week_text += f"🟢 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule}\n"
                    else:
                        # Empty slots are treated as REST days
                        current_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• REST\n"
                else:
                    # Day not in schedule or has no data = REST day
                    current_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• REST\n"
        else:
            current_week_text = "**📅 ΤΡΕΧΟΥΣΑ ΕΒΔΟΜΑΔΑ**\n"
            current_week_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            current_week_text += "⚠️ Δεν βρέθηκε πρόγραμμα"
        
        # Format next week schedule with improved design
        next_week_text = ""
        if next_week_schedule:
            next_week_text = "\n**📅 ΕΠΟΜΕΝΗ ΕΒΔΟΜΑΔΑ**\n"
            next_week_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_names_gr = ['Δευτέρα', 'Τρίτη', 'Τετάρτη', 'Πέμπτη', 'Παρασκευή', 'Σάββατο', 'Κυριακή']
            
            for i, day in enumerate(days):
                # Always show all 7 days, regardless of data availability
                if day in next_week_schedule and next_week_schedule[day]:
                    schedule = next_week_schedule[day]
                    if schedule and schedule.strip():
                        if schedule.strip().upper() in ['REST', 'OFF']:
                            next_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule}\n"
                        else:
                            next_week_text += f"🟢 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule}\n"
                    else:
                        # Empty slots are treated as REST days
                        next_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• REST\n"
                else:
                    # Day not in schedule or has no data = REST day
                    next_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• REST\n"
        else:
            next_week_text = "\n**📅 ΕΠΟΜΕΝΗ ΕΒΔΟΜΑΔΑ**\n"
            next_week_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            next_week_text += "⚪ Δεν έχει οριστεί ακόμα"
        
        message = f"""
{current_week_text}
{next_week_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Επιλέξτε την επόμενη ενέργεια:**
        """
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=smart_keyboard)
        
    except Exception as e:
        logger.error(f"Error during schedule request: {e}")
        await query.edit_message_text("❌ Σφάλμα κατά την ανάκτηση του προγράμματος.")

async def handle_contact(query):
    """Handle contact request"""
    user = query.from_user
    
    # Check if user is admin (you)
    if user.username == "DenisZgl" or user.id == 123456789:  # Replace with your actual Telegram ID
        # Admin sees different message
        admin_message = """
👨‍💻 **Admin Panel**

**Είστε ο admin του bot!**

**📊 Διαθέσιμες ενέργειες:**
- /workers - Λίστα εργαζομένων
- /office - Πληροφορίες γραφείου  
- /monthcreation - Δημιουργία μηνιαίων φύλλων

**ℹ️ Για επικοινωνία με εργαζόμενους:**
Χρησιμοποιήστε τα admin commands παραπάνω.
        """
        
        # Get worker info to show back button
        existing_worker = await sheets_service.find_worker_by_telegram_id(user.id)
        
        if existing_worker:
            worker_name = existing_worker['name']
            attendance_status = await sheets_service.get_worker_attendance_status(worker_name)
            keyboard = ReplyKeyboardMarkup([
                [KeyboardButton("✅ Check In"), KeyboardButton("🚪 Check Out")],
                [KeyboardButton("📅 My Schedule"), KeyboardButton("📞 Contact")]
            ], resize_keyboard=True)
            
            await query.edit_message_text(admin_message, parse_mode='Markdown', reply_markup=keyboard)
        else:
            await query.edit_message_text(admin_message, parse_mode='Markdown')
    else:
        # Regular users get contact button
        contact_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Chat με Admin", url="https://t.me/DenisZgl")]
        ])
        
        contact_message = """
💬 **Άμεση Επικοινωνία**

**Πατήστε το κουμπί για άμεση επικοινωνία:**
        """
        
        # Get worker info to show back button
        existing_worker = await sheets_service.find_worker_by_telegram_id(user.id)
        
        if existing_worker:
            worker_name = existing_worker['name']
            attendance_status = await sheets_service.get_worker_attendance_status(worker_name)
            keyboard = ReplyKeyboardMarkup([
                [KeyboardButton("✅ Check In"), KeyboardButton("🚪 Check Out")],
                [KeyboardButton("📅 My Schedule"), KeyboardButton("📞 Contact")]
            ], resize_keyboard=True)
            
            await query.edit_message_text(contact_message, parse_mode='Markdown', reply_markup=contact_keyboard)
        else:
            await query.edit_message_text(contact_message, parse_mode='Markdown', reply_markup=contact_keyboard)
    
    # Get worker info to show back button
    user = query.from_user
    existing_worker = await sheets_service.find_worker_by_telegram_id(user.id)
    
    if existing_worker:
        worker_name = existing_worker['name']
        attendance_status = await sheets_service.get_worker_attendance_status(worker_name)
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("✅ Check In"), KeyboardButton("🚪 Check Out")],
            [KeyboardButton("📅 My Schedule"), KeyboardButton("📞 Contact")]
        ], resize_keyboard=True)
        
        await query.edit_message_text(contact_message, parse_mode='Markdown', reply_markup=contact_keyboard)
    else:
        await query.edit_message_text(contact_message, parse_mode='Markdown', reply_markup=contact_keyboard)

async def list_workers_command(update: Update, context):
    """List all workers (admin command)"""
    sheets_service = context.bot_data.get('sheets_service')
    workers = await sheets_service.get_all_workers()
    
    if not workers:
        await update.message.reply_text("📊 Δεν υπάρχουν εγγεγραμμένοι εργαζόμενοι.")
        return
    
    workers_list = "📊 **Λίστα Εργαζομένων:**\n\n"
    
    for i, worker in enumerate(workers, 1):
        workers_list += f"{i}. **{worker['name']}**\n"
        workers_list += f"   📱 {worker['phone']}\n"
        workers_list += f"   🆔 {worker['telegram_id']}\n"
        workers_list += f"   📊 {worker['status']}\n\n"
    
    await update.message.reply_text(workers_list, parse_mode='Markdown')

async def office_info_command(update: Update, context):
    """Show office zone information"""
    location_service = context.bot_data.get('location_service')
    office_info = location_service.get_office_info()
    
    message = f"""
🏢 **Πληροφορίες Γραφείου**

**📍 Τοποθεσία:**
Latitude: {office_info['latitude']}
Longitude: {office_info['longitude']}

**📏 Ζώνη Check-in/out:**
Ακτίνα: {office_info['radius_meters']} μέτρα

**ℹ️ Περιγραφή:**
{office_info['description']}

**🗺️ Για να κάνετε check-in/out:**
Πρέπει να είστε μέσα σε {office_info['radius_meters']}m από το γραφείο.
    """
    
    await update.message.reply_text(message, parse_mode='Markdown')



async def handle_location_message(update: Update, context):
    """Handle location messages for check-in/out"""
    try:
        user = update.effective_user
        user_id = user.id
        
        # Check if user has a pending action
        pending_action = pending_actions.get(user_id)
        
        logger.info(f"🔍 DEBUG: Checking pending actions for user {user_id}")
        logger.info(f"🔍 DEBUG: Current pending actions: {pending_actions}")
        logger.info(f"🔍 DEBUG: User's pending action: {pending_action}")
        
        if not pending_action:
            # No pending action, ignore location
            logger.info(f"🔍 DEBUG: No pending action for user {user_id}, ignoring location")
            return
        
        # Get location from message
        if not update.message.location:
            await update.message.reply_text("❌ Παρακαλώ στείλτε την τοποθεσία σας (location), όχι κείμενο.")
            # Clear pending action for invalid location so user can try again
            pending_actions.pop(user_id, None)
            # Return to main menu even for invalid location
            await return_to_main_menu(update, context, user_id)
            return
        
        location = update.message.location
        latitude = location.latitude
        longitude = location.longitude
        
        logger.info(f"🔍 DEBUG: Received location from user {user_id}:")
        logger.info(f"🔍 DEBUG:   Raw location object: {location}")
        logger.info(f"🔍 DEBUG:   Latitude: {latitude}")
        logger.info(f"🔍 DEBUG:   Longitude: {longitude}")
        logger.info(f"🔍 DEBUG:   Location type: {type(latitude)}, {type(longitude)}")
        
        # Get services from context
        location_service = context.bot_data.get('location_service')
        if not location_service:
            logger.error("🔍 DEBUG: Location service not available in context")
            logger.error("Location service not available in context")
            await update.message.reply_text("❌ Σφάλμα: Δεν είναι διαθέσιμη η υπηρεσία τοποθεσίας.")
            # Clear pending action when service unavailable so user can try again
            pending_actions.pop(user_id, None)
            await return_to_main_menu(update, context, user_id)
            return
        
        logger.info(f"🔍 DEBUG: Location service found, calling is_within_office_zone...")
        # Verify location is within office zone
        location_result = location_service.is_within_office_zone(latitude, longitude)
        logger.info(f"🔍 DEBUG: Location verification result: {location_result}")
        
        if not location_result['is_within']:
            # Location outside zone - show error and return to main menu
            location_msg = location_service.format_location_message(location_result)
            await update.message.reply_text(location_msg, parse_mode='Markdown')
            
            # IMPORTANT: Clear pending action when location fails so user can try again
            pending_actions.pop(user_id, None)
            
            # Return to main menu after failed location check
            await return_to_main_menu(update, context, user_id)
            return
        
        # Location verified, proceed with action
        logger.info(f"🔍 DEBUG: Location verified, proceeding with action: {pending_action['action']}")
        if pending_action['action'] == 'checkin':
            logger.info(f"🔍 DEBUG: Calling complete_checkin for user {user_id}")
            await complete_checkin(update, context, pending_action, location_result)
        elif pending_action['action'] == 'checkout':
            logger.info(f"🔍 DEBUG: Calling complete_checkout for user {user_id}")
            await complete_checkout(update, context, pending_action, location_result)
        
        # Clear pending action
        logger.info(f"🔍 DEBUG: Clearing pending action for user {user_id}")
        pending_actions.pop(user_id, None)
        logger.info(f"🔍 DEBUG: Pending actions after clearing: {pending_actions}")
        
    except Exception as e:
        logger.error(f"Error handling location message: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά την επεξεργασία της τοποθεσίας.")
        # Clear pending action on error so user can try again
        pending_actions.pop(user_id, None)
        # Return to main menu even on error
        await return_to_main_menu(update, context, user_id)

async def return_to_main_menu(update: Update, context, user_id: int):
    """Return user to main menu after any check-in/out attempt"""
    try:
        # Get worker info
        sheets_service = context.bot_data.get('sheets_service')
        location_service = context.bot_data.get('location_service')
        existing_worker = await sheets_service.find_worker_by_telegram_id(user_id)
        if not existing_worker:
            return
        
        worker_name = existing_worker['name']
        
        # Get current attendance status
        attendance_status = await sheets_service.get_worker_attendance_status(worker_name)
        current_status = attendance_status['status']
        
        # Create smart keyboard based on current status
        smart_keyboard = create_smart_keyboard(worker_name, current_status)
        
        # Show main menu message
        menu_msg = f"🏠 Επιστροφή στο μενού"
        
        # Send message with smart keyboard
        await update.message.reply_text(menu_msg, parse_mode='Markdown', reply_markup=smart_keyboard)
        
    except Exception as e:
        logger.error(f"Error returning to main menu: {e}")
        # Fallback: just show basic message
        await update.message.reply_text("🏠 Επιστροφή στο κύριο μενού. Χρησιμοποιήστε /start για να ξαναρχίσετε.")

async def complete_checkin(update: Update, context, pending_data: dict, location_result: dict):
    """Complete check-in after location verification"""
    try:
        sheets_service = context.bot_data.get('sheets_service')
        location_service = context.bot_data.get('location_service')
        worker_name = pending_data['worker_name']
        current_time = datetime.now().strftime("%H:%M")
        
        # Update attendance sheet
        success = await sheets_service.update_attendance_cell(
            sheets_service.get_current_month_sheet_name(),
            worker_name,
            check_in_time=current_time
        )
        
        if success:
            # Create smart keyboard for check-in status
            smart_keyboard = create_smart_keyboard(worker_name, 'CHECKED_IN')
            
            message = f"""
✅ **Check-in επιτυχής!**

**Όνομα:** {worker_name}
**Ώρα:** {current_time}
**Ημερομηνία:** {datetime.now().strftime("%d/%m/%Y")}
**📍 Τοποθεσία:** Επαληθεύθηκε ({location_result['distance_meters']}m από γραφείο)

**Τώρα μπορείτε να κάνετε check-out όταν τελειώσετε τη βάρδια!**
            """
            
            # Send success message with smart keyboard
            await update.message.reply_text(message, parse_mode='Markdown', reply_markup=smart_keyboard)
        else:
            await update.message.reply_text("❌ Σφάλμα κατά το check-in. Παρακαλώ δοκιμάστε ξανά.")
            # Clear pending action on failure so user can try again
            user_id = update.effective_user.id
            pending_actions.pop(user_id, None)
            
    except Exception as e:
        logger.error(f"Error completing check-in: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά το check-in. Παρακαλώ δοκιμάστε ξανά.")
        # Clear pending action on error so user can try again
        user_id = update.effective_user.id
        pending_actions.pop(user_id, None)

async def complete_checkout(update: Update, context, pending_data: dict, location_result: dict):
    """Complete check-out after location verification"""
    try:
        sheets_service = context.bot_data.get('sheets_service')
        location_service = context.bot_data.get('location_service')
        worker_name = pending_data['worker_name']
        current_time = datetime.now().strftime("%H:%M")
        
        # Get current attendance status to find check-in time
        attendance_status = await sheets_service.get_worker_attendance_status(worker_name)
        
        if attendance_status['status'] == 'CHECKED_IN':
            # Extract check-in time from current cell
            check_in_time = attendance_status['time']
            
            # Update attendance sheet with both times
            success = await sheets_service.update_attendance_cell(
                sheets_service.get_current_month_sheet_name(),
                worker_name,
                check_in_time=check_in_time,
                check_out_time=current_time
            )
            
            if success:
                # Create smart keyboard for completed status
                smart_keyboard = create_smart_keyboard(worker_name, 'COMPLETE')
                
                message = f"""
🚪 **Check-out επιτυχής!**

**Όνομα:** {worker_name}
**Check-in:** {check_in_time}
**Check-out:** {current_time}
**Ημερομηνία:** {datetime.now().strftime("%d/%m/%Y")}
**📍 Τοποθεσία:** Επαληθεύθηκε ({location_result['distance_meters']}m από γραφείο)

**Η βάρδια σας ολοκληρώθηκε! Μπορείτε να κάνετε check-in αύριο.**
                """
                
                # Send success message with smart keyboard
                await update.message.reply_text(message, parse_mode='Markdown', reply_markup=smart_keyboard)
            else:
                await update.message.reply_text("❌ Σφάλμα κατά το check-out. Παρακαλώ δοκιμάστε ξανά.")
                # Clear pending action on failure so user can try again
                user_id = update.effective_user.id
                pending_actions.pop(user_id, None)
        else:
            await update.message.reply_text("❌ Δεν μπορείτε να κάνετε check-out χωρίς να έχετε κάνει check-in.")
            # Clear pending action when not checked in so user can try again
            user_id = update.effective_user.id
            pending_actions.pop(user_id, None)
            
    except Exception as e:
        logger.error(f"Error completing check-out: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά το check-out. Παρακαλώ δοκιμάστε ξανά.")
        # Clear pending action on error so user can try again
        user_id = update.effective_user.id
        pending_actions.pop(user_id, None)

async def handle_persistent_keyboard(update: Update, context):
    """Handle persistent keyboard button presses"""
    try:
        user = update.effective_user
        text = update.message.text
        
        logger.info(f"🔍 DEBUG: handle_persistent_keyboard called by user {user.id}")
        logger.info(f"🔍 DEBUG: Button text: '{text}'")
        logger.info(f"🔍 DEBUG: User info: {user.username} ({user.first_name} {user.last_name})")
        
        # Check if worker exists
        sheets_service = context.bot_data.get('sheets_service')
        location_service = context.bot_data.get('location_service')
        existing_worker = await sheets_service.find_worker_by_telegram_id(user.id)
        
        if not existing_worker:
            await update.message.reply_text("❌ Δεν είστε εγγεγραμμένος στο σύστημα. Παρακαλώ χρησιμοποιήστε /start για εγγραφή.")
            return
        
        worker_name = existing_worker['name']
        
        if text == "✅ Check In":
            # Handle check-in via persistent keyboard
            logger.info(f"🔍 DEBUG: Check In button pressed by user {user.id} ({worker_name})")
            await handle_persistent_checkin(update, context, worker_name)
            
        elif text == "🚪 Check Out":
            # Handle check-out via persistent keyboard
            logger.info(f"🔍 DEBUG: Check Out button pressed by user {user.id} ({worker_name})")
            await handle_persistent_checkout(update, context, worker_name)
            
        elif text == "📅 Πρόγραμμα":
            # Handle schedule request via persistent keyboard
            await handle_persistent_schedule(update, context, worker_name)
            
        elif text == "📞 Contact":
            # Handle contact request via persistent keyboard
            await handle_persistent_contact(update, context, worker_name)
            
        elif text == "🏠 Πίσω στο μενού":
            # Handle back to menu button - return to main menu
            await return_to_main_menu(update, context, user.id)
            
    except Exception as e:
        logger.error(f"Error handling persistent keyboard: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά την επεξεργασία της ενέργειας.")

async def handle_persistent_checkin(update: Update, context, worker_name: str):
    """Handle check-in from persistent keyboard"""
    try:
        # Check if user already has a pending action
        user_id = update.effective_user.id
        if user_id in pending_actions:
            existing_action = pending_actions[user_id]
            if existing_action['action'] == 'checkin':
                # Already in check-in flow - just remind them to send location
                await update.message.reply_text(
                    f"⏳ **Check-in σε εξέλιξη για {worker_name}**\n\n"
                    "**📱 Στείλτε την τοποθεσία σας** με το κουμπί που εμφανίστηκε.",
                    parse_mode='Markdown'
                )
                return
            elif existing_action['action'] == 'checkout':
                await update.message.reply_text(
                    f"⚠️ **Έχετε ήδη ένα check-out σε εξέλιξη**\n\n"
                    "**🔄 Περιμένετε να ολοκληρωθεί το check-out πριν κάνετε check-in.**",
                    parse_mode='Markdown'
                )
                return
        
        # Create location request keyboard
        location_keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("📍 Στείλε την τοποθεσία μου", request_location=True)],
            [KeyboardButton("🏠 Πίσω στο μενού")]
        ], resize_keyboard=True, one_time_keyboard=True)
        
        # Store check-in request in global pending_actions
        pending_actions[user_id] = {
            'worker_name': worker_name,
            'action': 'checkin',
            'timestamp': datetime.now()
        }
        logger.info(f"🔍 DEBUG: Stored check-in pending action for user {user_id}: {pending_actions[user_id]}")
        logger.info(f"🔍 DEBUG: All pending actions: {pending_actions}")
        
        # Show minimal location request message
        await update.message.reply_text(
            f"📍 **Check-in για {worker_name}**\n\n"
            "**Πατήστε το κουμπί τοποθεσίας παρακάτω:**\n\n"
            "⚠️ Πρέπει να είστε μέσα σε 300m από το γραφείο",
            reply_markup=location_keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error during persistent check-in: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά το check-in. Παρακαλώ δοκιμάστε ξανά.")

async def handle_persistent_checkout(update: Update, context, worker_name: str):
    """Handle check-out from persistent keyboard"""
    try:
        # Check if user already has a pending action
        user_id = update.effective_user.id
        if user_id in pending_actions:
            existing_action = pending_actions[user_id]
            if existing_action['action'] == 'checkout':
                # Already in check-out flow - just remind them to send location
                await update.message.reply_text(
                    f"⏳ **Check-out σε εξέλιξη για {worker_name}**\n\n"
                    "**📱 Στείλτε την τοποθεσία σας** με το κουμπί που εμφανίστηκε.",
                    parse_mode='Markdown'
                )
                return
            elif existing_action['action'] == 'checkin':
                await update.message.reply_text(
                    f"⚠️ **Έχετε ήδη ένα check-in σε εξέλιξη**\n\n"
                    "**🔄 Περιμένετε να ολοκληρωθεί το check-in πριν κάνετε check-out.**",
                    parse_mode='Markdown'
                )
                return
        
        # Create location request keyboard
        location_keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("📍 Στείλε την τοποθεσία μου", request_location=True)],
            [KeyboardButton("🏠 Πίσω στο μενού")]
        ], resize_keyboard=True, one_time_keyboard=True)
        
        # Store check-out request in global pending_actions
        pending_actions[user_id] = {
            'worker_name': worker_name,
            'action': 'checkout',
            'timestamp': datetime.now()
        }
        logger.info(f"🔍 DEBUG: Stored check-out pending action for user {user_id}: {pending_actions[user_id]}")
        logger.info(f"🔍 DEBUG: All pending actions: {pending_actions}")
        
        # Show minimal location request message
        await update.message.reply_text(
            f"🚪 **Check-out για {worker_name}**\n\n"
            "**Πατήστε το κουμπί τοποθεσίας παρακάτω:**\n\n"
            "⚠️ Πρέπει να είστε μέσα σε 300m από το γραφείο",
            reply_markup=location_keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error during persistent check-out: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά το check-out. Παρακαλώ δοκιμάστε ξανά.")

async def handle_persistent_schedule(update: Update, context, worker_name: str):
    """Handle weekly schedule request from persistent keyboard"""
    try:
        from datetime import datetime, timedelta
        
        # Get current date and format for sheets (Greece timezone)
        import pytz
        greece_tz = pytz.timezone('Europe/Athens')
        today = datetime.now(greece_tz)
        # Fix date format for macOS compatibility
        try:
            current_date = today.strftime("%-m/%-d/%Y")  # Format: 7/18/2025
        except ValueError:
            current_date = today.strftime("%m/%d/%Y")  # Format: 07/18/2025
        
        # Get worker's telegram ID to find their schedule
        user = update.effective_user
        
        # Get sheets_service from the bot context
        sheets_service = context.bot_data.get('sheets_service')
        if not sheets_service:
            await update.message.reply_text("❌ Σφάλμα: Δεν είναι διαθέσιμη η υπηρεσία Google Sheets.")
            return
            
        existing_worker = await sheets_service.find_worker_by_telegram_id(user.id)
        
        if not existing_worker:
            await update.message.reply_text("❌ Δεν είστε εγγεγραμμένος στο σύστημα.")
            return
        
        # Get current week schedule
        current_week_schedule = await sheets_service.get_weekly_schedule(str(user.id), current_date)
        
        # Get next week schedule using intelligent B3-based detection
        worker_name = existing_worker['name']
        next_week_schedule = await sheets_service.get_intelligent_next_week_schedule(current_date, worker_name)
        
        # Create smart keyboard based on current status
        attendance_status = await sheets_service.get_worker_attendance_status(worker_name)
        current_status = attendance_status['status']
        smart_keyboard = create_smart_keyboard(worker_name, current_status)
        
        # Format current week schedule with improved design
        current_week_text = ""
        if current_week_schedule:
            current_week_text = "**📅 ΤΡΕΧΟΥΣΑ ΕΒΔΟΜΑΔΑ**\n"
            current_week_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_names_gr = ['Δευτέρα', 'Τρίτη', 'Τετάρτη', 'Πέμπτη', 'Παρασκευή', 'Σάββατο', 'Κυριακή']
            
            for i, day in enumerate(days):
                # Always show all 7 days, regardless of data availability
                if day in current_week_schedule and current_week_schedule[day]:
                    schedule = current_week_schedule[day]
                    if schedule and schedule.strip():
                        if schedule.strip().upper() in ['REST', 'OFF']:
                            current_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule}\n"
                        else:
                            # Check if it's today
                            today_name = today.strftime("%A")
                            if day == today_name:
                                current_week_text += f"🎯 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule} _(Σήμερα)_\n"
                            else:
                                current_week_text += f"🟢 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule}\n"
                    else:
                        # Empty slots are treated as REST days
                        current_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• REST\n"
                else:
                    # Day not in schedule or has no data = REST day
                    current_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• REST\n"
        else:
            current_week_text = "**📅 ΤΡΕΧΟΥΣΑ ΕΒΔΟΜΑΔΑ**\n"
            current_week_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            current_week_text += "⚠️ Δεν βρέθηκε πρόγραμμα"
        
        # Format next week schedule with improved design
        next_week_text = ""
        if next_week_schedule:
            next_week_text = "\n**📅 ΕΠΟΜΕΝΗ ΕΒΔΟΜΑΔΑ**\n"
            next_week_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_names_gr = ['Δευτέρα', 'Τρίτη', 'Τετάρτη', 'Πέμπτη', 'Παρασκευή', 'Σάββατο', 'Κυριακή']
            
            for i, day in enumerate(days):
                # Always show all 7 days, regardless of data availability
                if day in next_week_schedule and next_week_schedule[day]:
                    schedule = next_week_schedule[day]
                    if schedule and schedule.strip():
                        if schedule.strip().upper() in ['REST', 'OFF']:
                            next_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule}\n"
                        else:
                            next_week_text += f"🟢 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• {schedule}\n"
                    else:
                        # Empty slots are treated as REST days
                        next_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• REST\n"
                else:
                    # Day not in schedule or has no data = REST day
                    next_week_text += f"🟡 **{day_names_gr[i]}**{' ' * (12 - len(day_names_gr[i]))}• REST\n"
        else:
            next_week_text = "\n**📅 ΕΠΟΜΕΝΗ ΕΒΔΟΜΑΔΑ**\n"
            next_week_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            next_week_text += "⚪ Δεν έχει οριστεί ακόμα"
        
        message = f"""
{current_week_text}
{next_week_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Επιλέξτε την επόμενη ενέργεια:**
        """
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=smart_keyboard)
        
    except Exception as e:
        logger.error(f"Error during persistent schedule request: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά την ανάκτηση του προγράμματος.")

async def handle_persistent_contact(update: Update, context, worker_name: str):
    """Handle contact request from persistent keyboard"""
    try:
        user = update.effective_user
        
        # Check if user is admin (you)
        if user.username == "DenisZgl" or user.id == 123456789:  # Replace with your actual Telegram ID
            # Admin sees different message
            admin_message = f"""
👨‍💻 **Admin Panel - {worker_name}**

**Είστε ο admin του bot!**

**📊 Διαθέσιμες ενέργειες:**
- /workers - Λίστα εργαζομένων
- /office - Πληροφορίες γραφείου  
- /monthcreation - Δημιουργία μηνιαίων φύλλων

**ℹ️ Για επικοινωνία με εργαζόμενους:**
Χρησιμοποιήστε τα admin commands παραπάνω.
            """
            await update.message.reply_text(admin_message, parse_mode='Markdown')
        else:
            # Regular users get contact button
            contact_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Chat με Admin", url="https://t.me/DenisZgl")]
            ])
            
            contact_message = f"""
💬 **Άμεση Επικοινωνία**

**Πατήστε το κουμπί για άμεση επικοινωνία:**
            """
            
            await update.message.reply_text(contact_message, parse_mode='Markdown', reply_markup=contact_keyboard)
        
    except Exception as e:
        logger.error(f"Error during persistent contact request: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά την επεξεργασία της επικοινωνίας.")

# OLD AUTOMATIC MONTHLY SHEET CREATION - REPLACED BY MANUAL /monthcreation COMMAND
# async def check_and_create_monthly_sheets():
#     """Check if new month started and create sheet automatically - runs once per day"""
#     global last_month_check
#     
#     try:
#         current_time = datetime.now()
#         
#         # Check only once per day to avoid spam
#         if last_month_check and (current_time - last_month_check).date() == current_time.date():
#             return
#         
#         last_month_check = current_time
#         
#         # Only create sheet on the 1st of the month
#         if current_time.day != 1:
#             return
#         
#         # Get next month's sheet name
#         next_month = current_time + timedelta(days=32)  # Go to next month
#         next_month_name = f"{next_month.month:02d}_{next_month.year}"
#         
#         logger.info(f"📅 First day of month detected - checking if {next_month_name} sheet exists...")
#         
#         # Check if next month's sheet already exists
#         try:
#             result = sheets_service.service.spreadsheets().get(
#                 spreadsheetId=sheets_service.spreadsheet_id
#                 ).execute()
#             
#             sheet_exists = any(sheet['properties']['title'] == next_month_name 
#                              for sheet in result.get('sheets', []))
#             
#             if not sheet_exists:
#                 logger.info(f"🔄 Bot automatically creating next month's sheet: {next_month_name}")
#                 
#                 # Create new sheet
#                 request = {
#                     'addSheet': {
#                         'properties': {
#                             'title': next_month_name,
#                         'gridProperties': {
#                             'rowCount': 1000,
#                             'columnCount': 32  # 31 days + name column
#                         }
#                     }
#                 }
#                 
#                 sheets_service.service.spreadsheets().batchUpdate(
#                     spreadsheetId=sheets_service.spreadsheet_id,
#                     body={'requests': [request]}
#                 ).execute()
#                 
#                 # Set up headers and styling
#                 await sheets_service.service.setup_monthly_sheet_headers(next_month_name)
#                 await asyncio.sleep(1)
#                 await sheets_service.service.style_monthly_sheet(next_month_name)
#                 
#                 logger.info(f"✅ Bot automatically created and styled monthly sheet: {next_month_name}")
#             else:
#                 logger.info(f"✅ Sheet {next_month_name} already exists - no action needed")
#                 
#         except Exception as e:
#             logger.error(f"❌ Error in automatic monthly sheet creation: {e}")
#             
#     except Exception as e:
#             logger.error(f"❌ Error in monthly sheet check: {e}")

async def create_next_two_months_sheets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to create current and next 2 months sheets if they don't exist"""
    try:
        # Check if user is admin (you can add more sophisticated admin checks here)
        user = update.effective_user
        logger.info(f"👤 User {user.username} ({user.id}) requested month creation")
        
        current_time = datetime.now()
        
        # Get current month and next 2 months
        current_month_name = f"{current_time.month:02d}_{current_time.year}"
        next_month = current_time + timedelta(days=32)
        next_next_month = next_month + timedelta(days=32)
        
        next_month_name = f"{next_month.month:02d}_{next_month.year}"
        next_next_month_name = f"{next_next_month.month:02d}_{next_next_month.year}"
        
        await update.message.reply_text(f"🔄 Checking and creating monthly sheets...")
        
        created_sheets = []
        
        try:
            result = sheets_service.service.spreadsheets().get(
                spreadsheetId=sheets_service.spreadsheet_id
            ).execute()
            
            # Check and create current month
            current_month_exists = any(sheet['properties']['title'] == current_month_name 
                                     for sheet in result.get('sheets', []))
            
            if not current_month_exists:
                logger.info(f"🔄 Creating current month sheet: {current_month_name}")
                
                try:
                    # Create new sheet
                    request = {
                        'addSheet': {
                            'properties': {
                                'title': current_month_name,
                                'gridProperties': {
                                    'rowCount': 1000,
                                    'columnCount': 32  # 31 days + name column
                                }
                            }
                        }
                    }
                    
                    sheets_service.service.spreadsheets().batchUpdate(
                        spreadsheetId=sheets_service.spreadsheet_id,
                        body={'requests': [request]}
                    ).execute()
                    
                    # Set up headers and styling
                    headers_success = await sheets_service.setup_monthly_sheet_headers(current_month_name)
                    if not headers_success:
                        logger.error(f"❌ Failed to set up headers for {current_month_name}")
                        await update.message.reply_text(f"❌ Failed to create {current_month_name} - headers setup failed")
                        return
                    
                    # Verify headers were created correctly
                    await asyncio.sleep(1)
                    await sheets_service.style_monthly_sheet(current_month_name)
                    
                    created_sheets.append(current_month_name)
                    logger.info(f"✅ Created current month sheet: {current_month_name}")
                    
                    # Add delay between month creations to avoid rate limiting
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"❌ Failed to create current month sheet {current_month_name}: {e}")
                    await update.message.reply_text(f"❌ Failed to create {current_month_name}: {e}")
                    return
            else:
                logger.info(f"✅ Current month sheet {current_month_name} already exists")
            
            # Check and create next month
            next_month_exists = any(sheet['properties']['title'] == next_month_name 
                                  for sheet in result.get('sheets', []))
            
            if not next_month_exists:
                logger.info(f"🔄 Creating next month sheet: {next_month_name}")
                
                try:
                    # Create new sheet
                    request = {
                        'addSheet': {
                            'properties': {
                                'title': next_month_name,
                                'gridProperties': {
                                    'rowCount': 1000,
                                    'columnCount': 32  # 31 days + name column
                                }
                            }
                        }
                    }
                    
                    sheets_service.service.spreadsheets().batchUpdate(
                        spreadsheetId=sheets_service.spreadsheet_id,
                        body={'requests': [request]}
                    ).execute()
                    
                    # Set up headers and styling
                    headers_success = await sheets_service.setup_monthly_sheet_headers(next_month_name)
                    if not headers_success:
                        logger.error(f"❌ Failed to set up headers for {next_month_name}")
                        await update.message.reply_text(f"❌ Failed to create {next_month_name} - headers setup failed")
                        return
                    
                    await asyncio.sleep(1)
                    await sheets_service.style_monthly_sheet(next_month_name)
                    
                    created_sheets.append(next_month_name)
                    logger.info(f"✅ Created next month sheet: {next_month_name}")
                    
                    # Add delay between month creations to avoid rate limiting
                    await asyncio.sleep(2)
                except Exception as e:
                    logger.error(f"❌ Failed to create next month sheet {next_month_name}: {e}")
                    await update.message.reply_text(f"❌ Failed to create {next_month_name}: {e}")
                    return
            else:
                logger.info(f"✅ Next month sheet {next_month_name} already exists")
            
            # Check and create next next month
            next_next_month_exists = any(sheet['properties']['title'] == next_next_month_name 
                                       for sheet in result.get('sheets', []))
            
            if not next_next_month_exists:
                logger.info(f"🔄 Creating next next month sheet: {next_next_month_name}")
                
                try:
                    # Create new sheet
                    request = {
                        'addSheet': {
                            'properties': {
                                'title': next_next_month_name,
                                'gridProperties': {
                                    'rowCount': 1000,
                                    'columnCount': 32  # 31 days + name column
                                }
                            }
                        }
                    }
                    
                    sheets_service.service.spreadsheets().batchUpdate(
                        spreadsheetId=sheets_service.spreadsheet_id,
                        body={'requests': [request]}
                    ).execute()
                    
                    # Set up headers and styling
                    headers_success = await sheets_service.setup_monthly_sheet_headers(next_next_month_name)
                    if not headers_success:
                        logger.error(f"❌ Failed to set up headers for {next_next_month_name}")
                        await update.message.reply_text(f"❌ Failed to create {next_next_month_name} - headers setup failed")
                        return
                    
                    await asyncio.sleep(1)
                    await sheets_service.style_monthly_sheet(next_next_month_name)
                    
                    created_sheets.append(next_next_month_name)
                    logger.info(f"✅ Created next next month sheet: {next_next_month_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to create next next month sheet {next_next_month_name}: {e}")
                    await update.message.reply_text(f"❌ Failed to create {next_next_month_name}: {e}")
                    return
            else:
                logger.info(f"✅ Next next month sheet {next_next_month_name} already exists")
                
        except Exception as e:
            logger.error(f"❌ Error creating monthly sheets: {e}")
            await update.message.reply_text(f"❌ Error creating monthly sheets: {e}")
            return
        
        # Send success message
        if created_sheets:
            await update.message.reply_text(
                f"✅ Successfully created monthly sheets:\n" +
                f"📅 {', '.join(created_sheets)}\n" +
                f"🎨 Applied styling (light blue names, light green dates)"
            )
        else:
            await update.message.reply_text(
                f"ℹ️ All monthly sheets already exist:\n" +
                f"📅 {current_month_name}, {next_month_name}, and {next_next_month_name}"
            )
            
    except Exception as e:
        logger.error(f"❌ Error in month creation command: {e}")
        await update.message.reply_text(f"❌ Error: {e}")

async def periodic_monthly_check(context: ContextTypes.DEFAULT_TYPE):
    """Periodic task to check and create monthly sheets - runs once per day"""
    # This function is no longer needed as monthly sheet creation is manual
    # await check_and_create_monthly_sheets()
    pass

async def webhook_handler(request):
    """Handle incoming webhook requests from Telegram with improved error handling"""
    try:
        # Add timeout protection
        async with asyncio.timeout(30):  # 30 second timeout
            
            # Get the update from Telegram
            try:
                update_data = await request.json()
            except Exception as e:
                logger.error(f"Failed to parse webhook JSON: {e}")
                return web.Response(text='Invalid JSON', status=400)
            
            # Validate update data
            if not update_data or 'update_id' not in update_data:
                logger.error("Invalid update data received")
                return web.Response(text='Invalid update data', status=400)
            
            # Process the update
            try:
                update = Update.de_json(update_data, request.app['bot'])
                await request.app['application'].process_update(update)
                logger.debug(f"✅ Processed update {update.update_id}")
            except Exception as e:
                logger.error(f"Error processing update {update_data.get('update_id', 'unknown')}: {e}")
                # Don't return error to Telegram to avoid retries
                return web.Response(text='OK')
            
            return web.Response(text='OK')
            
    except asyncio.TimeoutError:
        logger.error("Webhook request timed out after 30 seconds")
        return web.Response(text='Request timeout', status=408)
    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {e}")
        return web.Response(text='Internal server error', status=500)

async def health_check(request):
    """Health check endpoint for Render.com with system metrics"""
    try:
        # Get basic system info
        memory = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        disk = psutil.disk_usage('/')
        
        # Get pending actions count
        global pending_actions
        pending_count = len(pending_actions)
        
        # Get uptime
        uptime = time.time() - psutil.boot_time()
        
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'system': {
                'memory_percent': memory.percent,
                'cpu_percent': cpu,
                'disk_percent': disk.percent,
                'uptime_seconds': int(uptime)
            },
            'bot': {
                'pending_actions': pending_count,
                'webhook_active': True
            }
        }
        
        # Check if system is healthy
        if memory.percent > 90 or cpu > 90 or disk.percent > 90:
            health_data['status'] = 'warning'
        
        if memory.percent > 95 or cpu > 95 or disk.percent > 95:
            health_data['status'] = 'critical'
        
        return web.json_response(health_data)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return web.json_response({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)

async def shutdown_handler(request, shutdown_event):
    """Handle graceful shutdown"""
    try:
        logger.info("🔄 Shutdown request received")
        shutdown_event.set()
        return web.json_response({'status': 'shutdown_initiated'})
    except Exception as e:
        logger.error(f"Shutdown handler error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def main():
    """Main function"""
    # Global shutdown flag
    shutdown_event = asyncio.Event()
    
    try:
        # Load configuration
        config = load_config()
        token = config['bot_token']
        
        # Create application with better connection settings and error handling
        app = Application.builder().token(token).connection_pool_size(1).build()
        
        # Initialize services (lazy loading - no startup API calls)
        sheets_service = GoogleSheetsService(config['spreadsheet_id'])
        location_service = LocationService()
        
        # Add services to context
        app.bot_data['sheets_service'] = sheets_service
        app.bot_data['location_service'] = location_service
        
        logger.info("✅ Services initialized (lazy loading enabled)")
        
        # Add periodic cleanup job (every 15 minutes)
        job_queue = app.job_queue
        if job_queue:
            job_queue.run_repeating(periodic_cleanup, interval=900, first=900)
            logger.info("✅ Periodic cleanup job scheduled")
        
        # Add conversation handler for registration
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start_command)],
            states={
                ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
                ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)]
            },
            fallbacks=[CommandHandler("cancel", cancel_registration)]
        )
        
        # Add admin command to list workers
        app.add_handler(CommandHandler("workers", list_workers_command))

        # Add admin command to show office info
        app.add_handler(CommandHandler("office", office_info_command))

        # Add admin command to create monthly sheets (current + next 2 months)
        app.add_handler(CommandHandler("monthcreation", create_next_two_months_sheets))
        app.add_handler(CommandHandler("attendance", attendance_command))

        # Add message handler for location messages
        app.add_handler(MessageHandler(filters.LOCATION, handle_location_message))
        
        # Add conversation handler for registration flow (MUST come before generic text handler)
        app.add_handler(conv_handler)
        
        # Add message handler for persistent keyboard buttons (GENERIC - comes LAST)
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_persistent_keyboard))
        
        # Initialize the application properly
        await app.initialize()
        
        logger.info("🤖 Starting Working Metropolitan Bot...")
        
        # Get port from environment (Render.com sets this)
        port = int(os.getenv('PORT', 8080))
        
        # Create webhook URL dynamically
        render_app_name = os.getenv('RENDER_APP_NAME', 'metropolitan-bot')
        webhook_url = f"https://{render_app_name}.onrender.com/webhook"
        
        logger.info(f"🚀 Setting up webhook...")
        
        # Set up webhook with optimized retry logic
        webhook_success = False
        max_retries = 2  # Reduced from 3
        retry_delay = 2  # Reduced from 5
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔧 Webhook setup (attempt {attempt + 1}/{max_retries})")
                
                # Use proper async calls
                webhook_result = await app.bot.set_webhook(url=webhook_url)
                
                if webhook_result:
                    logger.info(f"✅ Webhook set successfully")
                    
                    # Quick verification
                    webhook_info = await app.bot.get_webhook_info()
                    if webhook_info.url == webhook_url:
                        logger.info(f"✅ Webhook verified")
                        webhook_success = True
                        break
                    else:
                        raise Exception("Webhook verification failed")
                else:
                    raise Exception("Webhook API returned False")
                    
            except Exception as e:
                logger.error(f"❌ Webhook attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("❌ All webhook attempts failed")
                    break
        
        if not webhook_success:
            logger.error("❌ Failed to set webhook after all retries")
            logger.info("🔄 Falling back to polling mode for local development")
            app.run_polling(timeout=30, drop_pending_updates=True)
            return
        
        # Create aiohttp web application
        web_app = web.Application()
        web_app['bot'] = app.bot
        web_app['application'] = app
        web_app['shutdown_event'] = shutdown_event
        
        # Add routes
        web_app.router.add_post('/webhook', webhook_handler)
        web_app.router.add_get('/health', health_check)
        web_app.router.add_get('/', health_check)
        web_app.router.add_post('/shutdown', lambda r: shutdown_handler(r, shutdown_event))
        
        # Start the web server
        logger.info(f"🚀 Starting web server...")
        
        try:
            # Use runner to avoid event loop conflicts
            runner = web.AppRunner(web_app)
            await runner.setup()
            site = web.TCPSite(runner, '0.0.0.0', port)
            await site.start()
            
            logger.info(f"✅ Bot ready! Webhook: {webhook_url}")
            
            # Keep the server running with proper shutdown handling
            while not shutdown_event.is_set():
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    # Check for shutdown signal every second
                    continue
                
            logger.info("🔄 Shutdown signal received, cleaning up...")
            
        except Exception as e:
            logger.error(f"❌ Failed to start web server: {e}")
            # Fallback to polling
            logger.info("🔄 Falling back to polling mode")
            app.run_polling(timeout=30, drop_pending_updates=True)
                    
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
    finally:
        # Cleanup on shutdown
        try:
            await cleanup_expired_actions()
            logger.info("🧹 Final cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during final cleanup: {e}")

async def attendance_command(update: Update, context):
    """Admin command to show today's attendance overview"""
    try:
        user = update.effective_user
        
        # Check if user is admin (you)
        if user.username != "DenisZgl" and user.id != 123456789:  # Replace with your actual Telegram ID
            await update.message.reply_text("❌ Access denied. Admin only.")
            return
        
        # Get services from context
        sheets_service = context.bot_data.get('sheets_service')
        if not sheets_service:
            await update.message.reply_text("❌ Σφάλμα: Δεν είναι διαθέσιμη η υπηρεσία Google Sheets.")
            return
        
        # Get current date in Greece timezone (GMT+3)
        import pytz
        greece_tz = pytz.timezone('Europe/Athens')
        today = datetime.now(greece_tz)
        current_date = today.strftime("%-m/%-d/%Y") if today.strftime("%-m/%-d/%Y") else today.strftime("%m/%d/%Y")
        today_name = today.strftime("%A")  # Monday, Tuesday, etc.
        
        # Get current week schedule to see who should work today
        logger.info(f"🔍 DEBUG STEP 3: Getting active week sheet for date: {current_date}")
        current_week_sheet = sheets_service.get_active_week_sheet(current_date)
        logger.info(f"🔍 DEBUG STEP 3: Active week sheet returned: {current_week_sheet}")
        
        # Read schedule sheet to get today's column and who should work
        try:
            logger.info(f"🔍 DEBUG STEP 4: Reading schedule sheet: {current_week_sheet}")
            schedule_result = sheets_service.service.spreadsheets().values().get(
                spreadsheetId=sheets_service.spreadsheet_id,
                range=f'{current_week_sheet}!A:Z'
            ).execute()
            
            schedule_values = schedule_result.get('values', [])
            logger.info(f"🔍 DEBUG STEP 4: Schedule sheet rows returned: {len(schedule_values)}")
            if not schedule_values or len(schedule_values) < 4:
                await update.message.reply_text("❌ Could not read schedule data.")
                return
            
            # Find today's column using Row 3 dates (much simpler and more reliable)
            today_col = None
            
            # Row 3 contains the actual dates
            if len(schedule_values) > 2:  # Make sure Row 3 exists
                row_3 = schedule_values[2]  # Row 3 (index 2)
                logger.info(f"🔍 DEBUG STEP 5: Row 3 (dates) content: {row_3}")
                for col_idx, cell in enumerate(row_3[1:8]):  # Columns B-H
                    if str(cell).strip():
                        try:
                            # Parse the date from Row 3
                            cell_date = datetime.strptime(str(cell), "%m/%d/%Y")
                            logger.info(f"🔍 DEBUG STEP 5: Parsed date from cell {col_idx+1}: {cell_date.date()}")
                            if cell_date.date() == today.date():
                                today_col = col_idx + 1  # +1 because we skipped column A
                                logger.info(f"🔍 DEBUG STEP 5: Found today's column: {col_idx + 1} for date {cell_date.date()}")
                                break
                        except Exception as e:
                            logger.warning(f"⚠️ Could not parse date from cell: {cell} - {e}")
                            continue
            
            if today_col is None:
                await update.message.reply_text("❌ Could not determine today's schedule column.")
                return
            
            # Get who should work today and their schedules
            logger.info(f"🔍 DEBUG STEP 6: Looking for employees in column {today_col}")
            today_schedules = {}
            for row in schedule_values[4:]:  # Start from row 5 (index 4) to get Αγγελος
                if len(row) > 0 and row[0] and today_col < len(row):
                    employee_name = row[0]
                    schedule = row[today_col] if row[today_col] else ""
                    logger.info(f"🔍 DEBUG STEP 6: Employee {employee_name} has schedule: '{schedule}'")
                    if schedule and schedule.strip() and schedule.strip().upper() not in ['REST', 'OFF', '']:
                        today_schedules[employee_name] = schedule
                        logger.info(f"🔍 DEBUG STEP 6: Added {employee_name} to today's schedules")
            
            logger.info(f"🔍 DEBUG STEP 6: Total employees scheduled today: {len(today_schedules)}")
            logger.info(f"🔍 DEBUG STEP 6: Today's schedules: {today_schedules}")
            
            if not today_schedules:
                await update.message.reply_text("📅 No one scheduled to work today.")
                return
            
            # Now read monthly sheet to get today's attendance
            logger.info(f"🔍 DEBUG STEP 7: Getting monthly sheet name")
            monthly_sheet = sheets_service.get_current_month_sheet_name()
            logger.info(f"🔍 DEBUG STEP 7: Monthly sheet name: {monthly_sheet}")
            
            logger.info(f"🔍 DEBUG STEP 7: Getting today's column letter")
            today_column_letter = sheets_service.get_today_column_letter()
            logger.info(f"🔍 DEBUG STEP 7: Today's column letter: {today_column_letter}")
            
            try:
                logger.info(f"🔍 DEBUG STEP 7: Reading monthly sheet range: {monthly_sheet}!A:Z (full range to find all employees)")
                attendance_result = sheets_service.service.spreadsheets().values().get(
                    spreadsheetId=sheets_service.spreadsheet_id,
                    range=f'{monthly_sheet}!A:Z'
                ).execute()
                
                attendance_values = attendance_result.get('values', [])
                logger.info(f"🔍 DEBUG STEP 8: Monthly sheet rows returned: {len(attendance_values)}")
                if not attendance_values:
                    await update.message.reply_text("❌ Could not read attendance data.")
                    return
                
                # Find today's column in monthly sheet
                logger.info(f"🔍 DEBUG STEP 8: Row 1 (dates) content: {attendance_values[0] if attendance_values else 'EMPTY'}")
                
                # Debug Row 2 content (employee data)
                if len(attendance_values) > 1:
                    logger.info(f"🔍 DEBUG STEP 8: Row 2 (first employee) content: {attendance_values[1]}")
                    logger.info(f"🔍 DEBUG STEP 8: Row 2 length: {len(attendance_values[1])}")
                else:
                    logger.warning(f"🔍 DEBUG STEP 8: No Row 2 found - only {len(attendance_values)} rows")
                
                # Debug all rows in monthly sheet
                logger.info(f"🔍 DEBUG STEP 8: All monthly sheet rows:")
                for row_idx, row in enumerate(attendance_values):
                    logger.info(f"🔍 DEBUG STEP 8: Row {row_idx}: {row}")
                
                today_monthly_col = None
                for col_idx, cell in enumerate(attendance_values[0]):  # Row 1 has dates
                    if str(cell).strip():
                        try:
                            # Parse date format (DD/MM)
                            if '/' in str(cell):
                                day, month = str(cell).split('/')
                                logger.info(f"🔍 DEBUG STEP 8: Parsed date from cell {col_idx}: day={day}, month={month}")
                                if int(day) == today.day and int(month) == today.month:
                                    today_monthly_col = col_idx
                                    logger.info(f"🔍 DEBUG STEP 8: Found today's column: {col_idx} for date {day}/{month}")
                                    break
                        except Exception as e:
                            logger.warning(f"🔍 DEBUG STEP 8: Error parsing cell {col_idx}: {cell} - {e}")
                            pass
                
                logger.info(f"🔍 DEBUG STEP 8: Today's monthly column: {today_monthly_col}")
                if today_monthly_col is None:
                    await update.message.reply_text("❌ Could not find today's column in monthly sheet.")
                    return
                
                # Get attendance status for each scheduled employee
                logger.info(f"🔍 DEBUG STEP 9: Starting attendance check for {len(today_schedules)} employees")
                attendance_report = {
                    'checked_in': [],
                    'not_checked_in': []
                }
                
                for employee_name in today_schedules.keys():
                    logger.info(f"🔍 DEBUG STEP 9: Checking attendance for {employee_name}")
                    # Find employee row in monthly sheet
                    employee_found = False
                    for row_idx, row in enumerate(attendance_values[1:]):  # Skip header row (0), start from row 1
                        if len(row) > 0 and row[0] == employee_name:
                            employee_found = True
                            logger.info(f"🔍 DEBUG STEP 9: Found {employee_name} at row {row_idx+1}")
                            logger.info(f"🔍 DEBUG STEP 9: Row content: {row}")
                            logger.info(f"🔍 DEBUG STEP 9: Looking in column {today_monthly_col}, row length: {len(row)}")
                            
                            if today_monthly_col < len(row) and row[today_monthly_col]:
                                full_check_in_data = row[today_monthly_col]
                                schedule_time = today_schedules[employee_name]
                                
                                # Extract check-in time from full schedule format (e.g., "09:00-17:00" -> "09:00")
                                if '-' in str(full_check_in_data):
                                    check_in_time = str(full_check_in_data).split('-')[0]
                                    logger.info(f"🔍 DEBUG STEP 9: {employee_name} CHECKED IN at {check_in_time} (extracted from {full_check_in_data})")
                                else:
                                    check_in_time = str(full_check_in_data)
                                    logger.info(f"🔍 DEBUG STEP 9: {employee_name} CHECKED IN at {check_in_time}")
                                
                                # Determine if late or on time
                                try:
                                    logger.info(f"🔍 DEBUG STEP 9: Processing check-in for {employee_name}: time={check_in_time}, schedule={schedule_time}")
                                    
                                    # Parse check-in time (format: HH:MM)
                                    if ':' in str(check_in_time):
                                        check_hour, check_minute = map(int, str(check_in_time).split(':'))
                                        check_in_minutes = check_hour * 60 + check_minute
                                        logger.info(f"🔍 DEBUG STEP 9: Check-in time parsed: {check_hour}:{check_minute} = {check_in_minutes} minutes")
                                        
                                        # Parse schedule start time (format: HH:MM-HH:MM)
                                        if '-' in schedule_time:
                                            schedule_start = schedule_time.split('-')[0]
                                            if ':' in schedule_start:
                                                sched_hour, sched_minute = map(int, schedule_start.split(':'))
                                                schedule_minutes = sched_hour * 60 + sched_minute
                                                logger.info(f"🔍 DEBUG STEP 9: Schedule start parsed: {sched_hour}:{sched_minute} = {schedule_minutes} minutes")
                                                
                                                # Determine status
                                                grace_period = 5
                                                if check_in_minutes <= schedule_minutes + grace_period:
                                                    status = "On time"
                                                    logger.info(f"🔍 DEBUG STEP 9: {employee_name} is ON TIME (check-in: {check_in_minutes}, schedule: {schedule_minutes}, grace: {grace_period})")
                                                else:
                                                    status = "Late"
                                                    logger.info(f"🔍 DEBUG STEP 9: {employee_name} is LATE (check-in: {check_in_minutes}, schedule: {schedule_minutes}, grace: {grace_period})")
                                                
                                                attendance_report['checked_in'].append({
                                                    'name': employee_name,
                                                    'time': check_in_time,
                                                    'status': status,
                                                    'schedule': schedule_time
                                                })
                                                logger.info(f"🔍 DEBUG STEP 9: Added {employee_name} to checked_in with status: {status}")
                                            else:
                                                logger.warning(f"🔍 DEBUG STEP 9: Could not parse schedule start time: {schedule_start}")
                                                attendance_report['checked_in'].append({
                                                    'name': employee_name,
                                                    'time': check_in_time,
                                                    'status': "Unknown",
                                                    'schedule': schedule_time
                                                })
                                        else:
                                            logger.warning(f"🔍 DEBUG STEP 9: Schedule time format invalid: {schedule_time}")
                                            attendance_report['checked_in'].append({
                                                'name': employee_name,
                                                'time': check_in_time,
                                                'status': "Unknown",
                                                'schedule': schedule_time
                                            })
                                    else:
                                        logger.warning(f"🔍 DEBUG STEP 9: Check-in time format invalid: {check_in_time}")
                                        attendance_report['checked_in'].append({
                                            'name': employee_name,
                                            'time': check_in_time,
                                            'status': "Unknown",
                                            'schedule': schedule_time
                                        })
                                except Exception as e:
                                    logger.warning(f"🔍 DEBUG STEP 9: Error processing check-in for {employee_name}: {e}")
                                    attendance_report['checked_in'].append({
                                        'name': employee_name,
                                        'time': check_in_time,
                                        'status': "Unknown",
                                        'schedule': schedule_time
                                    })
                            else:
                                # Not checked in
                                logger.info(f"🔍 DEBUG STEP 9: {employee_name} NOT CHECKED IN (column {today_monthly_col} empty or out of range)")
                                attendance_report['not_checked_in'].append({
                                    'name': employee_name,
                                    'schedule': today_schedules[employee_name]
                                })
                            break
                    
                    if not employee_found:
                        logger.info(f"🔍 DEBUG STEP 9: {employee_name} NOT FOUND in monthly sheet")
                        attendance_report['not_checked_in'].append({
                            'name': employee_name,
                            'schedule': today_schedules[employee_name]
                        })
                
                logger.info(f"🔍 DEBUG STEP 9: Final attendance report: {attendance_report}")
                
                # Generate the new redesigned report
                report = f"📊 **TODAY'S ATTENDANCE** ({today.strftime('%d/%m/%Y')})\n\n"
                
                # Separate employees by status
                on_time_employees = []
                late_employees = []
                not_checked_in_employees = []
                
                # Categorize checked-in employees
                for employee in attendance_report['checked_in']:
                    if employee['status'] == "On time":
                        on_time_employees.append(employee)
                    elif employee['status'] == "Late":
                        late_employees.append(employee)
                    else:
                        # Unknown status - treat as late for safety
                        late_employees.append(employee)
                
                # Add not checked in employees
                not_checked_in_employees = attendance_report['not_checked_in']
                
                # 1. GREEN: Checked in (On time)
                if on_time_employees:
                    report += "🟢 **CHECKED IN (ON TIME):**\n"
                    for employee in on_time_employees:
                        report += f"• {employee['name']} - {employee['time']}\n"
                    report += "\n"
                
                # 2. YELLOW: Checked in (Late)
                if late_employees:
                    report += "🟡 **CHECKED IN (LATE):**\n"
                    for employee in late_employees:
                        report += f"• {employee['name']} - {employee['time']}\n"
                    report += "\n"
                
                # 3. RED: Didn't check in
                if not_checked_in_employees:
                    report += "🔴 **DIDN'T CHECK IN:**\n"
                    for employee in not_checked_in_employees:
                        report += f"• {employee['name']}\n"
                    report += "\n"
                
                # Add summary
                total_scheduled = len(today_schedules)
                total_checked_in = len(attendance_report['checked_in'])
                total_missing = len(attendance_report['not_checked_in'])
                
                report += f"📈 **SUMMARY:**\n"
                report += f"• Total Scheduled: {total_scheduled}\n"
                report += f"• Checked In: {total_checked_in}\n"
                report += f"• Missing: {total_missing}"
                
                await update.message.reply_text(report, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Error reading monthly attendance: {e}")
                await update.message.reply_text("❌ Error reading attendance data.")
                
        except Exception as e:
            logger.error(f"Error reading schedule: {e}")
            await update.message.reply_text("❌ Error reading schedule data.")
            
    except Exception as e:
        logger.error(f"Error in attendance command: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά την ανάκτηση της αναφοράς.")

if __name__ == "__main__":
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Set up signal handling for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"🔄 Received signal {signum}, initiating graceful shutdown...")
        # The shutdown will be handled by the shutdown_event in main()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the bot with proper async handling and error recovery
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🔄 Keyboard interrupt received, shutting down gracefully...")
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        # Attempt to clean up
        try:
            cleanup_expired_actions()
        except:
            pass
        raise
