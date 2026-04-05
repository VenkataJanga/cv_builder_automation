"""
Test transcript parsing with actual voice input
"""

from src.infrastructure.parsers.transcript_cv_parser import TranscriptCVParser
import json

# Your actual voice transcript
TRANSCRIPT = """
My name is Venkata Kiran Kumar Janga. My portal ID is 229164. My employee ID is 1022134.
My email ID is VenkataKiranKumarJanga at the rate of global.entitydata.com. 
My professional summary is, have been working with IT industry past 16 years for developing, deploying for enterprises applications. 
My educational qualifications are, I completed Master of Science, Master of Computer of Applications from ITM University. 
Before that have completed my degree in Bachelor of Computer Science with distinction. Before I completed my 12th standard at 75%. 
I completed my 10th standard at 60%. 
I know languages in the English. 
My primary skill is Java Spring Spring Boot and Microservices. 
My secondary skill is Python, PySpark, Databricks, LangChain, LangGraph and LangSmith, NumPy and Pandas libraries. 
AI frameworks such as Cruella and Autogen frameworks. 
I well versed experience in databases such as MySQL, Postgres and DB2. 
My cloud experience, AWS and Azure services. 
In AWS, IAM, Glue, EC2, EventBridge, RDS, Lambda services. 
In Azure, I have a good experience in handling with services such as Blob, ADLS, Key Vault, AI Open Services, AI Foundry and ADF.
Thank you.
"""

def test_transcript_parsing():
    parser = TranscriptCVParser()
    result = parser.parse(TRANSCRIPT)
    
    print("=" * 80)
    print("TRANSCRIPT PARSING TEST")
    print("=" * 80)
    
    print("\nParsed CV Data:")
    print(json.dumps(result, indent=2))
    
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    # Verify key fields
    personal = result.get("personal_details", {})
    skills = result.get("skills", {})
    summary = result.get("summary", {})
    
    checks = []
    
    # Name
    name = personal.get("full_name", "")
    checks.append(("Name extracted", "Venkata" in name and "Janga" in name, f"Got: {name}"))
    
    # Employee ID (should pick employee_id over portal_id)
    emp_id = personal.get("employee_id", "")
    checks.append(("Employee ID extracted", emp_id == "1022134", f"Got: {emp_id}"))
    
    # Email
    email = personal.get("email", "")
    checks.append(("Email extracted", "@global.entitydata.com" in email, f"Got: {email}"))
    
    # Primary skills
    primary = skills.get("primary_skills", [])
    checks.append(("Primary skills extracted", len(primary) >= 3, f"Got {len(primary)} skills: {primary}"))
    checks.append(("Java in primary skills", "Java" in str(primary), f"Primary: {primary}"))
    checks.append(("Spring Boot in primary skills", "Spring Boot" in str(primary), f"Primary: {primary}"))
    checks.append(("Microservices in primary skills", "Microservices" in str(primary), f"Primary: {primary}"))
    
    # Secondary skills
    secondary = skills.get("secondary_skills", [])
    checks.append(("Secondary skills extracted", len(secondary) >= 5, f"Got {len(secondary)} skills: {secondary}"))
    checks.append(("Python in secondary skills", "Python" in str(secondary), f"Secondary: {secondary}"))
    checks.append(("PySpark in secondary skills", "PySpark" in str(secondary), f"Secondary: {secondary}"))
    checks.append(("LangChain in secondary skills", "LangChain" in str(secondary), f"Secondary: {secondary}"))
    
    # Print results
    passed = 0
    failed = 0
    for check_name, passed_check, details in checks:
        status = "[PASS]" if passed_check else "[FAIL]"
        print(f"\n{status}: {check_name}")
        if not passed_check or True:  # Always show details
            print(f"  {details}")
        if passed_check:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} checks")
    print("=" * 80)
    
    if failed == 0:
        print("\nALL CHECKS PASSED!")
    else:
        print(f"\n{failed} checks failed - parser needs more work")
    
    return failed == 0

if __name__ == "__main__":
    success = test_transcript_parsing()
    exit(0 if success else 1)
