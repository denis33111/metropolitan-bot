# 📝 **DISCUSSION NOTES - Metropolitan Bot Requirements**

## 🎯 **PROJECT OVERVIEW**

**Goal:** Create a Telegram bot for Metropolitan Expo that provides **ADMIN** with check in/out data and allows **WORKERS** to contact admin.

**CRITICAL REQUIREMENT:** The bot must be **EXTREMELY SIMPLE** and **UNDERSTANDABLE** for humans with **ZERO TECHNICAL KNOWLEDGE** or **ZERO IQ** for technology.

## 🎯 **REAL MAIN FUNCTIONALITY**

### **Primary Purpose:**
1. **Provide ADMIN with check in/out data** - Track who's working, when, where
2. **Enable WORKERS to contact ADMIN** - Get help, report issues, ask questions
3. **Monitor attendance compliance** - See who didn't follow the program

### **What the Bot Actually Does:**
- **For Workers:** Simple check-in/out + contact admin
- **For Admin:** Complete attendance data + worker communication
- **For Management:** Reports on who's following vs not following the program

### **Key Insight:**
This is **NOT** just an attendance tracker - it's an **ADMIN TOOL** that happens to have a simple worker interface.

## 🏢 **BUSINESS MODEL & SYSTEM WORKFLOW**

### **Company Structure:**
- **Company 1 (Metropolitan Expo):** Provides workers to Company 2
- **Company 2 (Client):** Receives workers and provides weekly program
- **Workers:** Employed by Company 1, work at Company 2 locations

### **Weekly Program Workflow:**
```
1. MID-WEEK (Wednesday/Thursday):
   - Company 2 tells Company 1: "We need X workers for next week"
   - Company 2 provides: Worker requirements, dates, times, locations

2. END OF WEEK (Friday):
   - Company 1 creates FINAL PROGRAM based on Company 2's requirements
   - Final program includes: Which workers, when, where, what times

3. NEXT WEEK:
   - Workers follow the FINAL PROGRAM
   - Bot monitors compliance with Company 1's final program
   - Bot reports to Company 1 admin about worker compliance
```

### **What This Means for the Bot:**
- **Bot works for Company 1** (Metropolitan Expo)
- **Bot monitors Company 1's workers** at Company 2 locations
- **Program sheet contains Company 1's final program** (not Company 2's initial request)
- **Admin is Company 1 management** (not Company 2)
- **Reports go to Company 1** about their workers' performance

## 🧠 **USER EXPERIENCE REQUIREMENTS**

### **Target Users:**
- **Workers with ZERO technical knowledge**
- **People who struggle with basic apps**
- **Users who get confused by complex interfaces**
- **Anyone who finds technology overwhelming**

### **Design Principles:**
- **KISS:** Keep It Super Simple
- **One button = One action**
- **No confusing menus or options**
- **Clear, simple language only**
- **Visual cues and emojis everywhere**
- **Step-by-step guidance only**
- **No technical jargon ever**

## 🏗️ **CURRENT STATUS**

✅ **Bot Connection:** Working (empty_bot.py)  
✅ **Google Sheet:** Created with structure  
✅ **Environment:** Basic config ready  
❌ **Functionality:** Zero - ready to build  

## 📊 **GOOGLE SHEET STRUCTURE**

**Sheet Name:** "metropolitan"  
**Columns:**
- **A: ID** → Telegram ID (automatic from bot)
- **B: NAME** → Worker's full name
- **C: PHONE** → Worker's phone number  
- **D: STATUS** → ACTIVE/INACTIVE (working or not)

**Program Sheet (New):**
**Sheet Name:** "PROGRAM" or "SCHEDULE"  
**Purpose:** Metropolitan Expo's (Company 1) FINAL PROGRAM for workers at Company 2 locations

**Columns:**
- **A: WORKER_NAME** → Worker's name (from Metropolitan Expo)
- **B: DATE** → Work date (next week)
- **C: START_TIME** → Expected start time (e.g., "09:00")
- **D: END_TIME** → Expected end time (e.g., "17:00")
- **E: LOCATION** → Company 2 work location
- **F: STATUS** → SCHEDULED, COMPLETED, MISSED

