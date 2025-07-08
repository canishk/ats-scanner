import pdfplumber
import sqlite3
import re
import os
import json
import spacy
from dotenv import load_dotenv

from ats.ai_prompt import get_resume_prompt
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser


class ATSParser:
    def __init__(self, db_path='ats.db'):
        self.db_path = db_path
        self.nlp = spacy.load("en_core_web_sm")
        self.init_db()
        load_dotenv()
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

    # Initialize DB
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                phone TEXT,
                skills TEXT,
                experience TEXT
            )
        ''')
        conn.commit()
        conn.close()

    # Extract email, phone, skills, and experience
    def extract_info(self, text):
        email = self._extract_email(text)
        phone = self._extract_phone(text)
        name = self._extract_name(text)
        skills = self._extract_skills(text)
        experience = self._extract_experience(text)
        return {
            "name": name,
            "email": email,
            "phone": phone,
            "skills": ", ".join(skills) if skills else None,
            "experience": experience
        }

    def _extract_email(self, text):
        # Try to find standard emails, obfuscated emails, and common patterns
        patterns = [
            r'[\w\.-]+@[\w\.-]+\.\w+',  # Standard email
            r'[\w\.-]+\s*\[\s*at\s*\]\s*[\w\.-]+\s*\[\s*dot\s*\]\s*\w+',  # name [at] domain [dot] com
            r'[\w\.-]+\s+at\s+[\w\.-]+\s+dot\s+\w+',  # name at domain dot com
            r'[\w\.-]+\s*@\s*[\w\.-]+\s*\.\s*\w+',  # name @ domain . com (with spaces)
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                email = match.group(0)
                # Clean up obfuscated emails
                email = re.sub(r'\s*\[\s*at\s*\]\s*', '@', email, flags=re.IGNORECASE)
                email = re.sub(r'\s*\[\s*dot\s*\]\s*', '.', email, flags=re.IGNORECASE)
                email = re.sub(r'\s+at\s+', '@', email, flags=re.IGNORECASE)
                email = re.sub(r'\s+dot\s+', '.', email, flags=re.IGNORECASE)
                email = re.sub(r'\s*@\s*', '@', email)
                email = re.sub(r'\s*\.\s*', '.', email)
                return email
        return None

    def _extract_phone(self, text):
        phone_match = re.search(r'(\+?\d[\d\s\-\(\)]{8,20}\d)', text)
        return phone_match.group(0) if phone_match else None

    def _extract_name(self, text):
        # Try GenAI extraction first if API key is available
        if self.google_api_key:
            try:
                llm = GoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    temperature=0.2,
                    api_key=self.google_api_key
                )
                prompt = (
                    "Extract the full name of the candidate from the following resume text. "
                    "Return only the name as a plain string, no explanations.\n\n"
                    f"Resume:\n{text}\n\nName:"
                )
                response = llm.invoke(prompt)
                # Clean up: take only the first line, strip whitespace
                if response:
                    name = response.strip().split('\n')[0]
                    # Heuristic: name should be 2-4 words, mostly alphabetic
                    if 2 <= len(name.split()) <= 4 and all(part.isalpha() for part in name.split()):
                        return name
            except Exception:
                pass  # Fallback to spaCy/heuristics below

        # Check the first few lines for a possible name (heading)
        lines = text.strip().split('\n')
        for i in range(min(5, len(lines))):
            line = lines[i].strip()
            if 2 <= len(line.split()) <= 4 and (line.isalpha() or line.replace(" ", "").isalpha()):
                # Run NER on the line to confirm it's a PERSON entity
                doc = self.nlp(line)
                for ent in doc.ents:
                    if ent.label_ == "PERSON":
                        return ent.text
                # If NER doesn't find, but line looks like a name, return it
                if line and line[0].isupper():
                    return line

        # Fallback: use NER on the whole text
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text
        return None

    def _extract_skills(self, text):
        """
        Uses a GenAI model to extract all skills mentioned in the text, 
        rather than relying on static keywords.
        """
        if not self.google_api_key:
            raise ValueError("Google API key is not set in the environment variables.")

        llm = GoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.2,
            api_key=self.google_api_key
        )
        prompt = (
            "Extract a list of all professional skills mentioned in the following resume text. "
            "Return only a JSON array of skill strings, no explanations.\n\n"
            f"Resume:\n{text}\n\nSkills:"
        )
        try:
            response = llm.invoke(prompt)
            # Try to parse the response as a JSON array
            skills = []
            try:
                skills = json.loads(response)
            except Exception:
                # Fallback: extract list-like structure from response
                match = re.search(r'\[.*\]', response, re.DOTALL)
                if match:
                    skills = json.loads(match.group())
            if isinstance(skills, list):
                return set([s.strip() for s in skills if isinstance(s, str)])
            return set()
        except Exception as e:
            # Fallback: return empty set if AI fails
            return set()

    def _extract_experience(self, text):
        """
        Uses a GenAI model to extract the candidate's work/professional experience section.
        Falls back to regex if GenAI is unavailable or fails.
        """
        if self.google_api_key:
            try:
                llm = GoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    temperature=0.2,
                    api_key=self.google_api_key
                )
                prompt = (
                    "Extract the entire work or professional experience section from the following resume text. "
                    "Return only the relevant experience section as plain text, no explanations.\n\n"
                    f"Resume:\n{text}\n\nExperience Section:"
                )
                response = llm.invoke(prompt)
                # Clean up: Remove any leading/trailing whitespace or explanations
                if response:
                    # Heuristic: If the response is too short, fallback to regex
                    if len(response.strip().split()) > 10:
                        return response.strip()
            except Exception:
                pass  # Fallback to regex below

        # Fallback: Regex-based extraction
        experience_patterns = [
            r'(work experience[\s\S]{0,2000})',
            r'(professional experience[\s\S]{0,2000})',
            r'(experience[\s\S]{0,2000})'
        ]
        for pattern in experience_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                exp_text = match.group(1)
                stop_match = re.search(
                    r'\n\s*(education|skills|projects|certifications|summary|contact)\s*[\n:]', 
                    exp_text, re.IGNORECASE
                )
                if stop_match:
                    return exp_text[:stop_match.start()].strip()
                else:
                    return exp_text.strip()
        return None
    
    def save_to_db(self, data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        result = self._find_existing_record(cursor, data)
        if result:
            self._update_existing_record(cursor, result, data)
        else:
            self._insert_new_record(cursor, data)
        conn.commit()
        conn.close()

    def _find_existing_record(self, cursor, data):
        cursor.execute('''
            SELECT id, email FROM resumes WHERE email = ? OR phone = ?
        ''', (data.get("email"), data.get("phone")))
        return cursor.fetchone()

    def _update_existing_record(self, cursor, result, data):
        record_id, existing_email = result
        update_fields = []
        update_values = []
        if not existing_email and data.get("email"):
            update_fields.append("email = ?")
            update_values.append(data.get("email"))
        update_fields += ["name = ?", "skills = ?", "experience = ?"]
        update_values += [
            data.get("name"),
            data.get("skills"),
            data.get("experience")
        ]
        update_values.append(record_id)
        cursor.execute(f'''
            UPDATE resumes
            SET {', '.join(update_fields)}
            WHERE id = ?
        ''', update_values)

    def _insert_new_record(self, cursor, data):
        cursor.execute('''
            INSERT INTO resumes (name, email, phone, skills, experience)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get("name"),
            data.get("email"),
            data.get("phone"),
            data.get("skills"),
            data.get("experience")
        ))
    
    # Try parsing JSON or fallback with regex
    def clean_and_parse_json(self,response_text: str) -> dict:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            match = re.search(r'{[\s\S]+}', response_text)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    return {}
        return {}


    def process_resume_ai(self, resume_text:str):
        if not self.google_api_key:
            raise ValueError("Google API key is not set in the environment variables.")
        
        llm = GoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=0.2,
            api_key=self.google_api_key
        )
        output_parser = JsonOutputParser()
        prompt = get_resume_prompt(resume_text)
        try:
            chain = output_parser | PromptTemplate.from_template(prompt) | llm
            response = chain.invoke(resume_text)
            result = self.clean_and_parse_json(response)
            if not result:
                raise ValueError("Failed to parse the response from AI.")
            return result
        except Exception as e:
            raise RuntimeError(f"AI processing failed: {e}")    
        

    def parse_pdf(self, pdf_path):
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File {pdf_path} does not exist.")
        
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
        
        if not text.strip():
            raise ValueError("No text found in the PDF.")
        
        extracted_info = self.extract_info(text)
        
        if extracted_info.get("skills") is None:
            extracted_info = self.process_resume_ai(text)
        self.save_to_db(extracted_info)
        return extracted_info
    
# Example usage:
if __name__ == "__main__":

    resumes_dir = os.path.join(os.path.dirname(__file__), "../cvs")
    parser = ATSParser()
    for filename in os.listdir(resumes_dir):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(resumes_dir, filename)
            try:
                info = parser.parse_pdf(pdf_path)
                print(f"Processed {filename}: {info}")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")
