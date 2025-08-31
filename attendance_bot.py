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

async def handle_button_callback(update: Update, context):
    """Handle button callbacks - NOT USED ANYMORE (persistent keyboard only)"""
    # This function is no longer used - all actions are handled by persistent keyboard
    pass

async def handle_checkin(query, worker_name: str):
    """Handle worker check-in"""
    try:
        # Create location request keyboard with back button
        location_keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("📍 Στείλε την τοποθεσία μου", request_location=True)],
            [KeyboardButton("🏠 Πίσω στο μενού")]
        ], resize_keyboard=True, one_time_keyboard=True)
        
        # Ask for location with automated button
        location_message = f"""
📍 **Check-in για {worker_name}**

**Για να κάνετε check-in, πατήστε το κουμπί παρακάτω:**

**📍 Στείλε την τοποθεσία μου**

**⚠️ Προσοχή:** Πρέπει να είστε μέσα σε 200m από το γραφείο!

**🏠 Ή πατήστε "Πίσω στο μενού" για να ακυρώσετε**
        """
        
        # Store check-in request in global pending_actions
        user_id = query.from_user.id
        pending_actions[user_id] = {
            'worker_name': worker_name,
            'action': 'checkin',
            'timestamp': datetime.now()
        }
        
        # Show location request message with automated button
        await query.edit_message_text(location_message, parse_mode='Markdown')
        
        # Send the location request keyboard
        await query.message.reply_text(
            "**Πατήστε το κουμπί για να στείλετε την τοποθεσία σας:**",
            reply_markup=location_keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error during check-in: {e}")
        await query.edit_message_text("❌ Σφάλμα κατά το check-in. Παρακαλώ δοκιμάστε ξανά.")

async def handle_checkout(query, worker_name: str):
    """Handle worker check-out"""
    try:
        # Create location request keyboard with back button
        location_keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("📍 Στείλε την τοποθεσία μου", request_location=True)],
            [KeyboardButton("🏠 Πίσω στο μενού")]
        ], resize_keyboard=True, one_time_keyboard=True)
        
        # Ask for location with automated button
        location_message = f"""
🚪 **Check-out για {worker_name}**

**Για να κάνετε check-out, πατήστε το κουμπί παρακάτω:**

**📍 Στείλε την τοποθεσία μου**

**⚠️ Προσοχή:** Πρέπει να είστε μέσα σε 200m από το γραφείο!

**🏠 Ή πατήστε "Πίσω στο μενού" για να ακυρώσετε**
        """
        
        # Store check-out request in global pending_actions
        user_id = query.from_user.id
        pending_actions[user_id] = {
            'worker_name': worker_name,
            'action': 'checkout',
            'timestamp': datetime.now()
        }
        
        # Show location request message with automated button
        await query.edit_message_text(location_message, parse_mode='Markdown')
        
        # Send the location request keyboard
        await query.message.reply_text(
            "**Πατήστε το κουμπί για να στείλετε την τοποθεσία σας:**",
            reply_markup=location_keyboard,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error during check-out: {e}")
        await query.edit_message_text("❌ Σφάλμα κατά το check-out. Παρακαλώ δοκιμάστε ξανά.")

async def handle_schedule_request(query, worker_name: str):
    """Handle weekly schedule request"""
    try:
        from datetime import datetime, timedelta
        
        # Get current date and format for sheets
        today = datetime.now()
        # Fix date format for macOS compatibility
        try:
            current_date = today.strftime("%-m/%-d/%Y")  # Format: 7/18/2025
        except ValueError:
            current_date = today.strftime("%m/%d/%Y")  # Format: 07/18/2025
        
        # Get worker's telegram ID to find their schedule
        user = query.from_user
        existing_worker = await sheets_service.find_worker_by_telegram_id(user.id)
        
        if not existing_worker:
            await query.edit_message_text("❌ Δεν είστε εγγεγραμμένος στο σύστημα.")
            return
        
        # Get current week schedule
        current_week_schedule = await sheets_service.get_weekly_schedule(str(user.id), current_date)
        
        # Get next week schedule using rotation logic
        current_week_sheet = sheets_service.get_active_week_sheet(current_date)
        next_week_sheet = sheets_service.get_next_week_sheet(current_week_sheet)
        
        # Try to read from next week's sheet directly
        try:
            result = sheets_service.service.spreadsheets().values().get(
                spreadsheetId=sheets_service.spreadsheet_id,
                range=f'{next_week_sheet}!A:Z'
            ).execute()
            
            values = result.get('values', [])
            if values:
                # Parse next week schedule manually
                next_week_schedule = {}
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                # Find the employee row by name
                worker_name = existing_worker['name']
                for row in values:
                    if len(row) > 0 and row[0] == worker_name:
                        for i, day in enumerate(days):
                            day_col = i + 1
                            if day_col < len(row):
                                schedule_text = row[day_col] if row[day_col] else ""
                                next_week_schedule[day] = schedule_text
                        break
            else:
                next_week_schedule = None
                
        except Exception as e:
            logger.warning(f"⚠️ Could not read next week schedule: {e}")
            next_week_schedule = None
        
        # Create appropriate keyboard
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("✅ Check In"), KeyboardButton("🚪 Check Out")],
            [KeyboardButton("📅 My Schedule"), KeyboardButton("📞 Contact")]
        ], resize_keyboard=True)
        
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
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=keyboard)
        
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
        
        if not pending_action:
            # No pending action, ignore location
            return
        
        # Get location from message
        if not update.message.location:
            await update.message.reply_text("❌ Παρακαλώ στείλτε την τοποθεσία σας (location), όχι κείμενο.")
            # Return to main menu even for invalid location
            await return_to_main_menu(update, context, user_id)
            return
        
        location = update.message.location
        latitude = location.latitude
        longitude = location.longitude
        
        # Verify location is within office zone
        location_result = location_service.is_within_office_zone(latitude, longitude)
        
        if not location_result['is_within']:
            # Location outside zone - show error and return to main menu
            location_msg = location_service.format_location_message(location_result)
            await update.message.reply_text(location_msg, parse_mode='Markdown')
            
            # IMPORTANT: Return to main menu after failed location check
            await return_to_main_menu(update, context, user_id)
            return
        
        # Location verified, proceed with action
        if pending_action['action'] == 'checkin':
            await complete_checkin(update, context, pending_action, location_result)
        elif pending_action['action'] == 'checkout':
            await complete_checkout(update, context, pending_action, location_result)
        
        # Clear pending action
        pending_actions.pop(user_id, None)
        
    except Exception as e:
        logger.error(f"Error handling location message: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά την επεξεργασία της τοποθεσίας.")
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
        menu_msg = f"""
🏠 **Επιστροφή στο κύριο μενού**

**Καλώς ήρθατε, {worker_name}!**

**Χρησιμοποιήστε τα κουμπιά κάτω από το πεδίο εισαγωγής:**
        """
        
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
            
    except Exception as e:
        logger.error(f"Error completing check-in: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά το check-in. Παρακαλώ δοκιμάστε ξανά.")

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
        else:
            await update.message.reply_text("❌ Δεν μπορείτε να κάνετε check-out χωρίς να έχετε κάνει check-in.")
            
    except Exception as e:
        logger.error(f"Error completing check-out: {e}")
        await update.message.reply_text("❌ Σφάλμα κατά το check-out. Παρακαλώ δοκιμάστε ξανά.")

