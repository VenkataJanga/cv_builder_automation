"""Test regex-based CV extraction with actual voice input."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.parsers.transcript_cv_parser import TranscriptCVParser
import json

# Actual voice input from user
VOICE_INPUT = """My name is Venkata Kiran Kumar Janga. My portal ID is 229164. My current grade is 10. My contact number is 991248765. 
My email id is venkata.janga at the rate nttdata.com. My professional summary is I have been 16 years of experience in the IT industry 
for developing, deploying and operational support for enterprise grade applications using Java, Python, PySpark, Databricks, 
AWS, Azure cloud services. Developed web-based enterprise-based applications. My primary skill is Java, Spring, Spring Boot, 
Microservices. My secondary skill is Python, Microservices, Lanchain, Langsmith, Langgraph, NumPy, Pandas, PySpark, Databricks.
 My AI frameworks are Autogen crew AI frameworks coming to the operating systems. I well-versed Windows and Linux. Database side I have 
 good experience in SQL, MySQL, Postgres, DB2, Oracle. I worked on domains in healthcare, transport, automobile industry and insurance domain. 
 Currently, my designation is system intelligence advisor. My current location is in Hyderabad. I worked for nttdata for past 5 years with 
 clients Daimler truck, BMW and Volkswagen. Now coming to my project details. My first project is Rekostack system. Current client is John Deere. 
 My project description is the parts which are available in the store to purchase to the customers. Our application gives advice to the dealer 
 in which season what kind of parts are recommended to the store. It is not useful for all the dealers. It is losing the money and space 
 if you keep non-moving parts into the store. So to overcome this, which we have done, we have developed a Java-based application and alerts 
 come to the dealer based on the sales which is done, based on the past history. We are suggesting to the dealer what type, when, what season, 
 which type of parts is required to the store. So my role in this project, I co-developer, designed an application deployed in CICD pipelines 
 using Jenkins. I developed UI screens. I developed backend data scripts, DTO layers. I written some unit test cases. My second project is human
 healthcare. Client is US. The project description is the client is currently quantity assisted data is being loaded every 30 minutes.
 The patient it is. The data from the staging tables reporting the data. Table occurs once in a day after business hours. 
 My role in this project as a developer, keep tracking the source data tables into silver tables by using cleaning, cleansing, 
 and processing. Coming to my application, role here is a developer. Coming to my qualifications, that means educational qualifications. 
 I have completed Master of Computer Science, branches computers. My year of passing is 2007. The name of the college is ITM. University name 
 is Kakatiya University. My second educational qualification is Bachelor of Science, that means branch is computers. 
 My college name is Sri Chaitanya Degree College. University name is Kakatiya University. I got 59%. I have completed my 12th standard. 
 Branch is MPC. College is Sri Chaitanya Junior College. University name is Board of Intermediate. I got 59%. I have completed 10th standard. 
 School name is ZPPSI School.
 University name is boards of secondary. Year of passing is 2000. I got the 80%. Thank you."""


def test_regex_extraction():
    """Test the regex-based extraction."""
    print("=" * 80)
    print("REGEX-BASED CV EXTRACTION TEST")
    print("=" * 80)
    print()
    
    # Force regex extraction by not setting OpenAI API key
    parser = TranscriptCVParser()
    
    print("Extracting CV data from voice transcript...")
    print()
    
    result = parser.parse(VOICE_INPUT)
    
    print("EXTRACTION RESULTS:")
    print("=" * 80)
    print(json.dumps(result, indent=2))
    print()
    
    # Verify extracted fields
    print("=" * 80)
    print("VERIFICATION:")
    print("=" * 80)
    
    personal = result["personal_information"]
    
    checks = []
    
    # Personal Information
    checks.append(("Full Name", personal["full_name"], "Venkata Kiran Kumar Janga"))
    checks.append(("Portal ID", personal["portal_id"], "229164"))
    checks.append(("Grade", personal["grade"], "10"))
    checks.append(("Contact", personal["contact_number"], "991248765"))
    checks.append(("Email", personal["email"], "venkata.janga@nttdata.com"))
    checks.append(("Location", personal["current_location"], "Hyderabad"))
    checks.append(("Designation", personal["designation"], "System Intelligence Advisor"))
    
    # Professional Summary
    checks.append(("Experience Years", result["professional_summary"]["total_experience_years"], 16))
    checks.append(("Summary Extracted", len(result["professional_summary"]["summary"]) > 0, True))
    
    # Skills
    checks.append(("Primary Skills Count", len(result["skills"]["primary_skills"]) >= 3, True))
    checks.append(("Secondary Skills Count", len(result["skills"]["secondary_skills"]) >= 5, True))
    checks.append(("AI Frameworks", len(result["skills"]["ai_frameworks"]) > 0, True))
    checks.append(("Operating Systems", len(result["skills"]["operating_systems"]) >= 2, True))
    checks.append(("Databases", len(result["skills"]["databases"]) >= 4, True))
    checks.append(("Cloud Platforms", len(result["skills"]["cloud_platforms"]) >= 1, True))
    
    # Domain Expertise
    checks.append(("Domain Count", len(result["domain_expertise"]) >= 3, True))
    
    # Employment
    checks.append(("Company", result["employment_details"]["current_company"], "NTTDATA"))
    checks.append(("Years with Company", result["employment_details"]["years_with_current_company"], 5))
    checks.append(("Clients Count", len(result["employment_details"]["clients"]) >= 3, True))
    
    # Education
    checks.append(("Education Count", len(result["education"]) >= 3, True))
    
    # Count correct extractions
    correct = 0
    total = len(checks)
    
    for name, actual, expected in checks:
        if isinstance(expected, bool):
            match = actual == expected
        else:
            match = str(actual).lower().replace(" ", "") == str(expected).lower().replace(" ", "")
        
        status = "✓" if match else "✗"
        if match:
            correct += 1
        
        print(f"{status} {name:25} | Expected: {expected:30} | Got: {actual}")
    
    print()
    print("=" * 80)
    accuracy = (correct / total) * 100
    print(f"ACCURACY: {correct}/{total} = {accuracy:.1f}%")
    
    if accuracy >= 50:
        print("✓ SUCCESS: Extraction accuracy is >= 50%")
    else:
        print("✗ FAILED: Extraction accuracy is < 50%")
    
    print("=" * 80)
    
    return result, accuracy >= 50


if __name__ == "__main__":
    result, success = test_regex_extraction()
    sys.exit(0 if success else 1)
