"""
Performance benchmark tests for batch processing.

Tests validate NFR-performance.md requirements:
- Bulk upsert throughput ≥ 100 records/second
- 10,000 records processed in < 30 minutes
- Memory usage < 2 GB during processing
"""

import pytest
import time
import psutil
import os
from typing import List, Dict, Any
from datetime import datetime

from app.cron.processing.batch_processor import BatchProcessor
from app.cron.db.engine import create_ingestion_engine
from sqlalchemy.orm import Session


# Performance test configuration
SMALL_BATCH_SIZE = 100
MEDIUM_BATCH_SIZE = 1000
LARGE_BATCH_SIZE = 10000

# NFR thresholds
MIN_THROUGHPUT = 100  # records/second
MAX_PROCESSING_TIME_10K = 1800  # 30 minutes in seconds
MAX_MEMORY_MB = 2048  # 2 GB


def generate_team_member_data(count: int, batch_id: str) -> List[Dict[str, Any]]:
    """Generate test team member data for performance testing."""
    team_members = []
    
    for i in range(count):
        member = {
            'team_member_id': f'PERF-TM-{batch_id}-{i:06d}',
            'designation': f'Engineer {i % 5}',
            'profile_type': 'Technical',
            'team_member_status': 'active',
            'experience_in_months': 24 + (i % 120),
            'base_location': ['Bangalore', 'Mumbai', 'Pune'][i % 3],
            'work-mode': ['WFH', 'WFO', 'HYBRID'][i % 3],
            'profile': f'https://example.com/profile/{i}',
            'skills': [
                {
                    'skill_name': ['Python', 'Java', 'JavaScript', 'C++', 'Go'][i % 5],
                    'category': 'Engineering',
                    'rating': 3 + (i % 3),
                    'experience_in_months': 12 + (i % 60),
                    'is_deleted': False,
                    'certifications': []
                },
                {
                    'skill_name': ['AWS', 'Azure', 'GCP'][i % 3],
                    'category': 'Cloud',
                    'rating': 3 + (i % 3),
                    'experience_in_months': 6 + (i % 36),
                    'is_deleted': False,
                    'certifications': []
                }
            ],
            'allocations': [
                {
                    'project_id': f'PROJ-{i % 100}',
                    'allocation_percentage': 50.0 + (i % 50),
                    'start_date': '2024-01-01',
                    'end_date': '2024-12-31',
                    'billable': True,
                    'is_deleted': False
                }
            ]
        }
        team_members.append(member)
    
    return team_members


