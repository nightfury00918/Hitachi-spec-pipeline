# app.py
import os
import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from botocore.exceptions import ClientError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from pathlib import Path
import shutil
import logging
import numpy as np
import pandas as pd
from typing import List
from typing import Optional
import uuid
from db import SessionLocal
from models import MasterSpec, RawExtraction
from utils import clean_dataframe_for_json, clean_for_json
from s3_utils import upload_file_stream, download_file_stream, s3
from pipeline import process_all_and_build_master, process_all_and_build_master_from_s3, run_defect_mapping, UPLOAD_DIR

from dotenv import load_dotenv

load_dotenv()

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
    
    if s3 is None:
        raise HTTPException(status_code=500, detail="S3 not configured. Please check AWS credentials.")
    
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        raise HTTPException(status_code=500, detail="S3_BUCKET not configured")
    
    run_id = str(uuid.uuid4())
    results = []
    
    for file in files:
        try:
            # Generate unique filename with timestamp
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename_parts = file.filename.rsplit('.', 1)
            if len(filename_parts) == 2:
                base_name, extension = filename_parts
                unique_filename = f"{base_name}_{timestamp}.{extension}"
            else:
                unique_filename = f"{file.filename}_{timestamp}"
            
            # S3 key with run_id prefix
            s3_key = f"uploads/{run_id}/{unique_filename}"
            
            # Stream file directly to S3
            upload_file_stream(bucket, file.file, s3_key)
            
            results.append({
                "filename": file.filename,
                "s3_key": s3_key,
                "run_id": run_id,
                "unique_filename": unique_filename
            })
            logger.info(f"Uploaded {file.filename} to S3: s3://{bucket}/{s3_key}")
            
        except Exception as e:
            logger.error(f"Failed to upload {file.filename} to S3: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename}: {str(e)}")
    
    return {
        "uploaded": results,
        "run_id": run_id,
        "message": f"Successfully uploaded {len(results)} files to S3"
    }


@app.post("/process/")
async def process_pipeline(run_id: Optional[str] = Body(None), from_s3: bool = Body(True)):
    """
    Process files from S3 directly without local storage.
    If run_id is provided, processes files from s3://<S3_BUCKET>/uploads/<run_id>/
    If run_id is not provided, processes files from local uploads directory (fallback)
    All outputs are saved directly to S3.
    """
    bucket = os.getenv("S3_BUCKET")
    
    if from_s3 and bucket:
        if not run_id:
            raise HTTPException(status_code=400, detail="run_id is required when from_s3=True")
        
        logger.info(f"Processing files from S3 for run_id: {run_id}")
        try:
            # Process files directly from S3
            parsed_by_source, merged_master = process_all_and_build_master_from_s3(run_id)
        except Exception as e:
            logger.error(f"Failed to process files from S3: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to process files from S3: {str(e)}")
    else:
        # Fallback to local processing
        if not any(UPLOAD_DIR.iterdir()):
            raise HTTPException(status_code=400, detail="No uploaded files to process. Upload first.")
        
        logger.info("Processing files from local storage")
        parsed_by_source, merged_master = process_all_and_build_master()

    # defects mapping uses a defects.csv file either local or you can store it in S3; keep existing logic:
    defects_path = Path(__file__).parent / "data" / "defects.csv"
    defect_results = []
    if defects_path.exists():
        df = run_defect_mapping(defects_path, merged_master)
        # make sure we return JSON serializable result
        defect_results = df.to_dict(orient="records")

    return clean_for_json({
        "run_id": run_id,
        "parsed_by_source": parsed_by_source,
        "master": merged_master,
        "defects": defect_results,
        "message": "Processing completed. All outputs saved to S3."
    })


@app.get("/specs/")
def get_specs(
    view: str = Query("merged", enum=["merged", "raw"]),
    strategy: str = Query("priority", enum=["priority", "latest", "all"])
):
    db: Session = SessionLocal()
    try:
        rows = db.query(MasterSpec).all()
        logger.info(f"Found {len(rows)} specs in database")
        if not rows:
            logger.warning("No specs found in database")
            return []  # return immediately if no data

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
    """Get defect results from S3."""
    
    bucket = os.getenv("S3_BUCKET")
    if not bucket or s3 is None:
        raise HTTPException(status_code=500, detail="S3 not configured")
    
    s3_key = "outputs/defect_results.csv"
    
    try:
        # Check if file exists in S3
        s3.head_object(Bucket=bucket, Key=s3_key)
        
        # Download file as stream and read into DataFrame
        file_stream = download_file_stream(bucket, s3_key)
        df = pd.read_csv(file_stream)
        df = clean_dataframe_for_json(df)
        
        return clean_for_json(df.to_dict(orient="records"))
        
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            raise HTTPException(status_code=404, detail="No defect results available. Run /process/ first.")
        else:
            raise HTTPException(status_code=500, detail=f"Error accessing S3: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/debug/db-status")
