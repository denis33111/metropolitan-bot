# 🤖 Telegram Attendance Bot

A comprehensive employee attendance tracking system using Telegram bot, QR codes, geolocation verification, and Google Sheets integration.

## ✨ Features

### 📱 Employee Features
- **QR Code Check-in/out** - Simple scanning or text entry
- **Location Verification** - Ensures employees are at the office
- **Unusual Entry Notes** - Log location when working remotely
- **Real-time Status** - Check current attendance status

### 👨‍💼 Admin Features
- **Employee Management** - Add/remove employees anytime
- **Schedule Management** - Flexible weekly scheduling
- **Analytics & Reports** - Detailed attendance analytics
- **Google Sheets Integration** - Automatic data sync
- **Archive System** - Historical data preservation

### 🏢 System Features
- **Geofencing** - 100m radius office zone verification
- **Multiple Admin Levels** - Super Admin, Regular Admin, Viewer
- **Overtime Tracking** - Automatic overtime detection
- **Data Retention** - 2-month active + full archive
- **Backup System** - Google Sheets + daily snapshots

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Google Sheets API credentials
- Google Spreadsheet

### 2. Installation

```bash
# Clone the repository
git clone <repository-url>
cd telegram-attendance-bot

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### 3. Configuration

#### Telegram Bot Setup
1. Create bot via @BotFather on Telegram
2. Get bot token and username
3. Update `.env` file:
```env
TELEGRAM_TOKEN=your_bot_token_here
BOT_USERNAME=your_bot_username_here
```

#### Google Sheets Setup
1. Create Google Cloud Project
2. Enable Google Sheets API
3. Create service account and download credentials
4. Share your Google Spreadsheet with service account email
5. Update `.env` file:
```env
SPREADSHEET_ID=your_spreadsheet_id_here
```

#### Office Location Setup
1. Get your office coordinates (latitude/longitude)
2. Update `.env` file:
```env
OFFICE_LATITUDE=your_office_latitude
OFFICE_LONGITUDE=your_office_longitude
OFFICE_RADIUS_METERS=100
```

### 4. Run the Bot

```bash
python attendance_bot.py
```

## 📊 Google Sheets Structure

### Main Attendance Sheet
```
| Employee Name | 01/01 | 02/01 | 03/01 | 04/01 | 05/01 |
|---------------|-------|-------|-------|-------|-------|
| John Doe      | 9-17  | 9-17* | OFF   | 9-17  | 9-17  |
| Jane Smith    | 8-16  | SICK  | 8-16  | 8-16  | 8-16  |
| Alice Brown   | N/A   | N/A   | 9-17  | 9-17  | 9-17  |
```

**Status Codes:**
- `9-17` = Checked in at 9:00, out at 17:00
- `9-17*` = With location note (remote work)
- `SICK` = Sick leave
- `OFF` = Scheduled day off
- `MISS` = Missed shift
- `N/A` = Not applicable (before start date)

### Weekly Schedule Sheet
```
| Employee Name | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---------------|-----|-----|-----|-----|-----|-----|-----|
| John Doe      | 9-17| 9-17| 9-17| 9-17| 9-17| OFF | OFF |
| Jane Smith    | 8-16| 8-16| 8-16| 8-16| 8-16| OFF | OFF |
```

## 🤖 Bot Commands

### Employee Commands
- `/start` - Welcome message and bot introduction
- `/help` - Show available commands
- `/qr_scan` - Start QR code scanning process
- `/status` - Check current attendance status

### Admin Commands

#### Employee Management
- `/add_employee [Name] [Start_Date] [Schedule]` - Add new employee
- `/remove_employee [Name] [End_Date]` - Remove employee
- `/list_employees` - Show all employees

#### Analytics
- `/analytics [Employee] [Month]` - Employee analytics
- `/analytics_all [Month]` - All employees summary
- `/analytics_late [Month]` - Late arrivals report
- `/analytics_overtime [Month]` - Overtime summary

#### Schedule Management
- `/schedule_add [Employee] [Date] [Hours]` - Add schedule
- `/schedule_remove [Employee] [Date]` - Remove schedule
- `/generate_next_week` - Prepare next week's schedule

#### Status & Reports
- `/status_all` - All employees current status
- `/status_today` - Today's attendance summary
- `/notes [Employee] [Month]` - View location notes

#### System
- `/archive_month [Month]` - Archive month data
- `/backup_now` - Create backup
- `/office_location` - Show office location

## 🔧 Configuration Options

### Office Zone
- **Radius**: 100m (configurable)
- **Location**: Set via coordinates
- **Verification**: Automatic on QR scan

### Data Retention
- **Active Data**: Current + previous month
- **Archive**: All historical data preserved
- **Backup**: Daily automatic backups

### Admin Levels
- **Super Admin**: All permissions
- **Regular Admin**: Basic management + analytics
- **Viewer**: Read-only access

## 📱 QR Code System

### Employee Registration
1. Admin creates employee via `/add_employee`
2. Bot generates unique QR code
3. Employee receives QR code (physical or digital)
4. Employee can scan or type QR code for check-in/out

### QR Code Format
```
EMP_[EmployeeID]_[UniqueHash]
Example: EMP_123_abc123def
```

## 🌍 Geolocation Features

### Office Zone Verification
- Automatic location check on QR scan
- 100m radius around office coordinates
- Prevents remote check-ins without approval

### Unusual Entry Handling
- Outside zone requires location note
- Simple note system (no approval needed)
- All unusual entries logged for review

## 📈 Analytics & Reporting

### Individual Analytics
- Attendance rate
- Total hours worked
- Late arrivals count
- Sick/remote days
- Overtime hours

### Team Analytics
- Overall attendance summary
- Late arrival patterns
- Overtime trends
- Employee performance comparison

### Export Options
- Google Sheets integration
- Automatic report generation
- Historical data preservation

## 🔒 Security Features

### Access Control
- Multiple admin levels
- Permission-based commands
- Secure QR code validation

### Data Protection
- Google Sheets security
- Automatic backups
- Data retention policies

### Location Verification
- Geofencing protection
- GPS coordinate validation
- Unusual entry logging

## 🚀 Deployment

### Local Development
```bash
python attendance_bot.py
```

### Production Deployment
1. Set up server (VPS, cloud, etc.)
2. Install Python and dependencies
3. Configure environment variables
4. Set up process manager (systemd, PM2, etc.)
5. Configure SSL certificates
6. Set up monitoring and logging

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "attendance_bot.py"]
```

## 📞 Support

### Troubleshooting
1. Check bot token in `.env`
2. Verify Google Sheets permissions
3. Ensure office coordinates are correct
4. Check internet connectivity

### Common Issues
- **Bot not responding**: Check token and permissions
- **QR scan fails**: Verify QR code format
- **Location errors**: Check office coordinates
- **Sheets sync issues**: Verify API credentials

## 🔄 Updates & Maintenance

### Regular Tasks
- Monthly data archiving
- Backup verification
- Admin user management
- Office location updates

### System Updates
- Monitor for dependency updates
- Test new features in development
- Backup before major updates
- Gradual rollout to production

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📞 Contact

For support or questions:
- Create an issue on GitHub
- Contact the development team
- Check documentation

---

**Built with ❤️ for efficient employee attendance tracking** 