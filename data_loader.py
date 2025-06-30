from ats.ats_parser import ATSParser
import os
import logging

class DataLoader:
    def __init__(self, db_path="ats.db"):
        self.parser = ATSParser(db_path=db_path)
        self.resumes_dir = os.path.join(os.path.dirname(__file__), "cvs")
        logging.basicConfig(level=logging.INFO)

    def load_resumes(self):
        if not os.path.exists(self.resumes_dir):
            os.mkdir(self.resumes_dir)
            # logging.error(f"Resumes directory {self.resumes_dir} does not exist.")
        
        for filename in os.listdir(self.resumes_dir):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(self.resumes_dir, filename)
                try:
                    info = self.parser.parse_pdf(pdf_path)
                    logging.info(f"Processed {filename}: {info}")
                except Exception as e:
                    logging.error(f"Failed to process {filename}: {e}")

if __name__ == "__main__":
    loader = DataLoader()
    loader.load_resumes()
    logging.info("Resume loading completed.")
