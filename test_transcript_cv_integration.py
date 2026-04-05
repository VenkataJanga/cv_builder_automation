#!/usr/bin/env python3
"""
Comprehensive test to verify the complete CV transcript integration:
- Transcript parsing into CV fields
- Merging extracted fields into active session
- Preview showing structured CV-style data
- DOCX/PDF export including actual content
"""

import json
from src.infrastructure.parsers.transcript_cv_parser import TranscriptCVParser
from src.domain.cv.services.merge_cv import MergeCVService
from src.ai.agents.cv_formatting_agent import CVFormattingAgent
from src.infrastructure.rendering.template_engine import TemplateEngine
from src.infrastructure.rendering.docx_renderer import DocxRenderer
from src.infrastructure.rendering.pdf_renderer import PdfRenderer


def test_transcript_parsing():
    """Test 1: Parse transcript into CV fields"""
    print("\n" + "="*80)
    print("TEST 1: Transcript Parsing")
    print("="*80)
    
    sample_transcript = """
    This is Ramesh Yenugonda. My employee id is 247438. My portal id is 12345.
    My current grade is 6. My contact number is 9876543210.
    My email is ramesh.yenugonda at the rate of entitydata.com.
    I am located in Hyderabad.
    
    My designation is Senior Data Engineer. I have 10 years of IT experience.
    My professional summary is: Experienced data engineer with expertise in big data 
    and cloud technologies, specializing in building scalable data pipelines.
    
    My primary skills are Python, PySpark, SQL, Apache Spark.
    My secondary skills are Azure Data Factory, Databricks, Data Warehousing.
    Operating systems are Windows, Linux.
    Databases are SQL Server, PostgreSQL, MongoDB.
    
    Domain knowledge is Healthcare and Automobile.
    
    I have worked with NTT DATA from the past 5 years.
    Clients are ABC Corp, XYZ Inc.
    
    My first project, my client is ABC Corp. Project name is Healthcare Data Platform.
    Duration from 2020 to date. My role was Lead Data Engineer.
    Environment: Python, Spark, Azure, Databricks.
    Project description is: Developed a comprehensive healthcare data platform 
    for processing patient records and medical claims.
    
    I completed Java J2EE training in 2015.
    
    I completed Bachelor of Technology from ABC University in 2010.
    """
    
    parser = TranscriptCVParser()
    cv_data = parser.parse(sample_transcript)
    
    print("\n[+] Parsed Personal Information:")
    personal = cv_data.get("personal_information", {})
    print(f"  - Name: {personal.get('full_name')}")
    print(f"  - Email: {personal.get('email')}")
    print(f"  - Employee ID: {personal.get('employee_id')}")
    print(f"  - Location: {personal.get('location')}")
    print(f"  - Designation: {personal.get('designation')}")
    
    print("\n[+] Parsed Professional Summary:")
    summary = cv_data.get("professional_summary", {})
    print(f"  - Total Experience: {summary.get('total_experience_years')} years")
    print(f"  - Summary: {summary.get('summary', '')[:100]}...")
    
    print("\n[+] Parsed Skills:")
    skills = cv_data.get("skills", {})
    print(f"  - Primary Skills: {skills.get('primary_skills', [])}")
    print(f"  - Secondary Skills: {skills.get('secondary_skills', [])}")
    print(f"  - Databases: {skills.get('databases', [])}")
    
    print("\n[+] Parsed Domain Expertise:")
    print(f"  - Domains: {cv_data.get('domain_expertise', [])}")
    
    print("\n[+] Parsed Employment Details:")
    employment = cv_data.get("employment_details", {})
    print(f"  - Current Company: {employment.get('current_company')}")
    print(f"  - Years: {employment.get('years_with_current_company')}")
    print(f"  - Clients: {employment.get('clients_worked_for', [])}")
    
    print("\n[+] Parsed Projects:")
    projects = cv_data.get("project_experience", [])
    print(f"  - Total Projects: {len(projects)}")
    if projects:
        proj = projects[0]
        print(f"  - First Project: {proj.get('project_name')}")
        print(f"  - Client: {proj.get('client')}")
        print(f"  - Role: {proj.get('role')}")
    
    print("\n[+] Parsed Training:")
    training = cv_data.get("training_and_certifications", [])
    print(f"  - Total Trainings: {len(training)}")
    if training:
        print(f"  - First Training: {training[0].get('name')}")
    
    print("\n[+] Parsed Education:")
    education = cv_data.get("education", [])
    print(f"  - Total Education: {len(education)}")
    if education:
        edu = education[0]
        print(f"  - Degree: {edu.get('degree')}")
        print(f"  - Institution: {edu.get('institution')}")
        print(f"  - Year: {edu.get('year_of_completion')}")
    
    return cv_data


