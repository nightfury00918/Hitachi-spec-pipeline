#!/usr/bin/env python3
"""
Debug script to help troubleshoot the specs issue.
This script will help identify why /specs/ returns nothing.
"""

import os
import sys
import requests
import json
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

base_url = "http://localhost:8001"

def test_specs_workflow():
    """Test the complete workflow and check specs."""
        
    print("Debugging Specs Issue")
    print("=" * 50)
    
    # Step 1: Check database status
    print("\nStep 1: Checking database status...")
    try:
        response = requests.get(f"{base_url}/debug/db-status")
        response.raise_for_status()
        db_status = response.json()
        
        print(f"Database Status:")
        print(f"   - Total specs: {db_status['total_specs']}")
        print(f"   - Total extractions: {db_status['total_extractions']}")
        print(f"   - Database URL: {db_status['database_url']}")
        
        if db_status['recent_specs']:
            print(f"   - Recent specs:")
            for spec in db_status['recent_specs']:
                print(f"     * {spec['param']}: {spec['value']} ({spec['source']})")
        else:
            print("   - No recent specs found")
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to get database status: {e}")
        return False
    
    # Step 2: Check specs endpoint
    print("\nStep 2: Checking specs endpoint...")
    try:
        response = requests.get(f"{base_url}/specs/")
        response.raise_for_status()
        specs = response.json()
        
        print(f"Specs endpoint response:")
        print(f"   - Type: {type(specs)}")
        print(f"   - Length: {len(specs) if isinstance(specs, list) else 'N/A'}")
        
        if specs:
            print(f"   - First spec: {specs[0] if isinstance(specs, list) else specs}")
        else:
            print("   - No specs returned")
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to get specs: {e}")
        return False
    
    # Step 3: Check model status
    print("\nStep 3: Checking embedding model status...")
    try:
        response = requests.get(f"{base_url}/debug/model-status")
        response.raise_for_status()
        model_status = response.json()
        
        print(f"Model Status:")
        print(f"   - Model loaded: {model_status['model_loaded']}")
        print(f"   - Canonical params: {len(model_status['canonical_params'])}")
        print(f"   - Param embeddings loaded: {model_status['param_embeddings_loaded']}")
        
        if model_status['test_mappings']:
            print(f"   - Test mappings:")
            for test in model_status['test_mappings']:
                print(f"     * '{test['line']}' -> {test['param']} (score: {test['score']:.3f})")
                
    except requests.exceptions.RequestException as e:
        print(f"Failed to get model status: {e}")
        return False
    
    # Step 4: Test with different view options
    print("\nStep 4: Testing different view options...")
    
    views = ["merged", "raw"]
    strategies = ["priority", "latest", "all"]
    
    for view in views:
        for strategy in strategies:
            try:
                url = f"{base_url}/specs/?view={view}&strategy={strategy}"
                response = requests.get(url)
                response.raise_for_status()
                specs = response.json()
                
                print(f"   - {view}/{strategy}: {len(specs) if isinstance(specs, list) else 'N/A'} specs")
                
            except requests.exceptions.RequestException as e:
                print(f"   - {view}/{strategy}: Error - {e}")
    
    return True

