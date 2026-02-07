# S3 Buckets Module

# S3 Buckets
resource "aws_s3_bucket" "buckets" {
  for_each = var.buckets
  
  bucket = "${var.name_prefix}-${each.key}"
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-${each.key}"
    }
  )
}

# Bucket Versioning
resource "aws_s3_bucket_versioning" "buckets" {
  for_each = { for k, v in var.buckets : k => v if v.versioning_enabled }
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "buckets" {
  for_each = var.buckets
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Block Public Access
resource "aws_s3_bucket_public_access_block" "buckets" {
  for_each = var.buckets
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle Rules
resource "aws_s3_bucket_lifecycle_configuration" "buckets" {
  for_each = { for k, v in var.buckets : k => v if length(v.lifecycle_rules) > 0 }
  
  bucket = aws_s3_bucket.buckets[each.key].id
  
  dynamic "rule" {
    for_each = each.value.lifecycle_rules
    content {
      id     = rule.value.id
      status = rule.value.enabled ? "Enabled" : "Disabled"
      
      dynamic "expiration" {
        for_each = lookup(rule.value, "expiration_days", null) != null ? [1] : []
        content {
          days = rule.value.expiration_days
        }
      }
      
      dynamic "transition" {
        for_each = lookup(rule.value, "transition_days", null) != null ? [1] : []
        content {
          days          = rule.value.transition_days
          storage_class = rule.value.storage_class
        }
      }
      
      dynamic "noncurrent_version_expiration" {
        for_each = lookup(rule.value, "noncurrent_version_expiration_days", null) != null ? [1] : []
        content {
          noncurrent_days = rule.value.noncurrent_version_expiration_days
        }
      }
    }
  }
}

# Bucket Policies for specific buckets
resource "aws_s3_bucket_policy" "logs" {
  bucket = aws_s3_bucket.buckets["logs"].id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSCloudTrailAclCheck"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.buckets["logs"].arn
      },
      {
        Sid    = "AWSCloudTrailWrite"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.buckets["logs"].arn}/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

# Outputs
output "bucket_names" {
  description = "Map of bucket names"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.id }
}

output "bucket_arns" {
  description = "Map of bucket ARNs"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.arn }
}

output "bucket_regional_domain_names" {
  description = "Map of bucket regional domain names"
  value       = { for k, v in aws_s3_bucket.buckets : k => v.bucket_regional_domain_name }
}