async def handle_persistent_keyboard(update: Update, context):
    """Handle persistent keyboard button presses"""
    try:
        user = update.effective_user
        text = update.message.text
        
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
            await handle_persistent_checkin(update, context, worker_name)
            
        elif text == "🚪 Check Out":
            # Handle check-out via persistent keyboard
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
                await update.message.reply_text(
                    f"⏳ **Check-in σε εξέλιξη για {worker_name}**\n\n"
                    "**🔄 Δεν χρειάζεται να πατήσετε ξανά το κουμπί Check In!**\n\n"
                    "**📱 Απλά στείλτε την τοποθεσία σας** με το κουμπί που ήδη εμφανίστηκε.\n\n"
                    "**⏰ Περιμένετε την επεξεργασία...**",
                    parse_mode='Markdown'
                )
                return
            elif existing_action['action'] == 'checkout':
                await update.message.reply_text(
                    f"⚠️ **Έχετε ήδη ένα check-out σε εξέλιξη**\n\n"
                    "**🔄 Περιμένετε να ολοκληρωθεί το check-out πριν κάνετε check-in.**\n\n"
                    "**📱 Χρησιμοποιήστε το κουμπί που ήδη εμφανίστηκε.**",
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
        
        # Show location request message with automated button
        await update.message.reply_text(
            f"📍 **Check-in για {worker_name}**\n\n"
            "**Για να κάνετε check-in, πατήστε το κουμπί παρακάτω:**\n\n"
            "**📍 Στείλε την τοποθεσία μου**\n\n"
            "**⚠️ Προσοχή:** Πρέπει να είστε μέσα σε 200m από το γραφείο!\n\n"
            "**🔄 ΜΗΝ πατάτε ξανά το κουμπί Check In - χρησιμοποιήστε μόνο το κουμπί τοποθεσίας!**",
            parse_mode='Markdown'
        )
        
        # Send the location request keyboard
        await update.message.reply_text(
            "**Πατήστε το κουμπί για να στείλετε την τοποθεσία σας:**",
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
                await update.message.reply_text(
                    f"⏳ **Check-out σε εξέλιξη για {worker_name}**\n\n"
                    "**🔄 Δεν χρειάζεται να πατήσετε ξανά το κουμπί Check Out!**\n\n"
                    "**📱 Απλά στείλτε την τοποθεσία σας** με το κουμπί που ήδη εμφανίστηκε.\n\n"
                    "**⏰ Περιμένετε την επεξεργασία...**",
                    parse_mode='Markdown'
                )
                return
            elif existing_action['action'] == 'checkin':
                await update.message.reply_text(
                    f"⚠️ **Έχετε ήδη ένα check-in σε εξέλιξη**\n\n"
                    "**🔄 Περιμένετε να ολοκληρωθεί το check-in πριν κάνετε check-out.**\n\n"
                    "**📱 Χρησιμοποιήστε το κουμπί που ήδη εμφανίστηκε.**",
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
        
        # Show location request message with automated button
        await update.message.reply_text(
            f"🚪 **Check-out για {worker_name}**\n\n"
            "**Για να κάνετε check-out, πατήστε το κουμπί παρακάτω:**\n\n"
            "**📍 Στείλε την τοποθεσία μου**\n\n"
            "**⚠️ Προσοχή:** Πρέπει να είστε μέσα σε 200m από το γραφείο!\n\n"
            "**🔄 ΜΗΝ πατάτε ξανά το κουμπί Check Out - χρησιμοποιήστε μόνο το κουμπί τοποθεσίας!**",
            parse_mode='Markdown'
        )
        
        # Send the location request keyboard
        await update.message.reply_text(
            "**Πατήστε το κουμπί για να στείλετε την τοποθεσία σας:**",
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
        
        # Get current date and format for sheets
        today = datetime.now()
        # Fix date format for macOS compatibility
        try:
            current_date = today.strftime("%-m/%-d/%Y")  # Format: 7/18/2025
        except ValueError:
            current_date = today.strftime("%m/%d/%Y")  # Format: 07/18/2025
        
        # Get worker's telegram ID to find their schedule
        user = update.effective_user
        existing_worker = await sheets_service.find_worker_by_telegram_id(user.id)
        
        if not existing_worker:
            await update.message.reply_text("❌ Δεν είστε εγγεγραμμένος στο σύστημα.")
            return
        
        # Get current week schedule
        current_week_schedule = await sheets_service.get_weekly_schedule(str(user.id), current_date)
        
        # Get next week schedule using rotation logic
        current_week_sheet = sheets_service.get_active_week_sheet(current_date)
        next_week_sheet = sheets_service.get_next_week_sheet(current_week_sheet)
        
        # Try to read from next week's sheet directly
        try:
            result = sheets_service.service.spreadsheets().values().get(
                spreadsheetId=sheets_service.spreadsheet_id,
                range=f'{next_week_sheet}!A:Z'
            ).execute()
            
            values = result.get('values', [])
            if values:
                # Parse next week schedule manually
                next_week_schedule = {}
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                # Find the employee row by name
                worker_name = existing_worker['name']
                for row in values:
                    if len(row) > 0 and row[0] == worker_name:
                        for i, day in enumerate(days):
                            day_col = i + 1
                            if day_col < len(row):
                                schedule_text = row[day_col] if row[day_col] else ""
                                next_week_schedule[day] = schedule_text
                        break
            else:
                next_week_schedule = None
                
        except Exception as e:
            logger.warning(f"⚠️ Could not read next week schedule: {e}")
            next_week_schedule = None
        
        # Create appropriate keyboard
        keyboard = ReplyKeyboardMarkup([
            [KeyboardButton("✅ Check In"), KeyboardButton("🚪 Check Out")],
            [KeyboardButton("📅 My Schedule"), KeyboardButton("📞 Contact")]
        ], resize_keyboard=True)
        
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
        
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=keyboard)
        
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
    """Handle incoming webhook requests from Telegram"""
    try:
        # Get the update from Telegram
        update_data = await request.json()
        update = Update.de_json(update_data, request.app['bot'])
        
        # Process the update
        await request.app['application'].process_update(update)
        
        return web.Response(text='OK')
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return web.Response(text='Error', status=500)

async def health_check(request):
    """Health check endpoint for Render.com"""
    return web.Response(text='Bot is running! 🤖')

def main():
    """Main function"""
    try:
        # Load configuration
        config = load_config()
        token = config['bot_token']
        
        # Create application with better connection settings
        app = Application.builder().token(token).connection_pool_size(1).build()
        
        # Initialize services
        sheets_service = GoogleSheetsService(config['spreadsheet_id'])
        location_service = LocationService()
        
        # Add services to context
        app.bot_data['sheets_service'] = sheets_service
        app.bot_data['location_service'] = location_service
        
        # Add conversation handler for registration
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start_command)],
            states={
                ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
                ASKING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone)]
            },
            fallbacks=[CommandHandler("cancel", cancel_registration)]
        )
        
        app.add_handler(conv_handler)
        
        # Add admin command to list workers
        app.add_handler(CommandHandler("workers", list_workers_command))

        # Add admin command to show office info
        app.add_handler(CommandHandler("office", office_info_command))

        # Add admin command to create monthly sheets (current + next 2 months)
        app.add_handler(CommandHandler("monthcreation", create_next_two_months_sheets))

        # Add message handler for location messages
        app.add_handler(MessageHandler(filters.LOCATION, handle_location_message))
        
        # Add message handler for persistent keyboard buttons
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_persistent_keyboard))
        
        logger.info("🤖 Starting Working Metropolitan Bot with Google Sheets and Attendance Buttons...")
        
        # Get port from environment (Render.com sets this)
        port = int(os.getenv('PORT', 8080))
        
        # Create webhook URL dynamically
        render_app_name = os.getenv('RENDER_APP_NAME', 'metropolitan-bot')
        webhook_url = f"https://{render_app_name}.onrender.com/webhook"
        
        logger.info(f"🚀 Attempting to set webhook to: {webhook_url}")
        
        # Set up webhook
        try:
            webhook_result = await app.bot.set_webhook(url=webhook_url)
            if webhook_result:
                logger.info(f"✅ Webhook set successfully to: {webhook_url}")
            else:
                logger.error(f"❌ Webhook setting failed - API returned False")
                raise Exception("Webhook API returned False")
                
        except Exception as e:
            logger.error(f"❌ Failed to set webhook: {e}")
            logger.info("🔄 Falling back to polling mode for local development")
            app.run_polling(timeout=30, drop_pending_updates=True)
            return
        
        # Create aiohttp web application
        web_app = web.Application()
        web_app['bot'] = app.bot
        web_app['application'] = app
        
        # Add routes
        web_app.router.add_post('/webhook', webhook_handler)
        web_app.router.add_get('/health', health_check)
        web_app.router.add_get('/', health_check)
        
        # Start the web server
        logger.info(f"🚀 Starting web server on port {port}")
        logger.info(f"🌐 Webhook endpoint: {webhook_url}")
        logger.info(f"🏥 Health check: http://0.0.0.0:{port}/health")
        
        try:
            web.run_app(web_app, host='0.0.0.0', port=port)
        except Exception as e:
            logger.error(f"❌ Failed to start web server: {e}")
            # Fallback to polling
            logger.info("🔄 Falling back to polling mode")
            app.run_polling(timeout=30, drop_pending_updates=True)
                    
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Run the bot
    main()
