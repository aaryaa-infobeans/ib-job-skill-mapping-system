# RDS PostgreSQL Database Module

# Random password generation
resource "random_password" "master" {
  length  = 32
  special = true
}

# Store password in Secrets Manager
resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.name_prefix}-db-master-password"
  
  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.master.result
}

# DB Subnet Group (if not provided)
resource "aws_db_subnet_group" "main" {
  count = var.db_subnet_group_name == "" ? 1 : 0
  
  name       = "${var.name_prefix}-db-subnet-group"
  subnet_ids = var.database_subnets
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-db-subnet-group"
    }
  )
}

# DB Parameter Group
resource "aws_db_parameter_group" "main" {
  name   = "${var.name_prefix}-pg-params"
  family = "postgres15"
  
  # Performance tuning parameters
  parameter {
    name  = "shared_buffers"
    value = "4194304" # 32 GB (25% of 128 GB RAM for db.r6g.xlarge)
  }
  
  parameter {
    name  = "effective_cache_size"
    value = "12582912" # 96 GB (75% of RAM)
  }
  
  parameter {
    name  = "maintenance_work_mem"
    value = "2097151" # 2 GB
  }
  
  parameter {
    name  = "work_mem"
    value = "524288" # 512 MB
  }
  
  parameter {
    name  = "max_connections"
    value = "500"
  }
  
  parameter {
    name  = "random_page_cost"
    value = "1.1" # For SSD storage
  }
  
  parameter {
    name  = "log_min_duration_statement"
    value = "1000" # Log queries taking > 1 second
  }
  
  parameter {
    name  = "log_connections"
    value = "1"
  }
  
  parameter {
    name  = "log_disconnections"
    value = "1"
  }
  
  parameter {
    name  = "log_lock_waits"
    value = "1"
  }
  
  tags = var.tags
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier = "${var.name_prefix}-db"
  
  # Engine
  engine               = var.engine
  engine_version       = var.engine_version
  instance_class       = var.instance_class
  
  # Storage
  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  storage_encrypted     = var.storage_encrypted
  iops                  = var.iops
  
  # Database
  db_name  = var.database_name
  username = var.master_username
  password = random_password.master.result
  port     = var.port
  
  # Network
  db_subnet_group_name   = var.db_subnet_group_name != "" ? var.db_subnet_group_name : aws_db_subnet_group.main[0].name
  vpc_security_group_ids = var.security_group_ids
  publicly_accessible    = false
  
  # High Availability
  multi_az = var.multi_az
  
  # Backup
  backup_retention_period = var.backup_retention_period
  backup_window          = var.backup_window
  skip_final_snapshot    = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : var.final_snapshot_identifier
  copy_tags_to_snapshot  = true
  
  # Maintenance
  maintenance_window              = var.maintenance_window
  auto_minor_version_upgrade      = var.auto_minor_version_upgrade
  deletion_protection             = var.deletion_protection
  
  # Monitoring
  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports
  monitoring_interval             = var.monitoring_interval
  monitoring_role_arn             = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null
  performance_insights_enabled    = var.performance_insights_enabled
  performance_insights_retention_period = var.performance_insights_enabled ? 7 : null
  
  # Parameter Group
  parameter_group_name = aws_db_parameter_group.main.name
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-db"
    }
  )
}

# Read Replica for production workload
resource "aws_db_instance" "read_replica" {
  count = var.create_read_replica ? 1 : 0
  
  identifier = "${var.name_prefix}-db-read-replica"
  
  replicate_source_db = aws_db_instance.main.identifier
  instance_class      = var.replica_instance_class != "" ? var.replica_instance_class : var.instance_class
  
  # Storage
  storage_encrypted = var.storage_encrypted
  
  # Network
  publicly_accessible = false
  
  # Monitoring
  enabled_cloudwatch_logs_exports = var.enabled_cloudwatch_logs_exports
  monitoring_interval             = var.monitoring_interval
  monitoring_role_arn             = var.monitoring_interval > 0 ? aws_iam_role.rds_monitoring[0].arn : null
  performance_insights_enabled    = var.performance_insights_enabled
  
  # Maintenance
  auto_minor_version_upgrade = var.auto_minor_version_upgrade
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-db-read-replica"
    }
  )
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "rds_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0
  
  name = "${var.name_prefix}-rds-monitoring-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "monitoring.rds.amazonaws.com"
      }
    }]
  })
  
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "rds_monitoring" {
  count = var.monitoring_interval > 0 ? 1 : 0
  
  role       = aws_iam_role.rds_monitoring[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name          = "${var.name_prefix}-db-cpu-utilization"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors database CPU utilization"
  alarm_actions       = var.alarm_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
  
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name          = "${var.name_prefix}-db-storage-space"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "10737418240" # 10 GB in bytes
  alarm_description   = "This metric monitors database free storage space"
  alarm_actions       = var.alarm_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
  
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "database_connections" {
  alarm_name          = "${var.name_prefix}-db-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "400" # 80% of max_connections (500)
  alarm_description   = "This metric monitors database connections"
  alarm_actions       = var.alarm_actions
  
  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
  
  tags = var.tags
}

# Outputs
output "endpoint" {
  description = "Database endpoint"
  value       = aws_db_instance.main.endpoint
}

output "address" {
  description = "Database address"
  value       = aws_db_instance.main.address
}

output "port" {
  description = "Database port"
  value       = aws_db_instance.main.port
}

output "name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "username" {
  description = "Database master username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "password_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the database password"
  value       = aws_secretsmanager_secret.db_password.arn
}

output "read_replica_endpoint" {
  description = "Read replica endpoint"
  value       = var.create_read_replica ? aws_db_instance.read_replica[0].endpoint : null
}
