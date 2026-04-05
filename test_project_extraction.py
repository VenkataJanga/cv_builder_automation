"""Test project extraction from the provided voice transcript."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.infrastructure.parsers.transcript_cv_parser import TranscriptCVParser
import json

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

print("Testing project extraction with TranscriptCVParser...")
print("=" * 80)

parser = TranscriptCVParser()
result = parser.parse(transcript)

print("\nExtracted Project Experience:")
print("=" * 80)
print(json.dumps(result["project_experience"], indent=2))

print("\n\nFull Extracted Data:")
print("=" * 80)
print(json.dumps(result, indent=2))

print("\n\nProject Count:", len(result["project_experience"]))
if result["project_experience"]:
    for i, project in enumerate(result["project_experience"], 1):
        print(f"\nProject {i}:")
        print(f"  Name: {project.get('project_name', 'N/A')}")
        print(f"  Client: {project.get('client', 'N/A')}")
        print(f"  Description: {project.get('project_description', 'N/A')[:100]}...")
        print(f"  Role: {project.get('role', 'N/A')}")
        print(f"  Responsibilities: {len(project.get('responsibilities', []))} items")
        print(f"  Technologies: {project.get('technologies_used', [])}")
