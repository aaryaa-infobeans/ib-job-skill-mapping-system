# Monitoring Infrastructure Module
# CloudWatch Alarms, SNS Topics, Dashboards, and Log Groups

terraform {
  required_version = ">= 1.5.0"
}

# SNS Topic for Critical Alerts
resource "aws_sns_topic" "critical_alerts" {
  name              = "${var.name_prefix}-critical-alerts"
  display_name      = "Critical Production Alerts"
  kms_master_key_id = aws_kms_key.monitoring.id

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-critical-alerts"
    AlertLevel  = "critical"
  })
}

# SNS Topic for Warning Alerts
resource "aws_sns_topic" "warning_alerts" {
  name              = "${var.name_prefix}-warning-alerts"
  display_name      = "Warning Production Alerts"
  kms_master_key_id = aws_kms_key.monitoring.id

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-warning-alerts"
    AlertLevel  = "warning"
  })
}

# KMS Key for SNS Topic Encryption
resource "aws_kms_key" "monitoring" {
  description             = "KMS key for monitoring SNS topics"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-monitoring-kms"
  })
}

resource "aws_kms_alias" "monitoring" {
  name          = "alias/${var.name_prefix}-monitoring"
  target_key_id = aws_kms_key.monitoring.key_id
}

# SNS Topic Subscriptions (Email)
resource "aws_sns_topic_subscription" "critical_email" {
  count     = length(var.critical_alert_emails)
  topic_arn = aws_sns_topic.critical_alerts.arn
  protocol  = "email"
  endpoint  = var.critical_alert_emails[count.index]
}

resource "aws_sns_topic_subscription" "warning_email" {
  count     = length(var.warning_alert_emails)
  topic_arn = aws_sns_topic.warning_alerts.arn
  protocol  = "email"
  endpoint  = var.warning_alert_emails[count.index]
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "application" {
  name              = "/aws/ib-job-skill-mapping/${var.environment}/application"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.monitoring.arn

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-application-logs"
    LogType     = "application"
  })
}

resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/ib-job-skill-mapping/${var.environment}/api-gateway"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.monitoring.arn

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-api-gateway-logs"
    LogType     = "api-gateway"
  })
}

resource "aws_cloudwatch_log_group" "ai_agents" {
  name              = "/aws/ib-job-skill-mapping/${var.environment}/ai-agents"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.monitoring.arn

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-ai-agents-logs"
    LogType     = "ai-agents"
  })
}

resource "aws_cloudwatch_log_group" "database" {
  name              = "/aws/rds/instance/${var.name_prefix}-db/postgresql"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.monitoring.arn

  tags = merge(var.tags, {
    Name        = "${var.name_prefix}-database-logs"
    LogType     = "database"
  })
}

# CloudWatch Metric Namespace
locals {
  metric_namespace = "IB-JobSkillMapping-${title(var.environment)}"
}

# API Gateway Alarms
resource "aws_cloudwatch_metric_alarm" "api_error_rate" {
  alarm_name          = "${var.name_prefix}-api-error-rate-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ErrorRate"
  namespace           = local.metric_namespace
  period              = 300  # 5 minutes
  statistic           = "Average"
  threshold           = 1.0  # 1% error rate
  alarm_description   = "API error rate exceeded 1%"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]
  ok_actions          = [aws_sns_topic.critical_alerts.arn]

  dimensions = {
    Service = "API"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_latency_high" {
  alarm_name          = "${var.name_prefix}-api-latency-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RequestDuration"
  namespace           = local.metric_namespace
  period              = 300
  extended_statistic  = "p95"
  threshold           = 2000  # 2 seconds
  alarm_description   = "API p95 latency exceeded 2 seconds"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    Service = "API"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_latency_critical" {
  alarm_name          = "${var.name_prefix}-api-latency-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RequestDuration"
  namespace           = local.metric_namespace
  period              = 300
  extended_statistic  = "p95"
  threshold           = 5000  # 5 seconds
  alarm_description   = "API p95 latency exceeded 5 seconds (CRITICAL)"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]
  ok_actions          = [aws_sns_topic.critical_alerts.arn]

  dimensions = {
    Service = "API"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "api_throughput_low" {
  alarm_name          = "${var.name_prefix}-api-throughput-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "RequestCount"
  namespace           = local.metric_namespace
  period              = 300
  statistic           = "Sum"
  threshold           = 10  # Less than 10 requests in 5 minutes
  alarm_description   = "API throughput dropped below threshold"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    Service = "API"
  }

  tags = var.tags
}

