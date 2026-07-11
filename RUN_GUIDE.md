# RegOps — Step-by-Step Run Guide

This guide describes how to clone, configure, and execute the RegOps Agentic Compliance Copilot prototype on another machine, within an IDE (like VS Code or PyCharm), or directly from a Git repository.

---

## 1. Prerequisites
Ensure you have the following installed on your machine:
* **Python 3.10+** (Python 3.10, 3.11, or 3.12 are recommended).
* **Git** (for cloning from GitHub).

---

## 2. Get the Code & Setup Environment

### Step A: Clone the Repository
Clone the repository using Git and navigate to the project directory:
```bash
git clone <your-repository-url>
cd regops-prototype
```

### Step B: Create a Python Virtual Environment
Initialize a clean environment to isolate the project's dependencies:
* **On Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
* **On Windows (Command Prompt):**
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate
  ```
* **On Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```

### Step C: Install Dependencies
Install all package requirements in your activated virtual environment:
```bash
pip install -r requirements.txt
```

---

## 3. Configuration & API Keys

### Step A: Create a `.env` File
Create a new file named `.env` in the root of the project directory. The application is configured to dynamically check for this file on every request:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey). No credit card required).*

---

## 4. IDE Integration (Resolving Import Warnings / Red Lines)

If your IDE displays squiggly lines under imports like `import streamlit` or `import pdfplumber`, follow these steps to tell the IDE to use the virtual environment's Python interpreter:

### In Visual Studio Code (VS Code)
1. Open the project folder in VS Code.
2. Open the Command Palette:
   * **Linux/Windows:** `Ctrl+Shift+P`
   * **macOS:** `Cmd+Shift+P`
3. Type and select **Python: Select Interpreter**.
4. Choose the interpreter associated with the virtual environment:
   * It should be listed as `./.venv/bin/python` (or `.\.venv\Scripts\python.exe` on Windows).
5. Open any Python file; all red lines and warnings will disappear.

### In PyCharm
1. Open the project folder in PyCharm.
2. Open the settings window:
   * **Linux/Windows:** `Ctrl+Alt+S`
   * **macOS:** `Cmd+,`
3. In the sidebar, navigate to **Project: regops-prototype** ➔ **Python Interpreter**.
4. Click the gear icon or dropdown at the top right, and select **Add Interpreter...**.
5. Select **Existing Environment**, navigate to your project directory, and select:
   * `.venv/bin/python` (Linux/macOS) or `.venv/Scripts/python.exe` (Windows).
6. Click **OK** to apply.

---

## 5. Running the Application

Ensure your virtual environment is active, then launch the Streamlit app:
```bash
streamlit run app.py
```

### Accessing the UI
Streamlit will launch a local web server and print the address. 
* Open your browser and navigate to: **`http://localhost:8501`**

---

## 6. Pipeline Ingestion & Demo Workflow

To run a demonstration in the user interface:
1. **Tab 1: Ingest & Extract**
   * Upload a SEBI circular PDF (e.g. `temp_circular.pdf`).
   * Drag the chunk slider to a small number of clauses (e.g. `8` or `15` chunks) for a quick live pitch.
   * Click **Run Extraction Agent**. The structured obligations will load in an interactive table.
   * Click **Download Extracted Obligations (JSON)** to download the output.
2. **Tab 2: Baseline Register**
   * Click **Use current extraction as baseline** to load the extracted data as your master register, or upload a JSON baseline file directly.
   * Click **Download Baseline Register (JSON)** if you want to save the baseline locally.
3. **Tab 3: Diff / Change Detection**
   * Upload another circular's obligations JSON (or upload your downloaded `extracted_obligations.json`).
   * Click **Run Diff Agent** to perform a semantic rule comparison. It will categorize changes into **NEW**, **AMENDED**, and **UNCHANGED** with LLM reasoning.
   * Click **Download Rule Changes Diff (JSON)** to save the diff results.
