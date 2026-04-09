#!/usr/bin/env python3
"""
Debug script to test recorded audio vs uploaded audio education extraction
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ai.services.voice_transcript_production_extractor import extract_from_voice_transcript

# Test transcript that should extract education (similar to user's transcript)
test_transcript = """
My name is Venkata Kiran Kumar Janga, portal id 229164, email id venkata.janga@nttdata.com
I have over past 16 years in the IT industry specializing in
the development and deployment and operational support for enterprise grade applications.

my primary skill is Java, Spring Boot, microservices.
My secondary skill is Python, Langchain, Langgraph, Langsmith, NumPy, Pandas, PySpark and Databricks.

I have also hands on experience in AI frameworks such as AutoZen and crew AI frameworks.
I was working in Linux and Windows operating systems. Coming to the database,
I have strong experience with MySQL and Postgres, DB2 and Oracle

over the course of my career.
I worked across multiple domains including healthcare, transportation, automotive, insurance and banking domains

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
Passing year is 2000. Got 70 percentage.
"""

print("=== TESTING EDUCATION EXTRACTION FROM RECORDED AUDIO TRANSCRIPT ===")

result = extract_from_voice_transcript(test_transcript)

print("\n=== EXTRACTED EDUCATION ===")
education = result.get('education', [])
print(f"Number of education entries: {len(education)}")
for i, edu in enumerate(education):
    print(f"  Education {i+1}: {edu}")

print("\n=== FULL RESULT KEYS ===")
print(f"Result keys: {list(result.keys())}")

print("\n=== EDUCATION EXTRACTION DEBUG ===")
# Test the education extraction function directly
from src.ai.services.voice_transcript_production_extractor import extract_all_education

# Debug: print the education section
import re
text_lower = test_transcript.lower()
edu_match = re.search(r'coming to my educational (?:background|qualification|details)[^\.]*?(.+?)(?:thank you|that\'s all|$)', text_lower, re.DOTALL)
if edu_match:
    edu_text = edu_match.group(1)
    print(f"Education text found: {edu_text[:200]}...")
else:
    print("No education section found with regex")

direct_education = extract_all_education(test_transcript.lower())
print(f"Direct education extraction: {direct_education}")