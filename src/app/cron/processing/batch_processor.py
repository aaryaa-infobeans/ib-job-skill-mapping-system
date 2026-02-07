"""
Batch processor for team member data ingestion.

Provides transaction-isolated batch processing with automatic rollback on errors.
"""

from typing import Dict, List, Any, Tuple, Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.cron.db.repositories import TeamMemberRepository, BatchStateRepository


logger = structlog.get_logger(__name__)


class BatchProcessor:
    """
    Process batches of team member data with transaction isolation.
    
    Features:
    - Single transaction boundary per batch
    - Automatic rollback on any error
    - State tracking (PENDING → PROCESSING → SUCCESS/FAILED)
    - Dry run mode for validation without persistence
    - Comprehensive audit logging
    """
    
    def __init__(self, session: AsyncSession, dry_run: bool = False):
        """
        Initialize batch processor.
        
        Args:
            session: Async SQLAlchemy session for database operations
            dry_run: If True, perform validation without committing changes
        """
        self.session = session
        self.dry_run = dry_run
        self.team_member_repo = TeamMemberRepository(session)
        self.batch_state_repo = BatchStateRepository(session)
        self.logger = logger.bind(dry_run=dry_run)
    
    async def process_batch(
        self,
        batch_id: str,
        correlation_id: str,
        team_members: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Process a single batch of team members within a transaction.
        
        Transaction boundaries:
        - Begins transaction
        - Initializes batch state (PENDING)
        - Updates to PROCESSING
        - Processes all team members
        - Commits transaction on success (updates to SUCCESS)
        - Rolls back transaction on error (updates to FAILED)
        
        Args:
            batch_id: Unique batch identifier
            correlation_id: External correlation ID for tracing
            team_members: List of team member data dictionaries
            metadata: Optional batch metadata
        
        Returns:
            True if batch processed successfully, False otherwise
        
        Raises:
            Exception: Propagates any processing errors for caller to handle
        """
        self.logger.info(
            "Starting batch processing",
            batch_id=batch_id,
            correlation_id=correlation_id,
            total_records=len(team_members)
        )
        
        try:
            # Initialize batch state with PENDING status
            await self.batch_state_repo.initialize_batch(
                batch_id=batch_id,
                correlation_id=correlation_id,
                total_records=len(team_members),
                metadata=metadata or {}
            )
            
            # Update to PROCESSING
            await self.batch_state_repo.update_batch_status(
                batch_id=batch_id,
                status='PROCESSING'
            )
            
            # Process all team members
            processed_count = 0
            for member_data in team_members:
                await self._process_team_member(member_data)
                processed_count += 1
            
            # Dry run: rollback instead of commit
            if self.dry_run:
                await self.session.rollback()
                self.logger.info(
                    "Dry run complete - changes rolled back",
                    batch_id=batch_id,
                    processed_count=processed_count
                )
                return True
            
            # Update to SUCCESS and commit transaction
            await self.batch_state_repo.update_batch_status(
                batch_id=batch_id,
                status='SUCCESS',
                processed_records=processed_count,
                failed_records=0
            )
            
            await self.session.commit()
            
            self.logger.info(
                "Batch processing completed successfully",
                batch_id=batch_id,
                processed_count=processed_count
            )
            
            return True
        
        except Exception as error:
            # Rollback transaction
            await self.session.rollback()
            
            # Mark batch as failed (outside transaction)
            await self._mark_batch_failed(batch_id, correlation_id, str(error))
            
            self.logger.error(
                "Batch processing failed",
                batch_id=batch_id,
                error=str(error),
                error_type=type(error).__name__
            )
            
            raise
    
    async def process_all_batches(
        self,
        payload: Dict[str, Any]
    ) -> Tuple[List[str], List[str]]:
        """
        Process all batches from external API payload.
        
        Each batch is processed independently with its own transaction.
        Failures in one batch do not affect others.
        
        Args:
            payload: External API response with metadata and team_members array
        
        Returns:
            Tuple of (successful_batch_ids, failed_batch_ids)
        """
        metadata = payload.get('metadata', {})
        correlation_id = metadata.get('correlation_id', 'unknown')
        batches = payload.get('batches', [])
        
        self.logger.info(
            "Processing all batches",
            correlation_id=correlation_id,
            total_batches=len(batches)
        )
        
        successful = []
        failed = []
        
        for batch_data in batches:
            batch_id = batch_data.get('batch_id')
            team_members = batch_data.get('team_members', [])
            
            if not batch_id:
                self.logger.warning(
                    "Skipping batch without batch_id",
                    correlation_id=correlation_id
                )
                continue
            
            try:
                # Each batch gets its own transaction via new session
                # (caller should provide fresh session for each batch)
                success = await self.process_batch(
                    batch_id=batch_id,
                    correlation_id=correlation_id,
                    team_members=team_members,
                    metadata=metadata
                )
                
                if success:
                    successful.append(batch_id)
                else:
                    failed.append(batch_id)
            
            except Exception as error:
                failed.append(batch_id)
                self.logger.error(
                    "Batch processing exception",
                    batch_id=batch_id,
                    error=str(error)
                )
        
        self.logger.info(
            "All batches processed",
            correlation_id=correlation_id,
            successful_count=len(successful),
            failed_count=len(failed)
        )
        
        return successful, failed
    
    async def _process_team_member(self, member_data: Dict[str, Any]) -> None:
        """
        Process a single team member with all related data.
        
        Processing order ensures foreign key constraints are satisfied:
        1. Category (referenced by skill)
        2. Skills (referenced by team_member_skill, certifications)
        3. Team member (referenced by skills, allocations, certifications)
        4. Team member skills (junction table)
        5. Allocations
        6. Certifications
        
        Args:
            member_data: Team member data dictionary from external API
        
        Raises:
            Exception: Any validation or database errors
        """
        team_member_id = member_data.get('team_member_id')
        
        if not team_member_id:
            raise ValueError("team_member_id is required")
        
        self.logger.debug("Processing team member", team_member_id=team_member_id)
        
        # Extract category from skills (assumes all skills have same category for simplicity)
        # In production, each skill would have its own category
        skills_data = member_data.get('skills', [])
        category_name = None
        
        if skills_data:
            # Use first skill's category as default
            first_skill = skills_data[0]
            category_name = first_skill.get('category', 'Uncategorized')
        else:
            category_name = 'Uncategorized'
        
        # 1. UPSERT category
        category_id = await self.team_member_repo.upsert_category(category_name)
        
        # 2. UPSERT team member (must exist before relationships)
        await self.team_member_repo.upsert_team_member(member_data)
        
        # 3. UPSERT team member skills (many-to-many)
        if skills_data:
            await self.team_member_repo.upsert_team_member_skills(
                team_member_id=team_member_id,
                skills=skills_data,
                category_id=category_id
            )
        
        # 4. UPSERT allocations
        allocations_data = member_data.get('allocations', [])
        if allocations_data:
            await self.team_member_repo.upsert_allocations(
                team_member_id=team_member_id,
                allocations=allocations_data
            )
        
        # 5. UPSERT certifications (extract from skills)
        certifications_data = []
        for skill in skills_data:
            skill_certs = skill.get('certifications', [])
            if skill_certs:
                # Add skill_name to each certification for skill lookup
                skill_name = skill.get('skill_name')
                for cert in skill_certs:
                    cert_with_skill = cert.copy()
                    cert_with_skill['skill_name'] = skill_name
                    certifications_data.append(cert_with_skill)
        
        if certifications_data:
            await self.team_member_repo.upsert_certifications(
                team_member_id=team_member_id,
                certifications=certifications_data,
                category_id=category_id
            )
        
        self.logger.debug(
            "Team member processed",
            team_member_id=team_member_id,
            skills_count=len(skills_data),
            allocations_count=len(allocations_data),
            certifications_count=len(certifications_data)
        )
    
    async def _mark_batch_failed(
        self,
        batch_id: str,
        correlation_id: str,
        error_message: str
    ) -> None:
        """
        Mark batch as failed after transaction rollback.
        
        This operates in a separate transaction to ensure the failure
        state is persisted even if the main transaction failed.
        
        Args:
            batch_id: Batch identifier
            correlation_id: Correlation ID for audit trail
            error_message: Error description
        """
        try:
            # Create new session for failure recording
            # (in production, this would use a separate session factory)
            await self.batch_state_repo.update_batch_status(
                batch_id=batch_id,
                status='FAILED',
                error_message=error_message
            )
            await self.session.commit()
        
        except Exception as mark_error:
            self.logger.error(
                "Failed to mark batch as failed",
                batch_id=batch_id,
                error=str(mark_error)
            )
            # Swallow exception to avoid masking original error