# Database Alarms
resource "aws_cloudwatch_metric_alarm" "db_cpu_high" {
  alarm_name          = "${var.name_prefix}-db-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Database CPU utilization exceeded 80%"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "db_cpu_critical" {
  alarm_name          = "${var.name_prefix}-db-cpu-critical"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 90
  alarm_description   = "Database CPU utilization exceeded 90% (CRITICAL)"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]
  ok_actions          = [aws_sns_topic.critical_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "db_connections_high" {
  alarm_name          = "${var.name_prefix}-db-connections-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80  # Assuming max_connections = 100
  alarm_description   = "Database connections exceeded 80"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "db_storage_low" {
  alarm_name          = "${var.name_prefix}-db-storage-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 10737418240  # 10 GB in bytes
  alarm_description   = "Database free storage space less than 10 GB"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]
  ok_actions          = [aws_sns_topic.critical_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.db_instance_id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "db_replica_lag" {
  alarm_name          = "${var.name_prefix}-db-replica-lag-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ReplicaLag"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 30  # 30 seconds
  alarm_description   = "Read replica lag exceeded 30 seconds"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    DBInstanceIdentifier = var.db_replica_id
  }

  tags = var.tags
}

# Redis Alarms
resource "aws_cloudwatch_metric_alarm" "redis_cpu_high" {
  alarm_name          = "${var.name_prefix}-redis-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 75
  alarm_description   = "Redis CPU utilization exceeded 75%"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    CacheClusterId = var.redis_cluster_id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_memory_high" {
  alarm_name          = "${var.name_prefix}-redis-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Redis memory usage exceeded 80%"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    CacheClusterId = var.redis_cluster_id
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "redis_evictions" {
  alarm_name          = "${var.name_prefix}-redis-evictions-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Evictions"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Sum"
  threshold           = 1000
  alarm_description   = "Redis evictions exceeded 1000 in 5 minutes"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    CacheClusterId = var.redis_cluster_id
  }

  tags = var.tags
}

# EKS Cluster Alarms
resource "aws_cloudwatch_metric_alarm" "eks_node_cpu_high" {
  alarm_name          = "${var.name_prefix}-eks-node-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "node_cpu_utilization"
  namespace           = "ContainerInsights"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "EKS node CPU utilization exceeded 80%"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    ClusterName = var.eks_cluster_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "eks_node_memory_high" {
  alarm_name          = "${var.name_prefix}-eks-node-memory-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "node_memory_utilization"
  namespace           = "ContainerInsights"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "EKS node memory utilization exceeded 80%"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    ClusterName = var.eks_cluster_name
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "pod_restart_high" {
  alarm_name          = "${var.name_prefix}-pod-restart-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "pod_number_of_container_restarts"
  namespace           = "ContainerInsights"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Pod restarts exceeded 5 in 5 minutes"
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]
  ok_actions          = [aws_sns_topic.critical_alerts.arn]

  dimensions = {
    ClusterName = var.eks_cluster_name
    Namespace   = "production"
  }

  tags = var.tags
}

# Application-Specific Alarms
resource "aws_cloudwatch_metric_alarm" "matching_timeout" {
  alarm_name          = "${var.name_prefix}-matching-timeout-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "MatchingTimeout"
  namespace           = local.metric_namespace
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Matching timeouts exceeded 10 in 5 minutes"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    Service = "MatchingEngine"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "llm_api_errors" {
  alarm_name          = "${var.name_prefix}-llm-api-errors-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "LLMAPIErrors"
  namespace           = local.metric_namespace
  period              = 300
  statistic           = "Sum"
  threshold           = 20
  alarm_description   = "LLM API errors exceeded 20 in 5 minutes"
  alarm_actions       = [aws_sns_topic.warning_alerts.arn]
  ok_actions          = [aws_sns_topic.warning_alerts.arn]

  dimensions = {
    Service = "LLMIntegration"
  }

  tags = var.tags
}

# Composite Alarm for System Health
resource "aws_cloudwatch_composite_alarm" "system_unhealthy" {
  alarm_name          = "${var.name_prefix}-system-unhealthy"
  alarm_description   = "Multiple critical systems are unhealthy"
  actions_enabled     = true
  alarm_actions       = [aws_sns_topic.critical_alerts.arn]
  ok_actions          = [aws_sns_topic.critical_alerts.arn]

  alarm_rule = join(" OR ", [
    "ALARM(${aws_cloudwatch_metric_alarm.api_error_rate.alarm_name})",
    "ALARM(${aws_cloudwatch_metric_alarm.db_cpu_critical.alarm_name})",
    "ALARM(${aws_cloudwatch_metric_alarm.pod_restart_high.alarm_name})",
  ])

  tags = var.tags
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # API Metrics Row
      {
        type = "metric"
        properties = {
          metrics = [
            [local.metric_namespace, "RequestCount", { stat = "Sum", label = "Total Requests" }],
            [".", "ErrorCount", { stat = "Sum", label = "Errors" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "API Request Volume"
          period  = 300
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            [local.metric_namespace, "RequestDuration", { stat = "Average", label = "Average" }],
            ["...", { stat = "p50", label = "p50" }],
            ["...", { stat = "p95", label = "p95" }],
            ["...", { stat = "p99", label = "p99" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "API Latency"
          period  = 300
          yAxis = {
            left = {
              label = "Milliseconds"
            }
          }
        }
      },
      # Database Metrics Row
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "CPUUtilization", { stat = "Average", label = "CPU" }],
            [".", "DatabaseConnections", { stat = "Average", label = "Connections" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Database Performance"
          period  = 300
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/RDS", "ReadLatency", { stat = "Average", label = "Read Latency" }],
            [".", "WriteLatency", { stat = "Average", label = "Write Latency" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Database Latency"
          period  = 300
        }
      },
      # Redis Metrics Row
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CPUUtilization", { stat = "Average", label = "CPU" }],
            [".", "DatabaseMemoryUsagePercentage", { stat = "Average", label = "Memory" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Redis Performance"
          period  = 300
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/ElastiCache", "CacheHits", { stat = "Sum", label = "Cache Hits" }],
            [".", "CacheMisses", { stat = "Sum", label = "Cache Misses" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Redis Cache Performance"
          period  = 300
        }
      },
      # EKS Metrics Row
      {
        type = "metric"
        properties = {
          metrics = [
            ["ContainerInsights", "node_cpu_utilization", { stat = "Average", label = "CPU" }],
            [".", "node_memory_utilization", { stat = "Average", label = "Memory" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "EKS Node Utilization"
          period  = 300
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["ContainerInsights", "pod_number_of_container_restarts", { stat = "Sum", label = "Restarts" }],
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Pod Restarts"
          period  = 300
        }
      }
    ]
  })
}

# Outputs
output "critical_alerts_topic_arn" {
  description = "ARN of the critical alerts SNS topic"
  value       = aws_sns_topic.critical_alerts.arn
}

output "warning_alerts_topic_arn" {
  description = "ARN of the warning alerts SNS topic"
  value       = aws_sns_topic.warning_alerts.arn
}

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "log_group_names" {
  description = "Names of CloudWatch log groups"
  value = {
    application = aws_cloudwatch_log_group.application.name
    api_gateway = aws_cloudwatch_log_group.api_gateway.name
    ai_agents   = aws_cloudwatch_log_group.ai_agents.name
    database    = aws_cloudwatch_log_group.database.name
  }
}
