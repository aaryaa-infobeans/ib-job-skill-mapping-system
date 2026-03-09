#!/usr/bin/env python3
"""
Populate team_member_allocation table with random project assignments for existing candidates.
"""

import os
import sys
import random
import logging
from datetime import date, timedelta
from typing import List

# Add src to path
sys.path.insert(0, "src")

from app.db.session import SessionLocal
from app.db.models.models import TeamMember, TeamMemberAllocation
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Sample Projects
PROJECTS = [
    "PROJ-ALPHA-101",
    "PROJ-BETA-202",
    "PROJ-GAMMA-303",
    "INTERNAL-BENCH",
    "SUPPORT-SQUAD-01",
    "INNOVATION-LAB-X"
]

def fill_random_allocations():
    db = SessionLocal()
    try:
        # Get all team members
        team_members = db.query(TeamMember).all()
        logger.info(f"Retrieved {len(team_members)} team members.")

        if not team_members:
            logger.warning("No team members found in the database. Run enrichment script first.")
            return

        # Clear existing allocations to start fresh
        db.execute(text("DELETE FROM team_member_allocation"))
        db.commit()
        logger.info("Cleared existing allocations.")

        total_allocations = 0
        for tm in team_members:
            # Assign 1 or 2 random projects
            num_projects = random.randint(1, 2)
            selected_projects = random.sample(PROJECTS, num_projects)
            
            for project_id in selected_projects:
                # Random allocation details
                # If 2 projects, split 50/50 or similar, otherwise 100
                if num_projects == 2:
                    alloc_pct = 50.0
                else:
                    alloc_pct = random.choice([75.0, 100.0])

                start_date = date.today() - timedelta(days=random.randint(30, 365))
                end_date = date.today() + timedelta(days=random.randint(30, 365))
                billable = random.choice([True, False])
                
                allocation = TeamMemberAllocation(
                    team_member_id=tm.team_member_id,
                    project_id=project_id,
                    allocation_percentage=alloc_pct,
                    start_date=start_date,
                    end_date=end_date,
                    billable=billable,
                    is_deleted=False
                )
                db.add(allocation)
                total_allocations += 1
            
            # Commit every 10 members
            if total_allocations % 20 == 0:
                db.commit()

        db.commit()
        logger.info(f"✅ Successfully created {total_allocations} random allocations for {len(team_members)} team members.")

    except Exception as e:
        logger.error(f"❌ Error filling allocations: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fill_random_allocations()
