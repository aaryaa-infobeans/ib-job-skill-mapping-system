#!/bin/bash
#
# IB Job Skill Mapping System - Log Rotation Installation & Testing
#
# This script installs and tests the logrotate configuration.
# Run with sudo: sudo ./install_logrotate.sh
#

set -euo pipefail

# ==============================================================================
# Configuration
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGROTATE_CONFIG="${SCRIPT_DIR}/logrotate.d/ib-job-skill-ingestion"
LOGROTATE_DEST="/etc/logrotate.d/ib-job-skill-ingestion"
LOG_DIR="/var/log/ib-job-skill-ingestion"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ==============================================================================
# Functions
# ==============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_logrotate_installed() {
    if ! command -v logrotate &> /dev/null; then
        log_error "logrotate is not installed"
        log_error "Install it: sudo apt-get install logrotate (Debian/Ubuntu) or sudo yum install logrotate (RHEL/CentOS)"
        exit 1
    fi
    
    local version
    version=$(logrotate --version | head -n 1)
    log_info "Found logrotate: ${version}"
}

check_log_directory() {
    if [[ ! -d "${LOG_DIR}" ]]; then
        log_warn "Log directory does not exist: ${LOG_DIR}"
        log_info "Creating log directory..."
        mkdir -p "${LOG_DIR}"
        chown app:app "${LOG_DIR}"
        chmod 755 "${LOG_DIR}"
        log_info "Created ${LOG_DIR}"
    else
        log_info "Log directory exists: ${LOG_DIR}"
    fi
}

validate_config() {
    log_info "Validating logrotate configuration..."
    
    if [[ ! -f "${LOGROTATE_CONFIG}" ]]; then
        log_error "Configuration file not found: ${LOGROTATE_CONFIG}"
        exit 1
    fi
    
    # Test configuration syntax
    if logrotate -d "${LOGROTATE_CONFIG}" &> /tmp/logrotate_test.log; then
        log_info "Configuration syntax is valid"
    else
        log_error "Configuration has syntax errors:"
        cat /tmp/logrotate_test.log
        exit 1
    fi
}

install_config() {
    log_info "Installing logrotate configuration..."
    
    # Backup existing config if present
    if [[ -f "${LOGROTATE_DEST}" ]]; then
        backup_file="${LOGROTATE_DEST}.backup.$(date +%Y%m%d_%H%M%S)"
        log_warn "Backing up existing configuration to ${backup_file}"
        cp "${LOGROTATE_DEST}" "${backup_file}"
    fi
    
    # Copy new configuration
    cp "${LOGROTATE_CONFIG}" "${LOGROTATE_DEST}"
    chmod 644 "${LOGROTATE_DEST}"
    chown root:root "${LOGROTATE_DEST}"
    
    log_info "Configuration installed to ${LOGROTATE_DEST}"
}

test_dry_run() {
    log_info "Running dry-run test..."
    
    if logrotate -d "${LOGROTATE_DEST}" > /tmp/logrotate_dryrun.log 2>&1; then
        log_info "Dry-run test PASSED"
        log_info "Output:"
        grep -E "rotating|considering|running|skipping" /tmp/logrotate_dryrun.log | head -n 10
    else
        log_error "Dry-run test FAILED"
        cat /tmp/logrotate_dryrun.log
        exit 1
    fi
}

test_force_rotation() {
    log_info ""
    read -p "Force test rotation? This will rotate current logs. (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Forcing log rotation..."
        
        if logrotate -f "${LOGROTATE_DEST}" > /tmp/logrotate_force.log 2>&1; then
            log_info "Force rotation completed"
            
            # Show rotated files
            log_info "Rotated log files:"
            ls -lh "${LOG_DIR}"/*.gz 2>/dev/null | tail -n 5 || log_info "No compressed logs yet"
        else
            log_error "Force rotation failed"
            cat /tmp/logrotate_force.log
        fi
    fi
}

print_summary() {
    log_info ""
    log_info "=========================================="
    log_info "Log Rotation Configuration Summary"
    log_info "=========================================="
    log_info ""
    log_info "Configuration file: ${LOGROTATE_DEST}"
    log_info "Log directory: ${LOG_DIR}"
    log_info "Rotation schedule: Daily"
    log_info "Retention period: 30 days"
    log_info "Compression: Yes (gzip, delayed by 1 day)"
    log_info "Permissions: 640 (rw-r-----) app:app"
    log_info ""
    log_info "Manual Commands:"
    log_info "  Test configuration:  sudo logrotate -d ${LOGROTATE_DEST}"
    log_info "  Force rotation:      sudo logrotate -f ${LOGROTATE_DEST}"
    log_info "  View logs:           ls -lh ${LOG_DIR}"
    log_info "  View compressed:     ls -lh ${LOG_DIR}/*.gz"
    log_info "  Check log size:      du -sh ${LOG_DIR}"
    log_info ""
    log_info "Logrotate runs daily via cron (usually in /etc/cron.daily/logrotate)"
    log_info "=========================================="
}

# ==============================================================================
# Main Installation
# ==============================================================================

main() {
    log_info "=========================================="
    log_info "IB Job Skill Mapping - Logrotate Setup"
    log_info "=========================================="
    log_info ""
    
    # Pre-flight checks
    check_root
    check_logrotate_installed
    check_log_directory
    
    # Installation
    validate_config
    install_config
    test_dry_run
    
    # Optional force rotation
    test_force_rotation
    
    # Success
    log_info ""
    log_info "${GREEN}Installation Complete!${NC}"
    print_summary
}

# Run main
main "$@"
