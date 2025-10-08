# Terraform Variables Configuration
# Copy this file to terraform.tfvars and update the values

# Project Configuration
project_name = "specs-pipeline-dev"
environment  = "dev"

# AWS Configuration
aws_region = "us-east-1"

# EC2 Configuration
key_name      = "hitachi-spec-pipeline-key-pair" # Must exist in AWS
instance_type = "t3.medium"

# Database Configuration
db_username = "postgres"
db_password = "HitachiDatabase<>?" # Change this for production!

# Security Configuration
allowed_cidr = "0.0.0.0/0" # Restrict this for production!

# Repository Configuration
repo_git_url = "https://github.com/nightfury00918/Hitachi-spec-pipeline.git"
