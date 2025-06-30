# ats-scanner
Applicant Tracking System
## Application Snapshot

`ats-scanner` is a Python-based tool designed to streamline applicant tracking and resume parsing. It leverages [spaCy](https://spacy.io/) for natural language processing.

### Installation

1. **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/ats-scanner.git
    cd ats-scanner
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Install the spaCy English model:**
    ```bash
    python -m spacy download en_core_web_sm
    ```

### Usage

After installation, you can run the application as follows:
```bash
python data_loader.py
```

The application will process resumes and extract relevant information using the installed `en_core_web_sm` model.