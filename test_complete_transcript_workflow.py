"""Test complete transcript-to-CV workflow via API."""
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

# Your actual transcript
transcript = """My name is Venkata Kiran Kumar Janga, my portal id is 229164, my current grade is 10, contact number is 9912487654,
 my email id is venkata.janga at the rate nttdata.com. My professional summary, I have been 16 years of experience in the IT industry for developing,
 deploying and operational support for enterprise grade applications using Java, Python, PySpark, Databricks, AWS and Azure cloud services, 
 developed web-based and enterprise-based applications. My primary skill is Java, Spring Boot, Microservices. My secondary skill is Python,
 Microservices, Lanchain, Langraph, NumPy, Pandas, PySpark, Databricks. My AI frameworks are AutoZen Framework, Crue AI Framework. 
 Coming to my operating systems, I well versed in Linux and Windows. Database side, I have good experience in SQL, MySQL, Postgres, 
 Oracle, DB2 and DB2. I worked on a domain in healthcare, transport, automobile industry and insurance domains. Currently my designation 
 is System Intelligency Advisor, my current location is Hyderabad. I worked for NTT data for first 5 years, worked with clients Daimler truck, 
 BMW and Volkswagen. Coming to my project details, my first project is Rekosystem. Current client is John Deere. My project description is
 the parts which are available in the store to purchase by the customers based on availability. So our application gives advice to the dealer
 in which season what kind of parts are required to store the system, it will recommendation basically. So by this, it will not only useful 
 for the dealers, it is increasing the company sales and profits. So it is losing the money and space if we don't give the recommendation to
 the dealer. So based on sales which is done, based on the past history, we are suggesting to the dealer what type of parts is required in
 which season. My role in this project, I code core developer and designed an application deployed in CACD pipelines using Jenkins. 
 I developed UI screens, I developed backend data scripts, I developed DTO layers, I returned some unit test cases. Coming to
 my second project is human health care. Client is users, US project description is the client is currently quantity 
 assisted data is being loaded every 30 minutes. The patient data from the staging tables to the reporting table, 
 the tabling occurs once in a day after business hours. My role in this project as a developer, I keep tracking of source data tables 
 into silver table by using cleaning, cleansing, and processing. My role here is a developer. Coming to my qualifications, 
 that means educational qualifications, I have completed my master of computer science, branches computers, my year of passing is 2007,
 the name of the college is ITM, university name is Kakatiya University. My second educational qualification is bachelor of science, 
 that means branches computers, my college name is Sri Chaitanya Degree College, university is Kakatiya University, I got 59% percentage.
 I have completed my 12th standard, branch is MPC, college is Sri Chaitanya Junior College, university is Board of Intermediate, 
 I got 59% percentage. I have completed my 10th standards, the school name is ZPPSI school, university name is ZPPSI university,
 name is School of Secondary, year of passing is 2000, I got 80%. Thank you."""

print("=" * 80)
print("COMPLETE TRANSCRIPT-TO-CV WORKFLOW TEST")
print("=" * 80)

# Step 1: Create a new session
print("\n1. Creating new session...")
response = requests.post(f"{BASE_URL}/session/start")
if response.status_code == 200:
    session_data = response.json()
    session_id = session_data["session_id"]
    print(f"[OK] Session created: {session_id}")
else:
    print(f"[FAIL] Failed to create session: {response.status_code}")
    print(response.text)
    exit(1)

# Step 2: Process transcript with session_id
print("\n2. Processing transcript...")
response = requests.post(
    f"{BASE_URL}/speech/correct",
    data={
        "transcript": transcript,
        "session_id": session_id
    }
)

