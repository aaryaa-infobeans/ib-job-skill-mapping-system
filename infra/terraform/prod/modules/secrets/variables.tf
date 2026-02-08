variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "secret_recovery_days" {
  description = "Number of days to retain deleted secrets"
  type        = number
  default     = 7
}

# OAuth Configuration
variable "oauth_client_id" {
  description = "OAuth 2.0 client ID"
  type        = string
  sensitive   = true
}

variable "oauth_client_secret" {
  description = "OAuth 2.0 client secret"
  type        = string
  sensitive   = true
}

variable "oauth_tenant_id" {
  description = "OAuth 2.0 tenant ID"
  type        = string
  sensitive   = true
}

# LLM API Keys
variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_openai_endpoint" {
  description = "Azure OpenAI endpoint URL"
  type        = string
  default     = ""
}

variable "azure_openai_api_key" {
  description = "Azure OpenAI API key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_openai_deployment" {
  description = "Azure OpenAI deployment name"
  type        = string
  default     = ""
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  default     = ""
  sensitive   = true
}

# Redis Configuration
variable "redis_endpoint" {
  description = "Redis endpoint"
  type        = string
}

variable "redis_port" {
  description = "Redis port"
  type        = number
  default     = 6379
}

# KMS Configuration
variable "kms_key_arn" {
  description = "ARN of KMS key for secrets encryption (will create if not provided)"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
