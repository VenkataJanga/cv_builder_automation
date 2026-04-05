from src.infrastructure.parsers.doc_extractor import extract_doc
import re
import json

# Extract text
text = extract_doc('data/storage/00a35c50-7ed6-40c0-b098-94e97cc1b424_Ramesh_Yenugonda_Resume10yrs_Updated.doc')

# Count Hanover Insurance occurrences
matches = list(re.finditer(r'Hanover Insurance', text, re.IGNORECASE))
print(f'Hanover Insurance appears {len(matches)} times in the CV text')

# Show context around each occurrence
print('\n' + '='*80)
for i, match in enumerate(matches):
    print(f'\n--- Occurrence {i+1} (position {match.start()}):')
    context = text[max(0, match.start()-150):match.end()+150]
    print(context)
    print('-'*80)

# Check extracted projects
with open('final_extraction_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

projects = data['project_experience']
hanover_projects = [p for p in projects if 'Hanover' in p.get('project_name', '')]

print('\n' + '='*80)
print(f'\nExtracted Hanover projects: {len(hanover_projects)}')
for i, proj in enumerate(hanover_projects):
    print(f'\nProject {i+1}:')
    print(f"  Name: {proj.get('project_name')}")
    print(f"  Client: {proj.get('client')}")
    print(f"  Role: {proj.get('role')}")
    print(f"  Description (first 100 chars): {proj.get('description', '')[:100]}")
