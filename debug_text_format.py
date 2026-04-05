import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.infrastructure.parsers.doc_extractor import extract_doc

# Parse the document
doc_path = "data/storage/00a35c50-7ed6-40c0-b098-94e97cc1b424_Ramesh_Yenugonda_Resume10yrs_Updated.doc"
text = extract_doc(doc_path)

# Find and print the Training section with visible special characters
import re

# Find Training section
training_match = re.search(r"Training.*?Certifications.*?(.*?)Qualification", text, re.IGNORECASE | re.DOTALL)
if training_match:
    training_section = training_match.group(0)[:1000]
    print("=" * 80)
    print("TRAINING SECTION (first 1000 chars):")
    print("=" * 80)
    # Show with repr to see special characters
    print(repr(training_section))
    print("\n" + "=" * 80)

# Find Qualification section  
qual_match = re.search(r"Qualification.*?Details.*?(.*?)(?:NAME:|$)", text, re.IGNORECASE | re.DOTALL)
if qual_match:
    qual_section = qual_match.group(0)[:1500]
    print("QUALIFICATION SECTION (first 1500 chars):")
    print("=" * 80)
    print(repr(qual_section))
    print("\n" + "=" * 80)

# Find Experience Details section
exp_match = re.search(r"Experience\s+Details.*?(.*?)Project Details", text, re.IGNORECASE | re.DOTALL)
if exp_match:
    exp_section = exp_match.group(0)[:1000]
    print("EXPERIENCE DETAILS SECTION (first 1000 chars):")
    print("=" * 80)
    print(repr(exp_section))
