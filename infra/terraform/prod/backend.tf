# Terraform Backend Configuration

terraform {
  backend "s3" {
    bucket         = "ib-job-skill-mapping-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "ib-job-skill-mapping-terraform-locks"
    
    # Enable versioning on the S3 bucket
    # versioning = true
  }
}

# Note: Before running terraform init, ensure:
# 1. S3 bucket exists: ib-job-skill-mapping-terraform-state
# 2. DynamoDB table exists: ib-job-skill-mapping-terraform-locks
# 3. Both have appropriate IAM permissions configured
#
# Create the state bucket and DynamoDB table:
# aws s3 mb s3://ib-job-skill-mapping-terraform-state --region us-east-1
# aws s3api put-bucket-versioning --bucket ib-job-skill-mapping-terraform-state --versioning-configuration Status=Enabled
# aws s3api put-bucket-encryption --bucket ib-job-skill-mapping-terraform-state --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
#
# aws dynamodb create-table --table-name ib-job-skill-mapping-terraform-locks \
#   --attribute-definitions AttributeName=LockID,AttributeType=S \
#   --key-schema AttributeName=LockID,KeyType=HASH \
#   --billing-mode PAY_PER_REQUEST \
#   --region us-east-1
