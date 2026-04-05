# CV Upload Issue - OneDrive Sync Error

## Problem
Error: **0x800701AA - The cloud operation was not completed before the time-out period expired**

The file you're trying to upload is stored in a OneDrive folder and is currently syncing. Windows won't allow the file to be read while it's syncing.

---

## ✅ SOLUTION 1: Copy File to Local Folder (Recommended)

### Step 1: Create a local folder
1. Open File Explorer
2. Go to: `C:\`
3. Create a new folder: `C:\temp_cv_uploads`

### Step 2: Copy your CV file
1. Find your CV file: "Lokesh Kumar Resume.docx"
2. **Copy** it (don't move) to: `C:\temp_cv_uploads\`
3. Wait for the copy to complete

### Step 3: Upload from local folder
1. In the CV Builder demo
2. Click "Choose File" under "Upload Existing CV"
3. Navigate to: `C:\temp_cv_uploads\`
4. Select your CV file
5. Click "Upload and Merge"

This will work because the file in `C:\temp_cv_uploads\` is NOT in OneDrive and won't have sync conflicts.

---

## ✅ SOLUTION 2: Wait for OneDrive Sync

1. Look at the file in File Explorer
2. Check if it shows a **cloud icon** or **sync status**
3. Wait until it shows a **green checkmark** ✓ (fully synced)
4. Then try uploading again

---

## ✅ SOLUTION 3: Pause OneDrive Temporarily

1. Right-click the **OneDrive icon** in system tray (bottom-right of screen)
2. Click **Settings** (gear icon)
3. Go to **Sync and backup** tab
4. Click **Pause sync**
5. Choose **2 hours**
6. Try uploading your CV again
7. Remember to resume sync later!

---

## ✅ SOLUTION 4: Use Desktop or Downloads Folder

If your CV is in a OneDrive-synced folder, copy it to:
- `C:\Users\229164\Desktop` (if Desktop is not in OneDrive)
- `C:\Users\229164\Downloads`
- Any local folder outside OneDrive

Then upload from there.

---

## How to Check if Folder is in OneDrive

Your current working directory is:
```
c:\Users\229164\OneDrive - NTT DATA, Inc\AI\cv_builder_automation\
```

**This IS a OneDrive folder!** (notice "OneDrive" in the path)

Files in this location will sync with OneDrive cloud, which can cause this error.

---

## Quick Test

### Try This Simple Test:
1. Create: `C:\test_cv\`
2. Copy any .docx file there
3. Upload that file
4. It should work without sync errors

---

## For Testing Purposes

If you don't have a CV handy, you can:

1. **Create a simple test file:**
   - Open Word
   - Type: "Name: John Doe\nExperience: 5 years\nSkills: Python, Java"
   - Save as: `C:\test_cv\test_resume.docx`
   - Upload this file

2. **Use one of the uploaded files from data/storage:**
   - Your project already has sample CVs in: `data/storage/`
   - Example: `NavyaJanga_247438.docx`
   - These are already uploaded and parsed successfully before

---

## Technical Details

### Why This Happens:
- Windows locks files that are actively syncing with OneDrive
- The application cannot read the file while it's locked
- OneDrive sync can take time depending on file size and connection

### What the Application Does:
1. User selects file in browser
2. Browser sends file to server
3. Server tries to write file to: `data/storage/`
4. Server reads the file to parse it
5. **Error occurs** if file is locked by OneDrive sync

### Not a Code Bug:
- The upload code is correct
- The error is from Windows/OneDrive, not the application
- Solution is to use a non-syncing file location

---

## Recommended Workflow

For smooth CV upload testing:

1. ✅ Keep test CV files in: `C:\test_cv\`
2. ✅ Or use Desktop/Downloads if they're not in OneDrive
3. ✅ Upload from these local folders
4. ✅ No sync conflicts

---

## After Upload Success

Once uploaded successfully, you should see:
- **Response Box**: Shows parsed_data and cv_data
- **Preview Box**: Updates with merged CV information
- **Chat**: Shows "Uploaded CV parsed and merged into current session"

The parsed data will include:
- Full name
- Summary/Profile
- Skills
- Experience
- Education
- Certifications
- Projects

---

## If Still Having Issues

1. Check the **Console** (F12) for error messages
2. Check the **Response Box** for server error details
3. Verify file is:
   - .docx or .pdf format
   - Less than 10MB
   - Not password-protected
   - Not corrupted

---

## Alternative: Use Sample Files

Your project already has successfully uploaded CVs:
```
data/storage/13b222ee-5e6e-4f28-8af2-0d764a22748f_NavyaJanga_247438.docx
data/storage/6793ef3b-fcc5-4bc5-a03b-dc21dcf65af0_NavyaJanga_247438.docx
data/storage/b8b2afb5-11ce-480b-a1dd-9f3da4e58750_NavyaJanga_247438.docx
data/storage/d8afb2b9-5d55-428f-9631-7a1f5d5bd000_NavyaJanga_247438.docx
```

These files are already parsed and working. You can use these for testing if needed.
