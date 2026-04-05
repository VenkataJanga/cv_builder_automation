from typing import Optional
import subprocess
import os
import tempfile
import shutil

def extract_doc(file_path: str) -> str:
    """
    Extract text from a .doc file (old Microsoft Word format).
    
    Tries multiple methods in order of reliability.
    """
    
    # Method 1: Try using win32com on Windows (most reliable for .doc files)
    try:
        import win32com.client
        import pythoncom
        import os
        
        # Get absolute path
        abs_path = os.path.abspath(file_path)
        
        pythoncom.CoInitialize()
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            
            # Open document
            doc = word.Documents.Open(abs_path)
            
            # Extract text from all content including tables
            text = doc.Content.Text
            
            # Also extract text from tables separately as they might not be in Content
            table_text = []
            for table in doc.Tables:
                for row in table.Rows:
                    row_text = []
                    for cell in row.Cells:
                        cell_text = cell.Range.Text.strip()
                        # Keep \x07 character as it's used for parsing skills sections
                        # Only remove carriage return before \x07
                        cell_text = cell_text.replace('\r\x07', '\x07')
                        if cell_text:
                            row_text.append(cell_text)
                    if row_text:
                        # Use \x07 as separator to maintain table structure
                        table_text.append('\x07'.join(row_text))
            
            # Close document and Word
            doc.Close(False)
            word.Quit()
            pythoncom.CoUninitialize()
            
            # Combine text and table text
            final_text = text
            if table_text:
                final_text += '\n\n' + '\n'.join(table_text)
            
            if final_text.strip() and len(final_text.strip()) > 50:
                return final_text
        except Exception as e:
            pythoncom.CoUninitialize()
            raise e
    except Exception as ex:
        # Continue to next method
        pass
    
    # Method 2: Try using antiword (command-line tool) - good for simple docs
    try:
        result = subprocess.run(
            ['antiword', file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            if len(result.stdout.strip()) > 50:
                return result.stdout
    except Exception:
        pass
    
    # Method 3: Try using textract library
    try:
        import textract
        text = textract.process(file_path).decode('utf-8')
        # Check for binary garbage
        if text.strip() and not text.startswith('ࡱ') and len(text.strip()) > 50:
            return text
    except Exception:
        pass
    
    # Method 4: Try using olefile with improved extraction
    try:
        import olefile
        
        ole = olefile.OleFileIO(file_path)
        
        # Try to read WordDocument stream
        if ole.exists('WordDocument'):
            word_stream = ole.openstream('WordDocument').read()
            
            # Extract text using improved heuristic
            text_parts = []
            current = bytearray()
            
            for byte in word_stream:
                # Printable ASCII + tab, newline, carriage return
                if 32 <= byte <= 126 or byte in (9, 10, 13):
                    current.append(byte)
                else:
                    if len(current) > 2:  # Keep strings longer than 2 chars
                        decoded = current.decode('ascii', errors='ignore').strip()
                        if decoded:
                            text_parts.append(decoded)
                    current = bytearray()
            
            if len(current) > 2:
                decoded = current.decode('ascii', errors='ignore').strip()
                if decoded:
                    text_parts.append(decoded)
            
            ole.close()
            
            # Clean and join text parts
            cleaned_parts = []
            for part in text_parts:
                # Filter out very short or suspicious parts
                if len(part) > 2 and not all(c in '.,;:!?-_' for c in part):
                    cleaned_parts.append(part)
            
            text = ' '.join(cleaned_parts)
            if text.strip() and len(text) > 50:
                return text
    except Exception:
        pass
    
    # If all methods fail, provide helpful error
    raise ValueError(
        "Could not extract text from .doc file (old Word format). "
        "Please convert your file to .docx format using Microsoft Word: "
        "Open the file → File → Save As → Choose 'Word Document (.docx)'. "
        "Alternatively, use a .docx or .pdf file instead."
    )
