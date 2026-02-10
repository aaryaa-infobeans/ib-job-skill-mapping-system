# Secrets Management - Production

This document describes the secrets management strategy for the IB Job Skill Mapping System production deployment.

## Overview

All sensitive credentials are stored in **AWS Secrets Manager** with encryption at rest using AWS KMS. The application retrieves secrets at runtime using IAM roles and never stores credentials in code or configuration files.

## Secret Types

### 1. Database Credentials
- **Secret Name**: `ib-job-skill-mapping-prod-db-master-password`
- **Created By**: Database Terraform module
- **Contains**: PostgreSQL master password
- **Rotation**: 90 days (automated via Lambda)
- **Access**: Application pods, database administrators

### 2. OAuth Client Secrets
- **Secret Name**: `ib-job-skill-mapping-prod-oauth-client`
- **Contains**:
  - `client_id`: Microsoft Graph API client ID
  - `client_secret`: Client secret
  - `tenant_id`: Azure AD tenant ID
  - `authority`: OAuth authority URL
  - `scope`: API scopes
- **Rotation**: Manual (when OAuth app rotated)
- **Access**: Application pods

### 3. LLM API Keys
- **Secret Name**: `ib-job-skill-mapping-prod-llm-api-keys`
- **Contains**:
  - `openai_api_key`: OpenAI API key (if using OpenAI)
  - `azure_openai_endpoint`: Azure OpenAI endpoint
  - `azure_openai_api_key`: Azure OpenAI key
  - `azure_openai_deployment`: Deployment name
  - `anthropic_api_key`: Anthropic API key (optional)
- **Rotation**: Manual (when keys rotated by provider)
- **Access**: LangGraph AI agent pods

### 4. Application Secrets
- **Secret Name**: `ib-job-skill-mapping-prod-application-secrets`
- **Contains**:
  - `jwt_secret_key`: JWT token signing key (64 chars)
  - `encryption_key`: Data encryption key (32 chars)
  - `session_secret_key`: Session encryption key
  - `api_key_salt`: API key hashing salt
- **Rotation**: 90 days (automated)
- **Access**: Application pods
- **Auto-generated**: Yes (by Terraform)

### 5. Redis Credentials
- **Secret Name**: `ib-job-skill-mapping-prod-redis-credentials`
- **Contains**:
  - `auth_token`: Redis authentication token
  - `host`: Redis endpoint
  - `port`: Redis port
- **Rotation**: 90 days (automated)
- **Access**: Application pods
- **Auto-generated**: Yes (by Terraform)

## Secret Management Workflow

### Initial Setup

```bash
# 1. Deploy infrastructure with Terraform
cd infra/terraform/prod
terraform init
terraform plan -var-file=secrets.tfvars
terraform apply

# 2. Export secrets template
python scripts/manage_secrets.py export-template --output secrets.json

# 3. Edit secrets.json with actual values
nano secrets.json

# 4. Upload secrets to AWS
python scripts/manage_secrets.py update-from-file secrets.json

# 5. Verify secrets
python scripts/manage_secrets.py list
```

### Retrieving Secrets for Deployment

```bash
# Generate application configuration
python scripts/manage_secrets.py generate-config --output config/prod-config.json

# Use in Kubernetes deployment
kubectl create secret generic app-secrets \
  --from-file=config.json=config/prod-config.json \
  --namespace production
```

### Updating Secrets

#### OAuth Credentials (Manual)

```bash
# Get current secret
python scripts/manage_secrets.py get oauth-client > oauth-current.json

# Edit values
nano oauth-current.json

# Update in AWS
aws secretsmanager put-secret-value \
  --secret-id ib-job-skill-mapping-prod-oauth-client \
  --secret-string file://oauth-current.json

# Restart application to pick up new values
kubectl rollout restart deployment/api-gateway -n production
```

#### LLM API Keys (Manual)

```bash
# Update LLM keys
aws secretsmanager put-secret-value \
  --secret-id ib-job-skill-mapping-prod-llm-api-keys \
  --secret-string '{
    "openai_api_key": "sk-...",
    "azure_openai_endpoint": "https://....openai.azure.com/",
    "azure_openai_api_key": "...",
    "azure_openai_deployment": "gpt-4",
    "anthropic_api_key": ""
  }'
```

