# EFL Global IDP — Warehouse Scanner Setup Guide

## What's in this folder?
```
warehouse_setup/
├── INSTALL.bat          ← Run ONCE to install (right-click → Run as Admin)
├── START_SCANNER.bat    ← Double-click every morning to start
├── scanner_watcher.py   ← The actual script (don't touch this)
├── scanner_input/       ← Kodak scanner saves PDFs HERE
└── scanner_uploaded/    ← Successfully uploaded PDFs go here (backup)
```

## First-Time Setup (Do this ONCE)

### Step 1: Install Python
- Download from https://www.python.org/downloads/
- **IMPORTANT:** Check ✅ "Add Python to PATH" during installation

### Step 2: Copy this entire `warehouse_setup` folder to the warehouse PC
- Example location: `C:\EFL_Scanner\`

### Step 3: Run the installer
- Double-click `INSTALL.bat`
- This installs the required packages automatically

### Step 4: Configure Kodak Alaris Scanner
- Open Kodak Capture Pro settings
- Set the **output/save folder** to: `C:\EFL_Scanner\scanner_input\`
- Save settings

### Step 5: Test it
- Double-click `START_SCANNER.bat`
- Scan a document
- Check the dashboard: http://130.61.243.161:8003

## Daily Usage (Manager's Workflow)

1. **Turn on the PC** → `START_SCANNER.bat` runs (if set to auto-start)
2. **Scan documents** with Kodak scanner as normal
3. **That's it!** — PDFs upload automatically to the cloud
4. **View results** at http://130.61.243.161:8003

## Auto-Start on Boot (Optional)

1. Press `Win + R`, type `shell:startup`, press Enter
2. Copy `START_SCANNER.bat` into that folder
3. Now it starts automatically when the PC boots!

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot reach server" | Check internet connection |
| Upload keeps failing | The script retries automatically every 10 seconds |
| PDF not detected | Make sure scanner saves to `scanner_input/` folder |
| Script won't start | Make sure Python is installed with PATH enabled |
