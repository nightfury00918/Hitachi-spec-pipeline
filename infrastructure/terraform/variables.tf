variable "project_name" {
  description = "Project prefix/name"
  type        = string
  default     = "specs-pipeline-dev"
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "dev"
}

variable "key_name" {
  description = "EC2 Key pair name (must exist in AWS)"
  type        = string
  default     = "hitachi-spec-pipeline-key-pair"
}

variable "instance_type" {
  description = "EC2 instance type for the FastAPI server"
  type        = string
  default     = "t3.medium"
}

variable "db_username" {
  description = "RDS master user"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "RDS master password (dev only)"
  type        = string
  default     = "HitachiDatabase<>?"
}

variable "allowed_cidr" {
  description = "CIDR allowed for SSH / HTTP (dev). Use 0.0.0.0/0 for public demo"
  type        = string
  default     = "0.0.0.0/0"
}

variable "repo_git_url" {
  description = "Git repository URL that EC2 will clone. Replace with your repo (HTTPS)."
  type        = string
  default     = "https://github.com/nightfury00918/Hitachi-spec-pipeline.git"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}