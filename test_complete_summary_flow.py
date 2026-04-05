#!/usr/bin/env python3
"""Test complete flow: parse transcript -> merge -> preview -> export."""

import json
from src.infrastructure.parsers.transcript_cv_parser import TranscriptCVParser
from src.domain.cv.services.merge_cv import MergeCVService
from src.application.services.preview_service import PreviewService
from src.infrastructure.rendering.template_engine import TemplateEngine
from src.infrastructure.rendering.docx_renderer import DocxRenderer
from src.infrastructure.rendering.pdf_renderer import PdfRenderer


def test_complete_flow():
    """Test complete professional summary flow."""
    
    print("=" * 80)
    print("COMPLETE PROFESSIONAL SUMMARY FLOW TEST")
    print("=" * 80)
    
    # Step 1: Parse transcript
    print("\n[STEP 1] Parsing transcript...")
    transcript = """
    My name is Venkata Kiran Kumar Janga. My portal ID is 229164. My current grade is 10. 
    My contact number is 9881248765. My email ID is Venkata.Janga at the rate nttdata.com. 
    
    My professional summary, I have been 16 years of experience in the IT industry for developing, 
    deploying and operational support for enterprise grade applications using Java, Python, PySpark, 
    Databricks, AWS and Azure cloud services, developed web-based and enterprise-based applications. 
    
    My primary skill is Java, Spring Boot and microservices. 
    My secondary skill is Python, Lanchain, Langroth, NumPy, Pandas, PySpark, Databricks.
    """
    
    parser = TranscriptCVParser()
    parsed_data = parser.parse(transcript)
    
    print(f"  [+] Parsed data keys: {list(parsed_data.keys())}")
    summary_data = parsed_data.get("professional_summary", {})
    print(f"  [+] Professional summary: {summary_data.get('summary', '')[:100]}...")
    print(f"  [+] Total experience: {summary_data.get('total_experience_years')} years")
    
    # Step 2: Merge into session
    print("\n[STEP 2] Merging into session...")
    existing_session = {
        "session_id": "test-session-123",
        "personal_information": {},
        "skills": {},
    }
    
    merge_service = MergeCVService()
    merged_data = merge_service.merge(existing_session, parsed_data)
    
    print(f"  [+] Merged data keys: {list(merged_data.keys())}")
    merged_summary = merged_data.get("professional_summary", {})
    print(f"  [+] Merged summary exists: {bool(merged_summary.get('summary'))}")
    
    # Step 3: Generate preview
    print("\n[STEP 3] Generating preview...")
    preview_service = PreviewService()
    preview_data = preview_service.build_preview(merged_data)
    
    print(f"  [+] Preview keys: {list(preview_data.keys())}")
    preview_summary = preview_data.get("summary", "")
    print(f"  [+] Preview summary: {preview_summary[:100]}...")
    print(f"  [+] Preview summary length: {len(preview_summary)} characters")
    
    # Step 4: Test template engine
    print("\n[STEP 4] Testing template engine...")
    template_engine = TemplateEngine()
    context = template_engine.render_context(merged_data)
    
    print(f"  [+] Context keys: {list(context.keys())}")
    context_summary = context.get("summary", "")
    print(f"  [+] Context summary: {context_summary[:100]}...")
    
    # Step 5: Test DOCX export
    print("\n[STEP 5] Testing DOCX export...")
    docx_renderer = DocxRenderer()
    docx_bytes = docx_renderer.render(context)
    print(f"  [+] DOCX size: {len(docx_bytes)} bytes")
    print(f"  [+] DOCX generated successfully")
    
    # Step 6: Test PDF export
    print("\n[STEP 6] Testing PDF export...")
    pdf_renderer = PdfRenderer()
    pdf_bytes = pdf_renderer.render(context)
    print(f"  [+] PDF size: {len(pdf_bytes)} bytes")
    print(f"  [+] PDF generated successfully")
    
    # Verify all steps
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    assert summary_data.get("summary"), "❌ Summary not extracted from transcript"
    print("[+] Summary extracted from transcript")
    
    assert merged_summary.get("summary"), "❌ Summary not in merged data"
    print("[+] Summary present in merged data")
    
    assert len(preview_summary) > 50, "❌ Summary not in preview or too short"
    print("[+] Summary present in preview")
    
    assert len(context_summary) > 50, "❌ Summary not in template context"
    print("[+] Summary present in template context")
    
    assert len(docx_bytes) > 1000, "❌ DOCX export failed"
    print("[+] DOCX export includes data")
    
    assert len(pdf_bytes) > 1000, "❌ PDF export failed"
    print("[+] PDF export includes data")
    
    print("\n" + "=" * 80)
    print("[SUCCESS] ALL FLOW TESTS PASSED!")
    print("=" * 80)
    
    # Save test output
    test_output = {
        "parsed_data": {
            "personal_information": parsed_data.get("personal_information", {}),
            "professional_summary": parsed_data.get("professional_summary", {}),
            "skills": parsed_data.get("skills", {}),
        },
        "preview_data": {
            "header": preview_data.get("header", {}),
            "summary": preview_data.get("summary", ""),
            "skills": preview_data.get("skills", [])[:5],
            "secondary_skills": preview_data.get("secondary_skills", [])[:5],
        },
        "export_sizes": {
            "docx_bytes": len(docx_bytes),
            "pdf_bytes": len(pdf_bytes),
        }
    }
    
    with open("test_complete_summary_flow_output.json", "w") as f:
        json.dump(test_output, f, indent=2)
    print("\n[+] Test output saved to test_complete_summary_flow_output.json")


if __name__ == "__main__":
    test_complete_flow()
