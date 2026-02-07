# Production Environment Variables

# General Configuration
variable "aws_region" {
  description = "AWS region for production deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "ib-job-skill-mapping"
}

variable "owner_team" {
  description = "Team owning this infrastructure"
  type        = string
  default     = "platform-team"
}

variable "cost_center" {
  description = "Cost center for billing"
  type        = string
  default     = "engineering"
}

# Networking
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "private_subnets" {
  description = "Private subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "Public subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "database_subnets" {
  description = "Database subnet CIDR blocks"
  type        = list(string)
  default     = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]
}

# Database Configuration
variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.4"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.r6g.xlarge" # 4 vCPU, 32 GB RAM
}

variable "db_allocated_storage" {
  description = "Initial storage allocation in GB"
  type        = number
  default     = 100
}

variable "db_max_allocated_storage" {
  description = "Maximum storage allocation in GB (auto-scaling)"
  type        = number
  default     = 1000
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "ib_job_skill_mapping"
}

variable "db_master_username" {
  description = "Database master username"
  type        = string
  default     = "postgres"
  sensitive   = true
}

variable "db_backup_retention_period" {
  description = "Backup retention period in days"
  type        = number
  default     = 30
}

variable "db_backup_window" {
  description = "Backup window (UTC)"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "Maintenance window (UTC)"
  type        = string
  default     = "mon:04:00-mon:05:00"
}

# EKS Configuration
variable "eks_cluster_version" {
  description = "EKS cluster version"
  type        = string
  default     = "1.28"
}

variable "eks_desired_nodes" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 3
}

variable "eks_min_nodes" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 3
}

variable "eks_max_nodes" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 10
}

variable "eks_instance_types" {
  description = "Instance types for EKS worker nodes"
  type        = list(string)
  default     = ["t3.xlarge"] # 4 vCPU, 16 GB RAM
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.r6g.large" # 2 vCPU, 13.07 GB RAM
}

variable "redis_num_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 2
}

variable "redis_snapshot_retention" {
  description = "Snapshot retention limit in days"
  type        = number
  default     = 7
}

# SSL Configuration
variable "ssl_certificate_arn" {
  description = "ARN of ACM certificate for HTTPS"
  type        = string
  default     = "" # To be provided
}

# Logging
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 90
}

# Tags
variable "additional_tags" {
  description = "Additional tags for all resources"
  type        = map(string)
  default     = {}
}
