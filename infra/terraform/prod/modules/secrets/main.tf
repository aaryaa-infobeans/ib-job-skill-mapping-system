# AWS Secrets Manager Module

# Database Master Password (already created in database module, import here)
data "aws_secretsmanager_secret" "database_password" {
  name = "${var.name_prefix}-db-master-password"
}

# OAuth Client Secrets
resource "aws_secretsmanager_secret" "oauth_client" {
  name                    = "${var.name_prefix}-oauth-client"
  description             = "OAuth 2.0 client credentials for Microsoft Graph API"
  recovery_window_in_days = var.secret_recovery_days
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-oauth-client"
      SecretType  = "oauth"
      Rotation    = "manual"
    }
  )
}

resource "aws_secretsmanager_secret_version" "oauth_client" {
  secret_id = aws_secretsmanager_secret.oauth_client.id
  secret_string = jsonencode({
    client_id     = var.oauth_client_id
    client_secret = var.oauth_client_secret
    tenant_id     = var.oauth_tenant_id
    authority     = "https://login.microsoftonline.com/${var.oauth_tenant_id}"
    scope         = "https://graph.microsoft.com/.default"
  })
}

# LLM API Keys (OpenAI/Azure OpenAI)
resource "aws_secretsmanager_secret" "llm_api_keys" {
  name                    = "${var.name_prefix}-llm-api-keys"
  description             = "API keys for LLM providers (OpenAI, Azure OpenAI, Anthropic)"
  recovery_window_in_days = var.secret_recovery_days
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-llm-api-keys"
      SecretType  = "api-keys"
      Rotation    = "manual"
    }
  )
}

resource "aws_secretsmanager_secret_version" "llm_api_keys" {
  secret_id = aws_secretsmanager_secret.llm_api_keys.id
  secret_string = jsonencode({
    openai_api_key         = var.openai_api_key
    azure_openai_endpoint  = var.azure_openai_endpoint
    azure_openai_api_key   = var.azure_openai_api_key
    azure_openai_deployment = var.azure_openai_deployment
    anthropic_api_key      = var.anthropic_api_key
  })
}

# Application Secrets (JWT, encryption keys, etc.)
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

resource "random_password" "encryption_key" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "application_secrets" {
  name                    = "${var.name_prefix}-application-secrets"
  description             = "Application-level secrets (JWT signing key, encryption keys)"
  recovery_window_in_days = var.secret_recovery_days
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-application-secrets"
      SecretType  = "application"
      Rotation    = "90-days"
    }
  )
}

resource "aws_secretsmanager_secret_version" "application_secrets" {
  secret_id = aws_secretsmanager_secret.application_secrets.id
  secret_string = jsonencode({
    jwt_secret_key         = random_password.jwt_secret.result
    encryption_key         = random_password.encryption_key.result
    session_secret_key     = random_string.session_secret.result
    api_key_salt          = random_string.api_key_salt.result
  })
}

resource "random_string" "session_secret" {
  length  = 32
  special = false
}

resource "random_string" "api_key_salt" {
  length  = 16
  special = false
}

# Redis Password
resource "random_password" "redis_auth_token" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "redis_credentials" {
  name                    = "${var.name_prefix}-redis-credentials"
  description             = "Redis authentication credentials"
  recovery_window_in_days = var.secret_recovery_days
  
  tags = merge(
    var.tags,
    {
      Name        = "${var.name_prefix}-redis-credentials"
      SecretType  = "database"
      Rotation    = "90-days"
    }
  )
}

resource "aws_secretsmanager_secret_version" "redis_credentials" {
  secret_id = aws_secretsmanager_secret.redis_credentials.id
  secret_string = jsonencode({
    auth_token = random_password.redis_auth_token.result
    host       = var.redis_endpoint
    port       = var.redis_port
  })
}

