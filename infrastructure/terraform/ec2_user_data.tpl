#!/bin/bash
set -ex
exec > /var/log/user-data.log 2>&1

echo "=== Starting user-data script at $(date) ==="

# Update and install packages
apt-get update
apt-get install -y git python3 python3-venv python3-pip awscli postgresql-client tesseract-ocr libtesseract-dev python3-pil

# Setup application
cd /home/ubuntu

# Clone or update repo
if [ ! -d specs-pipeline ]; then
  echo "Cloning repository..."
  sudo -u ubuntu git clone ${repo_git_url} specs-pipeline
else
  echo "Updating repository..."
  cd specs-pipeline
  sudo -u ubuntu git pull
  cd /home/ubuntu
fi

cd /home/ubuntu/specs-pipeline/backend

# Create virtual environment
echo "Setting up Python virtual environment..."
sudo -u ubuntu python3 -m venv venv
sudo -u ubuntu bash -c '. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt'

# Create directories
echo "Creating data directories..."
sudo -u ubuntu mkdir -p data/uploads data/landing data/outputs

# Create .env file
echo "Creating .env file..."
sudo -u ubuntu cat <<EOF > .env
AWS_REGION=${aws_region}
S3_BUCKET=${s3_bucket}
DATABASE_URL=postgresql://${db_user}:${db_password}@${db_endpoint}:5432/postgres
EOF

# Create systemd service
echo "Creating systemd service..."
cat <<EOF >/etc/systemd/system/fastapi.service
[Unit]
Description=FastAPI Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/specs-pipeline/backend
ExecStart=/home/ubuntu/specs-pipeline/backend/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
EnvironmentFile=/home/ubuntu/specs-pipeline/backend/.env
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Start service
echo "Starting FastAPI service..."
systemctl daemon-reload
systemctl enable fastapi.service
systemctl start fastapi.service

echo "=== User-data script completed ==="
systemctl status fastapi.service