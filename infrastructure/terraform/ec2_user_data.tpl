#cloud-config
package_update: true
package_upgrade: true
packages:
  - git
  - python3
  - python3-venv
  - python3-pip
  - awscli
  - postgresql-client
  - tesseract-ocr
  - libtesseract-dev
  - python3-pil
  - python3-pil.imagetk
write_files:
  - path: /home/ubuntu/setup.sh
    permissions: "0755"
    content: |
      #!/bin/bash
      set -e  # Exit on any error

      echo "Starting application setup..."

      # Ensure ubuntu user owns home directory
      chown ubuntu:ubuntu /home/ubuntu
      cd /home/ubuntu

      # Clone repository if not exists
      if [ ! -d specs-pipeline ]; then
        echo "Cloning repository..."
        git clone ${repo_git_url} specs-pipeline
      fi

      cd specs-pipeline
      chown -R ubuntu:ubuntu .

      # Create virtual environment
      echo "Creating virtual environment..."
      python3 -m venv venv

      # Activate virtual environment and install dependencies
      echo "Installing Python dependencies..."
      source venv/bin/activate
      pip install --upgrade pip
      pip install -r requirements.txt

      # Create necessary directories
      echo "Creating data directories..."
      mkdir -p data/uploads data/landing data/outputs
      chown -R ubuntu:ubuntu data/

      # Create environment file
      echo "Creating environment configuration..."
      cat > .env <<EOF
      AWS_REGION=${aws_region}
      S3_BUCKET=${s3_bucket}
      DATABASE_URL=postgresql://${db_user}:${db_password}@${db_endpoint}:5432/postgres
      EOF
      chown ubuntu:ubuntu .env

      # Test S3 connectivity
      echo "Testing S3 connectivity..."
      source venv/bin/activate
      python3 -c "
      import boto3
      import os
      try:
          s3 = boto3.client('s3', region_name='${aws_region}')
          s3.head_bucket(Bucket='${s3_bucket}')
          print('✓ S3 bucket access confirmed')
      except Exception as e:
          print(f'✗ S3 connectivity test failed: {e}')
          exit(1)
      "

      # Test database connectivity
      echo "Testing database connectivity..."
      PGPASSWORD='${db_password}' psql -h ${db_endpoint} -U ${db_user} -d postgres -c "SELECT 1;" || echo "Warning: Database connection test failed"

      # Start the application
      echo "Starting FastAPI application..."
      nohup uvicorn app:app --host 0.0.0.0 --port 80 > app.log 2>&1 &

      # Wait a moment and check if the process started
      sleep 5
      if pgrep -f "uvicorn app:app" > /dev/null; then
        echo "✓ FastAPI application started successfully"
        echo "Application logs: tail -f /home/ubuntu/specs-pipeline/app.log"
      else
        echo "✗ Failed to start FastAPI application"
        echo "Check logs: cat /home/ubuntu/specs-pipeline/app.log"
      fi

      echo "Setup completed!"
runcmd:
  - [bash, /home/ubuntu/setup.sh]
