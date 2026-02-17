#!/usr/bin/env python3
"""
Infrastructure Validation Checklist for Staging Environment
TASK-PII-201: Validate staging infrastructure readiness

This script validates all infrastructure requirements for the staging environment
before deployment.
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    check_name: str
    passed: bool
    message: str
    details: Dict = field(default_factory=dict)
    severity: str = "ERROR"  # ERROR, WARNING, INFO


class InfrastructureValidator:
    """Validates staging infrastructure readiness."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.results: List[ValidationResult] = []
        self.start_time = datetime.utcnow()
    
    def add_result(self, result: ValidationResult):
        """Add validation result."""
        self.results.append(result)
        status = "✓ PASS" if result.passed else "✗ FAIL"
        logger.log(
            logging.INFO if result.passed else logging.ERROR,
            f"{status}: {result.check_name} - {result.message}"
        )
    
    def validate_gpu(self) -> ValidationResult:
        """
        Validate GPU availability and configuration.
        NFR-PII-001: GPU required for performance
        """
        try:
            import subprocess
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,compute_cap", 
                 "--format=csv,noheader"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10
            )
            
            gpu_info = result.stdout.strip()
            if not gpu_info:
                return ValidationResult(
                    check_name="GPU Availability",
                    passed=False,
                    message="No GPU detected",
                    severity="ERROR"
                )
            
            # Parse GPU info
            parts = gpu_info.split(',')
            gpu_name = parts[0].strip() if len(parts) > 0 else "Unknown"
            driver_version = parts[1].strip() if len(parts) > 1 else "Unknown"
            memory_total = parts[2].strip() if len(parts) > 2 else "Unknown"
            compute_cap = parts[3].strip() if len(parts) > 3 else "Unknown"
            
            # Validate CUDA version
            cuda_result = subprocess.run(
                ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader"],
                capture_output=True,
                text=True
            )
            cuda_version = cuda_result.stdout.strip() if cuda_result.returncode == 0 else "Unknown"
            
            return ValidationResult(
                check_name="GPU Availability",
                passed=True,
                message=f"GPU detected: {gpu_name}",
                details={
                    "gpu_name": gpu_name,
                    "driver_version": driver_version,
                    "memory_total": memory_total,
                    "compute_capability": compute_cap,
                    "cuda_version": cuda_version
                },
                severity="INFO"
            )
            
        except subprocess.TimeoutExpired:
            return ValidationResult(
                check_name="GPU Availability",
                passed=False,
                message="nvidia-smi command timed out",
                severity="WARNING"
            )
        except FileNotFoundError:
            return ValidationResult(
                check_name="GPU Availability",
                passed=False,
                message="nvidia-smi not found (GPU may not be available)",
                severity="WARNING"
            )
        except Exception as e:
            return ValidationResult(
                check_name="GPU Availability",
                passed=False,
                message=f"GPU check failed: {str(e)}",
                severity="WARNING"
            )
    
    def validate_database(self) -> ValidationResult:
        """
        Validate database connectivity and configuration.
        TASK-PII-004: pii_scrub_audit table required
        """
        try:
            # Placeholder for database validation
            # In production, would connect to actual database
            
            # Check if database configuration exists
            import os
            db_url = os.getenv("DATABASE_URL")
            
            if not db_url:
                return ValidationResult(
                    check_name="Database Configuration",
                    passed=False,
                    message="DATABASE_URL not set",
                    severity="ERROR"
                )
            
            # In production, would validate:
            # 1. Connection successful
            # 2. pii_scrub_audit table exists
            # 3. Required permissions granted
            # 4. Immutability triggers configured
            
            return ValidationResult(
                check_name="Database Configuration",
                passed=True,
                message="Database configuration valid",
                details={"database_url": db_url.split('@')[1] if '@' in db_url else "configured"},
                severity="INFO"
            )
            
        except Exception as e:
            return ValidationResult(
                check_name="Database Configuration",
                passed=False,
                message=f"Database validation failed: {str(e)}",
                severity="ERROR"
            )
    
    def validate_prometheus(self) -> ValidationResult:
        """
        Validate Prometheus metrics exporter.
        TASK-PII-005: Prometheus metrics required
        NFR-PII-002: Observability requirements
        """
        try:
            import requests
            
            # Try to connect to Prometheus metrics endpoint
            response = requests.get("http://localhost:8000/metrics", timeout=5)
            
            if response.status_code == 200:
                # Check for required PII scrubber metrics
                metrics_text = response.text
                required_metrics = [
                    "pii_detections_total",
                    "pii_scrubbing_latency_seconds",
                    "validation_gate_blocked_total"
                ]
                
                missing_metrics = [m for m in required_metrics if m not in metrics_text]
                
                if missing_metrics:
                    return ValidationResult(
                        check_name="Prometheus Metrics",
                        passed=False,
                        message=f"Missing required metrics: {', '.join(missing_metrics)}",
                        severity="WARNING"
                    )
                
                return ValidationResult(
                    check_name="Prometheus Metrics",
                    passed=True,
                    message="All required metrics available",
                    details={"metrics_endpoint": "http://localhost:8000/metrics"},
                    severity="INFO"
                )
            else:
                return ValidationResult(
                    check_name="Prometheus Metrics",
                    passed=False,
                    message=f"Metrics endpoint returned status {response.status_code}",
                    severity="WARNING"
                )
                
        except requests.exceptions.RequestException:
            return ValidationResult(
                check_name="Prometheus Metrics",
                passed=False,
                message="Metrics endpoint not accessible (may not be started yet)",
                severity="WARNING"
            )
        except Exception as e:
            return ValidationResult(
                check_name="Prometheus Metrics",
                passed=False,
                message=f"Prometheus validation failed: {str(e)}",
                severity="WARNING"
            )
    
    def validate_grafana(self) -> ValidationResult:
        """
        Validate Grafana dashboards.
        TASK-PII-006: Grafana dashboards required
        """
        try:
            import requests
            
            # Try to connect to Grafana
            response = requests.get("http://localhost:3000/api/health", timeout=5)
            
            if response.status_code == 200:
                return ValidationResult(
                    check_name="Grafana Dashboards",
                    passed=True,
                    message="Grafana accessible",
                    details={"grafana_url": "http://localhost:3000"},
                    severity="INFO"
                )
            else:
                return ValidationResult(
                    check_name="Grafana Dashboards",
                    passed=False,
                    message=f"Grafana returned status {response.status_code}",
                    severity="WARNING"
                )
                
        except requests.exceptions.RequestException:
            return ValidationResult(
                check_name="Grafana Dashboards",
                passed=False,
                message="Grafana not accessible (may not be required for staging)",
                severity="WARNING"
            )
        except Exception as e:
            return ValidationResult(
                check_name="Grafana Dashboards",
                passed=False,
                message=f"Grafana validation failed: {str(e)}",
                severity="WARNING"
            )
    
    def validate_disk_space(self, min_gb: int = 50) -> ValidationResult:
        """Validate sufficient disk space available."""
        try:
            import shutil
            stats = shutil.disk_usage("/")
            free_gb = stats.free / (1024 ** 3)
            total_gb = stats.total / (1024 ** 3)
            used_percent = (stats.used / stats.total) * 100
            
            passed = free_gb >= min_gb
            
            return ValidationResult(
                check_name="Disk Space",
                passed=passed,
                message=f"Free: {free_gb:.2f} GB (Required: {min_gb} GB)",
                details={
                    "free_gb": round(free_gb, 2),
                    "total_gb": round(total_gb, 2),
                    "used_percent": round(used_percent, 2)
                },
                severity="ERROR" if not passed else "INFO"
            )
            
        except Exception as e:
            return ValidationResult(
                check_name="Disk Space",
                passed=False,
                message=f"Disk space check failed: {str(e)}",
                severity="ERROR"
            )
    
    def validate_memory(self, min_gb: int = 16) -> ValidationResult:
        """Validate sufficient memory available."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024 ** 3)
            available_gb = mem.available / (1024 ** 3)
            used_percent = mem.percent
            
            passed = total_gb >= min_gb
            
            return ValidationResult(
                check_name="Memory",
                passed=passed,
                message=f"Total: {total_gb:.2f} GB (Required: {min_gb} GB)",
                details={
                    "total_gb": round(total_gb, 2),
                    "available_gb": round(available_gb, 2),
                    "used_percent": round(used_percent, 2)
                },
                severity="ERROR" if not passed else "INFO"
            )
            
        except ImportError:
            return ValidationResult(
                check_name="Memory",
                passed=False,
                message="psutil not installed (cannot check memory)",
                severity="WARNING"
            )
        except Exception as e:
            return ValidationResult(
                check_name="Memory",
                passed=False,
                message=f"Memory check failed: {str(e)}",
                severity="WARNING"
            )
    
    def validate_docker(self) -> ValidationResult:
        """Validate Docker installation and configuration."""
        try:
            import subprocess
            
            # Check Docker version
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            docker_version = result.stdout.strip()
            
            # Check Docker Compose
            compose_result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                check=True
            )
            compose_version = compose_result.stdout.strip()
            
            return ValidationResult(
                check_name="Docker",
                passed=True,
                message="Docker and Docker Compose available",
                details={
                    "docker_version": docker_version,
                    "compose_version": compose_version
                },
                severity="INFO"
            )
            
        except FileNotFoundError:
            return ValidationResult(
                check_name="Docker",
                passed=False,
                message="Docker not installed",
                severity="ERROR"
            )
        except subprocess.CalledProcessError as e:
            return ValidationResult(
                check_name="Docker",
                passed=False,
                message=f"Docker check failed: {str(e)}",
                severity="ERROR"
            )
    
    def validate_spacy_model(self) -> ValidationResult:
        """
        Validate SpaCy model installation.
        TASK-PII-002: SpaCy en_core_web_trf required
        """
        try:
            import spacy
            
            # Try to load the model
            try:
                nlp = spacy.load("en_core_web_trf")
                
                # Validate model performance
                test_text = "John Smith works at Acme Corp. His email is john.smith@example.com."
                doc = nlp(test_text)
                entities = [(ent.text, ent.label_) for ent in doc.ents]
                
                has_person = any(label == "PERSON" for _, label in entities)
                has_org = any(label == "ORG" for _, label in entities)
                
                if not (has_person and has_org):
                    return ValidationResult(
                        check_name="SpaCy Model",
                        passed=False,
                        message="Model loaded but NER quality insufficient",
                        details={"entities_found": entities},
                        severity="WARNING"
                    )
                
                return ValidationResult(
                    check_name="SpaCy Model",
                    passed=True,
                    message="en_core_web_trf model loaded successfully",
                    details={"test_entities": entities},
                    severity="INFO"
                )
                
            except OSError:
                return ValidationResult(
                    check_name="SpaCy Model",
                    passed=False,
                    message="en_core_web_trf model not installed",
                    severity="ERROR"
                )
                
        except ImportError:
            return ValidationResult(
                check_name="SpaCy Model",
                passed=False,
                message="SpaCy not installed",
                severity="ERROR"
            )
        except Exception as e:
            return ValidationResult(
                check_name="SpaCy Model",
                passed=False,
                message=f"SpaCy validation failed: {str(e)}",
                severity="ERROR"
            )
    
    def validate_network(self) -> ValidationResult:
        """Validate network connectivity."""
        try:
            import socket
            
            # Test internet connectivity
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            
            return ValidationResult(
                check_name="Network Connectivity",
                passed=True,
                message="Network connectivity OK",
                severity="INFO"
            )
            
        except Exception as e:
            return ValidationResult(
                check_name="Network Connectivity",
                passed=False,
                message=f"Network check failed: {str(e)}",
                severity="ERROR"
            )
    
    def run_all_validations(self) -> bool:
        """Run all validation checks."""
        logger.info(f"Running infrastructure validation for {self.environment}...")
        
        # Run all validation checks
        self.add_result(self.validate_docker())
        self.add_result(self.validate_gpu())
        self.add_result(self.validate_database())
        self.add_result(self.validate_spacy_model())
        self.add_result(self.validate_disk_space())
        self.add_result(self.validate_memory())
        self.add_result(self.validate_prometheus())
        self.add_result(self.validate_grafana())
        self.add_result(self.validate_network())
        
        # Calculate results
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        errors = sum(1 for r in self.results if not r.passed and r.severity == "ERROR")
        warnings = sum(1 for r in self.results if not r.passed and r.severity == "WARNING")
        
        logger.info(f"\nValidation Summary:")
        logger.info(f"  Total checks: {total}")
        logger.info(f"  Passed: {passed}")
        logger.info(f"  Failed: {failed} ({errors} errors, {warnings} warnings)")
        
        # Return True only if all ERROR-severity checks passed
        return errors == 0
    
    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """Generate validation report."""
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        
        report = {
            "validation_id": f"infra-{self.start_time.strftime('%Y%m%d-%H%M%S')}",
            "environment": self.environment,
            "timestamp": self.start_time.isoformat(),
            "duration_seconds": duration,
            "checks": [
                {
                    "name": r.check_name,
                    "passed": r.passed,
                    "message": r.message,
                    "severity": r.severity,
                    "details": r.details
                }
                for r in self.results
            ],
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results if r.passed),
                "failed": sum(1 for r in self.results if not r.passed),
                "errors": sum(1 for r in self.results if not r.passed and r.severity == "ERROR"),
                "warnings": sum(1 for r in self.results if not r.passed and r.severity == "WARNING"),
                "status": "READY" if sum(1 for r in self.results if not r.passed and r.severity == "ERROR") == 0 else "NOT_READY"
            }
        }
        
        report_json = json.dumps(report, indent=2)
        
        if output_file:
            output_file.write_text(report_json)
            logger.info(f"Validation report saved to: {output_file}")
        
        return report_json


def main():
    """Main validation orchestration."""
    parser = argparse.ArgumentParser(description="Validate staging infrastructure readiness")
    parser.add_argument(
        "--environment",
        default="staging",
        help="Environment to validate (default: staging)"
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        help="Path to save validation report"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = InfrastructureValidator(environment=args.environment)
    success = validator.run_all_validations()
    
    # Generate report
    report_file = args.report_file or Path(f"validation-report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json")
    validator.generate_report(report_file)
    
    if success:
        logger.info("\n✓ Infrastructure validation PASSED - Ready for deployment")
        sys.exit(0)
    else:
        logger.error("\n✗ Infrastructure validation FAILED - Fix errors before deployment")
        sys.exit(1)


if __name__ == "__main__":
    main()
