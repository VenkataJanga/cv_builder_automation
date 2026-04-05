#!/usr/bin/env python3
"""Test professional summary extraction from transcript."""

from src.infrastructure.parsers.transcript_cv_parser import TranscriptCVParser

def test_summary_extraction():
    """Test that professional summary is correctly extracted."""
    
    # Sample transcript with professional summary
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
    result = parser.parse(transcript)
    
    print("=" * 80)
    print("PROFESSIONAL SUMMARY EXTRACTION TEST")
    print("=" * 80)
    
    summary_data = result.get("professional_summary", {})
    summary_text = summary_data.get("summary", "")
    total_exp = summary_data.get("total_experience_years", 0)
    
    print(f"\n[+] Total Experience: {total_exp} years")
    print(f"\n[+] Summary Text:")
    print(f"  {summary_text}")
    print(f"\n[+] Summary Length: {len(summary_text)} characters")
    
    # Verify extraction
    assert total_exp == 16, f"Expected 16 years, got {total_exp}"
    assert len(summary_text) > 50, f"Summary too short: {len(summary_text)} chars"
    assert "16 years" in summary_text.lower() or "experience" in summary_text.lower(), "Summary missing experience mention"
    
    print("\n" + "=" * 80)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("=" * 80)
    
    return result

if __name__ == "__main__":
    result = test_summary_extraction()