async def debug_db_status():
    """Debug endpoint to check database status and specs count."""
    db: Session = SessionLocal()
    try:
        # Check total specs count
        total_specs = db.query(MasterSpec).count()
        
        # Check recent specs
        recent_specs = db.query(MasterSpec).order_by(MasterSpec.added_at.desc()).limit(5).all()
        
        # Check raw extractions
        total_extractions = db.query(RawExtraction).count()
        
        return {
            "total_specs": total_specs,
            "total_extractions": total_extractions,
            "recent_specs": [
                {
                    "id": s.id,
                    "param": s.param,
                    "value": s.value,
                    "source": s.source,
                    "added_at": s.added_at.isoformat() if s.added_at else None
                }
                for s in recent_specs
            ],
            "database_url": os.getenv("DATABASE_URL", "sqlite:///./data/master.db")
        }
    finally:
        db.close()


@app.get("/debug/model-status")
async def debug_model_status():
    """Debug endpoint to check embedding model status."""
    from pipeline import EMBED_MODEL, PARAM_EMBEDS, CANONICAL, map_line_to_param
    
    # Test parameter mapping with sample text
    test_lines = [
        "cap diameter: 25mm",
        "hole diameter 30mm",
        "surface finish tolerance 0.5um",
        "max pressure 10 bar",
        "temperature range -40 to 85°C"
    ]
    
    test_results = []
    for line in test_lines:
        param, score = map_line_to_param(line)
        test_results.append({
            "line": line,
            "param": param,
            "score": score
        })
    
    return {
        "model_loaded": EMBED_MODEL is not None,
        "canonical_params": list(CANONICAL.keys()),
        "param_embeddings_loaded": len(PARAM_EMBEDS),
        "test_mappings": test_results
    }


@app.post("/debug/test-processing")
async def debug_test_processing():
    """Debug endpoint to test processing with hardcoded data."""
    from pipeline import _build_master_from_parsed_data
    from db import SessionLocal
    from models import RawExtraction
    
    # Create test data
    session = SessionLocal()
    try:
        # Create a test raw extraction
        test_text = """
        Cap diameter: 25mm
        Hole diameter: 30mm
        Surface finish tolerance: 0.5um
        Max pressure: 10 bar
        Temperature range: -40 to 85°C
        """
        
        re_obj = RawExtraction(
            source="test_debug.txt", 
            raw_text=test_text, 
            meta_info={"type": "DEBUG"}
        )
        session.add(re_obj)
        session.commit()
        
        # Create parsed data
        parsed_by_source = {
            "test_debug.txt": {
                "cap_diameter": [{
                    "raw": "Cap diameter: 25mm",
                    "value": "25",
                    "unit": "mm",
                    "source": "DEBUG",
                    "priority": 1,
                    "filename": "test_debug.txt",
                    "extraction_id": re_obj.id
                }],
                "hole_diameter": [{
                    "raw": "Hole diameter: 30mm",
                    "value": "30",
                    "unit": "mm",
                    "source": "DEBUG",
                    "priority": 1,
                    "filename": "test_debug.txt",
                    "extraction_id": re_obj.id
                }]
            }
        }
        
        extraction_id_by_file = {"test_debug.txt": re_obj.id}
        
        # Process the data
        parsed_by_source_result, merged_master = _build_master_from_parsed_data(
            session, parsed_by_source, extraction_id_by_file
        )
        
        return {
            "status": "success",
            "parsed_sources": len(parsed_by_source_result),
            "master_params": len(merged_master),
            "test_extraction_id": re_obj.id,
            "message": "Test processing completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Debug test processing failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Test processing failed"
        }
    finally:
        session.close()


@app.post("/debug/test-file-extraction")
async def debug_test_file_extraction():
    """Debug endpoint to test file extraction directly."""
    from pipeline import extract_text_for_s3_stream
    import io
    
    # Create test file content
    test_content = """
    Test Document
    Cap diameter: 25mm
    Hole diameter: 30mm
    Surface finish tolerance: 0.5um
    Max pressure: 10 bar
    Temperature range: -40 to 85°C
    """
    
    # Test with different file types
    test_cases = [
        ("test.txt", test_content.encode('utf-8')),
        ("test.docx", test_content.encode('utf-8')),  # This will fail but we'll catch the error
    ]
    
    results = []
    
    for filename, content in test_cases:
        try:
            file_stream = io.BytesIO(content)
            extracted_text = extract_text_for_s3_stream(file_stream, filename)
            
            results.append({
                "filename": filename,
                "success": True,
                "extracted_length": len(extracted_text),
                "extracted_text": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
            })
            
        except Exception as e:
            results.append({
                "filename": filename,
                "success": False,
                "error": str(e)
            })
    
    return {
        "test_results": results,
        "message": "File extraction test completed"
    }


@app.get("/download/master")
async def download_master():
    """Download master specs CSV from S3."""    
    bucket = os.getenv("S3_BUCKET")
    if not bucket or s3 is None:
        raise HTTPException(status_code=500, detail="S3 not configured")
    
    s3_key = "outputs/master_specs.csv"
    
    try:
        # Check if file exists in S3
        s3.head_object(Bucket=bucket, Key=s3_key)
        
        # Generate presigned URL for download
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': s3_key},
            ExpiresIn=3600  # URL expires in 1 hour
        )
        
        return JSONResponse({
            "download_url": url,
            "filename": "master_specs.csv",
            "expires_in": 3600
        })
        
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            raise HTTPException(status_code=404, detail="No master snapshot available. Run /process/ first.")
        else:
            raise HTTPException(status_code=500, detail=f"Error accessing S3: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
