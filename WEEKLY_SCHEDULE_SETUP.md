# 📅 Weekly Schedule Setup Guide

## 🎯 **What Changed**

The "📊 My Status" button has been **completely replaced** with "📅 My Schedule" functionality that shows:

- **Current Week Schedule** - Shows this week's work schedule
- **Next Week Schedule** - Shows next week's schedule (if available)

## 📊 **Google Sheets Structure Required**

### **Weekly Schedule Sheets**

You need to create weekly schedule sheets with this naming convention:
```
WEEK1_07_2025  (Week 1 of July 2025)
WEEK2_07_2025  (Week 2 of July 2025)  
WEEK3_07_2025  (Week 3 of July 2025)
WEEK4_07_2025  (Week 4 of July 2025)
```

### **Sheet Format**

Each weekly sheet should have this structure:

| Employee ID | Name | Monday | Tuesday | Wednesday | Thursday | Friday | Saturday | Sunday |
|-------------|------|--------|---------|-----------|----------|--------|----------|--------|
| 123456789 | John Smith | 9:00-17:00 | 9:00-17:00 | 9:00-17:00 | 9:00-17:00 | 9:00-17:00 | REST | REST |
| 987654321 | Maria Garcia | 8:00-16:00 | 8:00-16:00 | 8:00-16:00 | 8:00-16:00 | 8:00-16:00 | OFF | OFF |
| 555666777 | Alex Johnson | 10:00-18:00 | 10:00-18:00 | 10:00-18:00 | 10:00-18:00 | 10:00-18:00 | 10:00-18:00 | REST |

### **Schedule Values**

- **Work Hours**: `9:00-17:00`, `8:00-16:00`, etc.
- **Rest Days**: `REST` or `OFF`
- **Empty**: Leave blank for undefined schedules

## 🔧 **How to Set Up**

### **Step 1: Create Weekly Sheets**

1. In your Google Sheets, create new sheets named:
   - `WEEK1_07_2025`
   - `WEEK2_07_2025`
   - `WEEK3_07_2025`
   - `WEEK4_07_2025`

2. Copy the format from the example above

### **Step 2: Add Employee Data**

1. **Column A**: Employee Telegram ID (from your WORKERS sheet)
2. **Column B**: Employee Name
3. **Columns C-I**: Monday through Sunday schedules

### **Step 3: Test the Bot**

1. Run your bot
2. Press the "📅 My Schedule" button
3. You should see your weekly schedule

## 📱 **What Users Will See**

### **Current Week Example:**
```
📅 Πρόγραμμα Εργασίας για John Smith

📅 Τρέχουσα Εβδομάδα:
   Mon: 🟢 9:00-17:00
   Tue: 🟢 9:00-17:00
   Wed: 🟢 9:00-17:00
   Thu: 🟢 9:00-17:00
   Fri: 🟢 9:00-17:00
   Sat: 🟡 REST
   Sun: 🟡 REST

📅 Επόμενη Εβδομάδα:
   ⚪ Δεν έχει οριστεί ακόμα
```

### **Icons Meaning:**
- 🟢 **Green**: Work day with hours
- 🟡 **Yellow**: Rest day (REST/OFF)
- ⚪ **White**: No schedule defined
- ⚠️ **Warning**: Schedule not found

## 🚨 **Important Notes**

1. **Employee ID Must Match**: The Telegram ID in the schedule sheet must match the ID in your WORKERS sheet
2. **Sheet Names**: Must follow the exact format `WEEK{number}_{month:02d}_{year}`
3. **Date Format**: Bot expects dates in format `7/18/2025` (M/D/YYYY)
4. **Fallback**: If weekly sheets don't exist, users will see "No schedule found"

## 🧪 **Testing**

Use the test script to verify everything works:
```bash
python3 test_schedule_functionality.py
```

Update the spreadsheet ID and employee ID in the test script first!

## 🔄 **Next Steps**

Once this is working, you can:
1. Add more detailed schedule information
2. Include break times
3. Add shift types (morning, afternoon, night)
4. Include location information
5. Add schedule change notifications

