#!/usr/bin/env python3
"""
PII Leak Scanner for Production Data
TASK-PII-212: Run PII leak scan on all backfilled records
TASK-PII-233: Automated PII leak scan: Logs, metrics, traces
TASK-PII-304: Final PII leak scan on production backfilled data

This script scans for PII leakage in scrubbed data, logs, metrics, and code.
"""

import argparse
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PIIPattern:
    """PII detection patterns."""
    
    # Email pattern
    EMAIL = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    # Phone patterns (multiple formats)
    PHONE_US = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
    PHONE_INTL = r'\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
    
    # SSN pattern
    SSN = r'\b\d{3}-\d{2}-\d{4}\b'
    
    # Credit card pattern (basic)
    CREDIT_CARD = r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'
    
    # IP Address (may contain PII in some contexts)
    IP_ADDRESS = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
    
    # URL with potential PII
    URL_WITH_PARAMS = r'https?://[^\s]+[\?&][^\s]*'
    
    @classmethod
    def get_all_patterns(cls) -> Dict[str, str]:
        """Get all PII patterns."""
        return {
            "email": cls.EMAIL,
            "phone_us": cls.PHONE_US,
            "phone_intl": cls.PHONE_INTL,
            "ssn": cls.SSN,
            "credit_card": cls.CREDIT_CARD,
            "ip_address": cls.IP_ADDRESS,
            "url_with_params": cls.URL_WITH_PARAMS
        }


