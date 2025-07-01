

def get_resume_prompt(resume_content: str) -> str:
    return f"""
You are an intelligent resume parser. Extract the following fields from the resume content:
- Full Name
- Email Address
- Phone Number
- List of Skills (as an array)
- Total Experience in years or description

Respond only in valid JSON format like this:

{{
  "name": "",
  "email": "",
  "phone": "",
  "skills": [],
  "experience": ""
}}

Resume content:
\"\"\"
{resume_content}
\"\"\"
"""
