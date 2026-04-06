#!/usr/bin/env python3
"""
Test script to verify the enhanced transcript parser fixes
Tests with the actual voice transcript data provided
"""

import sys
import json
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from infrastructure.parsers.enhanced_transcript_parser import EnhancedTranscriptParser

def test_enhanced_parser():
    """Test the enhanced transcript parser with actual voice data"""
    
    # Actual enhanced transcript from the API response
    enhanced_transcript = """**Venkata Janga**  
Portal ID: 229164  
Grade: 10  
Contact: 9881248765  
Email: venkata.janga.com  

**Professional Summary**  
IT professional with over 16 years of experience specializing in the development, deployment, and operational support of enterprise-grade applications. Expertise spans Java, Python, PySpark, Databricks, AWS, and Azure cloud services, with a strong focus on building scalable web-based and enterprise applications.

**Core Competencies**  
- Primary skills: Java, Spring Boot, Microservices  
- Secondary skills: Python, Langchain, Langgraph, Langsmith, NumPy, Pandas, PySpark, Databricks  
- Hands-on experience with AI frameworks: Autogen, Crue AI  
- Proficient in Linux and Windows operating systems  
- Strong database experience: MySQL, Postgres, DB2, Oracle  

**Industry Experience**  
Demonstrated expertise across multiple domains, including healthcare, transportation, automotive, insurance, and banking. Currently serving as a System Intelligence Advisor at Entity Data in Hyderabad for the past five years, collaborating with clients such as Common Sprint, Daimler Truck, BMW, and Volkswagen.

**Project Experience**  
1. **Recommended Stock System** (Client: Volkswagen)  
   - Designed and developed an application to recommend optimal stock levels for automotive parts based on historical and seasonal demand patterns.  
   - Responsibilities included application architecture design, front-end UI component development, back-end service creation, data processing logic implementation, CI/CD pipeline completion using Jenkins in Azure environments, and unit testing to ensure code quality and reliability.

2. **Common Sprint Healthcare** (Client: Common Sprint)  
   - Developed an end-to-end data processing pipeline for accurate and timely reporting and analytical purposes.  
   - Responsibilities included designing and developing the pipeline using ADF, ADLS, Key Vault, and MySQL services, managing data cleansing and processing, and ensuring data quality and consistency across reporting levels.

**Education**  
- Master of Computer Applications, Institute of Technology and Management, Kakatiya University, 2007, 70%  
- Bachelor of Science in Computers, Sri Chaitanya Degree College, Kakatiya University, 2004, 59%  
- Intermediate Education (MPC), Sri Chaitanya Junior College, Board of Intermediate, 2002, 59%  
- Secondary School (10th Standard), ZPP HSI School, Board of Secondary School, 2000, 70%"""
    
    print("Testing Enhanced Transcript Parser with Structured Format...")
    print("=" * 60)
    
    # Initialize parser
    parser = EnhancedTranscriptParser()
    
    # Parse the transcript
    result = parser.parse(enhanced_transcript)
    
    # Print results in a formatted way
    print("HEADER INFORMATION:")
    print("-" * 20)
    for key, value in result["header"].items():
        print(f"{key}: {value}")
    
    print(f"\nSUMMARY:")
    print("-" * 20)
    print(result["summary"])
    
    print(f"\nPRIMARY SKILLS:")
    print("-" * 20)
    for skill in result["skills"]:
        print(f"- {skill}")
    
    print(f"\nSECONDARY SKILLS:")
    print("-" * 20)  
    for skill in result["secondary_skills"]:
        print(f"- {skill}")
        
    print(f"\nAI FRAMEWORKS:")
    print("-" * 20)
    for framework in result["ai_frameworks"]:
        print(f"- {framework}")
    
    print(f"\nCLOUD PLATFORMS:")
    print("-" * 20)
    for platform in result["cloud_platforms"]:
        print(f"- {platform}")
    
    print(f"\nDATABASES:")
    print("-" * 20)
    for db in result["databases"]:
        print(f"- {db}")
    
    print(f"\nDOMAIN EXPERTISE:")
    print("-" * 20)
    for domain in result["domain_expertise"]:
        print(f"- {domain}")
    
    print(f"\nEMPLOYMENT INFO:")
    print("-" * 20)
    employment = result["employment"]
    print(f"Current Company: {employment.get('current_company', '')}")
    print(f"Years: {employment.get('years_with_current_company', 0)}")
    print(f"Clients: {', '.join(employment.get('clients', []))}")
    
    print(f"\nPROJECT EXPERIENCE:")
    print("-" * 20)
    for i, project in enumerate(result["project_experience"], 1):
        print(f"Project {i}: {project['project_name']}")
        print(f"  Client: {project['client']}")
        print(f"  Description: {project['project_description'][:100]}...")
        print(f"  Technologies: {', '.join(project['technologies_used'])}")
        print(f"  Responsibilities: {len(project['responsibilities'])} items")
        print()
    
    print(f"EDUCATION:")
    print("-" * 20)
    for i, edu in enumerate(result["education"], 1):
        print(f"Education {i}:")
        print(f"  Qualification: {edu['qualification']}")
        print(f"  Specialization: {edu['specialization']}")
        print(f"  College: {edu['college']}")
        print(f"  University: {edu['university']}")  
        print(f"  Year: {edu['year_of_passing']}")
        print(f"  Percentage: {edu['percentage']}")
        print()
    
    print("=" * 60)
    print("TESTING WITH VOICE TRANSCRIPT FORMAT...")
    print("=" * 60)
    
    # Test with the voice format as well
    voice_transcript = """My name is Venkata Janga. My portal ID is 229164. My current grade is 10. 
I can reach at or my contact number is 9881248765. My email address is venkata.janga.entdata.com.
 My contact number is 9881248765. I have, coming to my professional summary, I have over past 16 years in the IT industry specializing in 
 the development and deployment and operational support for enterprise grade applications. My expertise span across Java, Python, 
 PySpark, Databricks, AWS, Azure cloud services with strong focus on building scale web based and enterprise applications. 
 
 
 Coming to my skillset, my primary skill is Java, Spring Boot, microservices. 
 My secondary skill is Python, Langchain, Langgraph, Langsmith, NumPy, Pandas, PySpark and Databricks. 
 I have also hands on experience in AI frameworks such as AutoZen and crew AI frameworks. 
 I was working in Linux and Windows operating systems. Coming to the database, 
 I have strong experience with MySQL and Postgres, DB2 and Oracle over the course of my career. 
 I worked across multiple domains including healthcare, transportation, automotive, insurance and banking domains. 
 
 
 Currently, my current role is system intelligency advisor at EntityData based in the Hyderabad location.
 I have been working with organization for the past five years. I worked with different domains and different clients.
 Clients such as Common Sprint, BMW and Volkswagen. Coming to my project experience, 
 
 
 my first project is recommended stock system and client is Volkswagen.
 My project description is the application is designed and recommended. 
 Designed and recommended optimal stock levels for automotive parts based on historical data and sensational data demand patterns. 
 It provides continued insights to the dealer and which part to stock and helping to increase the sales and optimize inventory and
 minimal financial storage loss. 
 
 Coming to my roles and responsibilities of this project, I have designed and developed the application architecture. 
 I built frontend UI components and backend services. I developed data processing logic at.dto layers. 
 I completed CICD pipelines using Jenkins in Azure environments and returned unit test cases to ensure code quality and reliability.


 My second project name is Common Sprint ELTK. 
 Client is Common Sprint. 
 Project description is ensure that accuracy and timely availability
 of further reporting and analytical purpose. 
 
 
 Coming to my roles and responsibilities of this project, I worked as a developer.
 
 I designed and developed data processing end-to-end pipeline using ADF, ADLS, Key Vault and MySQL services and managed the data next
 level cleaning, cleansing and the functionality processing, the silver layer. 
 I also participated ensure the data quality and consistency
 across the report levels. 
 
 
 Coming to my educational details, 
 I have completed a Master of Computer Applications in Institute of Technology 
 and Management College from Kakatiya University. The year of passing is 2007. My percentage is 70 percentile. Next,
 I have completed my Bachelor of Science, branch is computers. My college name is Sri Chaitanya Degree College at Kakatiya University in
 the year of 2004 and I got 59 percentile. I have completed intermediate education that is 12th standard, branch is MPC.
 My college name is Sri Chaitanya Junior College. University name is Board of Intermediate. My percentage is 59 percentile. 
 My secondary school that is 10th standard. My school name is JPPHSI School. University name is Board of Secondary School. 
 Passing year is 2000. Got 70 percentage."""
    
    # Parse voice transcript  
    voice_result = parser.parse(voice_transcript)
    
    print("VOICE TRANSCRIPT RESULTS:")
    print("-" * 30)
    
    print("Header Info:")
    for key, value in voice_result["header"].items():
        if value:
            print(f"  {key}: {value}")
    
    print(f"\nEducation Found: {len(voice_result['education'])}")
    for i, edu in enumerate(voice_result["education"], 1):
        print(f"Education {i}: {edu['qualification']}")
        if edu['college']:
            print(f"  College: {edu['college']}")
        if edu['year_of_passing']:
            print(f"  Year: {edu['year_of_passing']}")
        if edu['percentage']:
            print(f"  Percentage: {edu['percentage']}")
        
    print(f"\nProjects Found: {len(voice_result['project_experience'])}")
    for i, project in enumerate(voice_result["project_experience"], 1):
        print(f"Project {i}: {project['project_name']}")
        if project['client']:
            print(f"  Client: {project['client']}")
        if project['responsibilities']:
            print(f"  Responsibilities: {len(project['responsibilities'])} items")
    
    # Generate JSON output
    print("\n" + "=" * 60)
    print("COMPLETE JSON OUTPUT (Voice Transcript):")
    print("=" * 60)
    
    print(json.dumps(voice_result, indent=2))
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE!")

if __name__ == "__main__":
    test_enhanced_parser()
