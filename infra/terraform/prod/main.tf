# Production Infrastructure - Terraform Configuration

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    # Configure backend in backend.tf
    # This ensures state is stored remotely with locking
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.owner_team
      CostCenter  = var.cost_center
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# Local variables
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Terraform   = "true"
  }
  
  azs = slice(data.aws_availability_zones.available.names, 0, 3)
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"
  
  name_prefix         = local.name_prefix
  vpc_cidr            = var.vpc_cidr
  availability_zones  = local.azs
  private_subnets     = var.private_subnets
  public_subnets      = var.public_subnets
  database_subnets    = var.database_subnets
  enable_nat_gateway  = true
  single_nat_gateway  = var.environment == "prod" ? false : true
  enable_dns_hostnames = true
  enable_dns_support  = true
  
  tags = local.common_tags
}

# Security Groups
module "security_groups" {
  source = "./modules/security"
  
  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  
  tags = local.common_tags
}

# RDS PostgreSQL Database
module "database" {
  source = "./modules/database"
  
  name_prefix            = local.name_prefix
  vpc_id                 = module.vpc.vpc_id
  database_subnets       = module.vpc.database_subnet_ids
  security_group_ids     = [module.security_groups.database_sg_id]
  
  engine                 = "postgres"
  engine_version         = var.db_engine_version
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  max_allocated_storage  = var.db_max_allocated_storage
  storage_encrypted      = true
  
  database_name          = var.db_name
  master_username        = var.db_master_username
  multi_az               = var.environment == "prod" ? true : false
  
  backup_retention_period = var.db_backup_retention_period
  backup_window          = var.db_backup_window
  maintenance_window     = var.db_maintenance_window
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval    = 60
  
  deletion_protection    = var.environment == "prod" ? true : false
  skip_final_snapshot    = var.environment == "prod" ? false : true
  final_snapshot_identifier = "${local.name_prefix}-final-snapshot"
  
  tags = local.common_tags
}

# EKS Cluster
module "eks" {
  source = "./modules/eks"
  
  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  subnet_ids  = module.vpc.private_subnet_ids
  
  cluster_version = var.eks_cluster_version
  
  node_groups = {
    application = {
      desired_size   = var.eks_desired_nodes
      min_size       = var.eks_min_nodes
      max_size       = var.eks_max_nodes
      instance_types = var.eks_instance_types
      capacity_type  = "ON_DEMAND"
      disk_size      = 50
      
      labels = {
        role = "application"
      }
      
      taints = []
    }
  }
  
  tags = local.common_tags
}

# Application Load Balancer
module "alb" {
  source = "./modules/alb"
  
  name_prefix        = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  public_subnets     = module.vpc.public_subnet_ids
  security_group_ids = [module.security_groups.alb_sg_id]
  
  enable_deletion_protection = var.environment == "prod" ? true : false
  enable_http2              = true
  enable_waf                = var.environment == "prod" ? true : false
  
  ssl_certificate_arn = var.ssl_certificate_arn
  
  tags = local.common_tags
}

# ElastiCache Redis for session storage and caching
module "redis" {
  source = "./modules/redis"
  
  name_prefix        = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.security_groups.redis_sg_id]
  
  node_type                  = var.redis_node_type
  num_cache_nodes            = var.redis_num_nodes
  parameter_group_family     = "redis7"
  engine_version             = "7.0"
  port                       = 6379
  automatic_failover_enabled = var.environment == "prod" ? true : false
  
  snapshot_retention_limit = var.redis_snapshot_retention
  snapshot_window         = "03:00-05:00"
  maintenance_window      = "mon:05:00-mon:07:00"
  
  tags = local.common_tags
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"
  
  name_prefix = local.name_prefix
  
  buckets = {
    artifacts = {
      versioning_enabled = true
      lifecycle_rules = [
        {
          id      = "delete_old_versions"
          enabled = true
          noncurrent_version_expiration_days = 90
        }
      ]
    }
    
    backups = {
      versioning_enabled = true
      lifecycle_rules = [
        {
          id      = "transition_to_glacier"
          enabled = true
          transition_days = 30
          storage_class  = "GLACIER"
        }
      ]
    }
    
    logs = {
      versioning_enabled = false
      lifecycle_rules = [
        {
          id      = "expire_old_logs"
          enabled = true
          expiration_days = 90
        }
      ]
    }
  }
  
  tags = local.common_tags
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/eks/${local.name_prefix}/application"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "database" {
  name              = "/aws/rds/${local.name_prefix}/postgresql"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "database_endpoint" {
  description = "Database endpoint"
  value       = module.database.endpoint
  sensitive   = true
}

output "database_port" {
  description = "Database port"
  value       = module.database.port
}

output "eks_cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = module.alb.dns_name
}

output "alb_zone_id" {
  description = "ALB Zone ID for Route53"
  value       = module.alb.zone_id
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.redis.endpoint
  sensitive   = true
}

output "s3_bucket_names" {
  description = "S3 bucket names"
  value       = module.s3.bucket_names
}