#### Application Secrets (Automated Rotation)

Application secrets are automatically rotated every 90 days by a Lambda function. No manual intervention required.

### Secret Rotation

#### Automatic Rotation (Database, Application Secrets, Redis)

Secrets with automatic rotation are handled by AWS Lambda functions that:
1. Generate new credentials
2. Update the secret in Secrets Manager
3. Update the target service (database, application)
4. Mark old version as deprecated

**Rotation Schedule**: Every 90 days

#### Manual Rotation (OAuth, LLM Keys)

These secrets are tied to external services and must be rotated manually:

1. Generate new credentials in external service (Microsoft Graph, OpenAI, etc.)
2. Update secret in Secrets Manager
3. Restart application pods
4. Verify application functionality
5. Revoke old credentials in external service

## IAM Access Control

### Application IAM Policy

The application uses an IAM policy that grants read-only access to specific secrets:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-east-1:*:secret:ib-job-skill-mapping-prod-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Decrypt",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:us-east-1:*:key/*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "secretsmanager.us-east-1.amazonaws.com"
        }
      }
    }
  ]
}
```

### Attaching Policy to EKS Service Account

```bash
# Create Kubernetes service account
kubectl create serviceaccount app-service-account -n production

# Annotate with IAM role
kubectl annotate serviceaccount app-service-account \
  -n production \
  eks.amazonaws.com/role-arn=arn:aws:iam::ACCOUNT_ID:role/app-secrets-access-role

# Use in deployment
spec:
  serviceAccountName: app-service-account
```

## Application Integration

### Python Code Example

```python
import boto3
import json
from functools import lru_cache

class SecretsClient:
    """Client for retrieving secrets from AWS Secrets Manager."""
    
    def __init__(self, region: str = "us-east-1"):
        self.client = boto3.client('secretsmanager', region_name=region)
        self.region = region
    
    @lru_cache(maxsize=10)
    def get_secret(self, secret_name: str) -> dict:
        """Retrieve and cache a secret."""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise

# Usage in application
secrets = SecretsClient()

# Get database credentials
db_secret = secrets.get_secret("ib-job-skill-mapping-prod-db-master-password")
database_url = f"postgresql://postgres:{db_secret}@{db_host}:{db_port}/{db_name}"

# Get OAuth credentials
oauth_secret = secrets.get_secret("ib-job-skill-mapping-prod-oauth-client")
oauth_client = OAuthClient(
    client_id=oauth_secret["client_id"],
    client_secret=oauth_secret["client_secret"],
    tenant_id=oauth_secret["tenant_id"]
)

# Get LLM credentials
llm_secret = secrets.get_secret("ib-job-skill-mapping-prod-llm-api-keys")
llm_client = OpenAI(api_key=llm_secret["openai_api_key"])
```

### Environment Variables (NOT Recommended)

For local development only, secrets can be exported as environment variables:

```bash
# DO NOT USE IN PRODUCTION
export DATABASE_PASSWORD=$(aws secretsmanager get-secret-value --secret-id ... --query SecretString --output text)
```

**Production applications should retrieve secrets directly from Secrets Manager at runtime.**

## Security Best Practices

### ✅ Do's

- **Use IAM roles** for secret access (IRSA in EKS)
- **Rotate secrets** regularly (90-day maximum)
- **Audit secret access** via CloudWatch Logs
- **Use KMS encryption** for all secrets
- **Cache secrets** in application memory (refresh periodically)
- **Use least-privilege** IAM policies
- **Version secrets** for rollback capability
- **Monitor secret usage** with CloudWatch metrics
- **Delete secrets** with recovery window (7 days)

### ❌ Don'ts

- **Don't commit secrets** to version control
- **Don't log secret values** (even in debug mode)
- **Don't store secrets** in environment variables (production)
- **Don't hard-code secrets** in application code
- **Don't share secrets** across environments (dev/staging/prod)
- **Don't use long-lived** static credentials
- **Don't grant wildcard** access to secrets

## Monitoring and Auditing

### CloudWatch Logs

All secret access is logged to CloudWatch:

```bash
# View secret access logs
aws logs tail /aws/secretsmanager/ib-job-skill-mapping-prod --follow

