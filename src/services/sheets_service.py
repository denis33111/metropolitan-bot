#!/usr/bin/env python3
"""
📊 GOOGLE SHEETS SERVICE
Handles Google Sheets operations for worker data and monthly attendance
"""

import logging
import asyncio
from typing import Optional, Dict, List
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleSheetsService:
    """Service for Google Sheets operations"""
    
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        self.setup_credentials()
    
    def setup_credentials(self):
        """Set up Google Sheets API credentials"""
        try:
            # First try environment variable (for Render.com deployment)
            import base64
            import json
            
            # Check for base64 encoded credentials in environment
            creds_base64 = os.getenv('GOOGLE_CREDENTIALS_JSON')
            if creds_base64:
                try:
                    # Decode base64 credentials
                    creds_json = base64.b64decode(creds_base64).decode('utf-8')
                    creds_data = json.loads(creds_json)
                    
                    # Use decoded credentials
                    scopes = ['https://www.googleapis.com/auth/spreadsheets']
                    credentials = Credentials.from_service_account_info(creds_data, scopes=scopes)
                    self.service = build('sheets', 'v4', credentials=credentials)
                    logger.info("✅ Google Sheets API connected with environment credentials")
                    return
                except Exception as e:
                    logger.warning(f"⚠️ Failed to decode environment credentials: {e}")
            
            # Fallback to credentials file (for local development)
            creds_file = 'credentials.json'
            
            if os.path.exists(creds_file):
                # Use service account credentials file
                scopes = ['https://www.googleapis.com/auth/spreadsheets']
                credentials = Credentials.from_service_account_file(creds_file, scopes=scopes)
                self.service = build('sheets', 'v4', credentials=credentials)
                logger.info("✅ Google Sheets API connected with service account file")
            else:
                # No credentials found
                logger.warning("⚠️ No credentials found - using temporary storage")
                self.service = None
                
        except Exception as e:
            logger.error(f"❌ Error setting up Google Sheets: {e}")
            self.service = None
    
    def get_current_month_sheet_name(self) -> str:
        """Get current month sheet name in format MM_YYYY"""
        now = datetime.now()
        return f"{now.month:02d}_{now.year}"
    
    def get_today_column_letter(self) -> str:
        """Get today's column letter (B=1st, C=2nd, etc.)"""
        day = datetime.now().day
        # Column A is names, so day 1 = column B, day 2 = column C, etc.
        # Handle days beyond 26 (Z) by using AA, AB, AC, etc.
        if day <= 26:
            return chr(ord('A') + day)
        else:
            # For days 27-31, use AA, AB, AC, AD, AE
            first_letter = 'A'
            second_letter = chr(ord('A') + (day - 26))
            return first_letter + second_letter
    
    async def ensure_monthly_sheet_exists(self) -> bool:
        """Ensure current month's sheet exists, create if needed"""
        if not self.service:
            return False
            
        try:
            sheet_name = self.get_current_month_sheet_name()
            
            # Check if sheet exists
            try:
                result = self.service.spreadsheets().get(
                    spreadsheetId=self.spreadsheet_id
                ).execute()
                
                sheet_exists = any(sheet['properties']['title'] == sheet_name 
                                 for sheet in result.get('sheets', []))
                
                if sheet_exists:
                    logger.info(f"✅ Monthly sheet {sheet_name} already exists")
                    return True
                    
            except Exception as e:
                logger.error(f"❌ Error checking sheet existence: {e}")
                return False
            
            # Create new sheet if it doesn't exist
            logger.info(f"🔄 Creating new monthly sheet: {sheet_name}")
            
            # Get the first sheet to use as template
            first_sheet = result['sheets'][0]
            sheet_id = first_sheet['properties']['sheetId']
            
            # Create new sheet
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 32  # 31 days + name column
                        }
                    }
                }
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': [request]}
            ).execute()
            
            # Set up headers COMPLETELY before returning
            await self.setup_monthly_sheet_headers(sheet_name)
            
            # Wait a moment to ensure headers are fully set
            import asyncio
            await asyncio.sleep(1)
            
            # Style the sheet with colors and formatting
            await self.style_monthly_sheet(sheet_name)
            
            logger.info(f"✅ Created new monthly sheet: {sheet_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error creating monthly sheet: {e}")
            return False
    
    async def create_monthly_sheet(self, sheet_name: str):
        """Create new monthly attendance sheet"""
        try:
            # Add new sheet
            request = {
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': 1000,
                            'columnCount': 32  # 31 days + name column
                        }
                    }
                }
            }
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': [request]}
            ).execute()
            
            # Set up headers
            await self.setup_monthly_sheet_headers(sheet_name)
            
            logger.info(f"✅ Created new monthly sheet: {sheet_name}")
            
        except Exception as e:
            logger.error(f"❌ Error creating monthly sheet: {e}")
    
    async def setup_monthly_sheet_headers(self, sheet_name: str):
        """Set up headers for monthly attendance sheet"""
        try:
            # Create date headers for the month
            headers = ['Name']  # Column A is names
            
            # Parse sheet name to get actual month and year (e.g., "09_2025" -> month=9, year=2025)
            try:
                month_str, year_str = sheet_name.split('_')
                month = int(month_str)
                year = int(year_str)
            except ValueError:
                logger.error(f"❌ Invalid sheet name format: {sheet_name}. Expected format: MM_YYYY")
                return
            
            # Get number of days in the actual month (not current month)
            import calendar
            days_in_month = calendar.monthrange(year, month)[1]
            
            # Add date headers (01, 02, 03, etc.) for the actual month
            for day in range(1, days_in_month + 1):
                headers.append(f"{day:02d}/{month:02d}")
            
            # Write headers in batches to avoid rate limiting
            batch_size = 10  # Process 10 headers at a time
            for i in range(0, len(headers), batch_size):
                batch_headers = headers[i:i + batch_size]
                batch_data = []
                
                for col_idx in range(i, min(i + batch_size, len(headers))):
                    header_value = headers[col_idx]
                    col_letter = self._column_index_to_letter(col_idx)
                    batch_data.append({
                        'range': f"'{sheet_name}'!{col_letter}1",
                        'values': [[header_value]]
                    })
                
                # Write batch
                batch_body = {
                    'valueInputOption': 'RAW',
                    'data': batch_data
                }
                
                self.service.spreadsheets().values().batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body=batch_body
                ).execute()
                
                # Add delay between batches to avoid rate limiting
                if i + batch_size < len(headers):
                    await asyncio.sleep(0.5)  # 500ms delay
            
            logger.info(f"✅ Set up headers for {sheet_name}: {len(headers)} columns (A-{self._column_index_to_letter(len(headers)-1)})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up monthly sheet headers: {e}")
            # Try alternative approach - just write to A1
            try:
                self.service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f"'{sheet_name}'!A1",
                    valueInputOption='RAW',
                    body={'values': [['Name']]}
                ).execute()
                logger.info(f"✅ Set up basic header for {sheet_name}")
                return False  # Return False because only basic header was set up
            except Exception as e2:
                logger.error(f"❌ Failed to set up even basic header: {e2}")
                return False
    
    def _column_index_to_letter(self, col_idx: int) -> str:
        """Convert column index to letter (0=A, 1=B, ..., 25=Z, 26=AA, 27=AB, ...)"""
        result = ""
        while col_idx >= 0:
            col_idx, remainder = divmod(col_idx, 26)
            result = chr(65 + remainder) + result
            col_idx -= 1
        return result
    
    async def find_worker_row_in_monthly_sheet(self, sheet_name: str, worker_name: str) -> Optional[int]:
        """Find worker's row in monthly sheet, return row number or None"""
        if not self.service:
            return None
            
        try:
            # Read names column
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:A"
            ).execute()
            
            values = result.get('values', [])
            
            # Search for worker name (skip header row)
            for i, row in enumerate(values[1:], start=2):
                if row and row[0] == worker_name:
                    return i
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error finding worker row: {e}")
            return None
    
    async def add_worker_row_to_monthly_sheet(self, sheet_name: str, worker_name: str) -> int:
        """Add new worker row to monthly sheet, return row number"""
        if not self.service:
            return -1
            
        try:
            # Get next empty row
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:A"
            ).execute()
            
            values = result.get('values', [])
            next_row = len(values) + 1
            
            # Add worker name to new row
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A{next_row}",
                valueInputOption='RAW',
                body={'values': [[worker_name]]}
            ).execute()
            
            logger.info(f"✅ Added worker row for {worker_name} in {sheet_name}")
            return next_row
            
        except Exception as e:
            logger.error(f"❌ Error adding worker row: {e}")
            return -1
    
    async def update_attendance_cell(self, sheet_name: str, worker_name: str, check_in_time: str = None, check_out_time: str = None):
        """Update attendance cell for today"""
        if not self.service:
            return False
            
        try:
            # Ensure monthly sheet exists
            await self.ensure_monthly_sheet_exists()
            
            # Find or create worker row
            worker_row = await self.find_worker_row_in_monthly_sheet(sheet_name, worker_name)
            
            if worker_row is None:
                # Create new row for this worker
                worker_row = await self.add_worker_row_to_monthly_sheet(sheet_name, worker_name)
                if worker_row == -1:
                    return False
            
            # Get today's column
            today_col = self.get_today_column_letter()
            cell_range = f"{sheet_name}!{today_col}{worker_row}"
            
            # Prepare cell value
            if check_in_time and check_out_time:
                cell_value = f"{check_in_time}-{check_out_time}"
            elif check_in_time:
                cell_value = f"{check_in_time}-"
            else:
                cell_value = ""
            
            # Update cell
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=cell_range,
                valueInputOption='RAW',
                body={'values': [[cell_value]]}
            ).execute()
            
            logger.info(f"✅ Updated attendance for {worker_name}: {cell_value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating attendance: {e}")
            return False
    
    async def get_worker_attendance_status(self, worker_name: str) -> Dict:
        """Get worker's current attendance status for today"""
        if not self.service:
            return {'status': 'UNKNOWN', 'time': ''}
            
        try:
            sheet_name = self.get_current_month_sheet_name()
            
            # Ensure monthly sheet exists
            await self.ensure_monthly_sheet_exists()
            
            # Find worker row
            worker_row = await self.find_worker_row_in_monthly_sheet(sheet_name, worker_name)
            
            if worker_row is None:
                return {'status': 'NOT_REGISTERED', 'time': ''}
            
            # Get today's column
            today_col = self.get_today_column_letter()
            cell_range = f"{sheet_name}!{today_col}{worker_row}"
            
            # Read cell value
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=cell_range
            ).execute()
            
            values = result.get('values', [])
            cell_value = values[0][0] if values and values[0] else ""
            
            # Determine status
            time = ""  # Initialize time variable
            if not cell_value:
                status = 'NOT_CHECKED_IN'
            elif cell_value.endswith('-'):
                status = 'CHECKED_IN'
                time = cell_value[:-1]  # Remove trailing dash
            elif '-' in cell_value:
                status = 'COMPLETE'
                time = cell_value
            else:
                status = 'UNKNOWN'
                time = cell_value
            
            return {
                'status': status,
                'time': time
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting attendance status: {e}")
            return {'status': 'ERROR', 'time': ''}
    
    async def find_worker_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Find worker in Google Sheets by Telegram ID"""
        if not self.service:
            return None
            
        try:
            # Read the WORKERS sheet
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='WORKERS!A:D'
            ).execute()
            
            values = result.get('values', [])
            
            # Skip header row, search for telegram_id in column A
            for row in values[1:]:
                if len(row) >= 4 and str(row[0]) == str(telegram_id):
                    return {
                        'telegram_id': int(row[0]),
                        'name': row[1],
                        'phone': row[2],
                        'status': row[3] if len(row) > 3 else 'REGISTERED'
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error reading from Google Sheets: {e}")
            return None
    
    async def add_worker(self, telegram_id: int, name: str, phone: str) -> bool:
        """Add new worker to Google Sheets"""
        if not self.service:
            logger.warning("⚠️ Google Sheets not connected - using temporary storage")
            return False
            
        try:
            # Prepare row data
            row_data = [
                telegram_id,  # Column A: Telegram ID
                name,         # Column B: Name
                phone,        # Column C: Phone
                'REGISTERED'  # Column D: Status
            ]
            
            # Append to WORKERS sheet
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range='WORKERS!A:D',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body={'values': [row_data]}
            ).execute()
            
            logger.info(f"✅ Worker added to Google Sheets: {name} ({phone})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding worker to Google Sheets: {e}")
            return False
    
    async def update_worker_status(self, telegram_id: int, status: str) -> bool:
        """Update worker status in Google Sheets"""
        if not self.service:
            return False
            
        try:
            # Find the row with this telegram_id
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='WORKERS!A:D'
            ).execute()
            
            values = result.get('values', [])
            
            # Find row index (skip header)
            for i, row in enumerate(values[1:], start=2):
                if len(row) >= 1 and str(row[0]) == str(telegram_id):
                    # Update status in column D
                    range_name = f'WORKERS!D{i}'
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=range_name,
                        valueInputOption='RAW',
                        body={'values': [[status]]}
                    ).execute()
                    
                    logger.info(f"✅ Worker status updated: {telegram_id} -> {status}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error updating worker status: {e}")
            return False
    
    async def get_all_workers(self) -> List[Dict]:
        """Get all workers from Google Sheets"""
        if not self.service:
            return []
            
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range='WORKERS!A:D'
            ).execute()
            
            values = result.get('values', [])
            workers = []
            
            # Skip header row
            for row in values[1:]:
                if len(row) >= 3:
                    workers.append({
                        'telegram_id': int(row[0]),
                        'name': row[1],
                        'phone': row[2],
                        'status': row[3] if len(row) > 3 else 'REGISTERED'
                    })
            
            return workers
            
        except Exception as e:
            logger.error(f"❌ Error reading all workers: {e}")
            return []

    # Weekly Schedule Methods
    def get_active_week_sheet(self, date_str: str) -> str:
        """Get the active week sheet name for a given date"""
        try:
            from datetime import datetime
            # Fix date format for macOS compatibility
            try:
                # Try the original format first
                date_obj = datetime.strptime(date_str, "%-m/%-d/%Y")
            except ValueError:
                # Fallback to standard format
                date_obj = datetime.strptime(date_str, "%m/%d/%Y")
            
            # For your rotation system: schedule1 and schedule2 alternate
            # We'll use a simple approach: even weeks = schedule2, odd weeks = schedule1
            # This can be adjusted based on your actual rotation logic
            
            # Get week number in the year
            week_of_year = date_obj.isocalendar()[1]
            
            # Alternate between schedule1 and schedule2
            if week_of_year % 2 == 0:
                return "schedule2"
            else:
                return "schedule1"
            
        except Exception as e:
            logger.error(f"❌ Error calculating week sheet: {e}")
            return "schedule1"
    
    def get_next_week_sheet(self, current_sheet: str) -> str:
        """Get the next week sheet name for rotation system"""
        if current_sheet == "schedule1":
            return "schedule2"
        else:
            return "schedule1"

    async def get_employee_schedule_for_date(self, employee_id: str, date_str: str) -> Optional[Dict]:
        """Get employee schedule for a specific date"""
        if not self.service:
            return None
            
        try:
            # Get the week sheet for this date
            week_sheet = self.get_active_week_sheet(date_str)
            
            # Try to read from the week sheet
            try:
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{week_sheet}!A:Z'
                ).execute()
                
                values = result.get('values', [])
                if not values:
                    return None
                
                # Parse the schedule data
                # Expected format: Employee ID | Mon | Tue | Wed | Thu | Fri | Sat | Sun
                headers = values[0] if values else []
                
                # Find the employee row by name (we'll need to get name from telegram_id first)
                
                # First, get the employee name from telegram_id
                worker_info = await self.find_worker_by_telegram_id(int(employee_id))
                if not worker_info:
                    logger.warning(f"⚠️ Worker not found for telegram_id: {employee_id}")
                    return None
                
                worker_name = worker_info['name']
                
                # Find the employee row by name
                for row in values:
                    if len(row) > 0 and row[0] == worker_name:
                        # Find the day column (parse date to get day of week)
                        from datetime import datetime
                        try:
                            date_obj = datetime.strptime(date_str, "%-m/%-d/%Y")
                        except ValueError:
                            date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                        
                        day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday
                        
                        # Map to column index (Monday is column 1, etc.)
                        day_col = day_of_week + 1
                        
                        if day_col < len(row):
                            schedule_text = row[day_col] if row[day_col] else ""
                            
                            return {
                                'employee_id': employee_id,
                                'date': date_str,
                                'schedule': schedule_text,
                                'is_work_day': bool(schedule_text and schedule_text.strip().upper() not in ['REST', 'OFF', '']),
                                'status': schedule_text,
                                'schedule_type': 'WORK' if schedule_text and schedule_text.strip().upper() not in ['REST', 'OFF', ''] else 'REST'
                            }
                
                return None
                
            except Exception as e:
                logger.warning(f"⚠️ Could not read from {week_sheet}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting employee schedule: {e}")
            return None

    async def get_weekly_schedule(self, employee_id: str, date_str: str) -> Optional[Dict[str, str]]:
        """Get employee's full weekly schedule for the week containing the given date"""
        if not self.service:
            return None
            
        try:
            # Get the week sheet for this date
            week_sheet = self.get_active_week_sheet(date_str)
            
            # Try to read from the week sheet
            try:
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{week_sheet}!A:Z'
                ).execute()
                
                values = result.get('values', [])
                if not values:
                    return None
                
                # Expected format: Employee Name | Mon | Tue | Wed | Thu | Fri | Sat | Sun
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                # First, get the employee name from telegram_id
                worker_info = await self.find_worker_by_telegram_id(int(employee_id))
                if not worker_info:
                    logger.warning(f"⚠️ Worker not found for telegram_id: {employee_id}")
                    return None
                
                worker_name = worker_info['name']
                
                # Find the employee row by name
                for row in values:
                    if len(row) > 0 and row[0] == worker_name:
                        weekly_schedule = {}
                        
                        # Map each day to its schedule
                        for i, day in enumerate(days):
                            day_col = i + 1
                            if day_col < len(row):
                                schedule_text = row[day_col] if row[day_col] else ""
                                weekly_schedule[day] = schedule_text
                        
                        return weekly_schedule
                
                return None
                
            except Exception as e:
                logger.warning(f"⚠️ Could not read from {week_sheet}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting weekly schedule: {e}")
            return None

    async def get_all_employees_for_date(self, date_str: str) -> List[Dict]:
        """Get all employees scheduled for a specific date"""
        if not self.service:
            return []
            
        try:
            # Get the week sheet for this date
            week_sheet = self.get_active_week_sheet(date_str)
            
            # Try to read from the week sheet
            try:
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{week_sheet}!A:Z'
                ).execute()
                
                values = result.get('values', [])
                if not values:
                    return []
                
                # Expected format: Employee Name | Mon | Tue | Wed | Thu | Fri | Sat | Sun
                days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                # Parse the date to get day of week
                from datetime import datetime
                try:
                    date_obj = datetime.strptime(date_str, "%-m/%-d/%Y")
                except ValueError:
                    date_obj = datetime.strptime(date_str, "%m/%d/%Y")
                day_of_week = date_obj.weekday()  # 0=Monday, 6=Sunday
                day_col = day_of_week + 1
                
                employees = []
                
                # Process each employee row (skip header rows)
                for row in values:
                    if len(row) > 0 and row[0] and not row[0].startswith('Πρόγραμμα') and not row[0].startswith('ΕΒΔΟΜΑΔΑ'):
                        name = row[0]  # Employee name is in column A
                        
                        if day_col < len(row):
                            schedule_text = row[day_col] if row[day_col] else ""
                            
                            employees.append({
                                'employee_id': name,  # Use name as ID for now
                                'name': name,
                                'date': date_str,
                                'schedule': schedule_text,
                                'is_work_day': bool(schedule_text and schedule_text.strip().upper() not in ['REST', 'OFF', '']),
                                'status': schedule_text,
                                'schedule_type': 'WORK' if schedule_text and schedule_text.strip().upper() not in ['REST', 'OFF', ''] else 'REST'
                            })
                
                return employees
                
            except Exception as e:
                logger.warning(f"⚠️ Could not read from {week_sheet}: {e}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error getting all employees for date: {e}")
            return []

    async def style_monthly_sheet(self, sheet_name: str):
        """Style the monthly sheet with colors and formatting"""
        try:
            # Get sheet ID for styling
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            sheet_id = None
            for sheet in result.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if not sheet_id:
                logger.error(f"❌ Could not find sheet ID for {sheet_name}")
                return False
            
            # Style requests
            requests = [
                # Header row: Blue background, white text, bold
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1,
                            'startColumnIndex': 0,
                            'endColumnIndex': 32
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.8},
                                'textFormat': {'bold': True, 'foregroundColor': {'red': 1.0, 'green': 1.0, 'blue': 1.0}}
                            }
                        },
                        'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                    }
                },
                # Name column A2-A100: Light blue background
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 1,
                            'endRowIndex': 100,
                            'startColumnIndex': 0,
                            'endColumnIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.7, 'green': 0.9, 'blue': 1.0}
                            }
                        },
                        'fields': 'userEnteredFormat.backgroundColor'
                    }
                },
                # Date columns B2-AF100: Light green background
                {
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 1,
                            'endRowIndex': 100,
                            'startColumnIndex': 1,
                            'endColumnIndex': 32
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'backgroundColor': {'red': 0.8, 'green': 1.0, 'blue': 0.8}
                            }
                        },
                        'fields': 'userEnteredFormat.backgroundColor'
                    }
                },
                # Freeze header row and name column
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet_id,
                            'gridProperties': {
                                'frozenRowCount': 1,
                                'frozenColumnCount': 1
                            }
                        },
                        'fields': 'gridProperties.frozenRowCount,gridProperties.frozenColumnCount'
                    }
                }
            ]
            
            # Apply styling
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"✅ Styled monthly sheet: {sheet_name} with light blue names and light green dates")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error styling monthly sheet: {e}")
            return False

