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

write_files:
  - path: /etc/systemd/system/fastapi.service
    permissions: "0644"
    content: |
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

runcmd:
  - |
    set -e
    cd /home/ubuntu

    if [ ! -d specs-pipeline ]; then
      git clone ${repo_git_url} specs-pipeline
    else
      cd specs-pipeline && git pull
    fi

    cd specs-pipeline/backend
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    mkdir -p data/uploads data/landing data/outputs
    chown -R ubuntu:ubuntu data/

    echo "=== Writing .env file safely ==="
    printf '%s\n' \
      'AWS_REGION="${aws_region}"' \
      'S3_BUCKET="${s3_bucket}"' \
      'DATABASE_URL="postgresql://${db_user}:${db_password}@${db_endpoint}:5432/postgres"' \
      > .env
    chown ubuntu:ubuntu .env

    systemctl daemon-reload
    systemctl enable fastapi.service
    systemctl start fastapi.service