**Program Management Workflow:**
```
1. MID-WEEK: Company 2 sends requirements to Metropolitan Expo (us)
2. FRIDAY: Metropolitan Expo admin updates PROGRAM sheet with final assignments
3. NEXT WEEK: Bot monitors workers against Metropolitan Expo's final program
4. DAILY: Bot reports compliance to Metropolitan Expo admin
```

**Program Update Process:**
- **Source:** Google Sheets (manual entry by Metropolitan Expo admin)
- **Frequency:** Every Friday for next week
- **Method:** Admin manually updates PROGRAM sheet in Google Sheets
- **Bot Action:** Bot automatically reads updated program and starts monitoring

**Location Details:**
- **Work Location:** Same Company 2 location (not multiple locations)
- **Zone:** 500m radius from fixed Company 2 coordinates
- **Coordinates:** Already in .env file (37.924917, 23.931444)

**Weekly Schedule Handling:**
- **Manual:** Admin manually creates new weekly program every Friday
- **Bot Role:** Bot reads program and monitors compliance
- **No Automation:** Bot doesn't create or rollover programs automatically

**Practical Weekly Example:**
```
WEDNESDAY (Mid-week):
- Company 2 calls: "We need 5 workers next week: Monday-Friday, 9 AM - 5 PM"

FRIDAY (Program Creation):
- Metropolitan Expo admin opens Google Sheets
- Updates PROGRAM sheet with next week's assignments:
  Row 1: John Smith | Monday | 09:00 | 17:00 | Company2_Office | SCHEDULED
  Row 2: Maria Garcia | Monday | 09:00 | 17:00 | Company2_Office | SCHEDULED
  Row 3: Alex Johnson | Tuesday | 09:00 | 17:00 | Company2_Office | SCHEDULED
  ... (continues for the week)

MONDAY (Bot Monitoring):
- Bot reads PROGRAM sheet
- Sees John and Maria should work at 09:00
- Waits until 09:10 (10 min latency)
- If John/Maria didn't check in by 09:10
- Bot alerts Metropolitan Expo admin: "⚠️ John and Maria didn't check in by 09:10"
```

**Business Purpose:**
The bot makes communication between Metropolitan Expo (us) and our workers faster and easier, so we can provide better service to Company 2.

## 🔔 **AUTOMATIC NOTIFICATION SYSTEM**

### **Program-Based Monitoring:**
1. **Bot reads program sheet** - Gets today's scheduled workers and times
2. **Monitors check-ins** - Tracks who checked in vs who should have
3. **10-minute latency** - Waits 10 minutes after scheduled start time
4. **Automatic admin alerts** - Notifies admin of missing workers

### **Notification Logic:**
```
Example:
- John scheduled to work at 09:00
- Bot waits until 09:10 (10 min latency)
- If John hasn't checked in by 09:10
- Bot automatically sends admin: "⚠️ John didn't check in by 09:10 (scheduled 09:00)"
```

### **What Gets Monitored:**
- **Scheduled start times** - Who should be working when
- **Actual check-ins** - Who actually showed up
- **Missing workers** - Who didn't follow the program
- **Late arrivals** - Who checked in after scheduled time

## 🚀 **SYSTEM REQUIREMENTS**

### **Work Zone:**
- **Radius:** 500 meters from office
- **Office Coordinates:** 37.924917, 23.931444 (from .env)
- **Purpose:** Workers must be within zone to check in/out

### **Worker Management:**
- **Registration:** New workers go through onboarding flow
- **Identification:** Uses Telegram ID as unique identifier
- **Status Tracking:** ACTIVE (working) vs INACTIVE (not working)

## 🔄 **COMPLETE WORKFLOW DESIGN**

