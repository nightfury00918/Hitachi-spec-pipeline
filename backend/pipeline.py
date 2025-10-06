# pipeline.py
"""
Pipeline that:
- extracts from files,
- maps lines to canonical params,
- extracts value+unit,
- stores raw extractions,
- persists ALL variants to MasterSpec (one row per variant),
- returns parsed_by_source and merged_master (for UI consumption).
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import pdfplumber
from docx import Document
from PIL import Image
import pytesseract
from sentence_transformers import SentenceTransformer, util

from db import SessionLocal, engine, Base
from models import MasterSpec, RawExtraction
import pandas as pd

# ensure DB tables
Base.metadata.create_all(bind=engine)

ROOT = Path(__file__).parent
UPLOAD_DIR = ROOT / "data" / "uploads"
LANDING_DIR = ROOT / "data" / "landing"
OUTPUT_DIR = ROOT / "data" / "outputs"
LANDING_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load defect rules once
DEFECTS_CSV_PATH = ROOT / "data" / "defects.csv"
DEFECT_RULES = pd.read_csv(DEFECTS_CSV_PATH).to_dict(orient="records")

logger = logging.getLogger("pipeline")
logging.basicConfig(level=logging.INFO)

# canonical params
CANONICAL = {
    "cap_diameter": ["cap diameter", "cap_dia", "cap diameter", "cap dia"],
    "tear_size_limit": ["tear size limit", "tear limit", "tear_size"],
    "surface_finish_tolerance": ["surface finish tolerance", "surface finish tol"],
    "hole_diameter": ["hole diameter", "hole dia"],
    "length_tolerance": ["length tolerance"],
    "width_tolerance": ["width tolerance"],
    "thickness_tolerance": ["thickness tolerance"],
    "material_type": ["material type", "material"],
    "max_pressure": ["max pressure", "operating pressure"],
    "max_temperature": ["max temperature", "max temp"],
    "min_temperature": ["min temperature", "min temp"],
}

logger.info("Loading embedding model...")
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
PARAM_EMBEDS = {k: EMBED_MODEL.encode(v, convert_to_tensor=True) for k, v in CANONICAL.items()}
logger.info("Model loaded.")


def extract_from_pdf(path: Path) -> str:
    text = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n".join(text).strip()


def extract_from_docx(path: Path) -> str:
    doc = Document(str(path))
    pieces = []
    for p in doc.paragraphs:
        if p.text.strip():
            pieces.append(p.text)
    for t in doc.tables:
        for row in t.rows:
            row_text = [c.text.strip() for c in row.cells if c.text.strip()]
            if row_text:
                pieces.append("\t".join(row_text))
    return "\n".join(pieces).strip()


def extract_from_image(path: Path) -> str:
    img = Image.open(str(path))
    txt = pytesseract.image_to_string(img)
    return txt.strip()


def extract_text_for_file(file_path: Path):
    suf = file_path.suffix.lower()
    if suf in (".pdf",):
        return extract_from_pdf(file_path)
    elif suf in (".docx",):
        return extract_from_docx(file_path)
    elif suf in (".png", ".jpg", ".jpeg", ".tiff"):
        return extract_from_image(file_path)
    else:
        return file_path.read_text(encoding="utf-8", errors="ignore")


def map_line_to_param(line: str):
    emb = EMBED_MODEL.encode(line, convert_to_tensor=True)
    best_param = None
    best_score = -1.0
    for param, embeds in PARAM_EMBEDS.items():
        score = util.cos_sim(emb, embeds).max().item()
        if score > best_score:
            best_param = param
            best_score = score
    return best_param, best_score


VALUE_UNIT_RE = re.compile(
    r"([±]?\d+(?:\.\d+)?)\s*(mm|cm|m|µm|um|micron|bar|psi|°C|C|F)?",
    flags=re.IGNORECASE,
)


def extract_value_unit(text_line: str):
    m = VALUE_UNIT_RE.search(text_line)
    if not m:
        return None, None
    val = m.group(1)
    unit = m.group(2)
    if unit:
        unit = unit.replace("micron", "µm").lower()
    return val, unit


def normalize_numeric(value: str, unit: str, target="mm"):
    try:
        v = float(value.replace("±", ""))
    except Exception:
        return None
    if not unit:
        return str(v)
    u = unit.lower()
    if target == "mm":
        if u in ("mm",):
            return str(v)
        if u == "cm":
            return str(v * 10)
        if u == "m":
            return str(v * 1000)
        if u in ("µm", "um", "micron"):
            return str(v / 1000)
    if target == "um":
        if u in ("µm", "um", "micron"):
            return str(v)
        if u == "mm":
            return str(v * 1000)
    if target == "bar":
        if u in ("bar",):
            return str(v)
        if u == "psi":
            return str(v * 0.0689476)
    if target in ("c", "°c", "celsius"):
        if u in ("f",):
            return str((v - 32) * 5/9)
        return str(v)
    return str(v)


# helper to map extension to source string and priority rank
def source_type_and_priority(filepath: Path):
    suf = filepath.suffix.lower()
    if suf in (".docx",):
        return "DOCX", 1
    if suf in (".pdf",):
        return "PDF", 2
    if suf in (".png", ".jpg", ".jpeg", ".tiff"):
        return "Image", 3
    return "Other", 4


def process_all_and_build_master(priority=("DOCX", "PDF", "Image")):
    session = SessionLocal()
    parsed_by_source = {}

    # store raw extraction ids to pick latest when needed
    extraction_id_by_file = {}

    # --- Extract from files ---
    for filepath in sorted(UPLOAD_DIR.iterdir()):
        if filepath.is_dir():
            continue
        stype, sprio = source_type_and_priority(filepath)
        raw_text = extract_text_for_file(filepath)
        logger.info(f"Extracted {len(raw_text)} chars from {filepath.name} (type={stype})")

        # save raw extraction (DB)
        landing_payload = {"source": filepath.name, "type": stype, "raw_text": raw_text}
        landing_path = LANDING_DIR / f"{filepath.name}.json"
        landing_path.write_text(json.dumps(landing_payload, ensure_ascii=False), encoding="utf-8")

        re_obj = RawExtraction(source=filepath.name, raw_text=raw_text, meta_info={"type": stype})
        session.add(re_obj)
        session.commit()
        extraction_id_by_file[filepath.name] = re_obj.id

        # parse lines
        parsed = {}
        for line in raw_text.splitlines():
            if not line.strip():
                continue
            param, score = map_line_to_param(line)
            if score < 0.55:
                continue
            val, unit = extract_value_unit(line)
            if not val:
                tokens = line.strip().split()
                if len(tokens) >= 2:
                    candidate = tokens[-1]
                    val, unit = candidate, None
            if val:
                # choose normalization target heuristically
                target = None
                if any(k in param for k in ("diameter", "hole", "cap", "thickness", "length", "width", "size")):
                    target = "mm"
                elif "surface_finish" in param or "finish" in param:
                    target = "um"
                elif "pressure" in param:
                    target = "bar"
                elif "temperature" in param:
                    target = "C"

                norm_val = normalize_numeric(val, unit, target) if target else val
                parsed.setdefault(param, []).append({
                    "raw": line.strip(),
                    "value": norm_val,
                    "unit": unit or "",
                    "source": stype,
                    "priority": sprio,
                    "filename": filepath.name,
                    "extraction_id": re_obj.id
                })

        parsed_by_source[filepath.name] = parsed

    # --- Build in-memory master variants by param (list of variants) ---
    master_variants: Dict[str, List[Dict[str, Any]]] = {}
    for param in CANONICAL.keys():
        variants = []
        # collect from parsed_by_source: each source may have multiple lines for same param
        for filename, parsed_map in parsed_by_source.items():
            if not parsed_map:
                continue
            values_list = parsed_map.get(param, [])
            for v in values_list:
                variants.append(v)

        master_variants[param] = variants

    # --- Persist all variants into MasterSpec table (one row per variant) ---
    # We'll insert a row if exact (param, source, raw) doesn't already exist; else update.
    for param, variants in master_variants.items():
        for variant in variants:
            # check if a row exists with same param + source + raw (very likely unique)
            existing = session.query(MasterSpec).filter(
                MasterSpec.param == param,
                MasterSpec.source == variant.get("source"),
                MasterSpec.raw == variant.get("raw")
            ).first()
            meta = {"filename": variant.get("filename"), "extraction_id": variant.get("extraction_id")}
            if existing:
                existing.value = variant.get("value")
                existing.unit = variant.get("unit")
                existing.priority = int(variant.get("priority", 10))
                existing.meta = meta
            else:
                new = MasterSpec(
                    param=param,
                    value=variant.get("value"),
                    unit=variant.get("unit"),
                    raw=variant.get("raw"),
                    source=variant.get("source"),
                    priority=int(variant.get("priority", 10)),
                    meta=meta
                )
                session.add(new)
    session.commit()

    # --- Build merged master: for each param, choose a 'chosen' variant by priority & recency ---
    merged_master = {}
    for param, variants in master_variants.items():
        # load persisted variants from DB for param to get added_at timestamps
        rows = session.query(MasterSpec).filter(MasterSpec.param == param).all()
        # Convert DB rows to variant records for API output
        api_variants = []
        for r in rows:
            api_variants.append({
                "id": r.id,
                "value": r.value,
                "unit": r.unit,
                "raw": r.raw,
                "source": r.source,
                "priority": r.priority,
                "meta": r.meta,
                "added_at": r.added_at.isoformat() if r.added_at else None
            })

        # choose one: lowest priority (i.e., priority int smaller) wins; tie-break by latest added_at
        chosen = None
        if api_variants:
            api_variants_sorted = sorted(api_variants, key=lambda x: (x.get("priority", 99), x.get("added_at") or ""))
            chosen = api_variants_sorted[0]
        merged_master[param] = {
            "chosen": chosen,
            "variants": api_variants
        }

    # --- Save CSV snapshot of the chosen values ---
    df_rows = []
    for p, info in merged_master.items():
        chosen = info.get("chosen") or {}
        df_rows.append({"param": p, "value": chosen.get("value") or "", "unit": chosen.get("unit") or "", "source": chosen.get("source") or ""})
    df_out = pd.DataFrame(df_rows)
    out_csv = OUTPUT_DIR / "master_specs.csv"
    df_out.to_csv(out_csv, index=False)

    session.close()
    return parsed_by_source, merged_master


# ========== defect mapping (unchanged semantics but now expects merged_master format) ==========
def classify_defect_with_master(defect: dict, merged_master: dict):
    dtype = (defect.get("defect_type") or "").lower()
    
    # Find all rules for this defect type
    rules = [r for r in DEFECT_RULES if (r.get("defect_type") or "").lower() == dtype]
    if not rules:
        return "Unknown1"

    # We'll assume one rule per defect type for simplicity
    rule = rules[0]

    # Special cases
    special = rule.get("special", "").lower()
    if special == "always_fail":
        return rule.get("fail", "Not Repairable")
    if special == "coating":
        coating_info = merged_master.get("coating_required", {}).get("chosen")
        if coating_info and str(coating_info.get("value")).lower() in ("yes", "true", "1"):
            return rule.get("fail", "Not Repairable")
        return rule.get("ok", "Repairable")

    spec_name = rule.get("spec_name")
    field = rule.get("field")
    op = rule.get("op")

    spec_info = merged_master.get(spec_name, {}).get("chosen") if spec_name else None
    if spec_name and (not spec_info or not spec_info.get("value")):
        return "Unknown2"

    spec_val = spec_info["value"] if spec_info else None
    field_val = defect.get(field) if field else None

    # Numeric comparison
    try:
        if spec_val is not None and field_val is not None and op in ("<=", "<", ">=", ">", "=="):
            spec_num = float(spec_val)
            val_num = float(field_val)
            if eval(f"{val_num} {op} {spec_num}"):
                return rule.get("ok", "Repairable")
            else:
                return rule.get("fail", "Not Repairable")
    except Exception:
        # fallback to string comparison
        if op == "==" and field_val is not None and spec_val is not None:
            return rule.get("ok") if str(field_val).lower() == str(spec_val).lower() else rule.get("fail")

    return "Unknown3"


def run_defect_mapping(defect_file_path: Path, merged_master: Dict[str, Any]) -> pd.DataFrame:
    """
    Run defect mapping and return results as a DataFrame.
    Saves defect_results.csv to data/outputs/.
    """
    # Load defects CSV or JSON
    if defect_file_path.suffix.lower() == ".csv":
        df = pd.read_csv(defect_file_path)
    else:
        records = json.loads(defect_file_path.read_text())
        df = pd.DataFrame(records)

    # Apply defect classification
    df["decision"] = df.apply(lambda r: classify_defect_with_master(r.to_dict(), merged_master), axis=1)

    # Save results
    out_path = Path("data/outputs/defect_results.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    return df
