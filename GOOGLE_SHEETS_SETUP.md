# 🔐 Google Sheets API Setup Guide

## 🎯 **What We Need:**

1. **Google Cloud Project** with Sheets API enabled
2. **Service Account** with credentials
3. **Credentials file** (`credentials.json`)
4. **Spreadsheet shared** with service account

## 🚀 **Step-by-Step Setup:**

### **1. Create Google Cloud Project**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing
3. Enable Google Sheets API

### **2. Create Service Account**
1. Go to "IAM & Admin" → "Service Accounts"
2. Click "Create Service Account"
3. Name: `metropolitan-bot`
4. Description: `Bot for attendance tracking`
5. Click "Create and Continue"

### **3. Grant Permissions**
1. Role: "Editor" (for read/write access)
2. Click "Continue" and "Done"

### **4. Create & Download Credentials**
1. Click on your service account
2. Go to "Keys" tab
3. Click "Add Key" → "Create New Key"
4. Choose "JSON" format
5. Download the file

### **5. Set Up Credentials**
1. Rename downloaded file to `credentials.json`
2. Place it in your project root (same folder as `working_bot.py`)
3. **IMPORTANT:** Never commit this file to git!

### **6. Share Your Spreadsheet**
1. Open your Google Sheet: `metropolitan`
2. Click "Share" button
3. Add your service account email (ends with `@...iam.gserviceaccount.com`)
4. Give "Editor" access
5. Click "Send"

## 📁 **File Structure:**
```
metrpolitanbot/
├── working_bot.py
├── credentials.json          ← Place here
├── .env
└── src/
    └── services/
        └── sheets_service.py
```

## 🧪 **Test It:**
1. **Restart the bot:** `python3 working_bot.py`
2. **Send `/start`** to your bot
3. **Register a new worker**
4. **Check Google Sheets** - data should appear!

## 🚨 **Security Notes:**
- Keep `credentials.json` private
- Don't share service account keys
- Use minimal required permissions

## ❓ **Need Help?**
- Check bot logs for error messages
- Verify spreadsheet ID in `.env`
- Ensure service account has access
