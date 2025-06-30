import pdfplumber
import sqlite3
import re
import os
import spacy

class ATSParser:
    def __init__(self, db_path='ats.db'):
        self.db_path = db_path
        self.nlp = spacy.load("en_core_web_sm")
        self.init_db()

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
        # Check the first few lines for a possible name (heading)
        lines = text.strip().split('\n')
        for i in range(min(5, len(lines))):
            line = lines[i].strip()
            if 2 <= len(line.split()) <= 4 and line.isalpha() or line.replace(" ", "").isalpha():
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
        skill_keywords = [
            "python", "java", "sql", "c++", "javascript", "excel", "machine learning",
            "data analysis", "project management", "communication", "leadership"
        ]
        skills_found = set()
        text_lower = text.lower()
        for skill in skill_keywords:
            if skill in text_lower:
                skills_found.add(skill)
        return skills_found

    def _extract_experience(self, text):
        experience_patterns = [
            r'(work experience[\s\S]{0,1000})',
            r'(professional experience[\s\S]{0,1000})',
            r'(experience[\s\S]{0,1000})'
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
