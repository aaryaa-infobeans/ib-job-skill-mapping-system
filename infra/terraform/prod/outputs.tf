# Production Infrastructure Outputs

# Networking Outputs
output "vpc_id" {
  description = "ID of the production VPC"
  value       = module.vpc.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.vpc.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.vpc.public_subnet_ids
}

output "database_subnet_ids" {
  description = "IDs of database subnets"
  value       = module.vpc.database_subnet_ids
}

# Database Outputs
output "database_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.database.endpoint
  sensitive   = true
}

output "database_port" {
  description = "RDS PostgreSQL port"
  value       = module.database.port
}

output "database_name" {
  description = "Name of the production database"
  value       = var.db_name
}

output "database_connection_string" {
  description = "Full database connection string (excluding password)"
  value       = "postgresql://${var.db_master_username}@${module.database.endpoint}:${module.database.port}/${var.db_name}"
  sensitive   = true
}

# EKS Outputs
output "eks_cluster_id" {
  description = "EKS cluster ID"
  value       = module.eks.cluster_id
}

output "eks_cluster_endpoint" {
  description = "Endpoint for EKS cluster"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "Name of the EKS cluster"
  value       = module.eks.cluster_name
}

output "eks_cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data for EKS cluster"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "eks_node_group_id" {
  description = "EKS node group ID"
  value       = module.eks.node_group_id
}

# Load Balancer Outputs
output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = module.alb.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the ALB (for Route53)"
  value       = module.alb.zone_id
}

output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = module.alb.arn
}

# Redis Outputs
output "redis_endpoint" {
  description = "Redis cluster endpoint"
  value       = module.redis.endpoint
  sensitive   = true
}

output "redis_port" {
  description = "Redis port"
  value       = module.redis.port
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = "redis://${module.redis.endpoint}:${module.redis.port}"
  sensitive   = true
}

# S3 Outputs
output "s3_artifacts_bucket" {
  description = "S3 bucket for artifacts"
  value       = module.s3.bucket_names["artifacts"]
}

output "s3_backups_bucket" {
  description = "S3 bucket for backups"
  value       = module.s3.bucket_names["backups"]
}

output "s3_logs_bucket" {
  description = "S3 bucket for logs"
  value       = module.s3.bucket_names["logs"]
}

# Secrets Outputs
output "secrets_arns" {
  description = "ARNs of all secrets in Secrets Manager"
  value       = module.secrets.all_secret_arns
  sensitive   = true
}

output "secrets_access_policy_arn" {
  description = "ARN of IAM policy for accessing secrets"
  value       = module.secrets.secrets_access_policy_arn
}

output "secrets_kms_key_arn" {
  description = "ARN of KMS key for secrets encryption"
  value       = module.secrets.kms_key_arn
}

# CloudWatch Outputs
output "application_log_group" {
  description = "CloudWatch log group for application logs"
  value       = aws_cloudwatch_log_group.application.name
}

output "database_log_group" {
  description = "CloudWatch log group for database logs"
  value       = aws_cloudwatch_log_group.database.name
}

# Security Group Outputs
output "database_security_group_id" {
  description = "Security group ID for database"
  value       = module.security_groups.database_sg_id
}

output "alb_security_group_id" {
  description = "Security group ID for ALB"
  value       = module.security_groups.alb_sg_id
}

output "redis_security_group_id" {
  description = "Security group ID for Redis"
  value       = module.security_groups.redis_sg_id
}

# Summary Output for Documentation
output "deployment_summary" {
  description = "Summary of deployed infrastructure"
  value = {
    environment     = var.environment
    region          = var.aws_region
    vpc_cidr        = var.vpc_cidr
    database_class  = var.db_instance_class
    eks_version     = var.eks_cluster_version
    eks_node_count  = "${var.eks_min_nodes}-${var.eks_max_nodes} nodes"
    redis_nodes     = var.redis_num_nodes
  }
}

# Connection Details for Application Configuration
output "application_config" {
  description = "Configuration values for application deployment"
  value = {
    database_host          = module.database.endpoint
    database_port          = module.database.port
    database_name          = var.db_name
    database_password_arn  = module.secrets.database_password_arn
    redis_host             = module.redis.endpoint
    redis_port             = module.redis.port
    redis_auth_arn         = module.secrets.redis_credentials_arn
    oauth_secret_arn       = module.secrets.oauth_client_secret_arn
    llm_keys_arn           = module.secrets.llm_api_keys_secret_arn
    app_secrets_arn        = module.secrets.application_secrets_arn
    log_group              = aws_cloudwatch_log_group.application.name
    artifacts_bucket       = module.s3.bucket_names["artifacts"]
    secrets_access_policy  = module.secrets.secrets_access_policy_arn
  }
  sensitive = true
}