### **Phase 1: Worker Registration Flow**
```
1. New worker starts bot (/start)
2. Bot detects new vs existing worker
3. Bot asks for full name
4. Bot asks for phone number
5. Bot saves to Google Sheet: [Telegram_ID, NAME, PHONE, ACTIVE]
6. Registration complete - worker can now use check-in/out
```

### **Phase 2: Working Flow (Zone-Based)**
```
1. Worker sends location (GPS coordinates)
2. Bot checks if within 500m work zone
3. Check-in: Records start time + location + sets status
4. Check-out: Records end time + location + updates status
5. Status tracking: Shows current work status
```

## 🛠️ **TECHNICAL REQUIREMENTS**

### **Bot Deployment Method:**
- **Webhook Method:** Required for 24/7 production server operation
- **NOT Polling:** Not suitable for production deployment
- **HTTPS Required:** SSL certificate needed for webhook endpoint

### **Admin Access Control:**
- **Hardcoded Admin IDs:** Specific Telegram IDs hardcoded in bot
- **No Dynamic Admin Management:** Admins are pre-configured
- **Secure Access:** Only hardcoded IDs can access admin commands

### **Bot Commands Needed:**
- **Worker Commands:**
  - `/start` - Welcome + registration detection
  - `/checkin` - Start work day (with location)
  - `/checkout` - End work day (with location)
  - `/status` - Show current work status
  - `/help` - Show available commands
  - `/contact` - Contact admin for help

- **Admin Commands:**
  - `/admin` - Admin panel access (hardcoded IDs only)
  - `/report` - Generate missing workers report based on today's program
  - `/workers` - List all workers and status
  - `/missing` - Show workers who didn't check in/out based on program
  - `/contact_worker` - Send message to specific worker

### **Features Needed:**
- **Conversation Handler** - For registration flow
- **Location Validation** - 500m radius checking
- **Google Sheets Integration** - Read/write worker data + read program data
- **Time Tracking** - Check-in/out timestamps
- **Status Management** - ACTIVE/INACTIVE states
- **Webhook Server** - HTTP endpoint for Telegram updates
- **Admin Dashboard** - Monitor attendance and worker status
- **Worker Communication** - Two-way messaging system
- **Program Sheet Reading** - Read today's work schedule from Google Sheets
- **Automatic Notifications** - Alert admin when workers miss check-in (10 min latency)

## 📍 **LOCATION SYSTEM**

### **How Workers Share Location:**
- **Option 1:** Telegram location sharing (GPS)
- **Option 2:** Manual coordinate input
- **Option 3:** QR code scanning at office

### **Zone Validation:**
- Calculate distance from office coordinates
- Allow check-in/out only within 500m
- Store location data with timestamps

## 🔐 **SECURITY & VALIDATION**

### **Worker Verification:**
- Telegram ID is unique identifier
- Phone number validation
- Name verification
- Prevent duplicate registrations

### **Location Security:**
- Verify worker is actually at work location
- Prevent remote check-ins
- Log all location data

## 📱 **USER EXPERIENCE FLOW**

### **New Worker Journey (SUPER SIMPLE):**
```
1. Worker finds bot on Telegram
2. Sends /start (or just types "start")
3. Bot shows: "Hi! What's your name? (just type it)"
4. Worker types: "John Smith"
5. Bot shows: "Great! What's your phone number? (just type it)"
6. Worker types: "1234567890"
7. Bot shows: "Perfect! You're registered! 🎉"
8. Bot shows: "Now you can work! Just press these buttons:"
   [✅ START WORK] [🚪 END WORK] [📊 MY STATUS] [📞 CONTACT ADMIN]
```

### **Daily Work Flow (SUPER SIMPLE):**
```
1. Worker arrives at office
2. Presses [✅ START WORK] button
3. Bot shows: "Share your location 📍 (press the location button)"
4. Worker presses location button
5. Bot shows: "Great! You're at work! ✅"
6. Worker works...
7. Worker presses [🚪 END WORK] button
8. Bot shows: "Share your location 📍 (press the location button)"
9. Worker presses location button
10. Bot shows: "Work day finished! 👋"
```