# Filter by secret name
aws logs filter-log-events \
  --log-group-name /aws/secretsmanager/ib-job-skill-mapping-prod \
  --filter-pattern "oauth-client"
```

### CloudWatch Metrics

Monitor secret operations:
- `secretsmanager.GetSecretValue` API calls
- Failed authentication attempts
- Rotation failures

### Alarms

Set up alarms for:
- Rotation failures
- Excessive access attempts
- Unauthorized access attempts

```bash
# Create alarm for rotation failures
aws cloudwatch put-metric-alarm \
  --alarm-name secret-rotation-failure \
  --metric-name RotationSucceeded \
  --namespace AWS/SecretsManager \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 1 \
  --threshold 0 \
  --comparison-operator LessThanThreshold
```

## Disaster Recovery

### Backing Up Secrets

Secrets are automatically versioned in Secrets Manager. To export for disaster recovery:

```bash
# Export all secrets (encrypted backup)
python scripts/manage_secrets.py list > secrets-inventory.txt

# For each secret, create encrypted backup
for secret in $(cat secrets-inventory.txt); do
  aws secretsmanager get-secret-value \
    --secret-id $secret \
    --query SecretString \
    --output text > backup/${secret}.enc
done

# Encrypt backup directory
tar czf secrets-backup-$(date +%Y%m%d).tar.gz backup/
gpg --encrypt secrets-backup-*.tar.gz

# Store in secure location (S3 with versioning)
aws s3 cp secrets-backup-*.tar.gz.gpg \
  s3://ib-job-skill-mapping-prod-backups/secrets/
```

### Restoring Secrets

```bash
# Retrieve backup
aws s3 cp s3://ib-job-skill-mapping-prod-backups/secrets/secrets-backup-20260208.tar.gz.gpg .

# Decrypt
gpg --decrypt secrets-backup-20260208.tar.gz.gpg > secrets-backup.tar.gz
tar xzf secrets-backup.tar.gz

# Restore each secret
for file in backup/*.enc; do
  secret_name=$(basename $file .enc)
  aws secretsmanager create-secret \
    --name $secret_name \
    --secret-string file://$file
done
```

## Cost Optimization

### Secrets Manager Pricing (us-east-1)

- **Secret storage**: $0.40 per secret per month
- **API calls**: $0.05 per 10,000 calls

**Monthly Cost Estimate**:
- 5 secrets × $0.40 = $2.00
- ~100,000 API calls × $0.05/10K = $0.50
- **Total**: ~$2.50/month

### Optimization Tips

1. **Cache secrets** in application (reduce API calls)
2. **Batch retrievals** when possible
3. **Delete unused secrets** promptly
4. **Use secret versions** instead of creating new secrets

## Troubleshooting

### "Access Denied" Errors

```bash
# Check IAM policy
aws iam get-policy --policy-arn <policy-arn>

# Check service account annotation (EKS)
kubectl describe sa app-service-account -n production

# Check CloudWatch Logs for detailed error
aws logs tail /aws/secretsmanager/ib-job-skill-mapping-prod --since 5m
```

### Secret Not Found

```bash
# List all secrets
python scripts/manage_secrets.py list

# Verify secret exists
aws secretsmanager describe-secret --secret-id <secret-name>
```

### Rotation Failures

```bash
# Check rotation configuration
aws secretsmanager describe-secret --secret-id <secret-name>

# View rotation Lambda logs
aws logs tail /aws/lambda/rotation-function --follow

# Manually trigger rotation
aws secretsmanager rotate-secret --secret-id <secret-name>
```

## References

- [AWS Secrets Manager Documentation](https://docs.aws.amazon.com/secretsmanager/)
- [IAM Roles for Service Accounts (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Secret Rotation Best Practices](https://docs.aws.amazon.com/secretsmanager/latest/userguide/rotating-secrets.html)
- [Boto3 Secrets Manager](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/secretsmanager.html)
