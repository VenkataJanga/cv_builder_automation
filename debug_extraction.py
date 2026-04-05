#!/usr/bin/env python3
"""Debug script to see what text is extracted from the .doc file."""
from src.infrastructure.parsers.doc_extractor import extract_doc

cv_file = "data/storage/0b398e4f-d78d-4069-acfd-b724a77caab7_Ramesh_Yenugonda_Resume10yrs_Updated.doc"

print("Extracting text from .doc file...")
text = extract_doc(cv_file)

print(f"\nExtracted {len(text)} characters")
print("\n" + "="*70)
print("FIRST 2000 CHARACTERS:")
print("="*70)
print(text[:2000])
print("\n" + "="*70)
print("MIDDLE 2000 CHARACTERS:")
print("="*70)
mid = len(text) // 2
print(text[mid:mid+2000])

# Save to file
with open("extracted_text.txt", "w", encoding="utf-8") as f:
    f.write(text)

print("\n\nFull text saved to extracted_text.txt")
