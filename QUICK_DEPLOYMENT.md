# 🚀 Quick Deployment Guide

## ⚡ **Immediate Deployment (Local Testing)**

### 1. **Test Bot Locally**
```bash
python3 attendance_bot.py
```

### 2. **If Google Sheets Error Occurs:**
The bot will work with temporary storage until you set up Google Sheets.

## 🔐 **Google Sheets Setup (Required for Production)**

### **Step 1: Create Google Cloud Project**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: `metropolitan-bot`
3. Enable Google Sheets API

### **Step 2: Create Service Account**
1. Go to "IAM & Admin" → "Service Accounts"
2. Create service account: `metropolitan-bot`
3. Download JSON credentials as `credentials.json`

### **Step 3: Place Credentials**
```bash
# Place credentials.json in project root
cp ~/Downloads/credentials.json .
```

### **Step 4: Share Spreadsheet**
1. Open your Google Sheet
2. Click "Share" 
3. Add service account email (ends with `@...iam.gserviceaccount.com`)
4. Give "Editor" access

## 🚀 **Production Deployment**

### **Option 1: Simple Systemd Service**
```bash
# Copy service file
sudo cp metropolitan-bot.service /etc/systemd/system/

# Edit paths in service file
sudo nano /etc/systemd/system/metropolitan-bot.service

# Enable and start
sudo systemctl enable metropolitan-bot
sudo systemctl start metropolitan-bot
sudo systemctl status metropolitan-bot
```

### **Option 2: Docker Deployment**
```bash
# Build and run
docker build -t metropolitan-bot .
docker run -d --name metropolitan-bot metropolitan-bot
```

## 📱 **Test Your Bot**
1. Send `/start` to your bot
2. Register a new worker
3. Test check-in/out functionality

## 🆘 **Troubleshooting**
- Check logs: `sudo journalctl -u metropolitan-bot -f`
- Verify credentials: `ls -la credentials.json`
- Test API: `python3 -c "from src.services.sheets_service import GoogleSheetsService; print('OK')"`
