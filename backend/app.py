# app.py
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import logging
import numpy as np
import pandas as pd
from typing import List
from pipeline import process_all_and_build_master, run_defect_mapping, UPLOAD_DIR, OUTPUT_DIR
from db import SessionLocal
from models import MasterSpec
from utils import clean_dataframe_for_json, clean_for_json

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("backend")
logging.basicConfig(level=logging.INFO)


@app.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    results = []
    for file in files:
        dest = UPLOAD_DIR / file.filename
        # handle duplicate names by appending a suffix
        if dest.exists():
            base = dest.stem
            ext = dest.suffix
            i = 1
            while True:
                candidate = UPLOAD_DIR / f"{base}_{i}{ext}"
                if not candidate.exists():
                    dest = candidate
                    break
                i += 1
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        results.append({"filename": file.filename, "path": str(dest)})
    return {"uploaded": results}


@app.post("/process/")
async def process_pipeline():
    # Guard
    if not any(UPLOAD_DIR.iterdir()):
        raise HTTPException(status_code=400, detail="No uploaded files to process. Upload first.")

    # Step 1: Specs pipeline
    parsed_by_source, merged_master = process_all_and_build_master()

    # Step 2: Defect pipeline
    defects_path = Path(__file__).parent / "data" / "defects.csv"
    defect_results = []
    if defects_path.exists():
        df = run_defect_mapping(defects_path, merged_master)
        defect_results = clean_dataframe_for_json(df).to_dict(orient="records")

    # Step 3: Return combined result
    return clean_for_json({
        "parsed_by_source": parsed_by_source,
        "master": merged_master,
        "defects": defect_results
    })



@app.get("/specs/")
def get_specs(
    view: str = Query("merged", enum=["merged", "raw"]),
    strategy: str = Query("priority", enum=["priority", "latest", "all"])
):
    db: Session = SessionLocal()
    try:
        rows = db.query(MasterSpec).all()
        if not rows:
            return []  # return immediately if no data
        db.close()

        if view == "raw":
            # return every row (duplicates preserved)
            return clean_for_json([r.__dict__ for r in rows])

        merged = {}
        if strategy == "priority":
            # keep highest priority per param
            for r in rows:
                p = r.param
                if p not in merged or r.priority > merged[p].priority:
                    merged[p] = r

        elif strategy == "latest":
            # keep most recently uploaded per param
            for r in rows:
                p = r.param
                if p not in merged or (r.uploaded_at and r.uploaded_at > merged[p].uploaded_at):
                    merged[p] = r

        elif strategy == "all":
            # return ALL possible values for each param
            result = {}
            for r in rows:
                p = r.param
                if p not in result:
                    result[p] = []
                result[p].append({
                    "param": r.param,
                    "value": r.value,
                    "unit": r.unit,
                    "source": r.source,
                    "origin": r.origin,
                    "priority": r.priority,
                    "uploaded_at": r.uploaded_at,
                    "raw": r.raw,
                })
            return clean_for_json(result)

        return clean_for_json([
            {
                "param": r.param,
                "value": r.value,
                "unit": r.unit,
                "source": r.source,
                "origin": r.origin,
                "priority": r.priority,
                "uploaded_at": r.uploaded_at,
                "raw": r.raw,
            }
            for r in merged.values()
        ])
    finally:
        db.close()


@app.post("/update-specs/")
async def update_specs(payload: dict):
    """
    Accepts payload of the shape:
    { param: { value: ..., unit: ..., source?: "USER" } }
    This will upsert a MasterSpec entry with source "USER" (override).
    """
    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=400, detail="Payload must be a non-empty map of parameter updates.")

    db = SessionLocal()
    for param, v in payload.items():
        if not isinstance(param, str) or not param.strip():
            continue
        value, unit = None, None
        source = "USER"
        if isinstance(v, dict):
            value = v.get("value")
            unit = v.get("unit")
            source = v.get("source", "USER")
        else:
            parts = str(v).strip().split()
            if len(parts) == 1:
                value = parts[0]
            elif len(parts) >= 2:
                value = " ".join(parts[:-1])
                unit = parts[-1]
        if value is None or str(value).strip() == "":
            continue

        # store as a USER override: replace existing USER row for this param if any
        existing_user = db.query(MasterSpec).filter(MasterSpec.param == param, MasterSpec.source == "USER").first()
        meta = {"updated_via": "api"}
        if existing_user:
            existing_user.value = str(value).strip()
            existing_user.unit = unit or existing_user.unit
            existing_user.raw = f"USER_EDIT:{value} {unit or ''}".strip()
            existing_user.meta = meta
            existing_user.priority = 0
        else:
            db.add(MasterSpec(param=param, value=str(value).strip(), unit=(unit or ""), raw=f"USER_EDIT:{value} {unit or ''}".strip(), source=source, priority=0, meta=meta))
    db.commit()
    db.close()
    return JSONResponse({"status": "ok"})


@app.get("/defects/")
async def get_defects():
    defects_path = OUTPUT_DIR / "defect_results.csv"
    if not defects_path.exists():
        raise HTTPException(status_code=404, detail="No defect results available")

    df = pd.read_csv(defects_path)

    df = clean_dataframe_for_json(df)

    return clean_for_json(df.to_dict(orient="records"))


@app.get("/download/master")
async def download_master():
    path = OUTPUT_DIR / "master_specs.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No master snapshot available. Run /process/ first.")
    return FileResponse(path, filename="master_specs.csv")
