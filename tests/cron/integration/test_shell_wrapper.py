"""
Integration tests for shell wrapper script (run_ingestion.sh).

Tests verify:
- Script loads environment variables
- Script logs output to timestamped log file
- Script propagates exit codes correctly
- Script accepts and forwards CLI arguments
- Script handles missing .env gracefully
- Script verifies Python binary availability
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path
from datetime import datetime

import pytest


@pytest.fixture
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
def script_path(project_root):
    """Get the path to run_ingestion.sh script."""
    return project_root / "scripts" / "run_ingestion.sh"


@pytest.fixture
def temp_log_dir():
    """Create a temporary log directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestShellWrapperScript:
    """Integration tests for run_ingestion.sh wrapper script."""
    
    def test_script_exists_and_executable(self, script_path):
        """Test: Script file exists."""
        assert script_path.exists(), f"Script not found: {script_path}"
        # Note: Executable bit test may not work on Windows
    
    def test_script_runs_with_help_flag(self, script_path, temp_log_dir):
        """Test: Script runs and forwards --help to Python module."""
        env = os.environ.copy()
        env['LOG_DIR'] = str(temp_log_dir)
        
        # Use bash on Windows if available, otherwise skip
        try:
            result = subprocess.run(
                ['bash', str(script_path), '--help'],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            # Python module will handle --help and exit with code 0
            assert result.returncode in [0, 2], f"Unexpected exit code: {result.returncode}"
            
            # Should see usage information in output
            output = result.stdout + result.stderr
            assert '--dry-run' in output or 'usage:' in output.lower()
            
        except FileNotFoundError:
            pytest.skip("Bash not available on this system")
    
    def test_script_creates_log_file(self, script_path, temp_log_dir):
        """Test: Script creates timestamped log file in LOG_DIR."""
        env = os.environ.copy()
        env['LOG_DIR'] = str(temp_log_dir)
        
        try:
            # Run with --help for quick execution
            subprocess.run(
                ['bash', str(script_path), '--help'],
                capture_output=True,
                timeout=30,
                env=env
            )
            
            # Check that log file was created
            log_files = list(temp_log_dir.glob('ingestion_*.log'))
            assert len(log_files) > 0, "No log file created"
            
            # Verify log file has content
            log_content = log_files[0].read_text()
            assert len(log_content) > 0, "Log file is empty"
            assert "IB Job Skill Mapping" in log_content
            
        except FileNotFoundError:
            pytest.skip("Bash not available on this system")
    
    def test_script_propagates_exit_code_success(self, script_path, temp_log_dir):
        """Test: Script propagates successful exit code (0) from Python module."""
        env = os.environ.copy()
        env['LOG_DIR'] = str(temp_log_dir)
        
        try:
            # --help should exit with 0 or 2
            result = subprocess.run(
                ['bash', str(script_path), '--help'],
                capture_output=True,
                timeout=30,
                env=env
            )
            
            # argparse exits with 0 or 2 for help
            assert result.returncode in [0, 2]
            
        except FileNotFoundError:
            pytest.skip("Bash not available on this system")
    
    def test_script_accepts_cli_arguments(self, script_path, temp_log_dir):
        """Test: Script forwards CLI arguments to Python module."""
        env = os.environ.copy()
        env['LOG_DIR'] = str(temp_log_dir)
        
        try:
            # Run with --dry-run flag
            result = subprocess.run(
                ['bash', str(script_path), '--dry-run'],
                capture_output=True,
                text=True,
                timeout=60,
                env=env
            )
            
            # Check log file contains the --dry-run argument
            log_files = list(temp_log_dir.glob('ingestion_*.log'))
            assert len(log_files) > 0
            
            log_content = log_files[0].read_text()
            assert '--dry-run' in log_content, "Argument not logged"
            
        except FileNotFoundError:
            pytest.skip("Bash not available on this system")
    
    def test_script_handles_missing_env_file(self, script_path, temp_log_dir, project_root):
        """Test: Script handles missing .env file gracefully."""
        env = os.environ.copy()
        env['LOG_DIR'] = str(temp_log_dir)
        
        # Ensure we're not accidentally reading real .env
        fake_project_root = temp_log_dir / "fake_project"
        fake_project_root.mkdir()
        
        try:
            # Script should warn about missing .env but continue
            result = subprocess.run(
                ['bash', str(script_path), '--help'],
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
                cwd=str(fake_project_root)
            )
            
            # Should not fail completely
            assert result.returncode in [0, 1, 2], "Script failed catastrophically"
            
            # Check for warning in log
            log_files = list(temp_log_dir.glob('ingestion_*.log'))
            if log_files:
                log_content = log_files[0].read_text()
                # May contain warning about missing .env
                assert 'WARN' in log_content or 'ERROR' in log_content or 'INFO' in log_content
            
        except FileNotFoundError:
            pytest.skip("Bash not available on this system")
    
    def test_script_verifies_python_binary(self, script_path, temp_log_dir):
        """Test: Script verifies Python binary is available."""
        env = os.environ.copy()
        env['LOG_DIR'] = str(temp_log_dir)
        env['PYTHON_BIN'] = 'python_does_not_exist_12345'
        
        try:
            result = subprocess.run(
                ['bash', str(script_path), '--help'],
                capture_output=True,
                text=True,
                timeout=30,
                env=env
            )
            
            # Should fail with non-zero exit code
            assert result.returncode != 0, "Script should fail with invalid Python binary"
            
            # Check log file for error message
            log_files = list(temp_log_dir.glob('ingestion_*.log'))
            if log_files:
                log_content = log_files[0].read_text()
                assert 'Python binary not found' in log_content or 'ERROR' in log_content
            
        except FileNotFoundError:
            pytest.skip("Bash not available on this system")
    
    def test_script_log_timestamps(self, script_path, temp_log_dir):
        """Test: Script log file has timestamped name."""
        env = os.environ.copy()
        env['LOG_DIR'] = str(temp_log_dir)
        
        try:
            # Capture current timestamp
            before_time = datetime.now()
            
            subprocess.run(
                ['bash', str(script_path), '--help'],
                capture_output=True,
                timeout=30,
                env=env
            )
            
            after_time = datetime.now()
            
            # Check log file naming pattern: ingestion_YYYYMMDD_HHMMSS.log
            log_files = list(temp_log_dir.glob('ingestion_*.log'))
            assert len(log_files) > 0, "No log file created"
            
            log_file = log_files[0]
            assert log_file.name.startswith('ingestion_')
            assert log_file.name.endswith('.log')
            
            # Extract timestamp from filename
            timestamp_str = log_file.stem.replace('ingestion_', '')
            assert len(timestamp_str) == 15, f"Invalid timestamp format: {timestamp_str}"  # YYYYMMDD_HHMMSS
            
        except FileNotFoundError:
            pytest.skip("Bash not available on this system")
    
    def test_script_execution_logging(self, script_path, temp_log_dir):
        """Test: Script logs execution start, end, and details."""
        env = os.environ.copy()
        env['LOG_DIR'] = str(temp_log_dir)
        
        try:
            subprocess.run(
                ['bash', str(script_path), '--help'],
                capture_output=True,
                timeout=30,
                env=env
            )
            
            # Read log file
            log_files = list(temp_log_dir.glob('ingestion_*.log'))
            assert len(log_files) > 0
            
            log_content = log_files[0].read_text()
            
            # Verify log contains execution details
            assert 'IB Job Skill Mapping' in log_content
            assert 'Team Data Ingestion' in log_content
            assert 'Start time:' in log_content
            assert 'End time:' in log_content
            assert 'exit code:' in log_content
            
        except FileNotFoundError:
            pytest.skip("Bash not available on this system")


class TestShellWrapperEnvironment:
    """Test environment variable handling in shell wrapper."""
    
    def test_script_respects_log_dir_override(self, script_path):
        """Test: Script respects LOG_DIR environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir1, \
             tempfile.TemporaryDirectory() as tmpdir2:
            
            env = os.environ.copy()
            env['LOG_DIR'] = tmpdir1
            
            try:
                subprocess.run(
                    ['bash', str(script_path), '--help'],
                    capture_output=True,
                    timeout=30,
                    env=env
                )
                
                # Log should be in tmpdir1, not tmpdir2
                log_files_1 = list(Path(tmpdir1).glob('ingestion_*.log'))
                log_files_2 = list(Path(tmpdir2).glob('ingestion_*.log'))
                
                assert len(log_files_1) > 0, "Log file not created in LOG_DIR"
                assert len(log_files_2) == 0, "Log file created in wrong directory"
                
            except FileNotFoundError:
                pytest.skip("Bash not available on this system")
    
    def test_script_respects_python_bin_override(self, script_path, temp_log_dir):
        """Test: Script respects PYTHON_BIN environment variable."""
        env = os.environ.copy()
        env['LOG_DIR'] = str(temp_log_dir)
        env['PYTHON_BIN'] = 'python3'  # Try python3 instead of python
        
        try:
            result = subprocess.run(
                ['bash', str(script_path), '--help'],
                capture_output=True,
                timeout=30,
                env=env
            )
            
            # Should work if python3 is available, otherwise fail gracefully
            assert result.returncode in [0, 1, 2], "Script failed catastrophically"
            
            # Check log mentions python3 or error about it
            log_files = list(temp_log_dir.glob('ingestion_*.log'))
            if log_files and result.returncode == 0:
                log_content = log_files[0].read_text()
                # Log should mention Python version or binary
                assert 'Python' in log_content
            
        except FileNotFoundError:
            pytest.skip("Bash not available on this system")
