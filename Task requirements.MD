1. Objective
Build a proof-of-concept system that:
        • Extracts specifications from multiple document formats (PDF, Word, Handwritten/Scanned).
        • Normalizes and merges them into a consistent master dataset.
        • Processes 3D point cloud defect data and maps it against specifications.
        • Outputs whether defects are repairable, serviceable, or non-repairable.
        • Provides a simple React.js front-end for review, corrections, and validation.

2. Scope of POC (by next Friday)
        • Data Inputs (3 Sources):
                1. PDF document with specs (e.g., technical spec sheet).
                2. Word document with the same or overlapping specs.
                3. Handwritten/scanned document with specs (simulating messy/unstructured input).
        • Pipeline Features:
                • Extract parameters (10–15 fields max, for simplicity).
                • Normalize duplicates across documents (deduplication + conflict resolution).
                • Store unified results in a Master Dataset.
        • Defect Mapping (Simplified):
                • Assume we have a sample 3D point cloud defect dataset (CSV/JSON for demo).
                • Map defects to specifications (e.g., “tear size ≤ 3mm = repairable”).
                • Output decision: Repairable / Serviceable / Not repairable.
        • Front-End (React.js):
                • Upload section: select and upload documents.
                • Processing button: runs pipeline.
                • Output table: shows extracted specs + defect mapping results.
                • Inline editing: allow user to correct/update parameters.
                • Save/commit: updated specs saved back into dataset.
        • POC Deliverables:
                • Working ETL pipeline (Python preferred) handling the 3 document sources.
                • Normalization logic (deduplication, “latest source of truth”).
                • Simple data model (NoSQL for raw input, SQL-like master table).
                • React.js interface to visualize & edit results.
                • Demo script/walkthrough: explain workflow end-to-end.

3. Technical Stack
        • Backend / Data Processing:
                • Python (for ETL + document parsing + defect mapping logic).
                • OCR library (Tesseract / PyMuPDF / PDFplumber) for PDF & handwritten scans.
                • NLP/vectorization (spaCy / Hugging Face embeddings) for parameter extraction.
                • Pandas/SQLAlchemy for data normalization & master dataset.
        • Database:
                • Landing: NoSQL (JSON/flat files).
                • Master Dataset: SQL (SQLite for POC).
        • Frontend:
                • React.js with Node.js backend (Express or FastAPI bridge).
                • Simple table-based UI with CRUD (edit/update specs).

4. Milestones & Timeline
Day 1–2 (Today–Sunday):
        • Collect/create sample documents (PDF, Word, handwritten scan).
        • Define 10–15 key parameters (e.g., cap diameter, tear size limit, surface finish tolerance).
        • Implement basic document parsing + OCR extraction.
Day 3 (Monday):
        • Build pipeline to normalize extracted parameters.
        • Store in unified master dataset.
        • Implement deduplication rules.
Day 4 (Tuesday):
        • Create defect dataset (CSV/JSON).
        • Write mapping logic (defect vs. specs → decision outcome).
Day 5 (Wednesday):
        • Build basic React.js UI (upload, process, show table).
Day 6 (Thursday):
        • Add inline editing + update/commit features.
        • Polish pipeline for demo readiness.
Day 7 (Friday):
        • Prepare demo walkthrough:
        • Upload 3 docs → Extract → Normalize → Output table → Map defects → Edit & Commit.
        • Meet interviewer with working POC.

5. Expected Deliverables for Demo
        1. Pipeline Code (Python scripts for ETL + normalization + defect mapping).
        2. Sample Input Data:
                • One PDF, one Word, one scanned/handwritten doc.
                • One defect dataset (CSV/JSON).
        3. React.js App (UI with upload → process → results table + editing).
        4. Demo Presentation:
                • Walkthrough of pipeline logic.
                • Show input → processing → normalized dataset → UI output.
                • Explain how it scales to more documents and production setup.
