# Requisition Resumption Cron Job

This document describes how to set up and manage the cron job that monitors for stuck requisition processing and resumes them from their last checkpoint.

## Overview

The resumption system consists of:
1.  **Repository Method**: `get_stuck_requisitions` identifies requests that have been in the `PROCESSING` state for more than 30 minutes.
2.  **Resumption Utility**: `src/app/ai/resumption.py` restores the state from the last successful checkpoint and completes the processing pipeline.
3.  **Cron Script**: `scripts/resume_stuck_requisitions.py` orchestrates the detection and resumption.

## Setup

### 1. Script Permissions
Ensure the script is executable:
```bash
chmod +x /var/www/html/ib-job-skill-mapping-system/scripts/resume_stuck_requisitions.py
```

### 2. Configure Cron
Add the following entry to your crontab (e.g., `crontab -e`) to run the monitor every 15 minutes:

```cron
# Run the requisition resumption monitor every 15 minutes
*/15 * * * * /usr/bin/python3 /var/www/html/ib-job-skill-mapping-system/scripts/resume_stuck_requisitions.py >> /var/www/html/ib-job-skill-mapping-system/logs/resumption_cron.log 2>&1
```

> [!NOTE]
> Ensure the python path and file paths are correct for your environment. If using a virtual environment, use the path to the python executable within that environment.

## Monitoring and Logs

- **Script Logs**: The script logs its activity to `requisition_resumption.log` in the script directory and also pipes output to the cron log specified in the crontab.
- **Audit Trail**: Resumption attempts are recorded as checkpoints in the `langgraph_checkpoints` table. Look for stages completed after a gap in time.

## Troubleshooting

### Requisition Still Stuck
If a requisition is resumed but gets stuck again at the same stage:
1.  Check `llm_request_log` for API errors or timeouts.
2.  Inspect the "error" checkpoint for that request ID in the database.
3.  Manually trigger the resumption script and watch the logs for real-time output.

### Script Fails to Connect to Database
Ensure the database credentials in your environment are correct and that the script has the necessary permissions to access the database.
