# Production Infrastructure - Terraform

This directory contains Terraform configurations for deploying the IB Job Skill Mapping System to production on AWS.

## Architecture Overview

The production infrastructure includes:

- **VPC**: Multi-AZ VPC with public, private, and database subnets
- **RDS PostgreSQL**: Multi-AZ deployment with read replica
- **EKS**: Kubernetes cluster for container orchestration
- **ALB**: Application Load Balancer with SSL/TLS termination
- **ElastiCache Redis**: High-availability cache cluster
- **S3**: Buckets for artifacts, backups, and logs
- **CloudWatch**: Comprehensive logging and monitoring
- **Security Groups**: Network isolation and access control

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.5.0 installed
3. **kubectl** for EKS cluster management
4. **AWS account** with sufficient permissions
5. **ACM Certificate** for HTTPS (optional but recommended)

## Infrastructure Components

### Networking
- VPC with 3 availability zones
- Public subnets for ALB
- Private subnets for EKS nodes
- Database subnets for RDS (isolated)
- NAT Gateways for outbound internet access

### Database
- PostgreSQL 15.4 Multi-AZ
- db.r6g.xlarge instance (4 vCPU, 32 GB RAM)
- 100 GB storage with auto-scaling to 1 TB
- Read replica for query scaling
- Automated backups (30-day retention)
- Performance Insights enabled
- Enhanced monitoring (60-second interval)

### Kubernetes
- EKS cluster version 1.28
- Managed node group (3-10 nodes)
- t3.xlarge instances (4 vCPU, 16 GB RAM)
- Auto-scaling enabled
- IRSA (IAM Roles for Service Accounts) configured

### Load Balancer
- Application Load Balancer
- SSL/TLS termination
- HTTP to HTTPS redirect
- Health check monitoring
- WAF integration (optional)

### Cache
- ElastiCache Redis 7.0
- cache.r6g.large nodes (2 vCPU, 13.07 GB RAM)
- 2-node cluster with automatic failover
- Multi-AZ enabled
- Snapshot backups (7-day retention)

### Storage
- **Artifacts Bucket**: Docker images, deployment packages
- **Backups Bucket**: Database and application backups
- **Logs Bucket**: CloudTrail, ALB access logs

## Setup Instructions

### 1. Create S3 Backend

Before initializing Terraform, create the S3 bucket and DynamoDB table for state management:

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://ib-job-skill-mapping-terraform-state --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket ib-job-skill-mapping-terraform-state \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket ib-job-skill-mapping-terraform-state \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name ib-job-skill-mapping-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### 2. Configure Variables

```bash
# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
# IMPORTANT: Set ssl_certificate_arn for HTTPS support
nano terraform.tfvars
```

### 3. (Optional) Create ACM Certificate

For HTTPS support, create an ACM certificate:

```bash
# Request certificate
aws acm request-certificate \
  --domain-name api.your-domain.com \
  --validation-method DNS \
  --region us-east-1

# Follow AWS Console instructions to validate the certificate
# Update terraform.tfvars with the certificate ARN
```

### 4. Initialize Terraform

```bash
cd infra/terraform/prod
terraform init
```

### 5. Review Plan

```bash
terraform plan -out=tfplan
```

Review the plan carefully. Expected resources: ~80+ resources.

### 6. Apply Configuration

```bash
terraform apply tfplan
```

**Duration**: ~20-30 minutes for full deployment.

### 7. Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --region us-east-1 \
  --name ib-job-skill-mapping-prod-eks

# Verify connection
kubectl get nodes
```

### 8. Retrieve Outputs

```bash
# View all outputs
terraform output

# Specific outputs
terraform output -json application_config > config.json
terraform output database_endpoint
terraform output alb_dns_name
```

## Post-Deployment Steps

### 1. Database Initialization

```bash
# Get database password from Secrets Manager
DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id ib-job-skill-mapping-prod-db-master-password \
  --query SecretString \
  --output text)

# Connect to database
psql -h $(terraform output -raw database_endpoint) \
  -U postgres \
  -d ib_job_skill_mapping

# Run migrations
# (See deployment documentation)
```

### 2. Configure DNS

If you have a custom domain, create a Route53 record:

```bash
# Get ALB DNS name
ALB_DNS=$(terraform output -raw alb_dns_name)
ALB_ZONE=$(terraform output -raw alb_zone_id)

