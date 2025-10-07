# 📌 Specification Extraction & Defect Mapping POC

This project is a **proof-of-concept (POC)** system that takes messy engineering specifications (PDFs, Word docs, handwritten scans), normalizes them into a master dataset, and then maps **3D defect data** against those specs to decide if a part is **Repairable, Serviceable, or Not Repairable**.

It also includes a simple **React.js front-end** to upload docs, run the pipeline, view extracted specs + defect results, and make inline corrections.

---

## ✨ Features

- 📑 **Spec Extraction**

  - Parses PDF, DOCX, and scanned/handwritten inputs (OCR).
  - Extracts ~10–15 parameters like tear size, cap diameter, tolerances, pressure/temperature limits, etc.

- 🔄 **Normalization & Master Dataset**

  - Deduplicates across multiple sources.
  - Resolves conflicts and produces a unified master record.
  - Stores intermediate raw JSON + final normalized SQL table.

- 🔧 **Defect Mapping**

  - Loads sample defect dataset (CSV/JSON).
  - Compares defect values against extracted specs.
  - Outputs a decision: `Repairable`, `Serviceable`, or `Not Repairable`.

- 💻 **Front-End UI (React + Vite)**
  - Upload section for docs.
  - Processing button runs the pipeline via FastAPI.
  - Results table showing specs + defect mapping results.
  - Inline editing and corrections.
  - Save/commit updated specs back to dataset.

---

## 🛠️ Tech Stack

**Backend / Data Processing**

- Python 3.10+
- FastAPI (API layer)
- Pandas & SQLAlchemy (ETL + master dataset)
- PyMuPDF / pdfplumber / python-docx (document parsing)
- Pytesseract (OCR for scanned images)
- spaCy / regex (parameter extraction)

**Database**

- NoSQL (JSON files for raw inputs)
- SQLite (SQL-like master dataset)

**Frontend**

- React.js (Vite + TypeScript)
- Axios for API calls
- Table UI with inline editing

---

## 🚀 Setup & Installation

### 1. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app:app --reload
```

Backend will run on: **http://127.0.0.1:8000**

### 2. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Frontend will run on: **http://localhost:5173**

---

## 🎯 Demo Workflow

1. **Upload 3 documents** (PDF, Word, handwritten scan), sample input documents are in **data/input** folder.
2. Click **Process** → backend extracts + normalizes parameters.
3. Master dataset + defect dataset are combined → defect decisions are generated.
4. Results appear in a **table** (specs + defect outcomes).
5. User can **edit/correct specs inline** and save back into dataset.
6. Final dataset + results are stored for reporting/demo.

---

## 📊 Example

### Extracted Specs

- Cap Diameter: `24.5 mm`
- Tear Size Limit: `2.8 mm`
- Max Pressure: `5 bar`
- Max Temp: `80 °C`

### Defect Mapping

- Tear 2 mm → ✅ Repairable
- Tear 4 mm → ❌ Not Repairable
- Scratch 0.3 mm → ℹ️ Serviceable
- Oversize Hole 12.5 mm vs. 10 mm spec → ❌ Not Repairable

---

## ✅ Status

This POC implements:

- Full ETL pipeline
- Normalization logic
- Defect mapping engine
- React UI with upload + editable table

# Terraform: EC2 + RDS + S3 for Spec Extraction POC (dev)

Prereqs:

- Terraform v1.6+
- AWS CLI configured with credentials
- An existing EC2 key pair name in the target account/region

1. Edit `terraform/variables.tf` to set `key_name` and `repo_git_url` (or supply via `-var`).
2. Initialize Terraform:

- terraform init

3. Plan:

- terraform plan -var "key_name=your-key" -var "db_password=YourStrongPass!"

4. Apply:

- terraform apply -var "key_name=your-key" -var "db_password=YourStrongPass!"

5. After apply completes, note outputs:

- `ec2_public_ip` → visit `http://<ip>/docs` for FastAPI Swagger (if your app exposes it)
- `rds_endpoint` → database host
- `s3_bucket` → bucket for uploads/outputs

6. SSH (if needed):

- ssh -i /path/to/your-key.pem ubuntu@<ec2_public_ip>

7. Logs:

- `/home/ubuntu/specs-pipeline/app.log`
