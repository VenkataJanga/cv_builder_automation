from src.application.services.cv_builder_service import CVBuilderService
from src.ai.agents.cv_formatting_agent import CVFormattingAgent

answers = [
    ("What is your full name?", "Venkata Janga"),
    ("What is your current role/title?", "Tech Lead"),
    ("What is your employee or portal ID?", "f229164"),
    ("What is your official email address?", "venkata.janga@nttdata.com"),
    ("What is your current location?", "Pune"),
    ("How would you describe your professional profile in 2-3 lines?", "I have over past 16 years in the IT industry specializing in the development, deployment, and operational support for enterprise grade applications. My expertise span across Java, Python, PySpark, Databricks, AWS, Azure cloud services with strong focus on building scale web based and enterprise applications."),
    ("What kinds of roles are you targeting?", "Solution Arichtect"),
    ("What is your total years of experience?", "16"),
    ("What is your current organization?", "Ntt Data"),
    ("Which tools, platforms, databases, cloud services, or operating systems have you worked with?", "I have also hands on experience in AI frameworks such as AutoZen and crew AI frameworks. I was working in Linux and Windows operating systems. Coming to the database, I have strong experience with MySQL and Postgres, DB2 and Oracle"),
    ("What are your key primary skills?", "my primary skill is Java, Spring Boot, microservices."),
    ("What certifications do you hold?", "J2EE and ITIL V4"),
    ("Which industries or domains have you worked in?", "I worked across multiple domains including healthcare, transportation, automotive, insurance and banking domains"),
    ("Please share your educational qualifications.", "I have completed a Master of Computer Applications in Institute of Technology and Management College from Kakatiya University. The year of passing is 2007. My percentage is 70 percentile. Next, I have completed my Bachelor of Science, branch is computers. My college name is Sri Chaitanya Degree College at Kakatiya University in the year of 2004 and I got 59 percentile. I have completed intermediate education that is 12th standard, branch is MPC. My college name is Sri Chaitanya Junior College. University name is Board of Intermediate. My percentage is 59 percentile. My secondary school that is 10th standard. My school name is JPPHSI School. University name is Board of Secondary School. Passing year is 2000. Got 70 percentage."),
    ("What are your core areas of expertise?", "Java, Python, AI frameworks like Crew and Autogen gramwroks"),
    ("Which languages do you speak or write?", "English , Hindi and Telugu"),
    ("What are your secondary skills or supporting technologies?", "My secondary skill is Python, Langchain, Langgraph, Langsmith, NumPy, Pandas, PySpark and Databricks."),
]

cv_builder = CVBuilderService()
cv_data = cv_builder.initialize_cv_data()
for q, a in answers:
    cv_data = cv_builder.update_from_answer(cv_data, q, a)

print('CV Data:')
print(cv_data)
print('---')
print('Preview:')
print(CVFormattingAgent().format_cv(cv_data))
