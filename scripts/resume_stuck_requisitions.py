#!/usr/bin/env python3
"""Cron script to detect and resume stuck requisition processing."""

import logging
import sys
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Configure logging early to capture module initialization logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('requisition_resumption.log')
    ]
)
logger = logging.getLogger("resumption_cron")

from app.db.session import SessionLocal
from app.db.repositories.requisition_repository import RequisitionRepository
from app.ai.resumption import resume_requisition

def main():
    logger.info("Starting resumption cron job")
    db = SessionLocal()
    try:
        repo = RequisitionRepository(db)
        
        # Find requisitions stuck for more than 30 minutes
        stuck_reqs = repo.get_stuck_requisitions(timeout_minutes=30)
        
        if not stuck_reqs:
            logger.info("No stuck requisitions found")
            return

        logger.info(f"Found {len(stuck_reqs)} stuck requisition(s)")
        
        for req in stuck_reqs:
            logger.info(f"Resuming requisition {req.request_id} (Correlation: {req.correlation_id})")
            try:
                result = resume_requisition(req.request_id, db)
                if result:
                    logger.info(f"Successfully resumed requisition {req.request_id}")
                else:
                    logger.error(f"Failed to resume requisition {req.request_id}")
            except Exception as e:
                logger.exception(f"Error resuming requisition {req.request_id}: {str(e)}")
                
    except Exception as e:
        logger.exception(f"Critical error in resumption cron job: {str(e)}")
    finally:
        db.close()
        logger.info("Resumption cron job finished")

if __name__ == "__main__":
    main()
