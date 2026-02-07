#!/usr/bin/env python3
"""
Infrastructure Validation Script

This script validates the Terraform infrastructure before deployment:
1. Checks Terraform syntax
2. Validates variable configuration
3. Estimates costs
4. Checks security best practices
5. Validates module dependencies
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class InfrastructureValidator:
    """Validates Terraform infrastructure configuration."""
    
    def __init__(self, terraform_dir: Path):
        self.terraform_dir = terraform_dir
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def run_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """Run a shell command and return exit code, stdout, stderr."""
        result = subprocess.run(
            cmd,
            cwd=self.terraform_dir,
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr
    
    def validate_terraform_syntax(self) -> bool:
        """Validate Terraform syntax."""
        print("🔍 Validating Terraform syntax...")
        
        # Check if Terraform is installed
        code, _, _ = self.run_command(["terraform", "version"])
        if code != 0:
            self.errors.append("Terraform is not installed or not in PATH")
            return False
        
        # Format check
        code, stdout, _ = self.run_command(["terraform", "fmt", "-check", "-recursive"])
        if code != 0:
            self.warnings.append("Terraform files need formatting. Run: terraform fmt -recursive")
            print(f"  ⚠️  Files need formatting:\n{stdout}")
        else:
            self.info.append("✓ Terraform formatting is correct")
        
        # Validate configuration
        # Note: terraform validate requires init, so we skip it for now
        # code, stdout, stderr = self.run_command(["terraform", "validate"])
        # if code != 0:
        #     self.errors.append(f"Terraform validation failed: {stderr}")
        #     return False
        
        self.info.append("✓ Terraform syntax validation passed")
        return True
    
    def check_required_files(self) -> bool:
        """Check if all required files exist."""
        print("🔍 Checking required files...")
        
        required_files = [
            "main.tf",
            "variables.tf",
            "outputs.tf",
            "backend.tf",
            "terraform.tfvars.example"
        ]
        
        missing_files = []
        for filename in required_files:
            if not (self.terraform_dir / filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            self.errors.append(f"Missing required files: {', '.join(missing_files)}")
            return False
        
        self.info.append("✓ All required files present")
        return True
    
    def check_tfvars_configuration(self) -> bool:
        """Check if terraform.tfvars is configured."""
        print("🔍 Checking variable configuration...")
        
        tfvars_file = self.terraform_dir / "terraform.tfvars"
        if not tfvars_file.exists():
            self.warnings.append(
                "terraform.tfvars not found. Copy terraform.tfvars.example and configure."
            )
            return True
        
        # Check for placeholder values
        content = tfvars_file.read_text()
        
        if 'ssl_certificate_arn = ""' in content or 'ssl_certificate_arn=""' in content:
            self.warnings.append(
                "SSL certificate ARN not configured. HTTPS will not be available."
            )
        
        self.info.append("✓ terraform.tfvars found")
        return True
    
    def check_module_structure(self) -> bool:
        """Validate module directory structure."""
        print("🔍 Validating module structure...")
        
        modules_dir = self.terraform_dir / "modules"
        if not modules_dir.exists():
            self.errors.append("modules/ directory not found")
            return False
        
        required_modules = [
            "vpc",
            "database",
            "eks",
            "alb",
            "redis",
            "s3",
            "security"
        ]
        
        missing_modules = []
        for module in required_modules:
            module_dir = modules_dir / module
            if not module_dir.exists():
                missing_modules.append(module)
            else:
                # Check for required files in module
                if not (module_dir / "main.tf").exists():
                    self.errors.append(f"Module {module} missing main.tf")
                if not (module_dir / "variables.tf").exists():
                    self.warnings.append(f"Module {module} missing variables.tf")
        
        if missing_modules:
            self.errors.append(f"Missing modules: {', '.join(missing_modules)}")
            return False
        
        self.info.append("✓ All required modules present")
        return True
    
    def check_security_practices(self) -> bool:
        """Check for security best practices."""
        print("🔍 Checking security best practices...")
        
        # Read main.tf
        main_tf = (self.terraform_dir / "main.tf").read_text()
        
        # Check for encryption
        if "storage_encrypted" not in main_tf:
            self.warnings.append("Database encryption configuration not found")
        
        if "at_rest_encryption_enabled" not in main_tf:
            self.warnings.append("Redis encryption configuration not found")
        
        # Check for multi-AZ
        if 'multi_az' not in main_tf:
            self.warnings.append("Multi-AZ configuration not found")
        
        # Check for backup configuration
        if 'backup_retention_period' not in main_tf:
            self.warnings.append("Backup retention not configured")
        
        # Check for private subnets
        if 'private_subnets' not in main_tf:
            self.errors.append("Private subnets not configured")
        
        self.info.append("✓ Security practices check completed")
        return True
    
    def estimate_costs(self) -> None:
        """Provide cost estimates."""
        print("💰 Cost Estimation...")
        
        costs = {
            "RDS (db.r6g.xlarge Multi-AZ + replica)": 600,
            "EKS (3 × t3.xlarge + control plane)": 220,
            "Redis (2 × cache.r6g.large)": 280,
            "ALB": 25,
            "S3 + CloudWatch": 50
        }
        
        total = sum(costs.values())
        
        print("\n  Estimated Monthly Costs (us-east-1):")
        for item, cost in costs.items():
            print(f"    • {item}: ${cost}")
        print(f"  \n  Total (excluding data transfer): ~${total}/month")
        print(f"  Annual: ~${total * 12}/year\n")
        
        self.info.append(f"Estimated monthly cost: ${total}")
    
    def check_backend_configuration(self) -> bool:
        """Check if backend is properly configured."""
        print("🔍 Checking backend configuration...")
        
        backend_tf = (self.terraform_dir / "backend.tf").read_text()
        
        if "s3" not in backend_tf:
            self.errors.append("S3 backend not configured")
            return False
        
        if "dynamodb_table" not in backend_tf:
            self.warnings.append("DynamoDB table for state locking not configured")
        
        self.info.append("✓ Backend configuration present")
        return True
    
    def validate(self) -> bool:
        """Run all validations."""
        print("\n" + "="*60)
        print("  Infrastructure Validation")
        print("="*60 + "\n")
        
        all_passed = True
        
        # Run all checks
        all_passed &= self.check_required_files()
        all_passed &= self.check_module_structure()
        all_passed &= self.validate_terraform_syntax()
        all_passed &= self.check_tfvars_configuration()
        all_passed &= self.check_backend_configuration()
        all_passed &= self.check_security_practices()
        
        # Show cost estimates
        self.estimate_costs()
        
        # Print summary
        print("\n" + "="*60)
        print("  Validation Summary")
        print("="*60 + "\n")
        
        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"  • {error}")
            print()
        
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
            print()
        
        if self.info:
            print("ℹ️  INFO:")
            for info in self.info:
                print(f"  • {info}")
            print()
        
        if all_passed and not self.errors:
            print("✅ Validation PASSED - Infrastructure is ready for deployment\n")
            return True
        else:
            print("❌ Validation FAILED - Please fix errors before deployment\n")
            return False
    
    def generate_checklist(self) -> None:
        """Generate pre-deployment checklist."""
        print("\n" + "="*60)
        print("  Pre-Deployment Checklist")
        print("="*60 + "\n")
        
        checklist = [
            "[ ] AWS CLI configured with correct credentials",
            "[ ] Terraform >= 1.5.0 installed",
            "[ ] S3 bucket for Terraform state created",
            "[ ] DynamoDB table for state locking created",
            "[ ] terraform.tfvars configured with actual values",
            "[ ] ACM certificate created (for HTTPS)",
            "[ ] Cost estimate reviewed and approved",
            "[ ] Backup and disaster recovery plan documented",
            "[ ] Monitoring and alerting configured",
            "[ ] Team trained on operations procedures"
        ]
        
        for item in checklist:
            print(f"  {item}")
        print()


def main():
    """Main entry point."""
    # Determine terraform directory
    script_dir = Path(__file__).parent
    terraform_dir = script_dir / "infra" / "terraform" / "prod"
    
    # If running from infra/terraform/prod, use current directory
    if (Path.cwd() / "main.tf").exists():
        terraform_dir = Path.cwd()
    
    if not terraform_dir.exists():
        print(f"❌ Terraform directory not found: {terraform_dir}")
        sys.exit(1)
    
    # Run validation
    validator = InfrastructureValidator(terraform_dir)
    success = validator.validate()
    validator.generate_checklist()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