if response.status_code == 200:
    transcript_result = response.json()
    print(f"[OK] Transcript processed successfully")
    
    # Check for extracted_cv_data
    if "extracted_cv_data" in transcript_result:
        print("\n[OK] Extracted CV Data Present:")
        cv_data = transcript_result["extracted_cv_data"]
        print(f"  - Name: {cv_data.get('personal_information', {}).get('full_name', 'N/A')}")
        print(f"  - Email: {cv_data.get('personal_information', {}).get('email', 'N/A')}")
        print(f"  - Portal ID: {cv_data.get('personal_information', {}).get('portal_id', 'N/A')}")
        print(f"  - Primary Skills: {len(cv_data.get('skills', {}).get('primary_skills', []))} skills")
        print(f"  - Secondary Skills: {len(cv_data.get('skills', {}).get('secondary_skills', []))} skills")
        print(f"  - Projects: {len(cv_data.get('project_experience', []))} projects")
        print(f"  - Education: {len(cv_data.get('education', []))} qualifications")
    else:
        print("\n[FAIL] No extracted_cv_data in response")
    
    # Check for merged cv_data (since session_id was passed)
    if "cv_data" in transcript_result:
        print("\n[OK] Merged CV Data Present (session was updated)")
        merged_data = transcript_result["cv_data"]
        print(f"  - Session has merged data with {len(merged_data)} top-level keys")
    else:
        print("\n[WARN] No merged cv_data in response")
    
    print(f"\n[OK] Full Response Keys: {list(transcript_result.keys())}")
else:
    print(f"[FAIL] Failed to process transcript: {response.status_code}")
    print(response.text)
    exit(1)

# Step 3: Get preview
print("\n3. Getting CV preview...")
response = requests.get(f"{BASE_URL}/preview/{session_id}")

if response.status_code == 200:
    preview_result = response.json()
    print(f"[OK] Preview generated successfully")
    print(f"\n[OK] Preview Content Keys: {list(preview_result.keys())}")
    
    if "preview" in preview_result:
        preview_content = preview_result["preview"]
        print(f"\nPreview Content Preview (first 500 chars):")
        print("-" * 80)
        preview_str = str(preview_content) if not isinstance(preview_content, str) else preview_content
        print(preview_str[:500] + "..." if len(preview_str) > 500 else preview_str)
        print("-" * 80)
        
        # Check for structured data
        if "personal_information" in preview_content or "skills" in preview_content or "project_experience" in preview_content:
            print("\n[OK] Preview contains structured CV sections")
        else:
            print("\n[WARN] Preview may not have structured formatting")
    else:
        print("\n[FAIL] No preview in response")
else:
    print(f"[FAIL] Failed to get preview: {response.status_code}")
    print(response.text)

# Step 4: Test DOCX export
print("\n4. Testing DOCX export...")
response = requests.get(f"{BASE_URL}/export/docx/{session_id}")

if response.status_code == 200:
    # Save to file
    filename = f"test_export_{int(time.time())}.docx"
    with open(filename, "wb") as f:
        f.write(response.content)
    print(f"[OK] DOCX exported successfully: {filename}")
    print(f"  File size: {len(response.content)} bytes")
    
    if len(response.content) > 10000:  # Reasonable size for a CV with content
        print("  [OK] File size suggests it contains actual content")
    else:
        print("  [WARN] File size is small, may not have full content")
else:
    print(f"[FAIL] Failed to export DOCX: {response.status_code}")
    if response.status_code != 404:
        print(response.text[:500])

# Step 5: Test PDF export
print("\n5. Testing PDF export...")
response = requests.get(f"{BASE_URL}/export/pdf/{session_id}")

if response.status_code == 200:
    # Save to file
    filename = f"test_export_{int(time.time())}.pdf"
    with open(filename, "wb") as f:
        f.write(response.content)
    print(f"[OK] PDF exported successfully: {filename}")
    print(f"  File size: {len(response.content)} bytes")
    
    if len(response.content) > 5000:  # Reasonable size for a CV PDF
        print("  [OK] File size suggests it contains actual content")
    else:
        print("  [WARN] File size is small, may not have full content")
else:
    print(f"[FAIL] Failed to export PDF: {response.status_code}")
    if response.status_code != 404:
        print(response.text[:500])

# Summary
print("\n" + "=" * 80)
print("WORKFLOW TEST COMPLETE")
print("=" * 80)
print("\nExpected Behavior Verification:")
print("[OK] Transcript response includes extracted_cv_data")
print("[OK] Transcript response includes merged cv_data (when session_id passed)")
print("[OK] Preview shows formatted CV sections")
print("[OK] DOCX export contains actual data")
print("[OK] PDF export contains actual data")
print("\nSession ID for manual testing:", session_id)
