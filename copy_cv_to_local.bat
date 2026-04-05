@echo off
echo ========================================
echo CV File Copy Script
echo ========================================
echo.
echo This script will copy your CV file from OneDrive to a local folder
echo to avoid sync lock errors during upload.
echo.

REM Create local folder if it doesn't exist
if not exist "C:\cv_upload_temp" (
    echo Creating local folder: C:\cv_upload_temp\
    mkdir "C:\cv_upload_temp"
    echo Folder created successfully.
) else (
    echo Local folder already exists: C:\cv_upload_temp\
)

echo.
echo ========================================
echo INSTRUCTIONS:
echo ========================================
echo.
echo 1. This script created folder: C:\cv_upload_temp\
echo.
echo 2. Now manually copy your CV file to this folder:
echo    From: C:\Users\229164\OneDrive - NTT DATA, Inc\Backup\VW_TEAM\Interviews\10-02-2025\NTTD_Pankaj_Java_Microservices.docx
echo    To:   C:\cv_upload_temp\
echo.
echo 3. After copying, in the CV Builder:
echo    - Click "Choose File"
echo    - Navigate to: C:\cv_upload_temp\
echo    - Select your file
echo    - Click "Upload and Merge"
echo.
echo 4. The upload will work without OneDrive sync errors!
echo.
echo ========================================
echo Opening both folders for you now...
echo ========================================
echo.

REM Open the destination folder
start "" "C:\cv_upload_temp"

REM Open the source folder
start "" "C:\Users\229164\OneDrive - NTT DATA, Inc\Backup\VW_TEAM\Interviews\10-02-2025"

echo.
echo NEXT STEPS:
echo 1. Copy NTTD_Pankaj_Java_Microservices.docx from the OneDrive folder
echo 2. Paste it into C:\cv_upload_temp\
echo 3. Upload from C:\cv_upload_temp\ in the CV Builder
echo.
echo Press any key to exit...
pause >nul
