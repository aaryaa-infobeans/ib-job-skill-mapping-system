#!/usr/bin/env python3
"""
Performance Benchmark Script
TASK-PII-231: Run performance benchmarks at 2x production load

This script executes load testing at 20,000 profiles/min for 2 hours.
"""

import argparse
import json
import logging
import random
import statistics
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceBenchmark:
    """Load testing and performance benchmarking."""
    
    def __init__(
        self,
        target_rps: int = 333,  # 20,000/min = 333/sec
        duration_hours: float = 2.0,
        latency_target_ms: float = 50.0
    ):
        self.target_rps = target_rps
        self.duration_seconds = duration_hours * 3600
        self.latency_target_ms = latency_target_ms
        
        # Metrics
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.latencies: List[float] = []
        self.throughput_history: List[Dict] = []
        
        # Thread safety
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        
    def simulate_scrubbing_request(self) -> Dict:
        """
        Simulate a single PII scrubbing request.
        
        Returns:
            Request result with latency
        """
        start_time = time.perf_counter()
        
        try:
            # Simulate PII scrubbing workload
            # In production, this would call actual scrubber
            time.sleep(random.uniform(0.02, 0.08))  # 20-80ms
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            with self.lock:
                self.request_count += 1
                self.success_count += 1
                self.latencies.append(latency_ms)
            
            return {
                "success": True,
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            with self.lock:
                self.request_count += 1
                self.error_count += 1
            
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def worker_thread(self, worker_id: int):
        """Worker thread for load generation."""
        logger.info(f"Worker {worker_id} started")
        
        while not self.stop_flag.is_set():
            # Execute request
            self.simulate_scrubbing_request()
            
            # Sleep to maintain target RPS
            # Calculate sleep time based on number of workers
            sleep_time = 1.0 / self.target_rps
            time.sleep(sleep_time)
        
        logger.info(f"Worker {worker_id} stopped")
    
    def monitor_thread(self):
        """Monitor thread for collecting metrics."""
        logger.info("Monitor thread started")
        
        interval_seconds = 10
        
        while not self.stop_flag.is_set():
            time.sleep(interval_seconds)
            
            with self.lock:
                current_requests = self.request_count
                current_latencies = self.latencies.copy()
            
            # Calculate throughput
            if current_latencies:
                throughput = len(current_latencies) / interval_seconds
                
                # Calculate latency percentiles
                sorted_latencies = sorted(current_latencies[-1000:])  # Last 1000 requests
                p50 = sorted_latencies[len(sorted_latencies) // 2] if sorted_latencies else 0
                p95_index = int(len(sorted_latencies) * 0.95)
                p95 = sorted_latencies[p95_index] if sorted_latencies else 0
                
                snapshot = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "total_requests": current_requests,
                    "throughput_rps": throughput,
                    "p50_latency_ms": p50,
                    "p95_latency_ms": p95
                }
                
                self.throughput_history.append(snapshot)
                
                logger.info(
                    f"Metrics: {current_requests:,} requests, "
                    f"{throughput:.1f} RPS, "
                    f"p50: {p50:.2f}ms, "
                    f"p95: {p95:.2f}ms"
                )
        
        logger.info("Monitor thread stopped")
    
    def run_load_test(self, num_workers: int = 10) -> Dict:
        """
        Execute load test with multiple workers.
        TASK-PII-231: 2 hours sustained at 20,000 profiles/min
        
        Args:
            num_workers: Number of worker threads
            
        Returns:
            Load test results
        """
        logger.info("=" * 80)
        logger.info("PERFORMANCE LOAD TEST")
        logger.info("=" * 80)
        logger.info(f"Target RPS: {self.target_rps}")
        logger.info(f"Target profiles/min: {self.target_rps * 60:,}")
        logger.info(f"Duration: {self.duration_seconds / 3600:.1f} hours")
        logger.info(f"Latency target: p95 ≤ {self.latency_target_ms}ms")
        logger.info(f"Workers: {num_workers}")
        logger.info("=" * 80)
        
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=self.duration_seconds)
        
        logger.info(f"Start time: {start_time.isoformat()}")
        logger.info(f"Estimated end: {end_time.isoformat()}")
        logger.info("")
        
        # Start workers
        workers = []
        for i in range(num_workers):
            worker = threading.Thread(target=self.worker_thread, args=(i,))
            worker.start()
            workers.append(worker)
        
        # Start monitor
        monitor = threading.Thread(target=self.monitor_thread)
        monitor.start()
        
        try:
            # Run for specified duration
            time.sleep(self.duration_seconds)
            
        except KeyboardInterrupt:
            logger.warning("Load test interrupted by user")
        
        finally:
            # Stop all threads
            logger.info("Stopping workers...")
            self.stop_flag.set()
            
            for worker in workers:
                worker.join(timeout=5)
            
            monitor.join(timeout=5)
        
        # Calculate final metrics
        actual_duration = (datetime.utcnow() - start_time).total_seconds()
        summary = self._calculate_summary(actual_duration)
        
        return summary
    
    def _calculate_summary(self, duration: float) -> Dict:
        """Calculate load test summary."""
        if not self.latencies:
            return {"error": "No latency data collected"}
        
        sorted_latencies = sorted(self.latencies)
        
        # Calculate percentiles
        p50 = sorted_latencies[len(sorted_latencies) // 2]
        p95_index = int(len(sorted_latencies) * 0.95)
        p95 = sorted_latencies[p95_index]
        p99_index = int(len(sorted_latencies) * 0.99)
        p99 = sorted_latencies[p99_index]
        
        avg_latency = statistics.mean(sorted_latencies)
        max_latency = max(sorted_latencies)
        
        # Calculate throughput
        actual_rps = self.request_count / duration if duration > 0 else 0
        actual_rpm = actual_rps * 60
        
        # Validate performance
        latency_check_passed = p95 <= self.latency_target_ms
        throughput_check_passed = actual_rpm >= 20000 * 0.95  # Within 5% of target
        
        summary = {
            "test_duration_seconds": duration,
            "test_duration_hours": duration / 3600,
            "total_requests": self.request_count,
            "successful_requests": self.success_count,
            "failed_requests": self.error_count,
            "error_rate_percent": (self.error_count / self.request_count * 100) if self.request_count > 0 else 0,
            "throughput": {
                "actual_rps": actual_rps,
                "actual_rpm": actual_rpm,
                "target_rps": self.target_rps,
                "target_rpm": self.target_rps * 60,
                "throughput_check_passed": throughput_check_passed
            },
            "latency": {
                "avg_ms": avg_latency,
                "p50_ms": p50,
                "p95_ms": p95,
                "p99_ms": p99,
                "max_ms": max_latency,
                "target_p95_ms": self.latency_target_ms,
                "latency_check_passed": latency_check_passed
            },
            "all_checks_passed": latency_check_passed and throughput_check_passed
        }
        
        # Log summary
        logger.info("=" * 80)
        logger.info("LOAD TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Duration: {summary['test_duration_hours']:.2f} hours")
        logger.info(f"Total requests: {summary['total_requests']:,}")
        logger.info(f"Successful: {summary['successful_requests']:,}")
        logger.info(f"Failed: {summary['failed_requests']:,}")
        logger.info(f"Error rate: {summary['error_rate_percent']:.2f}%")
        logger.info("")
        logger.info(f"Throughput:")
        logger.info(f"  Actual: {summary['throughput']['actual_rpm']:,.0f} req/min")
        logger.info(f"  Target: {summary['throughput']['target_rpm']:,} req/min")
        logger.info(f"  Status: {'PASSED ✓' if throughput_check_passed else 'FAILED ✗'}")
        logger.info("")
        logger.info(f"Latency:")
        logger.info(f"  Average: {summary['latency']['avg_ms']:.2f}ms")
        logger.info(f"  p50: {summary['latency']['p50_ms']:.2f}ms")
        logger.info(f"  p95: {summary['latency']['p95_ms']:.2f}ms")
        logger.info(f"  p99: {summary['latency']['p99_ms']:.2f}ms")
        logger.info(f"  Target p95: {self.latency_target_ms}ms")
        logger.info(f"  Status: {'PASSED ✓' if latency_check_passed else 'FAILED ✗'}")
        logger.info("")
        logger.info(f"Overall: {'PASSED ✓' if summary['all_checks_passed'] else 'FAILED ✗'}")
        logger.info("=" * 80)
        
        return summary


def main():
    """Main performance benchmark orchestration."""
    parser = argparse.ArgumentParser(description="Performance load testing")
    parser.add_argument(
        "--target-rpm",
        type=int,
        default=20000,
        help="Target requests per minute (default: 20,000)"
    )
    parser.add_argument(
        "--duration-hours",
        type=float,
        default=2.0,
        help="Test duration in hours (default: 2.0)"
    )
    parser.add_argument(
        "--latency-target-ms",
        type=float,
        default=50.0,
        help="Target p95 latency in ms (default: 50.0)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of worker threads (default: 10)"
    )
    parser.add_argument(
        "--report-file",
        type=Path,
        help="Path to save test report"
    )
    
    args = parser.parse_args()
    
    # Calculate target RPS
    target_rps = args.target_rpm / 60
    
    # Initialize benchmark
    benchmark = PerformanceBenchmark(
        target_rps=int(target_rps),
        duration_hours=args.duration_hours,
        latency_target_ms=args.latency_target_ms
    )
    
    # Run load test
    try:
        summary = benchmark.run_load_test(num_workers=args.workers)
        
        # Save report
        report_file = args.report_file or Path(f"performance-report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json")
        report_file.write_text(json.dumps(summary, indent=2))
        logger.info(f"Report saved to: {report_file}")
        
        # Exit with appropriate code
        import sys
        sys.exit(0 if summary.get("all_checks_passed", False) else 1)
    
    except Exception as e:
        logger.error(f"Load test failed: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