# Create alias record (manual or via Route53)
# api.your-domain.com -> ALB DNS name
```

### 3. Deploy Application

See [Deployment Pipeline documentation](../../../docs/phase-7-production-deployment.md) for application deployment steps.

## Monitoring and Alarms

CloudWatch alarms are configured for:

- **Database**: CPU, storage, connections
- **ALB**: Response time, 5XX errors, unhealthy targets
- **Redis**: CPU, memory, evictions

Configure SNS topic for alarm notifications:

```bash
# Create SNS topic
aws sns create-topic --name ib-job-skill-mapping-prod-alerts

# Subscribe to email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:ib-job-skill-mapping-prod-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

## Maintenance

### Backup Verification

```bash
# List RDS snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier ib-job-skill-mapping-prod-db

# List Redis snapshots
aws elasticache describe-snapshots \
  --cache-cluster-id ib-job-skill-mapping-prod-redis
```

### Scaling

#### Database
```bash
# Modify instance class
terraform apply -var="db_instance_class=db.r6g.2xlarge"
```

#### EKS Nodes
```bash
# Update node count
terraform apply -var="eks_desired_nodes=5" -var="eks_max_nodes=15"
```

### Upgrades

#### RDS Minor Version
Automatic minor version upgrades are enabled. To upgrade major version:

```bash
terraform apply -var="db_engine_version=16.1"
```

#### EKS Version
```bash
# Upgrade control plane
terraform apply -var="eks_cluster_version=1.29"

# Upgrade nodes (will trigger rolling update)
```

## Disaster Recovery

### Database Restore

```bash
# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier ib-job-skill-mapping-prod-db-restored \
  --db-snapshot-identifier <snapshot-id>
```

### Infrastructure Rebuild

```bash
# Destroy and recreate (CAUTION!)
terraform destroy
terraform apply
```

## Cost Optimization

Estimated monthly costs (us-east-1):

- **RDS**: ~$600 (db.r6g.xlarge Multi-AZ + read replica)
- **EKS**: ~$220 (3 × t3.xlarge nodes + control plane $0.10/hr)
- **Redis**: ~$280 (2 × cache.r6g.large)
- **ALB**: ~$25
- **Data Transfer**: Variable
- **S3/CloudWatch**: ~$50

**Total**: ~$1,175/month

### Cost Reduction Options

1. **Non-production hours**: Scale down outside business hours
2. **Reserved Instances**: 40-60% savings for 1-3 year commit
3. **Spot Instances**: Use spot for EKS worker nodes (dev/staging)
4. **Storage optimization**: Adjust backup retention periods

## Security Best Practices

- [ ] Enable VPC Flow Logs
- [ ] Enable CloudTrail logging
- [ ] Configure AWS Config for compliance
- [ ] Implement least-privilege IAM policies
- [ ] Rotate database credentials regularly
- [ ] Enable GuardDuty for threat detection
- [ ] Configure AWS WAF rules for ALB
- [ ] Enable MFA for AWS Console access
- [ ] Implement AWS Backup for automated backups

## Troubleshooting

### Terraform State Lock

```bash
# If state is locked
aws dynamodb delete-item \
  --table-name ib-job-skill-mapping-terraform-locks \
  --key '{"LockID": {"S": "ib-job-skill-mapping-terraform-state/prod/terraform.tfstate"}}'
```

### EKS Node Issues

```bash
# Check node status
kubectl get nodes
kubectl describe node <node-name>

# View node group status
aws eks describe-nodegroup \
  --cluster-name ib-job-skill-mapping-prod-eks \
  --nodegroup-name ib-job-skill-mapping-prod-application
```

### Database Connection Issues

```bash
# Test connectivity
nc -zv <db-endpoint> 5432

# Check security groups
aws ec2 describe-security-groups \
  --group-ids <sg-id>
```

## Clean Up

**WARNING**: This will destroy all infrastructure and data!

```bash
# Disable deletion protection first
terraform apply -var="deletion_protection=false"

# Destroy infrastructure
terraform destroy

# Clean up S3 buckets manually (they're retained for safety)
aws s3 rb s3://ib-job-skill-mapping-prod-artifacts --force
aws s3 rb s3://ib-job-skill-mapping-prod-backups --force
aws s3 rb s3://ib-job-skill-mapping-prod-logs --force
```

## Support

For issues or questions:
- Check [Troubleshooting Guide](../../../docs/phase-7-production-deployment.md)
- Contact: platform-team@example.com
- Slack: #infrastructure-support

## References

- [AWS EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [RDS PostgreSQL Best Practices](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_BestPractices.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
