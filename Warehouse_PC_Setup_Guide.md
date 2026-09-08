# 🏭 EFL Global IDP — Warehouse PC Setup Guide

> **Purpose:** This guide explains how to connect the warehouse computer (with Kodak Alaris scanner) to the cloud-hosted IDP system so that scanned documents are automatically uploaded and processed by AI.

---

## 📋 Prerequisites

Before starting, make sure the warehouse PC has:

| Requirement | Details |
|---|---|
| **Operating System** | Windows 10 or 11 |
| **Internet Connection** | Wi-Fi or Ethernet (must be active during scanning) |
| **Kodak Alaris Scanner** | Connected and working |
| **Python** | Version 3.10 or higher (installation steps below) |

---

## 🔧 Step 1: Install Python

> Skip this step if Python is already installed on the warehouse PC.

1. Open a web browser and go to: **https://www.python.org/downloads/**
2. Click the yellow **"Download Python"** button
3. Run the downloaded installer
4. **⚠️ IMPORTANT:** Check the box that says **"Add Python to PATH"** at the bottom of the installer
5. Click **"Install Now"**
6. Wait for installation to complete → Click **"Close"**

### ✅ Verify Python is installed:
Open **Command Prompt** (search "cmd" in Start Menu) and type:
```
python --version
```
You should see something like: `Python 3.11.x`

---

## 📂 Step 2: Copy the Warehouse Folder

1. Download or copy the **`warehouse_setup`** folder from the project repository:
   - **GitHub:** https://github.com/Thasmika/AI-Powered-Intelligent-Document-Processing-IDP-Platform
   - Navigate to the `warehouse_setup/` folder and download it

2. Place it on the warehouse PC at a simple location, for example:
   ```
   C:\EFL_Scanner\
   ```

3. After copying, the folder should look like this:
   ```
   C:\EFL_Scanner\
   ├── INSTALL.bat
   ├── START_SCANNER.bat
   ├── scanner_watcher.py
   ├── README.md
   ```

---

## ⚙️ Step 3: Run the Installer (One-Time Only)

1. Open the **`C:\EFL_Scanner\`** folder
2. **Right-click** on **`INSTALL.bat`**
3. Select **"Run as administrator"**
4. A black window will appear showing installation progress:
   ```
   EFL Global IDP - Warehouse Scanner Setup
   Installing required packages...
   Successfully installed requests watchdog
   Creating scanner folders...
   Setup Complete!
   ```
5. Press any key to close the window

### ✅ After installation, you should see two new folders:
```
C:\EFL_Scanner\
├── INSTALL.bat
├── START_SCANNER.bat
├── scanner_watcher.py
├── README.md
├── scanner_input/       ← NEW (empty)
└── scanner_uploaded/    ← NEW (empty)
```

---

## 🖨️ Step 4: Configure the Kodak Alaris Scanner

Configure your scanner software (Kodak Capture Pro / Kodak Alaris Smart Touch) to save scanned documents as PDF files into the **`scanner_input`** folder.

### For Kodak Capture Pro:
1. Open **Kodak Capture Pro** software
2. Go to **Job Setup** → **Output** tab
3. Set **File Type** to **PDF**
4. Set **Output Folder** to:
   ```
   C:\EFL_Scanner\scanner_input\
   ```
5. Click **Save** / **Apply**

### For Kodak Smart Touch:
1. Open **Kodak Alaris Smart Touch** settings
2. Select your scan profile
3. Change **Save To** location to:
   ```
   C:\EFL_Scanner\scanner_input\
   ```
4. Ensure **File Format** is set to **PDF**
5. Save the profile

---

## ▶️ Step 5: Start the Scanner Watcher

1. Open the **`C:\EFL_Scanner\`** folder
2. **Double-click** on **`START_SCANNER.bat`**
3. A black window will appear:

```
==================================================
  EFL Global IDP - Warehouse Scanner
==================================================
  Server : http://130.61.243.161:8003
  Watch  : C:\EFL_Scanner\scanner_input
  Backup : C:\EFL_Scanner\scanner_uploaded