# IAM Policy for Application to Access Secrets
resource "aws_iam_policy" "secrets_access" {
  name        = "${var.name_prefix}-secrets-access-policy"
  description = "Policy for application to access Secrets Manager secrets"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.oauth_client.arn,
          aws_secretsmanager_secret.llm_api_keys.arn,
          aws_secretsmanager_secret.application_secrets.arn,
          aws_secretsmanager_secret.redis_credentials.arn,
          data.aws_secretsmanager_secret.database_password.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey"
        ]
        Resource = var.kms_key_arn != "" ? [var.kms_key_arn] : ["*"]
        Condition = {
          StringEquals = {
            "kms:ViaService" = "secretsmanager.${var.aws_region}.amazonaws.com"
          }
        }
      }
    ]
  })
  
  tags = var.tags
}

# Secret Rotation Lambda Role (for future rotation implementation)
resource "aws_iam_role" "secret_rotation" {
  name = "${var.name_prefix}-secret-rotation-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
  
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "secret_rotation_basic" {
  role       = aws_iam_role.secret_rotation.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "secret_rotation_secrets" {
  name = "${var.name_prefix}-secret-rotation-policy"
  role = aws_iam_role.secret_rotation.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetSecretValue",
          "secretsmanager:PutSecretValue",
          "secretsmanager:UpdateSecretVersionStage"
        ]
        Resource = [
          aws_secretsmanager_secret.application_secrets.arn,
          aws_secretsmanager_secret.redis_credentials.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetRandomPassword"
        ]
        Resource = "*"
      }
    ]
  })
}

# KMS Key for Secrets Encryption (if not provided)
resource "aws_kms_key" "secrets" {
  count = var.kms_key_arn == "" ? 1 : 0
  
  description             = "KMS key for Secrets Manager encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-secrets-kms-key"
    }
  )
}

resource "aws_kms_alias" "secrets" {
  count = var.kms_key_arn == "" ? 1 : 0
  
  name          = "alias/${var.name_prefix}-secrets"
  target_key_id = aws_kms_key.secrets[0].key_id
}

# CloudWatch Log Group for Secret Access Auditing
resource "aws_cloudwatch_log_group" "secret_access" {
  name              = "/aws/secretsmanager/${var.name_prefix}"
  retention_in_days = 90
  
  tags = var.tags
}

# Outputs
output "oauth_client_secret_arn" {
  description = "ARN of OAuth client secret"
  value       = aws_secretsmanager_secret.oauth_client.arn
}

output "llm_api_keys_secret_arn" {
  description = "ARN of LLM API keys secret"
  value       = aws_secretsmanager_secret.llm_api_keys.arn
}

output "application_secrets_arn" {
  description = "ARN of application secrets"
  value       = aws_secretsmanager_secret.application_secrets.arn
}

output "redis_credentials_arn" {
  description = "ARN of Redis credentials secret"
  value       = aws_secretsmanager_secret.redis_credentials.arn
}

output "database_password_arn" {
  description = "ARN of database password secret"
  value       = data.aws_secretsmanager_secret.database_password.arn
}

output "secrets_access_policy_arn" {
  description = "ARN of IAM policy for secrets access"
  value       = aws_iam_policy.secrets_access.arn
}

output "kms_key_arn" {
  description = "ARN of KMS key for secrets encryption"
  value       = var.kms_key_arn != "" ? var.kms_key_arn : aws_kms_key.secrets[0].arn
}

output "secret_rotation_role_arn" {
  description = "ARN of IAM role for secret rotation"
  value       = aws_iam_role.secret_rotation.arn
}

output "all_secret_arns" {
  description = "Map of all secret ARNs"
  value = {
    database_password    = data.aws_secretsmanager_secret.database_password.arn
    oauth_client         = aws_secretsmanager_secret.oauth_client.arn
    llm_api_keys         = aws_secretsmanager_secret.llm_api_keys.arn
    application_secrets  = aws_secretsmanager_secret.application_secrets.arn
    redis_credentials    = aws_secretsmanager_secret.redis_credentials.arn
  }
}
