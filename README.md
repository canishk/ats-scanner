# ats-scanner
Applicant Tracking System

## Application Snapshot

`ats-scanner` is a Python-based tool designed to streamline applicant tracking and resume parsing. It leverages [spaCy](https://spacy.io/) for natural language processing and can optionally integrate with Google Generative AI for enhanced resume analysis.

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

### Google Generative AI Integration

To enable Google Generative AI features, follow these steps:


1. **Generate a Gemini API Key:**
    - Go to the [Google AI Studio](https://aistudio.google.com/app/apikey).
    - Click **Create API Key**.
    - Copy the generated API key and save it securely.

2. **Configure Credentials with a `.env` File:**
    - Create a `.env` file in the project root and add the following line, replacing the path with your JSON key file:
        ```env
        GOOGLE_API_KEY=YOUR.API.KEY
        ```
    - The application will automatically load environment variables from the `.env` file using a package like [`python-dotenv`](https://pypi.org/project/python-dotenv/).

- No additional installation steps are required for Google Generative AI integration beyond setting your API key in the `.env` file.
- Refer to the application's documentation or code comments for further integration details if needed.

### Usage

After installation and (optionally) configuring Google Generative AI, you can run the application as follows:
```bash
python data_loader.py
```

The application will process resumes and extract relevant information using the installed `en_core_web_sm` model. If Google Generative AI is configured, additional analysis and insights will be provided.