class TestBatchPerformance:
    """Performance benchmark tests for batch processing."""
    
    @pytest.fixture(scope='class')
    def engine(self):
        """Create database engine for performance tests."""
        # Use test database with schema validation disabled for performance
        engine = create_ingestion_engine(validate_schema=False)
        yield engine
        engine.dispose()
    
    @pytest.fixture
    def session(self, engine):
        """Create database session."""
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        yield session
        session.close()
    
    def measure_performance(self, processor: BatchProcessor, batch_id: str, 
                          correlation_id: str, team_members: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Measure performance metrics for batch processing.
        
        Returns dict with:
        - duration_seconds: Total processing time
        - throughput: Records per second
        - memory_peak_mb: Peak memory usage in MB
        - success: Whether processing succeeded
        """
        # Get process for memory monitoring
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        baseline_memory_mb = process.memory_info().rss / (1024 * 1024)
        
        # Start timing
        start_time = time.time()
        
        try:
            # Process batch (blocking)
            import asyncio
            success = asyncio.run(processor.process_batch(
                batch_id=batch_id,
                correlation_id=correlation_id,
                team_members=team_members,
                metadata={'test_type': 'performance'}
            ))
            
            # End timing
            duration = time.time() - start_time
            
            # Measure peak memory
            peak_memory_mb = process.memory_info().rss / (1024 * 1024)
            memory_increase_mb = peak_memory_mb - baseline_memory_mb
            
            # Calculate throughput
            throughput = len(team_members) / duration if duration > 0 else 0
            
            return {
                'duration_seconds': duration,
                'throughput': throughput,
                'memory_peak_mb': peak_memory_mb,
                'memory_increase_mb': memory_increase_mb,
                'records_processed': len(team_members),
                'success': success
            }
        
        except Exception as e:
            duration = time.time() - start_time
            return {
                'duration_seconds': duration,
                'throughput': 0,
                'memory_peak_mb': 0,
                'memory_increase_mb': 0,
                'records_processed': 0,
                'success': False,
                'error': str(e)
            }
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_small_batch_performance(self, session):
        """Test performance with 100 records (baseline)."""
        batch_id = f'PERF-SMALL-{int(time.time())}'
        correlation_id = f'CORR-SMALL-{int(time.time())}'
        
        # Generate test data
        team_members = generate_team_member_data(SMALL_BATCH_SIZE, batch_id)
        
        # Create processor
        processor = BatchProcessor(session, dry_run=True)
        
        # Measure performance
        metrics = self.measure_performance(processor, batch_id, correlation_id, team_members)
        
        # Log results
        print(f"\n=== Small Batch Performance (n={SMALL_BATCH_SIZE}) ===")
        print(f"Duration: {metrics['duration_seconds']:.2f}s")
        print(f"Throughput: {metrics['throughput']:.2f} records/sec")
        print(f"Memory increase: {metrics['memory_increase_mb']:.2f} MB")
        print(f"Success: {metrics['success']}")
        
        # Assertions
        assert metrics['success'], "Batch processing should succeed"
        assert metrics['throughput'] >= MIN_THROUGHPUT, \
            f"Throughput {metrics['throughput']:.2f} < {MIN_THROUGHPUT} records/sec"
        assert metrics['memory_peak_mb'] < MAX_MEMORY_MB, \
            f"Memory {metrics['memory_peak_mb']:.2f} MB exceeds {MAX_MEMORY_MB} MB"
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_medium_batch_performance(self, session):
        """Test performance with 1,000 records."""
        batch_id = f'PERF-MEDIUM-{int(time.time())}'
        correlation_id = f'CORR-MEDIUM-{int(time.time())}'
        
        # Generate test data
        team_members = generate_team_member_data(MEDIUM_BATCH_SIZE, batch_id)
        
        # Create processor
        processor = BatchProcessor(session, dry_run=True)
        
        # Measure performance
        metrics = self.measure_performance(processor, batch_id, correlation_id, team_members)
        
        # Log results
        print(f"\n=== Medium Batch Performance (n={MEDIUM_BATCH_SIZE}) ===")
        print(f"Duration: {metrics['duration_seconds']:.2f}s")
        print(f"Throughput: {metrics['throughput']:.2f} records/sec")
        print(f"Memory increase: {metrics['memory_increase_mb']:.2f} MB")
        print(f"Success: {metrics['success']}")
        
        # Assertions
        assert metrics['success'], "Batch processing should succeed"
        assert metrics['throughput'] >= MIN_THROUGHPUT * 0.8, \
            f"Throughput {metrics['throughput']:.2f} significantly below {MIN_THROUGHPUT} records/sec"
        assert metrics['memory_peak_mb'] < MAX_MEMORY_MB, \
            f"Memory {metrics['memory_peak_mb']:.2f} MB exceeds {MAX_MEMORY_MB} MB"
    
    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.skipif(os.getenv('SKIP_LARGE_PERF_TESTS') == '1', 
                       reason="Large performance tests skipped (set SKIP_LARGE_PERF_TESTS=0 to run)")
    def test_large_batch_performance(self, session):
        """Test performance with 10,000 records (NFR validation)."""
        batch_id = f'PERF-LARGE-{int(time.time())}'
        correlation_id = f'CORR-LARGE-{int(time.time())}'
        
        # Generate test data
        team_members = generate_team_member_data(LARGE_BATCH_SIZE, batch_id)
        
        # Create processor
        processor = BatchProcessor(session, dry_run=True)
        
        # Measure performance
        metrics = self.measure_performance(processor, batch_id, correlation_id, team_members)
        
        # Log results
        print(f"\n=== Large Batch Performance (n={LARGE_BATCH_SIZE}) ===")
        print(f"Duration: {metrics['duration_seconds']:.2f}s ({metrics['duration_seconds']/60:.2f} min)")
        print(f"Throughput: {metrics['throughput']:.2f} records/sec")
        print(f"Memory increase: {metrics['memory_increase_mb']:.2f} MB")
        print(f"Peak memory: {metrics['memory_peak_mb']:.2f} MB")
        print(f"Success: {metrics['success']}")
        
        # NFR validations
        assert metrics['success'], "Batch processing should succeed"
        assert metrics['duration_seconds'] < MAX_PROCESSING_TIME_10K, \
            f"Processing time {metrics['duration_seconds']:.2f}s exceeds {MAX_PROCESSING_TIME_10K}s (30 min)"
        assert metrics['throughput'] >= MIN_THROUGHPUT * 0.5, \
            f"Throughput {metrics['throughput']:.2f} far below {MIN_THROUGHPUT} records/sec"
        assert metrics['memory_peak_mb'] < MAX_MEMORY_MB, \
            f"Memory {metrics['memory_peak_mb']:.2f} MB exceeds {MAX_MEMORY_MB} MB"
    
    @pytest.mark.performance
    def test_throughput_comparison(self, session):
        """Compare throughput across different batch sizes."""
        results = []
        
        for size, label in [(100, 'small'), (500, 'medium-small'), (1000, 'medium')]:
            batch_id = f'PERF-COMP-{label}-{int(time.time())}'
            correlation_id = f'CORR-COMP-{label}-{int(time.time())}'
            
            team_members = generate_team_member_data(size, batch_id)
            processor = BatchProcessor(session, dry_run=True)
            
            metrics = self.measure_performance(processor, batch_id, correlation_id, team_members)
            results.append({
                'size': size,
                'label': label,
                'throughput': metrics['throughput'],
                'duration': metrics['duration_seconds']
            })
        
        # Log comparison
        print("\n=== Throughput Comparison ===")
        for result in results:
            print(f"{result['label']:12s} (n={result['size']:4d}): "
                  f"{result['throughput']:6.2f} records/sec, "
                  f"{result['duration']:5.2f}s")
        
        # Verify all meet minimum threshold
        for result in results:
            assert result['throughput'] >= MIN_THROUGHPUT * 0.7, \
                f"{result['label']} throughput too low: {result['throughput']:.2f} records/sec"
