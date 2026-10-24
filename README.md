# AI Document Comparison Assistant

**Project Category:** Generative AI / LLM Application  
**Internship Project:** Xpert Champs Pvt Ltd — AI Engineering Internship

## 1. Project Overview
The **AI Document Comparison Assistant** is a modular Python + Streamlit web application that enables users to upload two PDF documents, validate and extract their text page-by-page using `pypdf`, and compare their contents using the Google Gemini API.

Unlike a simple chat wrapper, this application validates PDF inputs, retains page-level traceability (`[Page X]`), displays character and page statistics with content previews, enforces strict evidence-grounded JSON output from the LLM, displays organized comparison tabs, and generates a downloadable Microsoft Word (`.docx`) comparison report.

## 2. Features & Functional Requirements Covered
- **FR-01: Upload Documents** — Dedicated upload areas for **Document A** and **Document B** plus a quick-test option using bundled sample PDFs.
- **FR-02: Validate Files** — Rejects non-PDF files, 0-byte empty files, corrupted PDFs, password-protected PDFs, and scanned/image-only PDFs with clear, helpful user messages.
- **FR-03: Extract Text with Traceability** — Extracts text separately for each PDF using `pypdf` and embeds `--- [Page X] ---` markers so summaries and differences cite exact page numbers.
- **FR-04: Preview Extracted Content** — Displays readable page counts, character/word counts, and an expandable text preview for both documents before calling the LLM.
- **FR-05: Summarize Each Document** — Produces distinct, independent summaries for Document A and Document B.
- **FR-06 & FR-07: Similarities & Meaningful Differences** — Lists common points supported by both documents and structures additions, removals, modifications, and contradictions without inventing facts.
- **FR-08: Highlight Key Details** — Compares dates, deadlines, fees/amounts, eligibility criteria, and requirements side-by-side, explicitly stating `"Not found in the provided text"` when a detail is absent.
- **FR-09: Structured Display** — Organizes results into clean tabs: *Summaries*, *Similarities*, *Differences*, *Key Details Comparison*, and *Overall Conclusion & Limitations*.
- **FR-10: Download Comparison Report** — Generates a formatted `.docx` report via `python-docx` containing all 7 required sections.
- **FR-11: Graceful Error Handling** — Handles missing API keys, API timeouts, malformed JSON responses, and overly long documents (via safe truncation + limitation warnings).
- **FR-12: Reset & Compare Again** — One-click reset button clears session state and file uploaders to start a fresh comparison.

## 3. Project Folder Structure
```text
ai-document-comparison-assistant/
├── app.py                  # Streamlit web interface & workflow controller
├── document_reader.py      # PDF validation, pypdf text extraction, page/char preview & limits
├── comparison.py           # Gemini LLM prompt engineering, API call & JSON validation
├── report_generator.py     # Downloadable DOCX report generator (python-docx)
├── requirements.txt        # Required Python dependencies
├── .env.example            # Example environment variable file for GEMINI_API_KEY
├── .gitignore              # Git ignore rules (.env, __pycache__, venv)
├── README.md               # Setup, usage, and architecture documentation
└── sample_documents/
    ├── document_a.pdf      # Sample Policy v1.0 (2025) for testing
    └── document_b.pdf      # Sample Policy v2.0 (2026) for testing
```

## 4. Setup & Installation Instructions

### Step 1: Clone the Repository
```bash
git clone <your-github-repo-url>
cd ai-document-comparison-assistant
```

### Step 2: Create a Virtual Environment & Install Dependencies
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### Step 3: Configure Your Gemini API Key
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and paste your Google Gemini API key (from [Google AI Studio](https://aistudio.google.com/)):
   ```env
   GEMINI_API_KEY=AIzaSyYourActualKeyHere
   ```
   *(Alternatively, you can paste your API key directly into the Streamlit sidebar when running the app.)*

### Step 4: Run the Application
```bash
streamlit run app.py
```

## 5. Testing Scenarios Supported
| Test Case | Application Behaviour |
| :--- | :--- |
| **Two valid text-based PDFs** | Extracts text with page markers, shows previews, and generates summaries, similarities, differences, key details, and conclusion. |
| **One file missing** | Displays a clear warning asking the user to upload both Document A and Document B. |
| **Wrong file type** | Uploader and validator reject non-PDF extensions with a descriptive error message. |
| **Scanned/image-only or empty PDF** | Detects 0 extractable characters and stops before calling the LLM with a helpful explanation (noting OCR as a future enhancement). |
| **LLM API failure / invalid key** | Catches API and JSON errors gracefully, displays a clear message, and lets the user retry. |
| **Documents with different dates/numbers** | Accurately highlights changed dates, fees, and thresholds in the *Differences* and *Key Details* tables. |
| **Documents with mostly identical content** | Reports similarities accurately without hallucinating differences. |
| **Long document** | Safely truncates text at the context limit and records a notice in the *Limitations* section. |
| **Download report** | Exports a styled `.docx` file containing all 7 required comparison sections. |

## 6. Scope Disclaimer
This application is an **informational comparison tool** only. It is not a legal decision-maker and does not claim that any compared document is legally safe, compliant, or equivalent.
