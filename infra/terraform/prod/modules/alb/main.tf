# Application Load Balancer Module

# ALB
resource "aws_lb" "main" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = var.security_group_ids
  subnets            = var.public_subnets
  
  enable_deletion_protection = var.enable_deletion_protection
  enable_http2              = var.enable_http2
  enable_cross_zone_load_balancing = true
  
  access_logs {
    bucket  = var.access_logs_bucket
    prefix  = var.access_logs_prefix
    enabled = var.access_logs_bucket != ""
  }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-alb"
    }
  )
}

# Target Group
resource "aws_lb_target_group" "main" {
  name     = "${var.name_prefix}-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  
  target_type = "ip" # For EKS with Fargate or ENI-based targets
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }
  
  deregistration_delay = 30
  
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400 # 1 day
    enabled         = true
  }
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-tg"
    }
  )
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  count = var.ssl_certificate_arn != "" ? 1 : 0
  
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.ssl_certificate_arn
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.main.arn
  }
  
  tags = var.tags
}

# HTTP Listener (redirect to HTTPS)
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type = var.ssl_certificate_arn != "" ? "redirect" : "forward"
    
    dynamic "redirect" {
      for_each = var.ssl_certificate_arn != "" ? [1] : []
      content {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
    
    target_group_arn = var.ssl_certificate_arn == "" ? aws_lb_target_group.main.arn : null
  }
  
  tags = var.tags
}

# WAF Web ACL Association
resource "aws_wafv2_web_acl_association" "main" {
  count = var.enable_waf && var.waf_web_acl_arn != "" ? 1 : 0
  
  resource_arn = aws_lb.main.arn
  web_acl_arn  = var.waf_web_acl_arn
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "target_response_time" {
  alarm_name          = "${var.name_prefix}-alb-target-response-time"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Average"
  threshold           = "2"
  alarm_description   = "This metric monitors ALB target response time"
  alarm_actions       = var.alarm_actions
  
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
  
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "unhealthy_targets" {
  alarm_name          = "${var.name_prefix}-alb-unhealthy-targets"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "UnHealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "This metric monitors unhealthy target count"
  alarm_actions       = var.alarm_actions
  
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.main.arn_suffix
  }
  
  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "http_5xx_errors" {
  alarm_name          = "${var.name_prefix}-alb-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "This metric monitors 5XX error count"
  alarm_actions       = var.alarm_actions
  
  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
  
  tags = var.tags
}

# Outputs
output "arn" {
  description = "ALB ARN"
  value       = aws_lb.main.arn
}

output "dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.main.dns_name
}

output "zone_id" {
  description = "ALB zone ID"
  value       = aws_lb.main.zone_id
}

output "target_group_arn" {
  description = "Target group ARN"
  value       = aws_lb_target_group.main.arn
}
