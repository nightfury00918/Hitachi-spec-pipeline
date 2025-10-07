# s3_utils.py
import os
import boto3
from pathlib import Path
import logging
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
from typing import Optional

logger = logging.getLogger("s3_utils")

def get_s3_client():
    """Get S3 client with proper error handling and configuration."""
    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        logger.info(f"Initializing S3 client for region: {region}")
        
        # Initialize S3 client
        s3_client = boto3.client("s3", region_name=region)
        
        # Test credentials by listing buckets (this will fail if credentials are invalid)
        s3_client.list_buckets()
        logger.info("S3 client initialized successfully")
        return s3_client
        
    except NoCredentialsError:
        logger.error("AWS credentials not found. Please configure AWS credentials using one of these methods:")
        logger.error("1. AWS CLI: run 'aws configure'")
        logger.error("2. Environment variables: set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        logger.error("3. IAM role (for EC2 instances)")
        raise
    except PartialCredentialsError as e:
        logger.error(f"Incomplete AWS credentials: {e}")
        raise
    except ClientError as e:
        logger.error(f"AWS client error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error initializing S3 client: {e}")
        raise

# Initialize S3 client
try:
    s3 = get_s3_client()
except Exception as e:
    logger.warning(f"Failed to initialize S3 client: {e}")
    logger.warning("S3 operations will fail until AWS credentials are properly configured")
    s3 = None

def list_objects(bucket: str, prefix: str):
    """List objects in S3 bucket with error handling."""
    if s3 is None:
        raise RuntimeError("S3 client not initialized. Check AWS credentials.")
    
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                yield obj["Key"]
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(f"Bucket '{bucket}' does not exist")
        elif error_code == 'AccessDenied':
            logger.error(f"Access denied to bucket '{bucket}'. Check IAM permissions.")
        else:
            logger.error(f"Error listing objects in bucket '{bucket}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing objects: {e}")
        raise

def download_file_stream(bucket: str, s3_key: str):
    """Download a file from S3 as a stream without saving to local disk."""
    if s3 is None:
        raise RuntimeError("S3 client not initialized. Check AWS credentials.")
    
    try:
        logger.info("Downloading s3://%s/%s as stream", bucket, s3_key)
        response = s3.get_object(Bucket=bucket, Key=s3_key)
        return response['Body']
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchKey':
            logger.error(f"File s3://{bucket}/{s3_key} does not exist")
        elif error_code == 'NoSuchBucket':
            logger.error(f"Bucket '{bucket}' does not exist")
        elif error_code == 'AccessDenied':
            logger.error(f"Access denied to s3://{bucket}/{s3_key}")
        else:
            logger.error(f"Error downloading s3://{bucket}/{s3_key}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error downloading stream: {e}")
        raise

def download_prefix(bucket: str, prefix: str, local_dir: str):
    """
    Download all objects under s3://bucket/prefix to local_dir maintaining subfolders.
    """
    if s3 is None:
        raise RuntimeError("S3 client not initialized. Check AWS credentials.")
    
    try:
        Path(local_dir).mkdir(parents=True, exist_ok=True)
        downloaded_count = 0
        
        for key in list_objects(bucket, prefix):
            # skip "folders"
            if key.endswith("/"):
                continue
            rel = key[len(prefix):].lstrip("/")
            dest = Path(local_dir) / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            logger.info("Downloading s3://%s/%s -> %s", bucket, key, dest)
            
            try:
                s3.download_file(bucket, key, str(dest))
                downloaded_count += 1
            except ClientError as e:
                logger.error(f"Failed to download s3://{bucket}/{key}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error downloading s3://{bucket}/{key}: {e}")
                raise
        
        logger.info(f"Successfully downloaded {downloaded_count} files from s3://{bucket}/{prefix}")
        
    except Exception as e:
        logger.error(f"Error in download_prefix: {e}")
        raise

def upload_file_stream(bucket: str, file_stream, s3_key: str):
    """Upload a file stream directly to S3 without saving to local disk."""
    if s3 is None:
        raise RuntimeError("S3 client not initialized. Check AWS credentials.")
    
    try:
        logger.info("Uploading stream -> s3://%s/%s", bucket, s3_key)
        s3.upload_fileobj(file_stream, bucket, s3_key)
        logger.info("Successfully uploaded stream to s3://%s/%s", bucket, s3_key)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(f"Bucket '{bucket}' does not exist")
        elif error_code == 'AccessDenied':
            logger.error(f"Access denied to bucket '{bucket}'. Check IAM permissions.")
        else:
            logger.error(f"Error uploading stream to s3://{bucket}/{s3_key}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading stream: {e}")
        raise

def upload_file(bucket: str, local_path: str, s3_key: str):
    """Upload a single file to S3 with error handling."""
    if s3 is None:
        raise RuntimeError("S3 client not initialized. Check AWS credentials.")
    
    try:
        if not Path(local_path).exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        logger.info("Uploading %s -> s3://%s/%s", local_path, bucket, s3_key)
        s3.upload_file(local_path, bucket, s3_key)
        logger.info("Successfully uploaded %s to s3://%s/%s", local_path, bucket, s3_key)
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'NoSuchBucket':
            logger.error(f"Bucket '{bucket}' does not exist")
        elif error_code == 'AccessDenied':
            logger.error(f"Access denied to bucket '{bucket}'. Check IAM permissions.")
        else:
            logger.error(f"Error uploading file to s3://{bucket}/{s3_key}: {e}")
        raise
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error uploading file: {e}")
        raise

def upload_folder(bucket: str, local_dir: str, s3_prefix: str):
    """Upload all files in a folder to S3 with error handling."""
    if s3 is None:
        raise RuntimeError("S3 client not initialized. Check AWS credentials.")
    
    try:
        p = Path(local_dir)
        if not p.exists():
            raise FileNotFoundError(f"Local directory not found: {local_dir}")
        
        uploaded_count = 0
        for f in p.rglob("*"):
            if f.is_file():
                rel = f.relative_to(local_dir).as_posix()
                key = f"{s3_prefix.rstrip('/')}/{rel}"
                try:
                    upload_file(bucket, str(f), key)
                    uploaded_count += 1
                except Exception as e:
                    logger.error(f"Failed to upload {f}: {e}")
                    raise
        
        logger.info(f"Successfully uploaded {uploaded_count} files from {local_dir} to s3://{bucket}/{s3_prefix}")
        
    except Exception as e:
        logger.error(f"Error in upload_folder: {e}")
        raise
