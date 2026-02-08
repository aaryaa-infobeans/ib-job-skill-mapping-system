# VPC Module

resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = var.enable_dns_hostnames
  enable_dns_support   = var.enable_dns_support
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-vpc"
    }
  )
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-igw"
    }
  )
}

# Public Subnets
resource "aws_subnet" "public" {
  count = length(var.public_subnets)
  
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.public_subnets[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-public-${var.availability_zones[count.index]}"
      "kubernetes.io/role/elb" = "1"
    }
  )
}

# Private Subnets
resource "aws_subnet" "private" {
  count = length(var.private_subnets)
  
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.private_subnets[count.index]
  availability_zone = var.availability_zones[count.index]
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-private-${var.availability_zones[count.index]}"
      "kubernetes.io/role/internal-elb" = "1"
    }
  )
}

# Database Subnets
resource "aws_subnet" "database" {
  count = length(var.database_subnets)
  
  vpc_id            = aws_vpc.main.id
  cidr_block        = var.database_subnets[count.index]
  availability_zone = var.availability_zones[count.index]
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-database-${var.availability_zones[count.index]}"
    }
  )
}

# Elastic IPs for NAT Gateways
resource "aws_eip" "nat" {
  count = var.single_nat_gateway ? 1 : length(var.public_subnets)
  
  domain = "vpc"
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-nat-eip-${count.index + 1}"
    }
  )
  
  depends_on = [aws_internet_gateway.main]
}

# NAT Gateways
resource "aws_nat_gateway" "main" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.public_subnets)) : 0
  
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-nat-${count.index + 1}"
    }
  )
  
  depends_on = [aws_internet_gateway.main]
}

# Public Route Table
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-public-rt"
    }
  )
}

# Public Route
resource "aws_route" "public_internet_gateway" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# Public Route Table Associations
resource "aws_route_table_association" "public" {
  count = length(var.public_subnets)
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private Route Tables
resource "aws_route_table" "private" {
  count = var.single_nat_gateway ? 1 : length(var.private_subnets)
  
  vpc_id = aws_vpc.main.id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-private-rt-${count.index + 1}"
    }
  )
}

# Private Routes
resource "aws_route" "private_nat_gateway" {
  count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.private_subnets)) : 0
  
  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[count.index].id
}

# Private Route Table Associations
resource "aws_route_table_association" "private" {
  count = length(var.private_subnets)
  
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[var.single_nat_gateway ? 0 : count.index].id
}

# Database Subnet Group
resource "aws_db_subnet_group" "database" {
  name       = "${var.name_prefix}-db-subnet-group"
  subnet_ids = aws_subnet.database[*].id
  
  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-db-subnet-group"
    }
  )
}

# Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "List of database subnet IDs"
  value       = aws_subnet.database[*].id
}

output "database_subnet_group_name" {
  description = "Database subnet group name"
  value       = aws_db_subnet_group.database.name
}

output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = aws_nat_gateway.main[*].id
}