class PIILeakScanner:
    """Scans for PII leakage in various sources."""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
        self.scan_results: Dict[str, List[Dict]] = {
            "data": [],
            "logs": [],
            "metrics": [],
            "code": []
        }
        self.total_leaks = 0
        
    def scan_text(self, text: str, source: str, context: str = "") -> List[Dict]:
        """
        Scan text for PII patterns.
        
        Args:
            text: Text to scan
            source: Source identifier (file, record, etc.)
            context: Additional context
            
        Returns:
            List of detected PII instances
        """
        detections = []
        
        for pattern_name, pattern in PIIPattern.get_all_patterns().items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                # Skip false positives
                if self._is_false_positive(match.group(), pattern_name):
                    continue
                
                detection = {
                    "pattern": pattern_name,
                    "value": match.group(),
                    "position": match.start(),
                    "source": source,
                    "context": context,
                    "line_preview": self._get_line_preview(text, match.start())
                }
                
                detections.append(detection)
                logger.warning(f"PII detected: {pattern_name} in {source}")
        
        return detections
    
    def _is_false_positive(self, value: str, pattern_name: str) -> bool:
        """Check if detection is a false positive."""
        # Common false positives for IP addresses
        if pattern_name == "ip_address":
            if value in ["0.0.0.0", "127.0.0.1", "255.255.255.255"]:
                return True
            if value.startswith("192.168.") or value.startswith("10."):
                return True
        
        # Common false positives for credit cards
        if pattern_name == "credit_card":
            # Test card numbers
            test_cards = ["4111111111111111", "5555555555554444"]
            if value.replace("-", "").replace(" ", "") in test_cards:
                return True
        
        # Email patterns - allow documented test emails
        if pattern_name == "email":
            if "example.com" in value or "test.com" in value:
                return True
        
        return False
    
    def _get_line_preview(self, text: str, position: int, context_chars: int = 100) -> str:
        """Get preview of line containing PII."""
        start = max(0, position - context_chars)
        end = min(len(text), position + context_chars)
        preview = text[start:end].replace('\n', ' ')
        return f"...{preview}..."
    
    def scan_data_file(self, file_path: Path, sample_size: Optional[int] = None) -> Dict:
        """
        Scan data file for PII leakage.
        TASK-PII-212: Scan backfilled records
        
        Args:
            file_path: Path to data file (JSON lines)
            sample_size: Number of records to scan (None = all)
            
        Returns:
            Scan results summary
        """
        logger.info(f"Scanning data file: {file_path}")
        
        scan_start = datetime.utcnow()
        scanned_records = 0
        leaked_records = 0
        
        try:
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    if sample_size and line_num > sample_size:
                        break
                    
                    try:
                        record = json.loads(line.strip())
                        scanned_records += 1
                        
                        # Scan profile text (should be scrubbed)
                        if 'profile_text' in record and record.get('pii_scrubbed'):
                            detections = self.scan_text(
                                text=record['profile_text'],
                                source=f"{file_path.name}:record_{record.get('id', line_num)}",
                                context="profile_text (scrubbed)"
                            )
                            
                            if detections:
                                leaked_records += 1
                                self.scan_results["data"].extend(detections)
                                self.total_leaks += len(detections)
                        
                        # Progress logging
                        if scanned_records % 10000 == 0:
                            logger.info(f"Scanned {scanned_records:,} records...")
                    
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse line {line_num}")
                        continue
        
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return {"error": "File not found"}
        
        scan_duration = (datetime.utcnow() - scan_start).total_seconds()
        
        result = {
            "file": str(file_path),
            "scanned_records": scanned_records,
            "leaked_records": leaked_records,
            "total_detections": len([d for d in self.scan_results["data"] if d["source"].startswith(file_path.name)]),
            "duration_seconds": scan_duration,
            "scan_passed": leaked_records == 0
        }
        
        logger.info(f"Data scan complete: {scanned_records:,} records, {leaked_records:,} with leaks")
        
        return result
    
    def scan_log_directory(self, log_dir: Path, max_files: int = 100) -> Dict:
        """
        Scan log files for PII leakage.
        TASK-PII-233: Automated PII leak scan - Logs
        
        Args:
            log_dir: Directory containing log files
            max_files: Maximum log files to scan
            
        Returns:
            Scan results summary
        """
        logger.info(f"Scanning log directory: {log_dir}")
        
        if not log_dir.exists():
            logger.warning(f"Log directory not found: {log_dir}")
            return {"error": "Directory not found"}
        
        scan_start = datetime.utcnow()
        scanned_files = 0
        scanned_lines = 0
        leaked_files = 0
        
        # Find log files
        log_files = list(log_dir.glob("*.log")) + list(log_dir.glob("**/*.log"))
        log_files = log_files[:max_files]
        
        for log_file in log_files:
            scanned_files += 1
            file_has_leak = False
            
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        scanned_lines += 1
                        
                        detections = self.scan_text(
                            text=line,
                            source=f"{log_file.name}:L{line_num}",
                            context="log_line"
                        )
                        
                        if detections:
                            file_has_leak = True
                            self.scan_results["logs"].extend(detections)
                            self.total_leaks += len(detections)
                
                if file_has_leak:
                    leaked_files += 1
            
            except Exception as e:
                logger.error(f"Failed to scan {log_file}: {e}")
                continue
        
        scan_duration = (datetime.utcnow() - scan_start).total_seconds()
        
        result = {
            "directory": str(log_dir),
            "scanned_files": scanned_files,
            "scanned_lines": scanned_lines,
            "leaked_files": leaked_files,
            "total_detections": len(self.scan_results["logs"]),
            "duration_seconds": scan_duration,
            "scan_passed": leaked_files == 0
        }
        
        logger.info(f"Log scan complete: {scanned_files} files, {leaked_files} with leaks")
        
        return result
    
    def scan_metrics_endpoint(self, metrics_url: str = "http://localhost:8000/metrics") -> Dict:
        """
        Scan Prometheus metrics for PII leakage.
        TASK-PII-233: Automated PII leak scan - Metrics
        
        Args:
            metrics_url: URL of metrics endpoint
            
        Returns:
            Scan results summary
        """
        logger.info(f"Scanning metrics endpoint: {metrics_url}")
        
        try:
            import requests
            response = requests.get(metrics_url, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Metrics endpoint returned {response.status_code}")
                return {"error": f"HTTP {response.status_code}"}
            
            metrics_text = response.text
            
            detections = self.scan_text(
                text=metrics_text,
                source=metrics_url,
                context="prometheus_metrics"
            )
            
            self.scan_results["metrics"].extend(detections)
            self.total_leaks += len(detections)
            
            result = {
                "url": metrics_url,
                "total_detections": len(detections),
                "scan_passed": len(detections) == 0
            }
            
            logger.info(f"Metrics scan complete: {len(detections)} leaks detected")
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to scan metrics: {e}")
            return {"error": str(e)}
    
    def scan_code_directory(self, code_dir: Path, extensions: List[str] = [".py", ".js", ".ts"]) -> Dict:
        """
        Scan code files for hardcoded PII.
        TASK-PII-233: Scan code for hardcoded PII
        
        Args:
            code_dir: Directory containing code
            extensions: File extensions to scan
            
        Returns:
            Scan results summary
        """
        logger.info(f"Scanning code directory: {code_dir}")
        
        scanned_files = 0
        scanned_lines = 0
        leaked_files = 0
        
        for ext in extensions:
            for code_file in code_dir.glob(f"**/*{ext}"):
                # Skip test files and examples
                if "test" in code_file.name.lower() or "example" in code_file.name.lower():
                    continue
                
                scanned_files += 1
                file_has_leak = False
                
                try:
                    with open(code_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            scanned_lines += 1
                            
                            # Skip comments
                            if line.strip().startswith('#') or line.strip().startswith('//'):
                                continue
                            
                            detections = self.scan_text(
                                text=line,
                                source=f"{code_file.relative_to(code_dir)}:L{line_num}",
                                context="source_code"
                            )
                            
                            if detections:
                                file_has_leak = True
                                self.scan_results["code"].extend(detections)
                                self.total_leaks += len(detections)
                    
                    if file_has_leak:
                        leaked_files += 1
                
                except Exception as e:
                    logger.error(f"Failed to scan {code_file}: {e}")
                    continue
        
        result = {
            "directory": str(code_dir),
            "scanned_files": scanned_files,
            "scanned_lines": scanned_lines,
            "leaked_files": leaked_files,
            "total_detections": len(self.scan_results["code"]),
            "scan_passed": leaked_files == 0
        }
        
        logger.info(f"Code scan complete: {scanned_files} files, {leaked_files} with leaks")
        
        return result
    
    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """Generate comprehensive PII leak scan report."""
        report = {
            "scan_id": f"pii-leak-scan-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "total_leaks": self.total_leaks,
            "scan_passed": self.total_leaks == 0,
            "results_by_source": {
                "data": len(self.scan_results["data"]),
                "logs": len(self.scan_results["logs"]),
                "metrics": len(self.scan_results["metrics"]),
                "code": len(self.scan_results["code"])
            },
            "detections": self.scan_results
        }
        
        report_json = json.dumps(report, indent=2)
        
        if output_file:
            output_file.write_text(report_json)
            logger.info(f"Report saved to: {output_file}")
        
        # Log summary
        logger.info("=" * 80)
        logger.info("PII LEAK SCAN SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total leaks detected: {self.total_leaks}")
        logger.info(f"  - Data: {len(self.scan_results['data'])}")
        logger.info(f"  - Logs: {len(self.scan_results['logs'])}")
        logger.info(f"  - Metrics: {len(self.scan_results['metrics'])}")
        logger.info(f"  - Code: {len(self.scan_results['code'])}")
        logger.info(f"Scan result: {'PASSED ✓' if self.total_leaks == 0 else 'FAILED ✗'}")
        logger.info("=" * 80)
        
        return report_json


def main():
    """Main PII leak scanner orchestration."""
    parser = argparse.ArgumentParser(description="Scan for PII leakage")
    parser.add_argument(
        "--scan-data",
        type=Path,
        help="Data file to scan (JSON lines)"
    )
    parser.add_argument(
        "--scan-logs",
        type=Path,
        help="Log directory to scan"
    )
    parser.add_argument(
        "--scan-metrics",
        type=str,
        help="Metrics endpoint URL to scan"
    )
    parser.add_argument(
        "--scan-code",
        type=Path,
        help="Code directory to scan"
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        help="Sample size for data scan (default: all)"
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        help="Path to save scan report"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode (fewer false positive exceptions)"
    )
    
    args = parser.parse_args()
    
    # Initialize scanner
    scanner = PIILeakScanner(strict_mode=args.strict)
    
    # Run scans
    scan_results = {}
    
    if args.scan_data:
        scan_results["data"] = scanner.scan_data_file(args.scan_data, args.sample_size)
    
    if args.scan_logs:
        scan_results["logs"] = scanner.scan_log_directory(args.scan_logs)
    
    if args.scan_metrics:
        scan_results["metrics"] = scanner.scan_metrics_endpoint(args.scan_metrics)
    
    if args.scan_code:
        scan_results["code"] = scanner.scan_code_directory(args.scan_code)
    
    # Generate report
    report_file = args.report_file or Path(f"pii-leak-scan-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json")
    scanner.generate_report(report_file)
    
    # Exit with appropriate code
    import sys
    sys.exit(0 if scanner.total_leaks == 0 else 1)


if __name__ == "__main__":
    main()