### **Admin Workflow (Monitoring & Management):**
```
1. Admin sends /admin
2. Bot shows admin panel:
   [📊 TODAY'S REPORT] [👥 ALL WORKERS] [❌ MISSING WORKERS] [📞 CONTACT WORKER]

3. Admin presses [📊 TODAY'S REPORT]
4. Bot shows: "Today's Program Report: 15 scheduled, 12 checked in, 3 missing"

5. Admin presses [❌ MISSING WORKERS]
6. Bot shows: "Workers who didn't follow today's program:"
   "John Smith - Scheduled 09:00, didn't check in by 09:10"
   "Maria Garcia - Scheduled 08:30, didn't check in by 08:40"
   "Alex Johnson - Scheduled 09:00, didn't check in by 09:10"

7. Admin presses [📞 CONTACT WORKER]
8. Bot shows: "Which worker? (type name)"
9. Admin types: "John"
10. Bot shows: "Message for John: (type your message)"
11. Bot sends message to John: "Admin needs to talk to you"
```

### **Automatic Admin Notifications:**
```
Bot automatically sends admin when workers miss program:

"⚠️ MISSING WORKER ALERT ⚠️
John Smith didn't check in by 09:10
Scheduled start time: 09:00
Current time: 09:10
Status: MISSING"

"⚠️ MISSING WORKER ALERT ⚠️
Maria Garcia didn't check in by 08:40
Scheduled start time: 08:30
Current time: 08:40
Status: MISSING"
```

### **Worker Contact Admin Flow:**
```
5. Admin gets notification: "John Smith: I'm sick today, can't come to work"
```

### **Key Simplifications:**
- **No commands to remember** - Just buttons
- **No typing required** - Just press buttons
- **Clear visual feedback** - ✅ ❌ 🎉 👋
- **Simple language only** - "Press this button"
- **One action at a time** - Never overwhelm user
- **Always show next step** - "Now do this..."

## 🎯 **DEVELOPMENT PRIORITIES**

### **Priority 1: Foundation**
- [ ] Test empty bot connects
- [ ] Add basic command structure
- [ ] Set up conversation handlers
- [ ] **Convert to webhook method** (for production)

### **Priority 2: Registration**
- [ ] Build registration flow
- [ ] Integrate with Google Sheets
- [ ] Test worker onboarding

### **Priority 3: Check-in/out**
- [ ] Add location sharing
- [ ] Implement 500m zone validation
- [ ] Build time tracking

### **Priority 4: Program Integration**
- [ ] Add program sheet reading
- [ ] Implement automatic notifications
- [ ] Build missing worker alerts

### **Priority 5: Production Deployment**
- [ ] Set up webhook server
- [ ] Configure HTTPS endpoint
- [ ] Deploy to production server
- [ ] Test 24/7 operation

### **Priority 6: Polish**
- [ ] Add status commands
- [ ] Improve user experience
- [ ] Add error handling

## 🤔 **DECISIONS TO MAKE**

### **Location Method:**
- **GPS sharing** vs **Manual input** vs **QR codes**

### **Data Storage:**
- **Google Sheets only** vs **Local backup** vs **Database**

### **Admin Features:**
- **Worker management** vs **Reports** vs **Settings**

### **Notifications:**
- **Daily reminders** vs **Status updates** vs **None**

## 📋 **NEXT STEPS**

1. **Update .env** - Change radius to 500m
2. **Test empty bot** - Verify connection works
3. **Start building** - Begin with registration flow
4. **Test each step** - Don't move on until working
5. **Build gradually** - Add features one by one

## 💡 **KEY PRINCIPLES**

✅ **Keep it simple** - One feature at a time  
✅ **Test everything** - Never skip testing  
✅ **Build working code** - Don't add broken features  
✅ **User experience first** - Make it easy to use  
✅ **Document everything** - Keep notes updated  

---

**🎯 Ready to start building when you are!** 🚀