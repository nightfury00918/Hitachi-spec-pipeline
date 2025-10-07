# Terraform Infrastructure Setup

This directory contains Terraform configuration for deploying the specs pipeline application to AWS.

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Terraform installed** (version >= 1.6.0)
3. **EC2 Key Pair** created in your AWS account
4. **Git repository** accessible from EC2 instances

## Quick Start

### 1. Configure Variables

```bash
# Copy the example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required variables to update:**

- `key_name`: Your EC2 key pair name (must exist in AWS)
- `repo_git_url`: Your Git repository URL (HTTPS)

### 2. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply
```

### 3. Access Your Application

After deployment, get the application URL:

```bash
# Get the public IP
terraform output ec2_public_ip

# Get the S3 bucket name
terraform output s3_bucket
```

Your application will be available at: `http://<EC2_PUBLIC_IP>`

## Infrastructure Components

### 1. VPC and Networking

- Custom VPC with public subnet
- Internet Gateway for public access
- Route tables for traffic routing

### 2. Security Groups

- **EC2 Security Group**: Allows HTTP (80) and SSH (22) access
- **RDS Security Group**: Allows PostgreSQL (5432) from EC2 only

### 3. S3 Bucket

- Private bucket for file uploads and outputs
- Server-side encryption enabled
- Versioning enabled
- Lifecycle policies for cost optimization
- Public access blocked for security

### 4. IAM Role and Permissions

- EC2 instance profile with S3 access
- Permissions for:
  - S3 bucket operations (list, read, write, delete)
  - CloudWatch logging
  - Versioned object operations

### 5. RDS PostgreSQL

- Publicly accessible (dev only)
- 20GB storage
- t3.micro instance class
- Automated backups disabled (dev only)

### 6. EC2 Instance

- Ubuntu 22.04 LTS
- t3.medium instance type
- Auto-configuration via user data script
- Application deployment and startup

## Configuration Details

### S3 Bucket Configuration

The S3 bucket is configured with:

- **Encryption**: AES256 server-side encryption
- **Versioning**: Enabled for data protection
- **Lifecycle**:
  - Non-current versions deleted after 30 days
  - Objects transition to IA storage after 30 days
- **Access**: Private with public access blocked

### IAM Permissions

The EC2 instance has permissions for:

```json
{
  "s3:ListBucket",
  "s3:GetBucketLocation",
  "s3:GetBucketVersioning",
  "s3:GetObject",
  "s3:PutObject",
  "s3:DeleteObject",
  "s3:PutObjectAcl",
  "s3:GetObjectVersion",
  "s3:DeleteObjectVersion",
  "s3:GetObjectVersionAcl"
}
```

### Application Deployment

The EC2 user data script:

1. Installs system dependencies
2. Clones the Git repository
3. Creates Python virtual environment
4. Installs Python dependencies
5. Creates data directories
6. Sets up environment variables
7. Tests S3 and database connectivity
8. Starts the FastAPI application

## Environment Variables

The application is configured with these environment variables:

```
AWS_REGION=<aws_region>
S3_BUCKET=<s3_bucket_name>
DATABASE_URL=postgresql://<db_user>:<db_password>@<db_endpoint>:5432/postgres
```

## Monitoring and Logs

### Application Logs

```bash
# SSH to EC2 instance
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>

# View application logs
tail -f /home/ubuntu/specs-pipeline/app.log
```

### CloudWatch Logs

The application is configured to send logs to CloudWatch (if configured).

## Security Considerations

### For Development

- RDS is publicly accessible
- Security groups allow all IPs (0.0.0.0/0)
- Database password is in plain text

### For Production

- Use private subnets for RDS
- Restrict security group CIDRs
- Use AWS Secrets Manager for passwords
- Enable RDS encryption and backups
- Use Application Load Balancer with SSL

## Troubleshooting

### Common Issues

#### 1. EC2 Instance Not Starting

```bash
# Check EC2 instance logs
aws ec2 get-console-output --instance-id <instance-id>

# SSH to instance and check user data logs
sudo cat /var/log/cloud-init-output.log
```

#### 2. Application Not Accessible

```bash
# Check if application is running
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
ps aux | grep uvicorn

# Check application logs
tail -f /home/ubuntu/specs-pipeline/app.log
```

#### 3. S3 Access Issues

```bash
# Test S3 connectivity from EC2
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
cd /home/ubuntu/specs-pipeline
source venv/bin/activate
python3 -c "
import boto3
s3 = boto3.client('s3')
s3.list_buckets()
"
```

#### 4. Database Connection Issues

```bash
# Test database connectivity
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>
PGPASSWORD='<password>' psql -h <rds-endpoint> -U postgres -d postgres
```

### Useful Commands

```bash
# Get all outputs
terraform output

# Get specific output
terraform output s3_bucket

# Destroy infrastructure (be careful!)
terraform destroy

# Refresh state
terraform refresh

# Validate configuration
terraform validate
```

## Cost Optimization

The current configuration is optimized for development:

- t3.micro RDS instance
- t3.medium EC2 instance
- S3 lifecycle policies
- No RDS backups

For production, consider:

- Reserved instances
- RDS Multi-AZ
- Application Load Balancer
- Auto Scaling Groups

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

**Warning**: This will delete all data including:

- S3 bucket and all files
- RDS database and all data
- EC2 instance and any local data

Make sure to backup any important data before running destroy.