==================================================

  Connecting to http://130.61.243.161:8003 ...
  CONNECTED to EFL Global IDP Server
  No pending PDFs found.

  WATCHING: C:\EFL_Scanner\scanner_input
  Scan a document to test the system.
--------------------------------------------------
```

> **⚠️ DO NOT close this black window!** Keep it open while scanning documents. Minimise it if needed.

---

## 🧪 Step 6: Test the Connection

1. Make sure `START_SCANNER.bat` is running (the black window is open)
2. Scan **one test document** with the Kodak scanner
3. Watch the black window — you should see:

```
  NEW SCAN DETECTED: scan_001.pdf
  Waiting 5 seconds for file to complete...
  UPLOADING: scan_001.pdf (2.3 MB)
  SUCCESS: scan_001.pdf uploaded and queued for AI processing
  BACKUP: Moved to scanner_uploaded/
```

4. Open your browser and go to: **http://130.61.243.161:8003**
5. The new document should appear in the dashboard!

---

## 🔄 Step 7: Auto-Start on Boot (Optional but Recommended)

So the manager doesn't have to manually start the script every morning:

1. Press **`Win + R`** on the keyboard
2. Type **`shell:startup`** and press **Enter**
3. A folder will open (this is the Windows Startup folder)
4. **Copy** the `START_SCANNER.bat` file from `C:\EFL_Scanner\` into this Startup folder
5. Done! The scanner watcher will now start automatically when the PC turns on.

---

## 📅 Daily Workflow for the Warehouse Manager

| Time | What to Do |
|---|---|
| **Morning** | Turn on the PC. The scanner watcher starts automatically (if Step 7 was done). Otherwise double-click `START_SCANNER.bat`. |
| **During the day** | Scan documents as normal with the Kodak scanner. Each scanned PDF is automatically uploaded to the cloud system within seconds. |
| **Check progress** | Open **http://130.61.243.161:8003** in any browser on any device to see all processed documents. |
| **End of day** | Shut down the PC as usual. No extra steps needed. |

---

## ❓ Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| **"Cannot reach server"** | No internet or server is down | Check the internet connection. Try opening http://130.61.243.161:8003 in a browser. |
| **Upload keeps retrying** | Temporary internet issue | The script automatically retries every 10 seconds. Just wait. |
| **PDF not detected** | Scanner not saving to the correct folder | Verify Kodak scanner output is set to `C:\EFL_Scanner\scanner_input\` |
| **"Python is not recognized"** | Python not in PATH | Reinstall Python and check "Add Python to PATH" |
| **Script closes immediately** | Python error | Open Command Prompt, navigate to `C:\EFL_Scanner\`, and run: `python scanner_watcher.py` to see the error message. |
| **Old documents re-uploading** | Files in scanner_input from yesterday | This is normal — leftover files are uploaded on startup, then moved to backup. |

---

## 📁 Understanding the Folders

```
C:\EFL_Scanner\
│
├── scanner_input/        ← Kodak scanner saves PDFs here
│   └── (files appear here temporarily during scanning)
│
├── scanner_uploaded/     ← Successfully uploaded PDFs are moved here
│   ├── scan_001.pdf      (backup copy)
│   ├── scan_002.pdf      (backup copy)
│   └── ...
│
├── INSTALL.bat           ← Run once during initial setup
├── START_SCANNER.bat     ← Run daily (or auto-start on boot)
├── scanner_watcher.py    ← The script that does the work
└── README.md             ← This guide
```

- **`scanner_input/`** → Temporary: files are here only until uploaded
- **`scanner_uploaded/`** → Permanent backup: all uploaded files are saved here

---

## 🌐 Accessing the Dashboard

Anyone on the network can view processed documents by opening this URL in any browser:

```
http://130.61.243.161:8003
```

The dashboard shows:
- ✅ All processed containers and gate passes
- 📂 Folder explorer with individual documents
- 📊 KPI metrics and statistics
- 🤖 AI chat assistant for document queries
- 📄 AI-generated reports

---

## 📞 Support

If you encounter issues that are not covered in the troubleshooting section above, contact the IT team with:
1. A screenshot of the error message in the black window
2. The name of the file that failed to upload
3. Whether the internet connection is working (can you open google.com?)