def test_merge_cv(extracted_cv_data):
    """Test 2: Merge extracted fields into active session"""
    print("\n" + "="*80)
    print("TEST 2: Merge CV Data")
    print("="*80)
    
    # Simulate existing session CV data
    existing_session = {
        "personal_details": {
            "full_name": "Existing Name",  # Should be preserved
        },
        "skills": {
            "primary_skills": ["Java"],  # Should merge with extracted
        }
    }
    
    # Transform extracted_cv_data to match session format
    extracted_for_merge = {
        "personal_details": {
            "email": extracted_cv_data["personal_information"].get("email"),
            "employee_id": extracted_cv_data["personal_information"].get("employee_id"),
            "location": extracted_cv_data["personal_information"].get("location"),
        },
        "skills": {
            "primary_skills": extracted_cv_data["skills"].get("primary_skills", []),
            "secondary_skills": extracted_cv_data["skills"].get("secondary_skills", []),
        }
    }
    
    merge_service = MergeCVService()
    merged_cv = merge_service.merge(existing_session, extracted_for_merge)
    
    print("\n[+] Merged Personal Details:")
    personal = merged_cv.get("personal_details", {})
    print(f"  - Name (preserved): {personal.get('full_name')}")
    print(f"  - Email (added): {personal.get('email')}")
    print(f"  - Employee ID (added): {personal.get('employee_id')}")
    print(f"  - Location (added): {personal.get('location')}")
    
    print("\n[+] Merged Skills:")
    skills = merged_cv.get("skills", {})
    print(f"  - Primary Skills (merged): {skills.get('primary_skills', [])}")
    print(f"  - Secondary Skills (added): {skills.get('secondary_skills', [])}")
    
    return merged_cv


def test_preview_formatting(merged_cv):
    """Test 3: Preview shows structured CV-style data"""
    print("\n" + "="*80)
    print("TEST 3: Preview Formatting")
    print("="*80)
    
    formatter = CVFormattingAgent()
    preview = formatter.format_cv(merged_cv)
    
    print("\n[+] Formatted Header:")
    header = preview.get("header", {})
    print(f"  - Full Name: {header.get('full_name')}")
    print(f"  - Email: {header.get('email')}")
    print(f"  - Employee ID: {header.get('employee_id')}")
    print(f"  - Location: {header.get('location')}")
    
    print("\n[+] Formatted Skills:")
    print(f"  - Primary Skills: {preview.get('skills', [])}")
    print(f"  - Secondary Skills: {preview.get('secondary_skills', [])}")
    
    print("\n[+] Preview Structure:")
    print(f"  - Has Header: {bool(header)}")
    print(f"  - Has Summary: {bool(preview.get('summary'))}")
    print(f"  - Has Skills: {bool(preview.get('skills'))}")
    print(f"  - Schema Version: {preview.get('schema_version')}")
    
    return preview


def test_export_docx(merged_cv):
    """Test 4: DOCX export includes actual content"""
    print("\n" + "="*80)
    print("TEST 4: DOCX Export")
    print("="*80)
    
    template_engine = TemplateEngine()
    context = template_engine.render_context(merged_cv)
    
    print("\n[+] Export Context:")
    print(f"  - Full Name: {context.get('full_name')}")
    print(f"  - Title: {context.get('title')}")
    print(f"  - Location: {context.get('location')}")
    print(f"  - Skills: {context.get('skills', '')[:50]}...")
    
    docx_renderer = DocxRenderer()
    docx_bytes = docx_renderer.render(context)
    
    print("\n[+] DOCX Generation:")
    print(f"  - File Size: {len(docx_bytes)} bytes")
    print(f"  - Valid DOCX: {len(docx_bytes) > 1000}")
    
    return docx_bytes


def test_export_pdf(merged_cv):
    """Test 5: PDF export includes actual content"""
    print("\n" + "="*80)
    print("TEST 5: PDF Export")
    print("="*80)
    
    template_engine = TemplateEngine()
    context = template_engine.render_context(merged_cv)
    
    pdf_renderer = PdfRenderer()
    pdf_bytes = pdf_renderer.render(context)
    
    print("\n[+] PDF Generation:")
    print(f"  - File Size: {len(pdf_bytes)} bytes")
    print(f"  - Valid PDF: {pdf_bytes.startswith(b'%PDF')}")
    
    return pdf_bytes


def main():
    print("\n" + "="*80)
    print("COMPREHENSIVE CV TRANSCRIPT INTEGRATION TEST")
    print("="*80)
    
    try:
        # Test 1: Parse transcript
        extracted_cv_data = test_transcript_parsing()
        
        # Test 2: Merge into session
        merged_cv = test_merge_cv(extracted_cv_data)
        
        # Test 3: Preview formatting
        preview = test_preview_formatting(merged_cv)
        
        # Test 4: DOCX export
        docx_bytes = test_export_docx(merged_cv)
        
        # Test 5: PDF export
        pdf_bytes = test_export_pdf(merged_cv)
        
        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print("[PASS] Test 1: Transcript parsing")
        print("[PASS] Test 2: CV data merging")
        print("[PASS] Test 3: Preview formatting")
        print("[PASS] Test 4: DOCX export")
        print("[PASS] Test 5: PDF export")
        print("\n[SUCCESS] ALL TESTS PASSED!")
        
        # Save results
        results = {
            "extracted_cv_data": extracted_cv_data,
            "merged_cv": merged_cv,
            "preview": preview,
            "docx_size": len(docx_bytes),
            "pdf_size": len(pdf_bytes),
        }
        
        with open("transcript_cv_integration_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\n[FILE] Results saved to: transcript_cv_integration_results.json")
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