def test_processing_workflow():
    """Test the processing workflow to see if specs are created."""
    
    print("\nTesting Processing Workflow")
    print("=" * 50)
    
    # Check if we have test files
    test_files = [
        "backend/data/input/spec_v1.docx",
        "backend/data/input/spec_v2.pdf", 
        "backend/data/input/spec_v3.jpg"
    ]
    
    existing_files = []
    for file_path in test_files:
        if Path(file_path).exists():
            existing_files.append(file_path)
    
    if not existing_files:
        print("No test files found. Skipping processing test.")
        return True
    
    print(f"Found {len(existing_files)} test files")
    
    # Step 1: Upload files
    print("\nStep 1: Uploading files...")
    upload_url = f"{base_url}/upload/"
    
    files_to_upload = []
    for file_path in existing_files:
        with open(file_path, 'rb') as f:
            files_to_upload.append(('files', (Path(file_path).name, f, 'application/octet-stream')))
    
    try:
        response = requests.post(upload_url, files=files_to_upload)
        response.raise_for_status()
        upload_result = response.json()
        run_id = upload_result.get('run_id')
        print(f"Files uploaded. Run ID: {run_id}")
    except requests.exceptions.RequestException as e:
        print(f"Upload failed: {e}")
        return False
    
    # Step 2: Process files
    print(f"\nStep 2: Processing files...")
    process_url = f"{base_url}/process/"
    
    try:
        response = requests.post(process_url, json={"run_id": run_id, "from_s3": True})
        response.raise_for_status()
        process_result = response.json()
        print("Files processed successfully")
    except requests.exceptions.RequestException as e:
        print(f"Processing failed: {e}")
        return False
    
    # Step 3: Check specs after processing
    print(f"\nStep 3: Checking specs after processing...")
    try:
        response = requests.get(f"{base_url}/debug/db-status")
        response.raise_for_status()
        db_status = response.json()
        
        print(f"Database Status After Processing:")
        print(f"   - Total specs: {db_status['total_specs']}")
        print(f"   - Total extractions: {db_status['total_extractions']}")
        
        if db_status['recent_specs']:
            print(f"   - Recent specs:")
            for spec in db_status['recent_specs']:
                print(f"     * {spec['param']}: {spec['value']} ({spec['source']})")
        
    except requests.exceptions.RequestException as e:
        print(f"Failed to check database status: {e}")
        return False
    
    # Step 4: Check specs endpoint again
    print(f"\nStep 4: Checking specs endpoint after processing...")
    try:
        response = requests.get(f"{base_url}/specs/")
        response.raise_for_status()
        specs = response.json()
        
        print(f"Specs endpoint after processing:")
        print(f"   - Type: {type(specs)}")
        print(f"   - Length: {len(specs) if isinstance(specs, list) else 'N/A'}")
        
        if specs:
            print(f"   - Sample specs:")
            for i, spec in enumerate(specs[:3]):  # Show first 3 specs
                print(f"     {i+1}. {spec}")
        else:
            print("   - Still no specs returned")
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to get specs: {e}")
        return False
    
    return True

def main():
    """Main debug function."""
    print("Specs Debug Tool")
    print("=" * 50)
    
    # Test current state
    test_specs_workflow()
    
    # Test processing workflow
    test_processing_workflow()
    
    # Test file extraction
    print("\nTesting file extraction...")
    try:
        response = requests.post(f"{base_url}/debug/test-file-extraction")
        response.raise_for_status()
        extraction_test = response.json()
        
        print("File extraction test results:")
        for result in extraction_test['test_results']:
            if result['success']:
                print(f"{result['filename']}: {result['extracted_length']} chars extracted")
            else:
                print(f"{result['filename']}: {result['error']}")
                
    except requests.exceptions.RequestException as e:
        print(f"Failed to test file extraction: {e}")
    
    # Test processing with hardcoded data
    print("\nTesting processing with hardcoded data...")
    try:
        response = requests.post(f"{base_url}/debug/test-processing")
        response.raise_for_status()
        processing_test = response.json()
        
        if processing_test['status'] == 'success':
            print(f"Processing test successful:")
            print(f"   - Parsed sources: {processing_test['parsed_sources']}")
            print(f"   - Master params: {processing_test['master_params']}")
        else:
            print(f"Processing test failed: {processing_test['error']}")
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to test processing: {e}")
    
    print("\nDebug Summary")
    print("=" * 50)
    print("If specs are still empty after processing:")
    print("1. Check the application logs for errors")
    print("2. Verify S3 connectivity and permissions")
    print("3. Check if files are being processed correctly")
    print("4. Ensure the database is writable")
    print("5. Check the embedding model loading")
    print("6. Test file extraction with /debug/test-file-extraction")
    print("7. Test processing with /debug/test-processing")

if __name__ == "__main__":
    main()
