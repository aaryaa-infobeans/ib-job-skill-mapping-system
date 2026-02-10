#!/bin/bash
#
# IB Job Skill Mapping System - Team Data Ingestion Runner
#
# This script wraps the Python ingestion module for scheduled execution.
# Features:
# - Loads environment variables from .env
# - Sets up timestamped logging
# - Propagates exit codes
# - Forwards CLI arguments to Python module
#
# Usage:
#   ./run_ingestion.sh [OPTIONS]
#   
# Options:
#   --dry-run          Run without persisting data
#   --retry-failed     Retry failed batches instead of ingestion
#   --log-level LEVEL  Set logging level (DEBUG, INFO, WARNING, ERROR)
#
# Examples:
#   ./run_ingestion.sh --dry-run
#   ./run_ingestion.sh --retry-failed --log-level DEBUG
#

set -euo pipefail  # Exit on error, undefined variable, or pipe failure

# ==============================================================================
# Configuration
# ==============================================================================

# Default configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
LOG_DIR="${LOG_DIR:-${PROJECT_ROOT}/logs/ingestion}"
PYTHON_BIN="${PYTHON_BIN:-python}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
LOG_FILE="${LOG_DIR}/ingestion_${TIMESTAMP}.log"

# ==============================================================================
# Functions
# ==============================================================================

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] $*" | tee -a "${LOG_FILE}"
}

setup_log_directory() {
    if [[ ! -d "${LOG_DIR}" ]]; then
        log "INFO" "Creating log directory: ${LOG_DIR}"
        mkdir -p "${LOG_DIR}"
    fi
}

load_environment() {
    if [[ -f "${ENV_FILE}" ]]; then
        log "INFO" "Loading environment variables from ${ENV_FILE}"
        # Export variables from .env, ignoring comments and empty lines
        set -a
        # shellcheck disable=SC1090
        source "${ENV_FILE}"
        set +a
    else
        log "WARN" "Environment file not found: ${ENV_FILE}"
        log "WARN" "Proceeding with existing environment variables"
    fi
}

verify_python() {
    if ! command -v "${PYTHON_BIN}" &> /dev/null; then
        log "ERROR" "Python binary not found: ${PYTHON_BIN}"
        log "ERROR" "Set PYTHON_BIN environment variable to specify Python path"
        return 1
    fi
    
    local python_version
    python_version=$("${PYTHON_BIN}" --version 2>&1)
    log "INFO" "Using Python: ${python_version}"
}

run_ingestion() {
    local exit_code=0
    
    log "INFO" "=============================================="
    log "INFO" "IB Job Skill Mapping - Team Data Ingestion"
    log "INFO" "=============================================="
    log "INFO" "Start time: $(date)"
    log "INFO" "Arguments: $*"
    log "INFO" "Log file: ${LOG_FILE}"
    log "INFO" "=============================================="
    
    # Change to project root for module imports
    cd "${PROJECT_ROOT}"
    
    # Run Python module with arguments, capturing stdout and stderr
    log "INFO" "Executing ingestion module..."
    
    if "${PYTHON_BIN}" -m app.cron.main "$@" 2>&1 | tee -a "${LOG_FILE}"; then
        exit_code=${PIPESTATUS[0]}
    else
        exit_code=${PIPESTATUS[0]}
    fi
    
    log "INFO" "=============================================="
    log "INFO" "Execution completed with exit code: ${exit_code}"
    log "INFO" "End time: $(date)"
    log "INFO" "=============================================="
    
    return "${exit_code}"
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    local exit_code=0
    
    # Setup logging
    setup_log_directory
    
    # Load environment variables
    load_environment
    
    # Verify Python is available
    if ! verify_python; then
        exit 1
    fi
    
    # Run ingestion with all arguments
    if run_ingestion "$@"; then
        exit_code=0
    else
        exit_code=$?
    fi
    
    # Exit with Python module's exit code
    exit "${exit_code}"
}

# Run main function with all script arguments
main "$@"
