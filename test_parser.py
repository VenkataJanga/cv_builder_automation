from src.infrastructure.parsers.transcript_cv_parser_fixed import TranscriptCVParser

# Test transcript from the user
transcript = """Hi
What is your current role/title?
Tech Lead
What is your employee or portal ID?
229164
What is your official email address?
venkata.janga@nttdata.com
What is your current location?
Pune
How would you describe your professional profile in 2-3 lines?
urrent grade is 10. Contact number is 9881248765. My email ID is venkata.janga.com. My professional experience is, I have been 16 years of experience in the IT industry for developing, deploying and operational support for enterprises grade applications using Java, Python, PySpark, Databricks, AWS, Azure cloud services. Developed in web-based and enterprises applications.
What is your total years of experience?
16
What is your current organization?
Ntt data
What are your key primary skills?
My primary skill is Java, Spring Boot, microservices.
What are your secondary skills or supporting technologies?
My secondary skill is Python, Lanchain, Langraph, Langsmith, NumPy, Pandas, PySpark, Databricks.
Which tools, platforms, databases, cloud services, or operating systems have you worked with?
My AI frameworks are AutoZen framework, Crue AI framework. Coming to my operating systems, I well versed in Linux and Windows. Coming to the database side, I have good experience in MySQL, SQL, Postgres, DB2 and Oracle. I worked on domain in healthcare, transport, automobile industry and insurance domains.
What certifications do you hold?
J2EE and ITIL V4
Please share your educational qualifications.
I completed a master in computer science applications. The branch is computers. My year of passing is 2007. The name of the college is ITM. University name is Kakatiya University. My second educational qualification is Bachelor of Science. Branch is computers. My college name is Sri Chaitanya Degree College. University is Kakatiya University. I got 59 percentage. Then I have completed my 12th standard. Branch is MPC. College is Sri Chaitanya Junior College. University is Board of Intermediate. I got 59 percentage. I have completed my 10th standard. My school name is ZPPSI School. University is School of Secondary. Year of passing is 2000.
Which languages do you speak or write?
ENGLISH AND HINDI
All questions completed"""

parser = TranscriptCVParser()
result = parser.parse(transcript)

print("Summary:", repr(result.get("summary")))
print("Education:", result.get("education"))