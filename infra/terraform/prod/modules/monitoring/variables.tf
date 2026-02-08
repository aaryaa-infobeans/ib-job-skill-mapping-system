# Monitoring Module Variables

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "critical_alert_emails" {
  description = "Email addresses for critical alerts"
  type        = list(string)
  default     = []
}

variable "warning_alert_emails" {
  description = "Email addresses for warning alerts"
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

variable "db_instance_id" {
  description = "RDS database instance identifier"
  type        = string
}

variable "db_replica_id" {
  description = "RDS read replica instance identifier"
  type        = string
}

variable "redis_cluster_id" {
  description = "ElastiCache Redis cluster identifier"
  type        = string
}

variable "eks_cluster_name" {
  description = "EKS cluster name"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
