"""Skill availability router."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import verify_token
from app.api.schemas.team_member import BulkUpsertRequest, BulkUpsertResponse, UpsertSummary
from app.db.repositories.team_member_repository import TeamMemberRepository
from app.db.session import get_db

router = APIRouter(prefix="/team-members/skill-availability", tags=["skill-availability"])
logger = logging.getLogger(__name__)


@router.post("/bulk-upsert", response_model=BulkUpsertResponse, status_code=202)
async def bulk_upsert_skill_availability(
    request: BulkUpsertRequest,
    db: Session = Depends(get_db),
    token: dict = Depends(verify_token),
):
    """
    Bulk upsert team member skill availability data.

    This endpoint accepts batches of team member data including skills,
    allocations, and certifications. It implements idempotent upsert logic.
    """
    logger.info(f"Bulk upsert request received for batch_id={request.metadata.batch_id}")
    logger.info(f"Total team members: {len(request.team_members)}")
    
    repo = TeamMemberRepository(db)

    # Ensure default category exists
    try:
        logger.info("Ensuring default category exists")
        repo.ensure_default_category()
        logger.info("Default category ensured")
    except Exception as e:
        logger.error(f"Failed to ensure default category: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize repository: {str(e)}"
        )

    # Statistics
    team_members_inserted = 0
    team_members_updated = 0
    skills_inserted = 0
    skills_updated = 0
    allocations_inserted = 0
    allocations_updated = 0
    records_failed = 0

    try:
        for idx, member_data in enumerate(request.team_members):
            try:
                logger.info(f"Processing team member {idx+1}/{len(request.team_members)}: {member_data.team_member_id}")
                
                # Upsert team member
                was_created, member = repo.upsert_team_member(member_data)
                if was_created:
                    team_members_inserted += 1
                    logger.info(f"Created new team member: {member_data.team_member_id}")
                else:
                    team_members_updated += 1
                    logger.info(f"Updated existing team member: {member_data.team_member_id}")

                # Upsert skills
                if member_data.skills:
                    s_inserted, s_updated = repo.upsert_skills(
                        member_data.team_member_id, member_data.skills
                    )
                    skills_inserted += s_inserted
                    skills_updated += s_updated
                    logger.info(f"Upserted skills for {member_data.team_member_id}: {s_inserted} inserted, {s_updated} updated")

                # Upsert allocations
                if member_data.allocations:
                    a_inserted, a_updated = repo.upsert_allocations(
                        member_data.team_member_id, member_data.allocations
                    )
                    allocations_inserted += a_inserted
                    allocations_updated += a_updated
                    logger.info(f"Upserted allocations for {member_data.team_member_id}: {a_inserted} inserted, {a_updated} updated")

            except Exception as e:
                records_failed += 1
                # Log error but continue processing other records
                logger.error(
                    f"Error processing team member {member_data.team_member_id}: {str(e)}",
                    exc_info=True
                )

        # Commit all changes
        logger.info("Committing database changes")
        db.commit()
        logger.info("Database commit successful")

        # Create response summary
        summary = UpsertSummary(
            records_received=len(request.team_members),
            team_members_inserted=team_members_inserted,
            team_members_updated=team_members_updated,
            skills_inserted=skills_inserted,
            skills_updated=skills_updated,
            allocations_inserted=allocations_inserted,
            allocations_updated=allocations_updated,
            records_failed=records_failed,
            batch_id=request.metadata.batch_id,
            processed_at=datetime.utcnow(),
        )

        logger.info(f"Bulk upsert completed successfully for batch_id={request.metadata.batch_id}")
        
        return BulkUpsertResponse(
            status="ACCEPTED",
            message=f"Batch {request.metadata.batch_id} processed successfully",
            summary=summary,
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Critical error in bulk upsert: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during bulk upsert: {str(e)}"
        )
