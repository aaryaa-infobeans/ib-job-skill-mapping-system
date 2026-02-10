#!/bin/bash
#
# IB Job Skill Mapping System - Cron Installation Script
#
# This script installs the cron configuration for team data ingestion.
# Run with sudo: sudo ./install_cron.sh
#
# Prerequisites:
# - Application deployed to /opt/ib-job-skill-mapping-system
# - Service account 'app' created
# - Python environment configured
#

set -euo pipefail

# ==============================================================================
# Configuration
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CRON_FILE="${SCRIPT_DIR}/cron.d/ib-job-skill-ingestion"
CRON_DEST="/etc/cron.d/ib-job-skill-ingestion"
LOG_DIR="/var/log/ib-job-skill-ingestion"
APP_USER="app"
APP_GROUP="app"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

check_user_exists() {
    if ! id "${APP_USER}" &>/dev/null; then
        log_error "User '${APP_USER}' does not exist"
        log_error "Create the user first: sudo useradd -r -s /bin/bash ${APP_USER}"
        exit 1
    fi
    log_info "User '${APP_USER}' exists"
}

check_project_exists() {
    if [[ ! -d "${PROJECT_ROOT}" ]]; then
        log_error "Project directory not found: ${PROJECT_ROOT}"
        log_error "Deploy the application first"
        exit 1
    fi
    log_info "Project directory found: ${PROJECT_ROOT}"
}

create_log_directory() {
    log_info "Creating log directory: ${LOG_DIR}"
    
    if [[ ! -d "${LOG_DIR}" ]]; then
        mkdir -p "${LOG_DIR}"
        log_info "Created ${LOG_DIR}"
    else
        log_warn "Log directory already exists"
    fi
    
    # Set ownership and permissions
    chown "${APP_USER}:${APP_GROUP}" "${LOG_DIR}"
    chmod 755 "${LOG_DIR}"
    
    log_info "Set permissions: ${APP_USER}:${APP_GROUP} 755"
}

validate_cron_file() {
    log_info "Validating cron file: ${CRON_FILE}"
    
    if [[ ! -f "${CRON_FILE}" ]]; then
        log_error "Cron file not found: ${CRON_FILE}"
        exit 1
    fi
    
    # Check for common cron syntax issues
    if ! grep -q '^[0-9*]' "${CRON_FILE}"; then
        log_warn "Cron file may not contain valid cron entries"
    fi
    
    log_info "Cron file validated"
}

install_cron_file() {
    log_info "Installing cron file to ${CRON_DEST}"
    
    # Backup existing cron file if it exists
    if [[ -f "${CRON_DEST}" ]]; then
        backup_file="${CRON_DEST}.backup.$(date +%Y%m%d_%H%M%S)"
        log_warn "Backing up existing cron file to ${backup_file}"
        cp "${CRON_DEST}" "${backup_file}"
    fi
    
    # Copy new cron file
    cp "${CRON_FILE}" "${CRON_DEST}"
    
    # Set correct permissions (must be 644 for /etc/cron.d files)
    chmod 644 "${CRON_DEST}"
    chown root:root "${CRON_DEST}"
    
    log_info "Cron file installed successfully"
}

verify_cron_installation() {
    log_info "Verifying cron installation..."
    
    if [[ -f "${CRON_DEST}" ]]; then
        log_info "Cron file exists: ${CRON_DEST}"
        
        # Display the installed cron jobs
        log_info "Installed cron jobs:"
        grep -v '^#' "${CRON_DEST}" | grep -v '^$' || log_warn "No active cron jobs found"
    else
        log_error "Cron file not found after installation: ${CRON_DEST}"
        exit 1
    fi
}

test_dry_run() {
    log_info "Testing dry run execution..."
    
    # Try to run as the app user with dry-run flag
    if sudo -u "${APP_USER}" "${PROJECT_ROOT}/scripts/run_ingestion.sh" --dry-run; then
        log_info "Dry run test PASSED"
    else
        exit_code=$?
        log_warn "Dry run test completed with exit code: ${exit_code}"
        log_warn "This may be expected if environment is not fully configured"
    fi
}

print_next_execution() {
    log_info "Next scheduled execution:"
    
    # Extract cron schedule from file (first uncommented line)
    cron_schedule=$(grep -v '^#' "${CRON_DEST}" | grep -v '^$' | head -n 1 | awk '{print $1, $2, $3, $4, $5}')
    
    if [[ -n "${cron_schedule}" ]]; then
        log_info "Schedule: ${cron_schedule} (minute hour day month weekday)"
        log_info "User: ${APP_USER}"
        log_info "Command: /opt/ib-job-skill-mapping-system/scripts/run_ingestion.sh"
        log_info ""
        log_info "Logs will be written to: ${LOG_DIR}"
    else
        log_warn "Could not determine cron schedule"
    fi
}

print_manual_commands() {
    log_info ""
    log_info "=========================================="
    log_info "Manual Execution Commands:"
    log_info "=========================================="
    log_info ""
    log_info "Run ingestion manually:"
    log_info "  sudo -u ${APP_USER} ${PROJECT_ROOT}/scripts/run_ingestion.sh"
    log_info ""
    log_info "Run in dry-run mode:"
    log_info "  sudo -u ${APP_USER} ${PROJECT_ROOT}/scripts/run_ingestion.sh --dry-run"
    log_info ""
    log_info "Retry failed batches:"
    log_info "  sudo -u ${APP_USER} ${PROJECT_ROOT}/scripts/run_ingestion.sh --retry-failed"
    log_info ""
    log_info "View logs:"
    log_info "  tail -f ${LOG_DIR}/ingestion_*.log"
    log_info ""
    log_info "Remove cron job:"
    log_info "  sudo rm ${CRON_DEST}"
    log_info ""
    log_info "=========================================="
}

# ==============================================================================
# Main Installation
# ==============================================================================

main() {
    log_info "=========================================="
    log_info "IB Job Skill Mapping - Cron Installation"
    log_info "=========================================="
    log_info ""
    
    # Pre-flight checks
    check_root
    check_user_exists
    check_project_exists
    
    # Installation steps
    create_log_directory
    validate_cron_file
    install_cron_file
    verify_cron_installation
    
    # Optional test
    log_info ""
    read -p "Run dry-run test? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        test_dry_run
    fi
    
    # Success
    log_info ""
    log_info "=========================================="
    log_info "${GREEN}Installation Complete!${NC}"
    log_info "=========================================="
    print_next_execution
    print_manual_commands
}

# Run main function
main "$@"
